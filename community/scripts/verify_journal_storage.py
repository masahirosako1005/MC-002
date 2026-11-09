"""Read-only storage fingerprints for schema migration and restart checks.

No row values, credentials, media names or coordinates leave the container.
Run capture before deployment, compare after deployment, restart-check after QA.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "journal"
PROBE = r'''
import hashlib,json,os,sqlite3
from pathlib import Path
def digest(value):
 return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
result={}
with sqlite3.connect(os.environ['APP_DB_PATH']) as db:
 db.execute('BEGIN')
 result['schema_version']=db.execute('PRAGMA user_version').fetchone()[0]
 result['integrity_ok']=db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
 result['foreign_keys_valid']=db.execute('PRAGMA foreign_key_check').fetchall()==[]
 result['tables']={}
 for name, in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"):
  if name in ('sessions','stage_sessions','jobs'): continue
  rows=db.execute('SELECT * FROM "'+name.replace('"','""')+'" ORDER BY rowid').fetchall()
  if name=='settings': rows=[r for r in rows if r[0]!='deleted-media-cleanup-cursor-v1']
  result['tables'][name]={'count':len(rows),'sha256':digest(rows)}
files=[]
for p in sorted(Path(os.environ['MEDIA_DIR']).rglob('*')):
 if p.is_file():
  with p.open('rb') as f: files.append((str(p.relative_to(os.environ['MEDIA_DIR'])),hashlib.file_digest(f,'sha256').hexdigest()))
result['media']={'count':len(files),'sha256':digest(files)}
print(json.dumps(result))
'''


def run(*args, input=None):
    return subprocess.run(args, cwd=ROOT, input=input, text=True, encoding="utf-8",
                          capture_output=True, check=True).stdout.strip()


def compose(*args, input=None):
    return run("docker", "compose", "-p", "kou-community", "-f", str(ROOT / "compose.yaml"), *args, input=input)


def probe():
    return json.loads(compose("exec", "-T", "app", "python", "-", input=PROBE))


def save(name, result):
    OUT.mkdir(exist_ok=True)
    (OUT / name).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    global OUT
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("capture", "compare", "restart-check"))
    parser.add_argument("--expected-version", type=int, choices=(3, 4, 5, 6, 7, 8), default=3)
    parser.add_argument("--artifact-dir", choices=("journal", "circles", "discovery", "reflections", "occasions", "personalization"), default="journal")
    args = parser.parse_args()
    OUT = ROOT / "artifacts" / args.artifact_dir
    baseline = f"schema{args.expected_version - 1}-before.json"
    if args.mode == "capture":
        before = probe()
        if before["schema_version"] != args.expected_version - 1:
            raise ValueError("Capture requires the expected pre-migration schema")
        if (OUT / baseline).exists():
            raise ValueError("Existing baseline must not be overwritten")
        save(baseline, before)
        print(json.dumps({"captured": True, "tables": len(before["tables"]), "media_files": before["media"]["count"]}))
        return
    result = {"checked_at": datetime.now(timezone.utc).isoformat(), "mode": args.mode,
              "excluded_volatile_tables": ["sessions", "stage_sessions", "jobs"],
              "excluded_maintenance_setting": "deleted-media-cleanup-cursor-v1 (only cursor; all other settings retained)"}
    if args.mode == "compare":
        before = json.loads((OUT / baseline).read_text(encoding="utf-8"))
        after = probe()
        result.update(before=before, after=after)
        result["existing_tables_unchanged"] = all(after["tables"].get(t) == v for t, v in before["tables"].items())
        result["media_unchanged"] = before["media"] == after["media"]
        result["passed"] = all((after["schema_version"] == args.expected_version, result["existing_tables_unchanged"],
                                result["media_unchanged"], after["integrity_ok"], after["foreign_keys_valid"]))
        save("migration.json", result)
    else:
        before = probe()
        compose("restart", "app")
        compose("up", "-d", "--wait")
        after = probe()
        with urllib.request.urlopen("http://127.0.0.1:8081/api/health", timeout=10) as response:
            healthy = response.status == 200
        result.update(before=before, after=after, healthy=healthy)
        result["passed"] = before == after and healthy and after["schema_version"] == args.expected_version and after["integrity_ok"] and after["foreign_keys_valid"]
        save("restart.json", result)
    print(json.dumps({k: v for k, v in result.items() if k not in ("before", "after")}, ensure_ascii=True))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
