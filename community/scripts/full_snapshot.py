"""Back up DB+media and restore only into a NEW isolated volume.

No command overwrites, removes, or switches the active data volume.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import time
import urllib.request
import uuid


ROOT = Path(__file__).resolve().parents[1]
BACKUPS = ROOT / "backups"
PROJECT = "kou-community"
ACTIVE_VOLUME = "kou-community_community-data"


def command(*args):
    return subprocess.run(["docker", *args], cwd=ROOT, text=True, encoding="utf-8", capture_output=True, check=True).stdout.strip()


def compose(*args):
    return command("compose", "-p", PROJECT, "-f", str(ROOT / "compose.yaml"), *args)


def running_app():
    container_id = compose("ps", "-a", "-q", "app")
    if not container_id:
        raise ValueError("The community app container does not exist")
    app = json.loads(command("inspect", container_id))[0]
    if app["Config"]["Labels"].get("com.docker.compose.project") != PROJECT:
        raise ValueError("Unexpected Compose project")
    if not any(m.get("Name") == ACTIVE_VOLUME and m["Destination"] == "/app/data" for m in app["Mounts"]):
        raise ValueError("Unexpected active data volume")
    return app


def safe_snapshot(argument):
    snapshot = Path(argument).resolve()
    if not snapshot.is_relative_to(BACKUPS.resolve()) or snapshot == BACKUPS.resolve() or not snapshot.is_dir():
        raise ValueError("Snapshots must be a directory under community/backups")
    return snapshot


def helper(operation, snapshot, image, *, volume=None, db_name=None):
    args = ["run", "--rm", "--pull=never", "--network", "none", "--read-only", "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges:true", "--user", "10001:10001", "--memory", "256m", "--cpus", "1",
            "--tmpfs", "/tmp:size=32m,noexec,nosuid", "--mount", f"type=bind,src={ROOT / 'scripts'},dst=/tools,readonly",
            "--mount", f"type=bind,src={snapshot},dst=/snapshot" + ("" if operation == "backup" else ",readonly")]
    if operation == "backup":
        args += ["--mount", f"type=volume,src={ACTIVE_VOLUME},dst=/source,readonly"]
    elif operation == "restore":
        args += ["--mount", f"type=volume,src={volume},dst=/app/data"]
    args += ["--entrypoint", "python", image, "/tools/snapshot_worker.py", operation]
    if db_name:
        args.append(db_name)
    return json.loads(command(*args))


def wait_for_app():
    for _ in range(60):
        try:
            with urllib.request.urlopen("http://127.0.0.1:8081/api/health", timeout=2) as response:
                if response.status == 200:
                    return
        except OSError:
            pass
        time.sleep(0.5)
    raise RuntimeError("Community app did not become healthy after backup")


def save_event(report):
    directory = ROOT / "artifacts"
    directory.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    (directory / f"full-snapshot-{stamp}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=("backup", "verify", "restore"))
    parser.add_argument("--snapshot")
    parser.add_argument("--allow-stop", action="store_true", help="Permit stopping ONLY the community app briefly for a consistent backup")
    args = parser.parse_args()
    report = {"operation": args.operation, "checked_at": datetime.now(timezone.utc).isoformat(), "passed": False}
    try:
        if args.operation == "backup":
            if not args.allow_stop:
                raise ValueError("Backup requires --allow-stop after coordinating with UI work")
            app = running_app()
            db_path = next(value.split("=", 1)[1] for value in app["Config"]["Env"] if value.startswith("APP_DB_PATH="))
            if not db_path.startswith("/app/data/") or Path(db_path).name != db_path.removeprefix("/app/data/"):
                raise ValueError("Database must be directly under /app/data")
            BACKUPS.mkdir(exist_ok=True)
            snapshot = BACKUPS / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:12])
            if not snapshot.resolve().is_relative_to(ROOT.resolve()):
                raise ValueError("Backup destination escapes project")
            snapshot.mkdir()
            report["snapshot"] = str(snapshot)
            metadata = {"image": app["Image"], "created_at": report["checked_at"], "active_volume": ACTIVE_VOLUME,
                        "model_manifest": json.loads((ROOT / "models/manifest.json").read_text(encoding="utf-8"))}
            (snapshot / "runtime.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
            was_running = app["State"]["Running"]
            try:
                if was_running:
                    compose("stop", "app")
                stopped = running_app()
                if stopped["State"]["Running"]:
                    raise ValueError("App must be stopped while copying DB and media")
                report["result"] = helper("backup", snapshot, app["Image"], db_name=Path(db_path).name)
            finally:
                if was_running:
                    compose("start", "app")
                    wait_for_app()
            report["active_app_restarted"] = was_running
        else:
            if not args.snapshot:
                raise ValueError("--snapshot is required")
            snapshot = safe_snapshot(args.snapshot)
            metadata = json.loads((snapshot / "runtime.json").read_text(encoding="utf-8"))
            report["snapshot"] = str(snapshot)
            if args.operation == "verify":
                report["result"] = helper("verify", snapshot, metadata["image"])
            else:
                # Always choose a new volume; no option accepts the active one.
                volume = "kou-community-restore-" + uuid.uuid4().hex
                token = uuid.uuid4().hex
                command("volume", "create", "--label", "kou.snapshot.restore=" + token, volume)
                info = json.loads(command("volume", "inspect", volume))[0]
                if (info.get("Labels") or {}).get("kou.snapshot.restore") != token or volume == ACTIVE_VOLUME:
                    raise ValueError("Restore volume ownership check failed")
                report["restored_volume"] = volume
                report["result"] = helper("restore", snapshot, metadata["image"], volume=volume)
                report["active_volume_changed"] = False
        report["passed"] = True
    except Exception as exc:
        report["error_type"] = type(exc).__name__
    save_event(report)
    print(json.dumps(report, ensure_ascii=True))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
