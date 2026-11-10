"""Compare a pair of project-local snapshots without emitting private rows."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[2]


def inspect(folder):
    source = folder.resolve()
    if not source.is_relative_to(ROOT):
        raise ValueError("Snapshot must remain inside the project")
    data = source / "data"
    with sqlite3.connect((data / "community.db").as_uri() + "?mode=ro", uri=True) as db:
        names = [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        tables = {}
        for name in names:
            quoted = '"' + name.replace('"', '""') + '"'
            rows = db.execute("SELECT * FROM " + quoted).fetchall()
            tables[name] = Counter(hashlib.sha256(json.dumps(row, default=str).encode()).hexdigest() for row in rows)
        integrity = db.execute('PRAGMA integrity_check').fetchone()[0]
        foreign_keys = len(db.execute('PRAGMA foreign_key_check').fetchall())
    media = {p.relative_to(data).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in (data / 'media').rglob('*') if p.is_file()}
    return tables, media, integrity, foreign_keys


def verify(before, after):
    old, old_media, _, _ = inspect(before)
    new, new_media, integrity, foreign_keys = inspect(after)
    tables = {name: dict(before=sum(rows.values()), after=sum(new.get(name, {}).values()),
                        original_rows_preserved=not bool(rows - new.get(name, Counter()))) for name, rows in old.items()}
    media_ok = all(new_media.get(name) == checksum for name, checksum in old_media.items())
    return dict(passed=all(row['original_rows_preserved'] for row in tables.values()) and media_ok
                and integrity == 'ok' and foreign_keys == 0, tables=tables,
                old_media_count=len(old_media), new_media_count=len(new_media), old_media_preserved=media_ok,
                integrity=integrity, foreign_key_violations=foreign_keys)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('before', type=Path)
    parser.add_argument('after', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if not args.output.resolve().is_relative_to(ROOT):
        raise ValueError('Output must remain inside the project')
    result = verify(args.before, args.after)
    args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({key: value for key, value in result.items() if key != 'tables'}))
    raise SystemExit(0 if result['passed'] else 1)
