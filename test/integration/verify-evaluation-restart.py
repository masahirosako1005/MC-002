"""Probe app/gateway restart on the dedicated 8082 evaluation stack only.

Default is a read-only preflight. --execute is used only after coordinating with
browser evaluation. Never inspect/mount/stop the production 8080/8081 services.
"""
import argparse
import hashlib
import json
import subprocess
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
PROJECT = "kou-eval-ev02"
VOLUME = PROJECT + "_community-data"
BASE = "http://127.0.0.1:8082"
COMPOSE = ["docker", "compose", "-p", PROJECT, "-f", str(ROOT / "compose.yaml"),
           "-f", str(ROOT / "test/fixtures/ev02-compose.yaml")]


def command(args, timeout=30):
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError("Evaluation container command failed")
    return result.stdout.strip()


def inspect_field(cid, expression):
    return json.loads(command(["docker", "inspect", "--format", "{{json " + expression + "}}", cid]))


def preflight():
    containers = {}
    for role in ("app", "gateway"):
        cid = command(COMPOSE + ["ps", "-q", role])
        if not cid or len(cid.splitlines()) != 1:
            raise RuntimeError("Exactly one evaluation container per role is required")
        labels = inspect_field(cid, ".Config.Labels")
        if labels.get("com.docker.compose.project") != PROJECT or labels.get("com.docker.compose.service") != role:
            raise RuntimeError("Container project/role mismatch")
        ports = inspect_field(cid, ".NetworkSettings.Ports") or {}
        bindings = [item for values in ports.values() if values for item in values]
        if role == "gateway":
            if not bindings or any(item.get("HostPort") != "8082" or item.get("HostIp") != "127.0.0.1" for item in bindings):
                raise RuntimeError("Only loopback evaluation port 8082 is permitted")
        elif bindings:
            raise RuntimeError("Evaluation app must not publish a host port")
        mounts = inspect_field(cid, ".Mounts")
        data = [item for item in mounts if item.get("Destination") == "/app/data"]
        if role == "app" and (len(data) != 1 or data[0].get("Type") != "volume" or data[0].get("Name") != VOLUME):
            raise RuntimeError("Evaluation data volume mismatch")
        if any(item.get("Type") == "volume" and item.get("Name") != VOLUME for item in mounts):
            raise RuntimeError("Unexpected named volume attached")
        containers[role] = cid
    labels = json.loads(command(["docker", "volume", "inspect", "--format", "{{json .Labels}}", VOLUME]))
    if labels.get("com.docker.compose.project") != PROJECT:
        raise RuntimeError("Evaluation volume ownership mismatch")
    return containers


def data(response, expected=200):
    if response.status_code != expected:
        raise RuntimeError("Evaluation API status mismatch")
    return response.json()


def login(client, username):
    result = data(client.post(BASE + "/api/login", json={"username": username, "password": username + "-local-2026"}))
    client.headers["X-CSRF-Token"] = result["csrf_token"]


def state(client):
    return data(client.get(BASE + "/api/me/resume-state"))


def value_only(value):
    return {key: item for key, item in value.items() if key != "version"}


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def wait_health():
    deadline = time.monotonic() + 60
    with httpx.Client(timeout=3, trust_env=False) as client:
        while time.monotonic() < deadline:
            try:
                if client.get(BASE + "/api/health").status_code == 200:
                    return
            except httpx.RequestError:
                pass
            time.sleep(0.5)
    raise RuntimeError("Evaluation service did not become healthy")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    preflight()
    if not args.execute:
        print(json.dumps({"preflight_passed": True, "executed": False}))
        return
    output = ROOT / "artifacts/storage"
    output.mkdir(parents=True, exist_ok=True)
    checks = {"evaluation_port_project_volume_guard": True}
    report = {"executed_at": datetime.now(UTC).isoformat(), "passed": False, "checks": checks,
              "scope": "Dedicated evaluation app/gateway restart; production untouched",
              "limits": ["Not an OS restart or power-loss test", "Synthetic evaluation data only",
                         "Original field values restored through API; version advances normally"]}
    clients = [httpx.Client(headers={"Origin": BASE}, timeout=10, trust_env=False) for _ in range(3)]
    owner, other, fresh = clients
    original = saved = None
    try:
        login(owner, "aoi")
        login(other, "ren")
        original, other_before = state(owner), state(other)
        marker = "evaluation-restart-" + uuid.uuid4().hex
        wanted = dict(original, page="journal", community_id=None, circle_id=None,
                      filters={"query": marker, "category": "", "duration": "all", "schedule": "all", "area": ""})
        saved = data(owner.put(BASE + "/api/me/resume-state", json=wanted))
        checks["synthetic_state_saved"] = saved["filters"]["query"] == marker
        report["saved_state_sha256"] = fingerprint(saved)
        before = preflight()  # Recheck immediately before any restart.
        starts_before = {role: inspect_field(cid, ".State.StartedAt") for role, cid in before.items()}
        command(COMPOSE + ["restart", "app", "gateway"], timeout=120)
        wait_health()
        after = preflight()
        checks["both_containers_restarted"] = all(inspect_field(after[role], ".State.StartedAt") != starts_before[role] for role in before)
        checks["same_cookie_token_restores_owner_state"] = state(owner) == saved
        login(fresh, "aoi")
        checks["new_login_restores_owner_state"] = state(fresh) == saved
        checks["other_account_unchanged_and_marker_private"] = state(other) == other_before and marker not in json.dumps(state(other))
        checks["same_token_remains_valid_after_separate_login"] = state(owner) == saved
        if not all(checks.values()):
            raise AssertionError("Evaluation restart checks failed")
        report["passed"] = True
    except Exception as error:
        report["failure_type"] = type(error).__name__
    finally:
        if original is not None and saved is not None:
            try:
                current = state(owner)
                if current != saved:
                    raise RuntimeError("Unexpected concurrent resume change; restoration withheld")
                restored = data(owner.put(BASE + "/api/me/resume-state", json=dict(original, version=current["version"])))
                checks["original_field_values_restored"] = value_only(restored) == value_only(original)
                checks["restore_used_normal_version_advance"] = restored["version"] > original["version"]
                report["restored_field_values_sha256"] = fingerprint(value_only(restored))
            except Exception as error:
                report["restore_failure_type"] = type(error).__name__
                report["passed"] = False
        for client in clients:
            if "X-CSRF-Token" in client.headers:
                try:
                    response = client.post(BASE + "/api/logout", json={})
                    if response.status_code != 200:
                        report["session_cleanup_failed"] = True
                except httpx.RequestError:
                    report["session_cleanup_failed"] = True
            client.close()
        report["passed"] = report["passed"] and all(checks.values()) and not report.get("session_cleanup_failed", False)
        payload = json.dumps(report, ensure_ascii=False, indent=2)
        run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
        (output / ("evaluation-restart-" + run_id + ".json")).write_text(payload, encoding="utf-8")
        (output / "evaluation-restart.json").write_text(payload, encoding="utf-8")
        print(json.dumps({"passed": report["passed"], "checks": checks, "report": "artifacts/storage/evaluation-restart.json"}))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
