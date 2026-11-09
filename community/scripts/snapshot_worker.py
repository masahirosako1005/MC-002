"""Offline snapshot worker, run only in a constrained helper container."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import sqlite3
import sys


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def inventory(directory):
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("Snapshot inventory must be a real directory")
    result = {}
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise ValueError("Symlinks are not allowed in snapshots")
        if path.is_file():
            result[path.relative_to(directory).as_posix()] = {"bytes": path.stat().st_size, "sha256": digest(path)}
    return result


def database_check(path):
    with sqlite3.connect(f"file:{path.as_posix()}?mode=ro&immutable=1", uri=True) as connection:
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("Database integrity check failed")
        if connection.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("Database foreign key check failed")
        tables = [row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        counts = {table: connection.execute('SELECT COUNT(*) FROM "' + table.replace('"', '""') + '"').fetchone()[0] for table in tables}
        return {"integrity": "ok", "foreign_keys": "ok", "schema_version": connection.execute("PRAGMA user_version").fetchone()[0], "table_counts": counts}


def verify(snapshot):
    manifest = json.loads((snapshot / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("format") != 1 or manifest.get("complete") is not True:
        raise ValueError("Snapshot is incomplete or unsupported")
    for relative in manifest["files"]:
        path = PurePosixPath(relative)
        if path.is_absolute() or ".." in path.parts or "\\" in relative:
            raise ValueError("Unsafe manifest path")
    if inventory(snapshot / "data") != manifest["files"]:
        raise ValueError("Snapshot file hashes or file list do not match")
    db_name = manifest["database_file"]
    if PurePosixPath(db_name).name != db_name or db_name not in manifest["files"]:
        raise ValueError("Unsafe database path")
    if database_check(snapshot / "data" / db_name) != manifest["database"]:
        raise ValueError("Database schema or row counts do not match")
    return manifest


def backup(snapshot, db_name):
    if PurePosixPath(db_name).name != db_name or "\\" in db_name:
        raise ValueError("Unsafe database name")
    source = Path("/source")
    database = source / db_name
    if database.is_symlink() or not database.is_file():
        raise ValueError("Source database is missing or unsafe")
    # The app is stopped. Copy WAL/SHM along with the DB to a writable staging
    # directory, then use SQLite backup to make a standalone consistent DB.
    stage = snapshot / "staging-db"
    stage.mkdir()
    for suffix in ("", "-wal", "-shm"):
        path = source / (db_name + suffix)
        if path.is_symlink():
            raise ValueError("Source database sidecar is a symlink")
        if path.exists():
            shutil.copy2(path, stage / path.name)
    data = snapshot / "data"
    data.mkdir()
    with sqlite3.connect(stage / db_name) as original, sqlite3.connect(data / db_name) as copied:
        original.backup(copied)
        copied.execute("PRAGMA journal_mode=DELETE")
    media = source / "media"
    if not media.is_dir() or media.is_symlink():
        raise ValueError("Source media directory is missing or unsafe")
    inventory(media)  # Reject symlinks before copying any media.
    shutil.copytree(media, data / "media")
    manifest = {"format": 1, "complete": True, "database_file": db_name,
                "database": database_check(data / db_name), "files": inventory(data),
                "scope": "database and entire media directory; excludes old database-only backups and model weights"}
    # Only remove this newly created staging directory, never the source volume.
    if stage.resolve() != snapshot.resolve() / "staging-db":
        raise ValueError("Unsafe staging cleanup path")
    shutil.rmtree(stage)
    (snapshot / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    verify(snapshot)
    return manifest


def restore(snapshot):
    manifest = verify(snapshot)
    destination = Path("/app/data")
    if any(path.is_file() or path.is_symlink() for path in destination.rglob("*")):
        raise ValueError("Restore destination must be a newly created empty volume")
    # Do not copy directory ownership/timestamps onto the mount root. Docker
    # Desktop bind mounts can reject that even when file writes are allowed.
    for path in sorted((snapshot / "data").rglob("*")):
        target = destination / path.relative_to(snapshot / "data")
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
    if inventory(destination) != manifest["files"]:
        raise ValueError("Restored file hashes do not match")
    if database_check(destination / manifest["database_file"]) != manifest["database"]:
        raise ValueError("Restored database does not match")
    return manifest


if __name__ == "__main__":
    operation, snapshot = sys.argv[1], Path("/snapshot")
    if operation == "backup":
        result = backup(snapshot, sys.argv[2])
    elif operation == "verify":
        result = verify(snapshot)
    elif operation == "restore":
        result = restore(snapshot)
    else:
        raise ValueError("Unknown snapshot operation")
    print(json.dumps({"verified": True, "file_count": len(result["files"]),
                      "bytes": sum(item["bytes"] for item in result["files"].values()),
                      "database": result["database"]}))
