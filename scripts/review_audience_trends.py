"""Independent read-only audit; emits aggregate counts, never personal records."""
import csv
import hashlib
import io
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median

SOURCE = Path('C:/AI-Sprint/sample-data')
FILES = {
    'users': ('13_ユーザー一覧.csv', 'ユーザーID'),
    'before': ('09_アンケート回答_登録時.csv', 'user_id'),
    'after': ('08_アンケート回答_参加後.csv', 'user_id'),
    'stamps': ('12_スタンプ獲得履歴.csv', 'ユーザID'),
    'rewards': ('18_特典獲得履歴.csv', 'user_id'),
}

def run():
    tables, hashes, metrics = {}, {}, {}
    for kind, (name, id_col) in FILES.items():
        content = (SOURCE / name).read_bytes()
        hashes[kind] = hashlib.sha256(content).hexdigest()
        for encoding in ('utf-8-sig', 'cp932'):
            try:
                decoded = content.decode(encoding)
                break
            except UnicodeDecodeError:
                pass
        rows = list(csv.DictReader(io.StringIO(decoded)))
        assert all(None not in r and all(v is not None for v in r.values()) for r in rows)
        tables[kind] = rows
        ids = [r[id_col].strip() for r in rows]
        metrics[kind] = dict(rows=len(rows), distinct_ids=len(set(ids)),
                             blank_ids=ids.count(''), duplicate_full_rows=len(rows)-len({tuple(r.items()) for r in rows}))
    users = {r['ユーザーID'].strip(): r for r in tables['users']}
    for kind, (_, id_col) in FILES.items():
        metrics[kind]['orphan_ids'] = len({r[id_col].strip() for r in tables[kind]}-users.keys())
    stamps = Counter(r['ユーザID'].strip() for r in tables['stamps'])
    rewards = Counter(r['user_id'].strip() for r in tables['rewards'])
    sat_col = 'アンケート①(満足度を教えてください)'
    sat = {r['user_id'].strip():r[sat_col].strip() for r in tables['after']}
    allowed_sat = ['大変満足','やや満足','普通','やや不満','大変不満']
    sat_counts = Counter(sat.values())
    def age(v):
        m = re.match(r'\s*(\d+)', v)
        if not m: return '不明'
        n=int(m.group(1))
        return '20歳未満' if n<20 else '70歳以上' if n>=70 else f'{n//10*10}代'
    def sex(v):
        return v.strip() if v.strip() in ('男性','女性') else 'その他・未回答'
    groups = {}
    for field, mapper in [('年代',age),('性別',sex)]:
        grouped = defaultdict(list)
        for uid,r in users.items(): grouped[mapper(r[field])].append(uid)
        groups[field] = {label: dict(n=len(ids),stamp_users=sum(stamps[u]>0 for u in ids),
             stamps=sum(stamps[u] for u in ids),stamp_mean=mean(stamps[u] for u in ids),
             stamp_median=median(stamps[u] for u in ids),responses=sum(u in sat for u in ids),
             satisfied=sum(sat.get(u) in ('大変満足','やや満足') for u in ids))
             for label,ids in grouped.items() if len(ids)>=10}
    before = {r['user_id'].strip():r for r in tables['before']}
    out=dict(files=metrics,groups=groups,satisfaction={k:sat_counts[k] for k in allowed_sat},
        unknown_satisfaction=sum(v for k,v in sat_counts.items() if k not in allowed_sat),
        user_stamp_mismatch=sum(int(r['スタンプ獲得数']) != stamps[u] for u,r in users.items()),
        user_reward_mismatch=sum(int(r['特典獲得数']) != rewards[u] for u,r in users.items()),
        age_mismatch=sum(age(r['年代']) != age(before[u]['2489_年齢']) for u,r in users.items()),
        sex_mismatch=sum(sex(r['性別']) != sex(before[u]['2488_性別']) for u,r in users.items()),
        respondent_stamps=mean(stamps[u] for u in users if u in sat),
        nonrespondent_stamps=mean(stamps[u] for u in users if u not in sat),
        dates=dict(min=min(r['獲得日時'][:10] for r in tables['stamps']),
                   max=max(r['獲得日時'][:10] for r in tables['stamps'])),
        source_unchanged=all(hashlib.sha256((SOURCE / name).read_bytes()).hexdigest()==hashes[k]
                             for k,(name,_) in FILES.items()))
    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    run()
