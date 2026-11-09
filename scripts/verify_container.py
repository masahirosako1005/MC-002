"""Verify the running local Compose deployment without exporting credentials."""
import json
import subprocess
import time
from pathlib import Path
import http.cookiejar
import urllib.request
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "http://127.0.0.1:8080"


def docker(*args):
    result = subprocess.run(["docker", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True)
    return result.stdout.strip()


def main():
    jar = http.cookiejar.CookieJar()
    client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    csrf = ""

    def api(endpoint, body=None):
        request = urllib.request.Request(ORIGIN + "/api" + endpoint, data=json.dumps(body).encode() if body is not None else None, headers={"Origin": ORIGIN, "Content-Type": "application/json", "X-CSRF-Token": csrf})
        with client.open(request, timeout=10) as response:
            return json.load(response)

    csrf = api("/session", {})["csrf_token"]
    api("/visits", {"spot_id": "watergate", "code": "GATE-314"})
    api("/plans", {"experience_id": "gate-winter", "reason": "次の季節の水門を訪れるため"})
    before = api("/journal")
    probe = r'''
import json,os,socket,sqlite3
from pathlib import Path
result={"uid":os.getuid()}
status=Path('/proc/self/status').read_text()
result["capabilities_zero"]='CapEff:\t0000000000000000' in status
result["no_new_privileges"]='NoNewPrivs:\t1' in status
try:
    Path('/app/forbidden-write').write_text('check')
    result['rootfs_write_denied']=False
except OSError:
    result['rootfs_write_denied']=True
try:
    with socket.create_connection(('1.1.1.1',443),timeout=3): pass
    result['external_tcp_blocked']=False
except OSError:
    result['external_tcp_blocked']=True
with sqlite3.connect(os.environ['APP_DB_PATH']) as conn:
    result['database_integrity']=conn.execute('PRAGMA integrity_check').fetchone()[0]
print(json.dumps(result))
'''.replace("\\t", "\t")
    checks = json.loads(docker("compose", "exec", "-T", "app", "python", "-c", probe))
    checks["rootfs_readonly"] = json.loads(docker("inspect", "tang-you-chi-app-1"))[0]["HostConfig"]["ReadonlyRootfs"]
    # Whole container restart; persistence is checked through the same cookie jar.
    docker("compose", "restart", "app")
    for attempt in range(30):
        try:
            api("/health")
            break
        except Exception:
            time.sleep(0.5)
    after = api("/journal")
    checks["restart_preserves_journal"] = before == after
    backup_name = "verification-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".db"
    docker("compose", "exec", "-T", "app", "python", "-m", "app.backup", "/app/data/" + backup_name)
    compare = "import sqlite3,json,os; a=sqlite3.connect(os.environ['APP_DB_PATH']); b=sqlite3.connect('/app/data/" + backup_name + "'); tables=['users','visits','attempts','achievements','plans','sessions','recovery_codes']; print(json.dumps({'integrity':b.execute('PRAGMA integrity_check').fetchone()[0],'same_counts':all(a.execute('SELECT COUNT(*) FROM '+t).fetchone()==b.execute('SELECT COUNT(*) FROM '+t).fetchone() for t in tables)})); a.close(); b.close()"
    backup = json.loads(docker("compose", "exec", "-T", "app", "python", "-c", compare))
    checks["backup_integrity"] = backup["integrity"]
    checks["backup_same_counts"] = backup["same_counts"]
    checks["app_network_internal"] = json.loads(docker("network", "inspect", "tang-you-chi_local-only"))[0]["Internal"]
    checks["published_loopback_only"] = json.loads(docker("inspect", "tang-you-chi-gateway-1"))[0]["HostConfig"]["PortBindings"]["8080/tcp"][0]["HostIp"] == "127.0.0.1"
    expected = {"uid":10001,"capabilities_zero":True,"no_new_privileges":True,"rootfs_readonly":True,"rootfs_write_denied":True,"external_tcp_blocked":True,"database_integrity":"ok","restart_preserves_journal":True,"backup_integrity":"ok","backup_same_counts":True,"app_network_internal":True,"published_loopback_only":True}
    checks["passed"] = all(checks[key] == value for key,value in expected.items())
    (ROOT / "artifacts/container-verification.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(checks))
    if not checks["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
