"""Package the committed project and its revision history, never runtime data."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import zipfile


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs"


def git(*arguments: str) -> bytes:
    return subprocess.check_output(["git", *arguments], cwd=ROOT)


def main() -> None:
    # Refuse to publish a mixture of committed and edited files.
    if git("status", "--porcelain").strip():
        raise SystemExit("変更を確認してコミットしてから配布物を作成してください。")
    revision = git("rev-parse", "HEAD").decode().strip()
    files = git("ls-files", "-z").decode("utf-8").split("\0")
    entries: list[dict[str, str | int]] = []
    for name in filter(None, files):
        path = ROOT / name
        lowered = name.lower()
        if (
            path.is_symlink()
            or not path.resolve().is_relative_to(ROOT)
            or "/node_modules/" in lowered
            or lowered.startswith(("data/", ".venv/", ".tools/", "artifacts/browser-results/"))
            or "password" in lowered
            or path.name == ".env"
            or path.suffix.lower() in {".db", ".sqlite", ".sqlite3", ".pyc"}
        ):
            raise SystemExit(f"配布しない種類のファイルがGitに含まれています: {name}")
        payload = path.read_bytes()
        entries.append({"path": name, "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()})
    OUTPUT.mkdir(exist_ok=True)
    bundle = OUTPUT / "tang-you-chi-history.bundle"
    git("bundle", "create", str(bundle), "--all")
    git("bundle", "verify", str(bundle))
    manifest = {"revision": revision, "files": entries, "history_sha256": hashlib.sha256(bundle.read_bytes()).hexdigest()}
    (OUTPUT / "release-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    archive = OUTPUT / "tang-you-chi-source.zip"
    temporary = OUTPUT / "tang-you-chi-source.zip.tmp"
    with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as package:
        for entry in entries:
            package.write(ROOT / str(entry["path"]), "tang-you-chi/" + str(entry["path"]))
        package.write(bundle, "tang-you-chi/history.bundle")
        package.writestr("tang-you-chi/release-manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    with zipfile.ZipFile(temporary) as package:
        bad = package.testzip()
        if bad:
            raise SystemExit(f"圧縮内容の検証に失敗しました: {bad}")
    temporary.replace(archive)
    print(json.dumps({"files": len(entries), "archive_bytes": archive.stat().st_size, "revision": revision}, ensure_ascii=False))


if __name__ == "__main__":
    main()
