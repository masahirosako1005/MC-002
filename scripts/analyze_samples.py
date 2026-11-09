"""Read-only CSV validation and pseudonymous local analytics import.

Raw names, emails, LINE IDs, demographics and free text never enter the output DB.
The HMAC key and analytics DB stay local. This is pseudonymization, not anonymity.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import hmac
import io
import json
import os
from pathlib import Path
import secrets
import sqlite3
from contextlib import closing
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
SPECS = {
    "08": ("survey_after", "user_id", None, None),
    "09": ("survey_before", "user_id", None, None),
    "12": ("stamp", "ユーザID", "獲得日時", "スポット名"),
    "13": ("user", "ユーザーID", "登録日時", None),
    "18": ("reward", "user_id", "timestamp", "reward_name"),
}


def inside_project(path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(ROOT):
        raise ValueError("出力先はプロジェクト内に指定してください")
    return resolved


def parse_time(value: str) -> str | None:
    if not value.strip():
        return None
    value = value.strip().replace("/", "-")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).isoformat()
    except ValueError:
        return None


def decode_csv(raw: bytes) -> tuple[str, str]:
    for encoding in ("utf-8-sig", "cp932"):
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError:
            pass
    raise ValueError("CSVの文字コードを確認してください")


def token(key: bytes, domain: str, value: str) -> str:
    return hmac.new(key, (domain + "\0" + value).encode(), hashlib.sha256).hexdigest()


def analyze(source: Path, database: Path, key_path: Path) -> dict:
    database = inside_project(database)
    key_path = inside_project(key_path)
    if source.resolve().is_relative_to(database.parent) and source.resolve() == database.parent:
        raise ValueError("入力フォルダに出力を作成しません")
    database.parent.mkdir(parents=True, exist_ok=True)
    key_path.parent.mkdir(parents=True, exist_ok=True)
    if database.exists() and not key_path.exists():
        raise ValueError("既存DBの識別キーがありません。バックアップからキーを復元してください")
    if not key_path.exists():
        try:
            fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(fd, "wb") as stream:
                stream.write(secrets.token_bytes(32))
    key = key_path.read_bytes()
    if len(key) != 32:
        raise ValueError("取込識別用キーが不正です")
    report = {"files": [], "source_unchanged": True, "retained_fields": ["kind", "pseudonymous_user", "pseudonymous_subject", "occurred_at"], "limitations": ["仮名化された履歴は個人関連データとして保護する", "旅行IDがないため日付の違いから実際の再訪率は断定できない", "氏名・メール・LINE・属性・自由記述は出力DBに保存しない"]}
    imported_users: set[str] = set()
    referenced_users: set[str] = set()
    with closing(sqlite3.connect(database)) as conn, conn:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS source_files (
                digest TEXT PRIMARY KEY, name TEXT NOT NULL, row_count INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS records (
                identity TEXT PRIMARY KEY, kind TEXT NOT NULL,
                user_ref TEXT NOT NULL, subject_ref TEXT,
                occurred_at TEXT, source_digest TEXT NOT NULL REFERENCES source_files(digest)
            );
        """)
        for path in sorted(source.glob("*.csv")):
            spec = SPECS.get(path.name[:2])
            if not spec:
                continue
            raw = path.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            decoded, encoding = decode_csv(raw)
            reader = csv.DictReader(io.StringIO(decoded))
            kind, user_field, time_field, subject_field = spec
            required = [field for field in (user_field, time_field, subject_field) if field]
            missing = [field for field in required if field not in (reader.fieldnames or [])]
            if missing:
                # Reject the whole malformed file; never silently map the wrong column.
                report["files"].append({"name": path.name, "status": "rejected_schema", "missing_columns": missing, "sha256": digest})
                continue
            rows = list(reader)
            seen: set[str] = set()
            metrics = {"name": path.name, "sha256": digest, "encoding": encoding, "status": "processed", "rows": len(rows), "duplicate_rows": 0, "missing_user": 0, "invalid_time": 0, "invalid_shape": 0, "missing_subject": 0, "inserted": 0, "already_present": 0}
            conn.execute("INSERT OR IGNORE INTO source_files VALUES(?,?,?)", (digest, path.name, len(rows)))
            for row in rows:
                if None in row or any(value is None for value in row.values()):
                    metrics["invalid_shape"] += 1
                    continue
                canonical = json.dumps(row, ensure_ascii=False, sort_keys=True)
                identity = token(key, kind, canonical)
                if identity in seen:
                    metrics["duplicate_rows"] += 1
                    continue
                seen.add(identity)
                user = row[user_field].strip()
                if not user:
                    metrics["missing_user"] += 1
                    continue
                occurred = parse_time(row[time_field]) if time_field else None
                if time_field and occurred is None:
                    metrics["invalid_time"] += 1
                    continue
                subject = row[subject_field].strip() if subject_field else None
                if subject_field and not subject:
                    metrics["missing_subject"] += 1
                    continue
                user_ref = token(key, "user", user)
                (imported_users if kind == "user" else referenced_users).add(user_ref)
                cursor = conn.execute("INSERT OR IGNORE INTO records VALUES(?,?,?,?,?,?)", (identity, kind, user_ref, token(key, "subject", subject) if subject else None, occurred, digest))
                metrics["inserted" if cursor.rowcount else "already_present"] += 1
            report["source_unchanged"] &= hashlib.sha256(path.read_bytes()).hexdigest() == digest
            report["files"].append(metrics)
        report["unmatched_users"] = len(referenced_users - imported_users)
        report["stored_records"] = dict(conn.execute("SELECT kind, COUNT(*) FROM records GROUP BY kind").fetchall())
        report["stamp_users_with_multiple_dates"] = conn.execute("SELECT COUNT(*) FROM (SELECT user_ref FROM records WHERE kind='stamp' GROUP BY user_ref HAVING COUNT(DISTINCT substr(occurred_at,1,10)) > 1)").fetchone()[0]
        report["integrity_check"] = conn.execute("PRAGMA integrity_check").fetchone()[0]
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("C:/AI-Sprint/sample-data"))
    parser.add_argument("--database", type=Path, default=ROOT / "data/analytics.db")
    parser.add_argument("--key", type=Path, default=ROOT / "data/.import-key")
    parser.add_argument("--report", type=Path, default=ROOT / "artifacts/sample-quality.json")
    args = parser.parse_args()
    if not args.source.is_dir():
        parser.error("サンプルデータのフォルダが見つかりません")
    report = analyze(args.source, args.database, args.key)
    output = inside_project(args.report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"files": len(report["files"]), "stored_records": report["stored_records"], "source_unchanged": report["source_unchanged"], "integrity_check": report["integrity_check"]}, ensure_ascii=True))


if __name__ == "__main__":
    main()
