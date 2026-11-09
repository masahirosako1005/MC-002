"""Compare pre-migration backup rows to current DB, without outputting row values.

Concurrent new user messages are allowed; modifications/removals of old rows fail.
All comparison happens in a read-only networkless helper container.
"""
from datetime import datetime, timezone
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PROBE = r'''
from collections import Counter
import hashlib,json,sqlite3,sys
from pathlib import Path
report={'tables':{},'excluded_volatile_tables':['sessions','stage_sessions','jobs']}
with sqlite3.connect('file:/before/data/community.db?mode=ro&immutable=1',uri=True) as old, sqlite3.connect('file:/current/data/community.db?mode=ro&immutable=1',uri=True) as new:
 new.execute('BEGIN')
 for name, in old.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"):
  if name in report['excluded_volatile_tables']: continue
  query='SELECT * FROM "'+name.replace('"','""')+'"'
  a,b=Counter(old.execute(query).fetchall()),Counter(new.execute(query).fetchall())
  report['tables'][name]={'before':sum(a.values()),'current':sum(b.values()),'missing_or_modified':sum((a-b).values()),'additional':sum((b-a).values())}
 report['schema_version']=new.execute('PRAGMA user_version').fetchone()[0]
 report['integrity_ok']=new.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
 report['foreign_keys_valid']=not new.execute('PRAGMA foreign_key_check').fetchall()
media=[]
for p in sorted(Path('/before/data/media').rglob('*')):
 if not p.is_file(): continue
 current=Path('/current/data/media')/p.relative_to('/before/data/media')
 with p.open('rb') as a:
  first=hashlib.file_digest(a,'sha256').hexdigest()
 if not current.is_file(): media.append(False); continue
 with current.open('rb') as b: media.append(first==hashlib.file_digest(b,'sha256').hexdigest())
report['old_media_count']=len(media)
report['old_media_unchanged']=all(media)
report['passed']=all(t['missing_or_modified']==0 for t in report['tables'].values()) and report['old_media_unchanged'] and report['integrity_ok'] and report['foreign_keys_valid'] and report['schema_version']==int(sys.argv[1])
print(json.dumps(report))
'''


parser = argparse.ArgumentParser()
parser.add_argument('snapshot')
parser.add_argument('current')
parser.add_argument('--expected-version',type=int,choices=(3,4,5,6,7,8),default=3)
parser.add_argument('--artifact-dir',choices=('journal','circles','discovery','reflections','occasions','personalization'),default='journal')
args = parser.parse_args()
snapshot = Path(args.snapshot).resolve()
if not snapshot.is_relative_to((ROOT / 'backups').resolve()) or not (snapshot / 'manifest.json').is_file():
    raise ValueError('Expected an existing project snapshot')
current = Path(args.current).resolve()
if not current.is_relative_to((ROOT / 'backups').resolve()) or not (current / 'manifest.json').is_file():
    raise ValueError('Expected an existing current project snapshot')
process = subprocess.run([
    'docker','run','--rm','--pull=never','--network','none','--read-only','--cap-drop','ALL',
    '--security-opt','no-new-privileges:true','--user','10001:10001','--memory','128m','--cpus','1',
    '--mount',f'type=bind,src={snapshot},dst=/before,readonly',
    '--mount',f'type=bind,src={current},dst=/current,readonly',
    '--entrypoint','python','kou-community-app:latest','-c',PROBE,str(args.expected_version)],
    capture_output=True,text=True,encoding='utf-8')
if process.returncode:
    print(process.stderr[-1500:])
    raise SystemExit(process.returncode)
report = json.loads(process.stdout)
report['checked_at']=datetime.now(timezone.utc).isoformat()
report['scope']='Pre-migration backup subset preservation; additional user/QA rows allowed. Not equality of all current rows.'
output = ROOT / 'artifacts' / args.artifact_dir / 'migration-preservation.json'
output.parent.mkdir(parents=True,exist_ok=True)
output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'passed':report['passed'],'existing_tables':len(report['tables']),'old_media_unchanged':report['old_media_unchanged']}))
if not report['passed']:
    raise SystemExit(1)
