"""Verify schema-2 records across a coordinated backup restart and isolated restore.

Run only while browser writers are paused. No row bodies or credentials are logged.
The full_snapshot helper never changes the active data volume.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
PROBE = r'''
import hashlib,json,os,sqlite3
tables=('ko_groups','group_members','posts','media','travel_parties',
 'travel_party_members','travel_requirements','party_messages','condition_drafts',
 'recommendation_runs','plan_selections','consultations','consultation_messages','operation_keys')
result={}
with sqlite3.connect(os.environ['APP_DB_PATH']) as db:
 result['schema_version']=db.execute('PRAGMA user_version').fetchone()[0]
 result['integrity_ok']=db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
 result['foreign_keys_valid']=db.execute('PRAGMA foreign_key_check').fetchall()==[]
 result['tables']={}
 for name in tables:
  rows=db.execute('SELECT * FROM "'+name+'" ORDER BY rowid').fetchall()
  digest=hashlib.sha256(json.dumps(rows,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
  result['tables'][name]={'count':len(rows),'sha256':digest}
print(json.dumps(result))
'''


def run(*args):
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True,
                          encoding='utf-8', check=True).stdout.strip()


def probe():
    return json.loads(run('docker', 'compose', '-p', 'kou-community', '-f',
                          str(ROOT / 'compose.yaml'), 'exec', '-T', 'app', 'python', '-c', PROBE))


def health(port):
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/health', timeout=5) as response:
            return response.status == 200
    except OSError:
        return False


def snapshot(*args):
    return json.loads(run(sys.executable, str(ROOT / 'scripts/full_snapshot.py'), *args))


def main():
    if sys.argv[1:] != ['--allow-stop']:
        raise SystemExit('Use --allow-stop only after coordinating with browser work.')
    report = {'checked_at': datetime.now(timezone.utc).isoformat(), 'passed': False,
              'scope': '14 business tables, schema 2, DB+media file hashes; no restored API/browser claim'}
    try:
        report['old_8080_before'] = health(8080)
        report['before'] = probe()
        if report['before']['schema_version'] != 2:
            raise ValueError('Expected schema 2')
        report['backup'] = snapshot('backup', '--allow-stop')
        path = report['backup']['snapshot']
        report['verify'] = snapshot('verify', '--snapshot', path)
        report['restore'] = snapshot('restore', '--snapshot', path)
        report['after'] = probe()
        report['business_rows_unchanged'] = report['before'] == report['after']
        report['new_8081_after'] = health(8081)
        report['old_8080_after'] = health(8080)
        report['passed'] = all((report['business_rows_unchanged'], report['old_8080_before'],
                                report['old_8080_after'], report['new_8081_after'],
                                report['backup']['passed'], report['verify']['passed'],
                                report['restore']['passed']))
    except Exception as exc:
        report['error_type'] = type(exc).__name__
    content = json.dumps(report, ensure_ascii=False, indent=2)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    for name in ('schema2-persistence.json', f'schema2-persistence-{stamp}.json'):
        (ROOT / 'artifacts' / name).write_text(content, encoding='utf-8')
    print(json.dumps({'passed': report['passed'], 'business_rows_unchanged': report.get('business_rows_unchanged'),
                      'snapshot': report.get('backup', {}).get('snapshot'),
                      'restored_volume': report.get('restore', {}).get('restored_volume'),
                      'error_type': report.get('error_type')}))
    if not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
