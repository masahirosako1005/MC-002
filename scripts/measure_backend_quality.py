"""Local scans of the current community production Python source; no upload."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "backend/app"
TOOLS = ROOT / ".tools/quality-venv/Scripts"


def run(command: list[str], destination: Path, *, direct_file: bool = False) -> dict:
    started = time.monotonic()
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                            env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"})
    (destination.with_suffix(".stdout.txt") if direct_file else destination).write_text(result.stdout, encoding="utf-8")
    destination.with_suffix(".stderr.txt").write_text(result.stderr, encoding="utf-8")
    return {"command": command, "exit_code": result.returncode, "seconds": round(time.monotonic() - started, 3)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9-]+", args.phase):
        parser.error("phase must contain only lowercase letters, digits and hyphens")
    output = ROOT / "artifacts/community/quality" / args.phase
    output.mkdir(parents=True, exist_ok=True)
    sources = {str(p.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(SOURCE.rglob("*.py"))}
    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "phase": args.phase,
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()),
        "scope": "Every .py under backend/app. Tests, QA scripts and dependency caches are not production runtime source. The retired old/v1.1 source tree is no longer part of the workspace.",
        "comparison_note": "The daytrip phases include six added production modules and removal of the unused LocalClassifier code from images.py. Source hashes and scope must be compared; fewer findings caused by retired code are not scored as product-quality gains.",
        "files": sources,
        "source_count": len(sources),
        "config_sha256": hashlib.sha256((ROOT / "quality/ruff.toml").read_bytes()).hexdigest(),
        "runs": {},
    }
    py = str(TOOLS / "python.exe")
    report["runs"]["ruff"] = run([py, "-m", "ruff", "check", "--no-cache", "--config", "quality/ruff.toml", "--output-format", "json", str(SOURCE)], output / "ruff.json")
    report["runs"]["complexity"] = run([py, "-m", "ruff", "check", "--no-cache", "--isolated", "--select", "C90", "--output-format", "json", str(SOURCE)], output / "complexity.json")
    report["runs"]["bandit"] = run([py, "-m", "bandit", "-r", str(SOURCE), "-f", "json", "--ignore-nosec", "-o", str(output / "bandit.json")], output / "bandit.json", direct_file=True)
    for name in ("ruff", "complexity"):
        findings = json.loads((output / f"{name}.json").read_text(encoding="utf-8"))
        report[name] = {"total": len(findings), "by_rule": {code: sum(item["code"] == code for item in findings) for code in sorted({item["code"] for item in findings})}}
    bandit = json.loads((output / "bandit.json").read_text(encoding="utf-8"))
    report["bandit"] = {"total": len(bandit["results"]), "errors": bandit.get("errors", []), "metrics": bandit["metrics"]["_totals"], "severity": {level: sum(item["issue_severity"] == level for item in bandit["results"]) for level in ("LOW", "MEDIUM", "HIGH")}}
    (output / "summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("phase", "source_count", "ruff", "complexity", "bandit")}))


if __name__ == "__main__":
    main()
