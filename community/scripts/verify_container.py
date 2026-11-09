"""Check the community deployment without exporting credentials or personal rows.

Run only after coordinating with browser/model work: --restart restarts the new
app service, never the original project on port 8080.
"""
import argparse
from datetime import datetime, timezone
import http.cookiejar
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.error
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "http://127.0.0.1:8081"


def save_report(report):
    directory = ROOT / "artifacts"
    directory.mkdir(exist_ok=True)
    content = json.dumps(report, ensure_ascii=False, indent=2)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    (directory / f"container-verification-{stamp}.json").write_text(content, encoding="utf-8")
    (directory / "container-verification.json").write_text(content, encoding="utf-8")


def docker(*args: str) -> str:
    result = subprocess.run(["docker", *args], cwd=ROOT, capture_output=True,
                            text=True, encoding="utf-8", check=True)
    return result.stdout.strip()


def compose(*args: str) -> str:
    return docker("compose", "-p", "kou-community", "-f", str(ROOT / "compose.yaml"), *args)


def health(origin: str) -> bool:
    try:
        with urllib.request.urlopen(origin + "/api/health", timeout=5) as response:
            return response.status == 200
    except (OSError, urllib.error.URLError):
        return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--restart", action="store_true",
                        help="Explicitly allow restarting only kou-community app")
    options = parser.parse_args()
    original_before = health("http://127.0.0.1:8080")
    jar = http.cookiejar.CookieJar()
    client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    csrf = ""

    def api(endpoint: str, body: dict | None = None):
        request = urllib.request.Request(
            ORIGIN + "/api" + endpoint,
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Origin": ORIGIN, "Content-Type": "application/json", "X-CSRF-Token": csrf},
        )
        with client.open(request, timeout=20) as response:
            return json.load(response)

    # Public prototype account; a different configured password can be supplied
    # through the local process environment. Neither value nor response is logged.
    login = api("/login", {"username": "aoi", "password": os.environ.get("KOU_TEST_PASSWORD", "aoi-local-2026")})
    csrf = login["csrf_token"]
    before = {path: api(path) for path in ("/me", "/me/preferences", "/communities")}
    with client.open(ORIGIN + "/", timeout=10) as response:
        html = response.read()
        static_ok = response.status == 200 and "text/html" in response.headers.get("Content-Type", "") and b"<html" in html.lower()

    probe = r'''
import json,os,socket,sqlite3
from pathlib import Path
result={"non_root":os.getuid()==10001}
status=Path('/proc/self/status').read_text()
result['capabilities_zero']='CapEff:\t0000000000000000' in status
result['no_new_privileges']='NoNewPrivs:\t1' in status
try:
    Path('/app/verification-write-denied').write_text('check')
    result['rootfs_write_denied']=False
except OSError:
    result['rootfs_write_denied']=True
try:
    with socket.create_connection(('1.1.1.1',443),timeout=3): pass
    result['external_tcp_blocked']=False
except OSError:
    result['external_tcp_blocked']=True
with sqlite3.connect(os.environ['APP_DB_PATH']) as conn:
    result['database_integrity']=conn.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    result['foreign_keys_valid']=conn.execute('PRAGMA foreign_key_check').fetchall()==[]
result['media_directory_writable']=os.access(os.environ['MEDIA_DIR'],os.W_OK)
result['model_directory_present']=Path(os.environ['MODEL_DIR']).is_dir()
print(json.dumps(result))
'''
    checks = json.loads(compose("exec", "-T", "app", "python", "-c", probe))
    app_id, gateway_id = compose("ps", "-q", "app"), compose("ps", "-q", "gateway")
    app = json.loads(docker("inspect", app_id))[0]
    gateway = json.loads(docker("inspect", gateway_id))[0]
    checks["rootfs_readonly"] = app["HostConfig"]["ReadonlyRootfs"]
    checks["static_app_served"] = static_ok
    checks["published_loopback_only"] = gateway["HostConfig"]["PortBindings"]["8081/tcp"] == [{"HostIp": "127.0.0.1", "HostPort": "8081"}]
    checks["independent_project"] = app["Config"]["Labels"]["com.docker.compose.project"] == "kou-community"
    checks["independent_data_volume"] = any(m.get("Name") == "kou-community_community-data" and m["Destination"] == "/app/data" for m in app["Mounts"])
    checks["model_mount_readonly"] = any(m["Destination"] == "/app/models" and not m["RW"] for m in app["Mounts"])
    networks = app["NetworkSettings"]["Networks"]
    checks["app_network_internal"] = len(networks) == 1 and all(json.loads(docker("network", "inspect", name))[0]["Internal"] for name in networks)

    if options.restart:
        compose("restart", "app")
        for _ in range(60):
            if health(ORIGIN):
                break
            time.sleep(0.5)
        checks["restart_preserves_session_preferences_memberships"] = before == {path: api(path) for path in before}

    backup_probe = r'''
import json,os,sqlite3,uuid
from pathlib import Path
directory=Path(os.environ['APP_DB_PATH']).parent/'backups'
directory.mkdir(exist_ok=True)
destination=directory/('verification-'+uuid.uuid4().hex+'.sqlite3')
with sqlite3.connect(os.environ['APP_DB_PATH']) as source, sqlite3.connect(destination) as backup:
    source.backup(backup)
    tables=[r[0] for r in source.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
    def count(connection,name):
        return connection.execute('SELECT COUNT(*) FROM "'+name.replace('"','""')+'"').fetchone()[0]
    print(json.dumps({'backup_integrity':backup.execute('PRAGMA integrity_check').fetchone()[0]=='ok',
                     'backup_counts_match':all(count(source,t)==count(backup,t) for t in tables),
                     'backup_foreign_keys_valid':backup.execute('PRAGMA foreign_key_check').fetchall()==[]}))
'''
    checks.update(json.loads(compose("exec", "-T", "app", "python", "-c", backup_probe)))
    checks["original_8080_remains_healthy"] = original_before and health("http://127.0.0.1:8080")
    report = {"checked_at": datetime.now(timezone.utc).isoformat(), "checks": checks,
              "image_id": app["Image"], "app_started_at": app["State"]["StartedAt"],
              "resource_limits": {"memory_bytes": app["HostConfig"]["Memory"], "nano_cpus": app["HostConfig"]["NanoCpus"], "pids": app["HostConfig"]["PidsLimit"]},
              "restart_tested": options.restart, "passed": all(checks.values()),
              "scope": "community container/API only; database backup excludes media files; no UI/model-quality claim"}
    save_report(report)
    print(json.dumps(report, ensure_ascii=True))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        report = {"checked_at": datetime.now(timezone.utc).isoformat(), "passed": False,
                  "error_type": type(exc).__name__, "scope": "container integration check did not complete"}
        save_report(report)
        print(json.dumps(report))
        raise SystemExit(1)
