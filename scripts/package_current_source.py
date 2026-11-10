"""Package committed current source, never the working tree or runtime data.

Run after committing the intended release: python -B scripts/package_current_source.py
An explicit --commit is supported. Dependencies and ignored local models are not bundled.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import zipfile
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
DIRECTORIES = {"frontend", "backend", "assets", "deploy", "scripts", "test", "quality", "models", "docs"}
ROOT_FILES = {"Dockerfile", "compose.yaml", ".dockerignore", ".gitignore", "README.md", "DESIGN.md", "TASKS.md", "pytest.ini", "AGENTS.md"}
EXCLUDED_PARTS = {"node_modules", ".venv", "venv", ".git", "__pycache__", ".pytest_cache", ".ruff_cache", ".cache", "cache", "caches", "dist", "backups", "data", "outputs", "artifacts", ".tools"}
PRIVATE_KEY = re.compile(rb"(?m)^-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----\r?$")


class PackageError(RuntimeError):
    """A release failed validation; do not publish its partial archive."""


def safe_path(root: Path, path: Path) -> Path:
    target = path if path.is_absolute() else root / path
    if ".." in target.parts:
        raise PackageError("Parent traversal is not allowed")
    target = target.absolute()
    if target == root or not target.is_relative_to(root):
        raise PackageError("The output and temporary paths must stay inside the project")
    if target.resolve() != target:
        raise PackageError("Redirected paths are not allowed")
    for part in [target, *target.parents]:
        if part.exists() or part.is_symlink():
            info = part.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                raise PackageError("Symlinks and reparse points are not allowed")
        if part == root:
            break
    return target


def git(root: Path, *args: str) -> bytes:
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_TERMINAL_PROMPT="0")
    result = subprocess.run(
        ["git", "-c", f"core.attributesFile={os.devnull}", "--literal-pathspecs", *args],
        cwd=root, env=env, capture_output=True, check=False,
    )
    if result.returncode:
        # Git diagnostics may quote arbitrary local configuration; keep them out of reports.
        raise PackageError(f"Git {args[0]} failed (exit {result.returncode})")
    return result.stdout


def valid_member(name: str) -> None:
    path = PurePosixPath(name)
    if (not name or path.is_absolute() or "\\" in name or ":" in name
            or any(part in {".", ".."} for part in name.split("/"))
            or any(ord(char) < 32 for char in name)):
        raise PackageError("Unsafe archive member path")


def included(name: str) -> bool:
    valid_member(name)
    parts = PurePosixPath(name).parts
    if name not in ROOT_FILES and parts[0] not in DIRECTORIES:
        return False
    lowered = [part.lower() for part in parts]
    if (any(part in EXCLUDED_PARTS or part.endswith("-tmp") for part in lowered[:-1])
            or lowered[:3] == ["test", "fixtures", "runtime"]):
        return False
    filename = lowered[-1]
    public_password_source = name in {"backend/app/password_policy.py", "frontend/src/PasswordChange.tsx"}
    if (filename == ".env" or filename.startswith(".env.") or (filename.startswith("password") and not public_password_source)
            or filename in {"credentials.json", "credentials.yaml", "credentials.yml", "secrets.json", "secrets.yaml", "secrets.yml", ".npmrc", ".pypirc", "id_rsa", "id_ed25519", ".import-key"}
            or filename.endswith((".pem", ".key", ".p12", ".pfx"))):
        raise PackageError(f"Secret candidate in committed source: {name}")
    return not (re.search(r"\.(?:db|sqlite|sqlite3)(?:[-.].*)?$", filename)
                or filename.endswith((".pyc", ".pyo", ".zip", ".bundle", ".coverage")))


def inventory(root: Path, commit: str) -> dict[str, dict[str, str]]:
    files = {}
    folded = set()
    for entry in git(root, "ls-tree", "-r", "-z", "--full-tree", commit).split(b"\0"):
        if not entry:
            continue
        metadata, raw_name = entry.split(b"\t", 1)
        mode, kind, object_id = metadata.decode("ascii").split()
        name = raw_name.decode("utf-8", errors="strict")
        if not included(name):
            continue
        if kind != "blob" or mode not in {"100644", "100755"}:
            raise PackageError(f"Symlink, submodule or unsupported mode: {name}")
        if name.casefold() in folded:
            raise PackageError("Archive paths collide on case-insensitive filesystems")
        folded.add(name.casefold())
        files[name] = {"git_object": object_id, "mode": mode}
    if not ROOT_FILES.issubset(files) or not any(name.startswith("frontend/src/") for name in files) or not any(name.startswith("backend/app/") for name in files):
        raise PackageError("The selected commit does not contain the current root source layout")
    return dict(sorted(files.items()))


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify_archive(archive: Path, expected: dict[str, dict[str, str]], object_format: str) -> list[dict]:
    files = []
    seen = set()
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            name = member.filename.rstrip("/")
            valid_member(name)
            if member.is_dir():
                if not any(item.startswith(f"{name}/") for item in expected):
                    raise PackageError("Unexpected directory in archive")
                continue
            if name not in expected or name in seen or member.flag_bits & 1:
                raise PackageError("Unexpected, duplicate or encrypted archive member")
            seen.add(name)
            content = bundle.read(member)  # Also verifies ZIP CRC before publication.
            if PRIVATE_KEY.search(content):
                raise PackageError(f"Private-key candidate in committed source: {name}")
            blob = hashlib.new(object_format, f"blob {len(content)}\0".encode() + content)
            if blob.hexdigest() != expected[name]["git_object"]:
                raise PackageError(f"Archive differs from the committed blob: {name}")
            files.append({"path": name, "size_bytes": len(content), "sha256": hashlib.sha256(content).hexdigest(), **expected[name]})
    if seen != expected.keys():
        raise PackageError("Archive is missing committed files (check export-ignore attributes)")
    return sorted(files, key=lambda item: item["path"])


def publish(archive: Path, manifest: Path, output: Path, report: Path, temporary: Path) -> None:
    """Atomically replace each complete file; roll back both on a reported error."""
    previous = {}
    for target in (output, report):
        if target.exists():
            if not target.is_file():
                raise PackageError("A publication destination is not a regular file")
            copy = temporary / f"previous-{target.name}"
            shutil.copyfile(target, copy)
            previous[target] = copy
    replaced = []
    try:
        for staged, target in ((archive, output), (manifest, report)):
            os.replace(staged, target)
            replaced.append(target)
    except OSError:
        for target in reversed(replaced):
            if target in previous:
                os.replace(previous[target], target)
            else:
                # Only the new file created by this run is moved back, not deleted.
                os.replace(target, temporary / f"unpublished-{target.name}")
        raise


@contextmanager
def publication_lock(root: Path):
    """Two concurrent generators must not interleave ZIP/manifest replacement."""
    lock = safe_path(root, root / "test/fixtures/runtime/package-current.lock")
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise PackageError("Another publication holds package-current.lock; inspect it before retrying") from error
    os.close(descriptor)
    try:
        yield
    finally:
        lock.unlink()  # Only this run's exclusive, newly created lock file.


def package_source(root: Path = ROOT, revision: str = "HEAD", output: Path = Path("outputs/kou-current-source.zip")) -> dict:
    root = root.absolute()
    if root != ROOT and not root.is_relative_to(ROOT / "test/fixtures/runtime"):
        raise PackageError("Repository must be the project or its isolated test fixture")
    if root.resolve() != root:
        raise PackageError("Redirected repository path")
    if not revision or revision.startswith("-") or any(ord(char) < 32 for char in revision):
        raise PackageError("Invalid commit reference")
    if Path(git(root, "rev-parse", "--show-toplevel").decode().strip()).resolve() != root:
        raise PackageError("Repository root does not match the project")
    commit = git(root, "rev-parse", "--verify", "--end-of-options", f"{revision}^{{commit}}").decode().strip()
    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", commit):
        raise PackageError("Commit resolution failed")
    output = safe_path(root, output)
    if output.parent != root / "outputs" or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*\.zip", output.name):
        raise PackageError("Archive must be a ZIP directly inside project outputs")
    report = safe_path(root, output.with_name(f"{output.stem}-manifest.json"))
    files = inventory(root, commit)
    temporary = safe_path(root, root / "test/fixtures/runtime" / f"package-{uuid4().hex}")
    temporary.mkdir(parents=True, exist_ok=False)
    archive = temporary / "source.zip"
    args = ["archive", "--format=zip", "-0", f"--output={archive}", commit, "--", *files]
    if len(subprocess.list2cmdline(["git", *args])) > 29000:
        raise PackageError("Archive file list exceeds the supported Windows command length")
    git(root, *args)
    object_format = git(root, "rev-parse", "--show-object-format").decode().strip()
    if object_format not in {"sha1", "sha256"}:
        raise PackageError("Unsupported Git object format")
    verified = verify_archive(archive, files, object_format)
    value = {
        "schema_version": 1, "source_commit": commit,
        "generated_at": datetime.now(UTC).isoformat(),
        "source": "git archive of committed blobs; working-tree and untracked files are not included",
        "dependencies_bundled": False,
        "limitations": ["Installed dependencies, ignored model weights, runtime databases and backups are not bundled.", "Secret checks are conservative heuristics, not a complete security audit.", "ZIP bytes are reproducible for the same commit and Git implementation; generated_at changes.", "Each output file is atomically replaced. A process/OS crash between the two replacements can leave a mismatched pair; verify archive.sha256 before use."],
        "git_version": git(root, "--version").decode().strip(),
        "archive": {"path": output.relative_to(root).as_posix(), "size_bytes": archive.stat().st_size, "sha256": digest(archive)},
        "file_count": len(verified), "total_size_bytes": sum(item["size_bytes"] for item in verified),
        "files": verified,
    }
    staged_report = temporary / "manifest.json"
    staged_report.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    # Recheck immediately before replacing outputs; never follow redirected destinations.
    safe_path(root, output)
    safe_path(root, report)
    with publication_lock(root):
        publish(archive, staged_report, output, report, temporary)
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", default="HEAD", help="Commit/tag to resolve; default HEAD")
    parser.add_argument("--output", type=Path, default=Path("outputs/kou-current-source.zip"))
    args = parser.parse_args()
    try:
        result = package_source(revision=args.commit, output=args.output)
    except (PackageError, OSError, UnicodeError, zipfile.BadZipFile) as error:
        print(f"Source package was not published: {error}", file=sys.stderr)
        return 1
    print(json.dumps({key: result[key] for key in ("source_commit", "archive", "file_count")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
