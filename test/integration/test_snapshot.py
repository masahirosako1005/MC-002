"""Exercise snapshot/WAL/restore checks with synthetic files, not live data."""
import json
from pathlib import Path
import sqlite3
import subprocess
import uuid


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ROOT = PROJECT_ROOT
FIXTURES = PROJECT_ROOT / "test" / "fixtures" / "runtime"
EVIDENCE = PROJECT_ROOT / "artifacts" / "storage"


def main():
    directory = FIXTURES / "snapshot" / uuid.uuid4().hex
    source, snapshot, restored = (directory / name for name in ("source", "snapshot", "restored"))
    for path in (source, snapshot, restored):
        path.mkdir(parents=True)
    (source / "media").mkdir()
    (source / "media" / "fixture.bin").write_bytes(b"synthetic media fixture")
    image = subprocess.run(["docker", "compose", "-p", "kou-community", "-f", str(ROOT / "compose.yaml"), "images", "-q", "app"], capture_output=True, text=True, check=True).stdout.strip()

    def worker(operation):
        args = ["docker", "run", "--rm", "--pull=never", "--network", "none", "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges:true", "--user", "10001:10001",
                "--mount", f"type=bind,src={ROOT / 'scripts'},dst=/tools,readonly",
                "--mount", f"type=bind,src={source},dst=/source,readonly",
                "--mount", f"type=bind,src={snapshot},dst=/snapshot" + ("" if operation == "backup" else ",readonly"),
                "--mount", f"type=bind,src={restored},dst=/app/data", "--entrypoint", "python", image, "/tools/snapshot_worker.py", operation]
        if operation == "backup":
            args.append("community.db")
        return subprocess.run(args, capture_output=True, text=True, encoding="utf-8")

    checks = {}
    # Keep the writer open after commit so that real uncheckpointed WAL exists.
    with sqlite3.connect(source / "community.db") as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA wal_autocheckpoint=0")
        connection.execute("CREATE TABLE entries(id INTEGER PRIMARY KEY, value TEXT NOT NULL)")
        connection.commit()
        connection.execute("INSERT INTO entries VALUES(1,'committed in WAL')")
        connection.commit()
        assert (source / "community.db-wal").stat().st_size > 0
        response = worker("backup")
        checks["backup_with_uncheckpointed_wal"] = response.returncode == 0
    if response.returncode != 0:
        raise RuntimeError(response.stderr)
    with sqlite3.connect(snapshot / "data/community.db") as copied:
        checks["wal_committed_row_preserved"] = copied.execute("SELECT value FROM entries").fetchall() == [("committed in WAL",)]
    checks["valid_snapshot_verified"] = worker("verify").returncode == 0
    restoration = worker("restore")
    checks["empty_target_restored"] = restoration.returncode == 0
    if restoration.returncode != 0:
        print(restoration.stderr)
    checks["restored_media_exact"] = (restored / "media/fixture.bin").read_bytes() == b"synthetic media fixture"
    checks["nonempty_target_refused"] = worker("restore").returncode != 0
    (snapshot / "data/media/fixture.bin").write_bytes(b"corrupted fixture")
    checks["media_corruption_refused"] = worker("verify").returncode != 0
    result = {"checks": checks, "passed": all(checks.values()), "fixture_directory": str(directory), "scope": "synthetic DB/media only; active volumes unchanged"}
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / f"snapshot-{directory.name}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (EVIDENCE / "snapshot-tests.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
