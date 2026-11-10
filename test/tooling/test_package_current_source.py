"""Release archives must reflect Git blobs and exclude runtime/private material."""
import importlib.util
import json
import subprocess
import zipfile
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location("package_source", Path(__file__).resolve().parents[2] / "scripts/package_current_source.py")
package = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(package)


def git(repo, *args):
    result = subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)
    return result.stdout.decode().strip()


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.name", "Package fixture")
    git(tmp_path, "config", "user.email", "fixture@example.invalid")
    for name in package.ROOT_FILES | {"frontend/src/app.ts", "backend/app/main.py", "docs/history/notes.md", "models/manifest.json", "test/example.py", "frontend/node_modules/dep.js", "backend/data/runtime.db", "test/fixtures/runtime/old/file.py", "outputs/old.zip", "backups/snapshot.db"}:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("committed fixture\n", encoding="utf-8")
    git(tmp_path, "add", "-f", ".")
    git(tmp_path, "commit", "-qm", "fixture")
    return tmp_path


def test_committed_content_only_and_reproducible_zip(repo):
    policy = repo / "backend/app/password_policy.py"
    policy.write_text("def validate_password(value): return bool(value)\n")
    git(repo, "add", "backend/app/password_policy.py")
    git(repo, "commit", "-qm", "public password validation source")
    commit = git(repo, "rev-parse", "HEAD")
    (repo / "frontend/src/app.ts").write_text("uncommitted change")
    (repo / "frontend/src/new.ts").write_text("untracked change")
    first = package.package_source(repo)
    archive = repo / first["archive"]["path"]
    with zipfile.ZipFile(archive) as bundle:
        assert bundle.read("frontend/src/app.ts") == b"committed fixture\n"
        assert "frontend/src/new.ts" not in bundle.namelist()
    names = {item["path"] for item in first["files"]}
    assert "backend/app/password_policy.py" in names
    assert "docs/history/notes.md" in names and "models/manifest.json" in names
    assert not any("node_modules" in name or "runtime/" in name or name.startswith(("outputs/", "backups/")) for name in names)
    second = package.package_source(repo, revision=commit)
    assert first["archive"]["sha256"] == second["archive"]["sha256"]
    assert first["files"] == second["files"]
    assert second["source_commit"] == commit and not second["dependencies_bundled"]
    manifest = json.loads((repo / "outputs/kou-current-source-manifest.json").read_text())
    assert manifest == second


@pytest.mark.parametrize("name", ["backend/.env", "docs/Password.txt.txt", "deploy/signing.pem"])
def test_committed_secret_candidates_are_rejected_without_publishing(repo, name):
    target = repo / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("synthetic secret candidate")
    git(repo, "add", "-f", name)
    git(repo, "commit", "-qm", "secret fixture")
    with pytest.raises(package.PackageError, match="Secret candidate"):
        package.package_source(repo)
    assert not (repo / "outputs/kou-current-source.zip").exists()


def test_blob_tampering_and_private_key_content_are_rejected(repo):
    expected = {"README.md": {"git_object": "0" * 40, "mode": "100644"}}
    archive = repo / "bad.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("README.md", "changed content")
    with pytest.raises(package.PackageError, match="differs"):
        package.verify_archive(archive, expected, "sha1")
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("README.md", "-----BEGIN PRIVATE KEY-----\nsynthetic")
    with pytest.raises(package.PackageError, match="Private-key"):
        package.verify_archive(archive, expected, "sha1")
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("../README.md", "outside")
    with pytest.raises(package.PackageError, match="Unsafe"):
        package.verify_archive(archive, expected, "sha1")


def test_external_traversal_and_symlink_paths_are_rejected(repo):
    for output in [repo.parent / "outside.zip", Path("outputs/../outside.zip")]:
        with pytest.raises(package.PackageError):
            package.package_source(repo, output=output)
    object_id = git(repo, "hash-object", "README.md")
    git(repo, "update-index", "--add", "--cacheinfo", f"120000,{object_id},backend/app/link")
    git(repo, "commit", "-qm", "symlink fixture")
    with pytest.raises(package.PackageError, match="Symlink"):
        package.package_source(repo)


def test_failed_validation_preserves_previous_publication(repo, monkeypatch):
    package.package_source(repo)
    outputs = [repo / "outputs/kou-current-source.zip", repo / "outputs/kou-current-source-manifest.json"]
    before = [path.read_bytes() for path in outputs]
    def fail(*_args):
        raise package.PackageError("synthetic validation failure")
    monkeypatch.setattr(package, "verify_archive", fail)
    with pytest.raises(package.PackageError, match="validation failure"):
        package.package_source(repo)
    assert before == [path.read_bytes() for path in outputs]


def test_second_publish_error_rolls_back_both_files(repo, monkeypatch):
    package.package_source(repo)
    outputs = [repo / "outputs/kou-current-source.zip", repo / "outputs/kou-current-source-manifest.json"]
    before = [path.read_bytes() for path in outputs]
    original_replace = package.os.replace
    def fail_manifest(source, target):
        if Path(source).name == "manifest.json":
            raise OSError("synthetic publication failure")
        return original_replace(source, target)
    monkeypatch.setattr(package.os, "replace", fail_manifest)
    with pytest.raises(OSError, match="publication failure"):
        package.package_source(repo)
    assert before == [path.read_bytes() for path in outputs]


def test_concurrent_publication_lock_is_not_overwritten(repo):
    package.package_source(repo)
    archive = repo / "outputs/kou-current-source.zip"
    before = archive.read_bytes()
    lock = repo / "test/fixtures/runtime/package-current.lock"
    lock.write_text("another run")
    with pytest.raises(package.PackageError, match="Another publication"):
        package.package_source(repo)
    assert lock.read_text() == "another run" and archive.read_bytes() == before
