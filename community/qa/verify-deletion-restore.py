"""Verify real application deletion through the existing offline snapshot worker.

Only fresh synthetic data below artifacts/snapshot-tests is mounted. The running
app and its named volume are never stopped, mounted, or changed by this script.
Run with the project runtime Python after coordinating Docker resource use.
"""

import asyncio
import hashlib
import io
import json
import sqlite3
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import Settings  # noqa: E402
from app.database import Database  # noqa: E402
from app.image_guidance import ImageGuidance  # noqa: E402
from app.main import create_app  # noqa: E402
from app.service import Service  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from PIL import Image  # noqa: E402


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def rows_digest(path):
    """Hash every application table, including settings, without outputting rows."""
    result = {}
    # No immutable=1 here: the source intentionally contains committed WAL data.
    with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as conn:
        if conn.execute("PRAGMA integrity_check").fetchone() != ("ok",):
            raise AssertionError("Database integrity check failed")
        if conn.execute("PRAGMA foreign_key_check").fetchall():
            raise AssertionError("Database foreign key check failed")
        for (table,) in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ):
            # Identifiers originate only in this synthetic DB's schema.
            quoted = '"' + table.replace('"', '""') + '"'
            values = conn.execute("SELECT * FROM " + quoted).fetchall()
            encoded = sorted(json.dumps(row, ensure_ascii=False, separators=(",", ":"))
                             for row in values)
            result[table] = {"rows": len(values), "sha256": hashlib.sha256(
                "\n".join(encoded).encode("utf-8")).hexdigest()}
    return result


def settings_for(directory):
    return Settings(db_path=directory / "community.db", media_dir=directory / "media",
                    model_dir=directory / "absent-model", seed_asset_dir=None,
                    static_dir=None, worker_enabled=False)


async def fixture(source):
    settings = settings_for(source)
    app = create_app(settings)
    items = []
    async with app.router.lifespan_context(app):
        service = app.state.service
        for index, published in enumerate((True, False, True)):
            buffer = io.BytesIO()
            Image.new("RGB", (48, 48), (30 + index * 50, 90, 160)).save(buffer, "PNG")
            media = service.upload("u-aoi", buffer.getvalue())
            post = service.create_post("u-aoi", {
                "community_id": "peers", "body": "保存と削除の合成検証用",
                "media_ids": [media["id"]], "tags": ["walk"],
                "place_label": "", "taken_on": None,
            })
            if published:
                service.patch_post("u-aoi", post["id"], {"status": "published"})
            path = service.media_path("u-aoi", media["id"])
            item = {"media_id": media["id"], "post_id": post["id"],
                    "key": path.name, "sha256": digest(path), "deleted": index > 0}
            if item["deleted"]:
                service.delete_post("u-aoi", post["id"])
            items.append(item)
    return items


def check_deleted_and_active(directory, items):
    settings = settings_for(directory)
    service = Service(Database(settings.db_path), settings, ImageGuidance())
    with sqlite3.connect(settings.db_path.as_uri() + "?mode=ro", uri=True) as conn:
        for item in items:
            deleted = item["deleted"]
            assert conn.execute("SELECT deleted FROM media WHERE id=?", (item["media_id"],)).fetchone() == (int(deleted),)
            assert conn.execute("SELECT status FROM posts WHERE id=?", (item["post_id"],)).fetchone() == ("deleted" if deleted else "published",)
            path = settings.media_dir / item["key"]
            if deleted:
                assert not path.exists(), "A deleted photo was restored"
                assert conn.execute("SELECT tags FROM jobs WHERE media_id=?", (item["media_id"],)).fetchone() == ("[]",)
                try:
                    service.media_path("u-aoi", item["media_id"])
                except HTTPException as error:
                    assert error.status_code == 404
                else:
                    raise AssertionError("Deleted photo access was allowed")
            else:
                assert digest(path) == item["sha256"], "Active photo bytes changed"
                assert service.media_path("u-aoi", item["media_id"]) == path
    assert len(list(settings.media_dir.iterdir())) == 1


def main():
    base = (ROOT / "artifacts" / "snapshot-tests").resolve()
    directory = base / ("deletion-restore-" + uuid.uuid4().hex)
    directory.mkdir(parents=True, exist_ok=False)
    source, snapshot, restored = (directory / name for name in ("source", "snapshot", "restored"))
    for path in (source, snapshot, restored):
        if not path.resolve().is_relative_to(base) or path.is_symlink():
            raise ValueError("Unsafe isolated fixture directory")
        path.mkdir(exist_ok=False)
    checks = {}
    report = {"executed_at": datetime.now(UTC).isoformat(), "passed": False,
              "scope": "Fresh synthetic application DB/media only; production volumes untouched",
              "fixture_directory": directory.relative_to(ROOT).as_posix(), "checks": checks,
              "limits": ["Not a production disaster recovery drill", "No OS crash or power loss injected",
                         "No app restart after restore: exact row comparison precedes maintenance mutations"]}
    try:
        items = asyncio.run(fixture(source))
        check_deleted_and_active(source, items)
        checks["source_real_service_deletion_and_active_photo"] = True
        image = subprocess.run(
            ["docker", "compose", "-p", "kou-community", "-f", str(ROOT / "compose.yaml"),
             "images", "-q", "app"], capture_output=True, text=True, check=True, timeout=30,
        ).stdout.strip()
        if not image or len(image.splitlines()) != 1:
            raise RuntimeError("Exactly one locally built app image is required")

        def worker(operation, expected_success=True):
            args = ["docker", "run", "--rm", "--pull=never", "--network", "none",
                    "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges:true",
                    "--user", "10001:10001", "--memory", "256m", "--cpus", "1", "--pids-limit", "64",
                    "--mount", f"type=bind,src={ROOT / 'scripts'},dst=/tools,readonly",
                    "--mount", f"type=bind,src={snapshot},dst=/snapshot" + ("" if operation == "backup" else ",readonly")]
            if operation == "backup":
                args.extend(["--mount", f"type=bind,src={source},dst=/source,readonly"])
            if operation == "restore":
                args.extend(["--mount", f"type=bind,src={restored},dst=/app/data"])
            args.extend(["--entrypoint", "python", image, "/tools/snapshot_worker.py", operation])
            if operation == "backup":
                args.append("community.db")
            response = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", timeout=120)
            if expected_success and response.returncode != 0:
                raise RuntimeError("Isolated snapshot worker failed: " + operation)
            if not expected_success:
                assert response.returncode != 0 and "Restore destination must be a newly created empty volume" in response.stderr

        # Keep the connection open, but do not write concurrently with backup.
        with sqlite3.connect(source / "community.db") as writer:
            writer.execute("PRAGMA journal_mode=WAL")
            writer.execute("PRAGMA wal_autocheckpoint=0")
            writer.execute("INSERT INTO settings(key,value) VALUES(?,?)",
                           ("deletion-restore-synthetic-wal", "committed"))
            writer.commit()
            assert (source / "community.db-wal").stat().st_size > 0
            before = rows_digest(source / "community.db")
            worker("backup")
            assert rows_digest(source / "community.db") == before
        checks["committed_wal_backup_source_rows_unchanged"] = True
        assert rows_digest(snapshot / "data" / "community.db") == before
        checks["snapshot_all_table_rows_exact"] = True
        check_deleted_and_active(snapshot / "data", items)
        checks["snapshot_deleted_absent_active_exact"] = True
        worker("verify")
        checks["existing_worker_verified_manifest_and_files"] = True
        worker("restore")
        checks["restored_to_new_empty_area"] = True
        assert rows_digest(restored / "community.db") == before
        checks["restored_all_table_rows_exact"] = True
        check_deleted_and_active(restored, items)
        checks["restored_deletion_flags_access_denial_and_files_absent"] = True
        checks["restored_active_photo_readable_and_bytes_exact"] = True
        worker("restore", expected_success=False)
        checks["nonempty_restore_target_refused"] = True
        assert rows_digest(restored / "community.db") == before
        assert rows_digest(source / "community.db") == before
        check_deleted_and_active(source, items)
        checks["source_and_restored_rows_still_exact_after_checks"] = True
        report.update(passed=True, table_hashes=before, table_count=len(before),
                      synthetic_photos={"active": 1, "deleted": 2},
                      helper_policy={"network": "none", "read_only_root": True,
                                     "memory_mb": 256, "cpus": 1, "production_mounts": 0})
    except Exception as error:
        report["failure_type"] = type(error).__name__
        raise
    finally:
        payload = json.dumps(report, ensure_ascii=False, indent=2)
        (directory / "result.json").write_text(payload, encoding="utf-8")
        (ROOT / "artifacts" / "deletion-restore.json").write_text(payload, encoding="utf-8")
        print(json.dumps({"passed": report["passed"], "checks": len(checks),
                          "report": "community/artifacts/deletion-restore.json"}))


if __name__ == "__main__":
    main()
