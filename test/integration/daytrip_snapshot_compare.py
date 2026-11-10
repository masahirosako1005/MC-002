"""Compare two read-only snapshots without emitting rows or media filenames."""

import argparse
import hashlib
import json
from pathlib import Path
import sqlite3


def table_digest(connection, table):
    quoted = '"' + table.replace('"', '""') + '"'
    rows = connection.execute(f"SELECT * FROM {quoted}").fetchall()
    encoded = sorted(
        json.dumps(row, ensure_ascii=False, default=lambda value: value.hex()).encode()
        for row in rows
    )
    digest = hashlib.sha256()
    for row in encoded:
        digest.update(len(row).to_bytes(8, "big"))
        digest.update(row)
    return {"rows": len(rows), "sha256": digest.hexdigest()}


def inspect(snapshot):
    data = snapshot / "data"
    with sqlite3.connect((data / "community.db").resolve().as_uri() + "?mode=ro", uri=True) as db:
        tables = [row[0] for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )]
        result = {
            "integrity": db.execute("PRAGMA integrity_check").fetchone()[0],
            "foreign_key_violations": len(db.execute("PRAGMA foreign_key_check").fetchall()),
            "tables": {table: table_digest(db, table) for table in tables},
        }
    result["media"] = {
        path.relative_to(data).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (data / "media").rglob("*") if path.is_file()
    }
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("before")
    parser.add_argument("after")
    parser.add_argument("output")
    args = parser.parse_args()
    before, after = inspect(Path(args.before)), inspect(Path(args.after))
    old = before["tables"]
    report = {
        "before_snapshot": Path(args.before).name,
        "after_snapshot": Path(args.after).name,
        "before_integrity": before["integrity"],
        "after_integrity": after["integrity"],
        "before_fk_violations": before["foreign_key_violations"],
        "after_fk_violations": after["foreign_key_violations"],
        "existing_tables": {
            table: {"before_count": value["rows"],
                    "after_count": after["tables"].get(table, {}).get("rows"),
                    "identical": value == after["tables"].get(table)}
            for table, value in old.items()
        },
        "new_tables": {table: value["rows"] for table, value in after["tables"].items() if table not in old},
        "media_count_before": len(before["media"]),
        "media_count_after": len(after["media"]),
        "all_media_identical": before["media"] == after["media"],
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "existing_tables": len(old),
        "changed_tables": [table for table, value in report["existing_tables"].items() if not value["identical"]],
        "media_identical": report["all_media_identical"],
        "output": str(output),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
