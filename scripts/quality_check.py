"""Measure locally, retain all findings, and reject regressions against a fixed baseline."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
FRONT = ROOT / "artifacts/community/frontend-quality"
BACK = ROOT / "artifacts/community/quality"
BASE_FRONT = "daytrip-wa-verified"
BASE_BACK = "daytrip-final"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def normalized_path(value: str) -> str:
    value = value.replace("\\", "/")
    # The preserved baseline still uses community/backend/app; both layouts
    # identify the same current file without rewriting historical evidence.
    for marker in ("backend/app/", "src/"):
        if marker in value:
            return marker + value.split(marker, 1)[1]
    return value


def findings(front: str, back: str) -> Counter:
    """Location-independent identities preserve findings after source line moves."""
    rows = []
    for item in read_json(FRONT / f"{front}-oxlint.json")["diagnostics"]:
        rows.append(("oxlint", normalized_path(item["filename"]), item["code"], item["message"]))
    for item in read_json(FRONT / f"{front}-stylelint.json"):
        for warning in item["warnings"]:
            rows.append(("stylelint", normalized_path(item["source"]), warning["rule"], warning["text"]))
    for name in ("ruff", "complexity"):
        for item in read_json(BACK / back / f"{name}.json"):
            rows.append((name, normalized_path(item["filename"]), item["code"], item["message"]))
    for item in read_json(BACK / back / "bandit.json")["results"]:
        rows.append(("bandit", normalized_path(item["filename"]), item["test_id"], item["issue_text"]))
    return Counter(rows)


def compare(before: Counter, after: Counter) -> dict:
    added, resolved = after - before, before - after
    def expand(values):
        return [dict(tool=k[0], file=k[1], rule=k[2], message=k[3], count=v)
                for k, v in sorted(values.items())]
    tools = ("bandit", "complexity", "oxlint", "ruff", "stylelint")
    return {
        "counts": {tool: {"before": sum(v for k, v in before.items() if k[0] == tool),
                          "after": sum(v for k, v in after.items() if k[0] == tool)} for tool in tools},
        "new": expand(added), "resolved": expand(resolved),
        "remaining": sum(after.values()), "new_count": sum(added.values()),
    }


def validate_measurements(front: dict, back: dict) -> list[str]:
    errors = []
    for name, accepted in (("oxlint", (0, 1)), ("stylelint", (0, 2)), ("tsc", (0,))):
        if front.get("results", {}).get(name, {}).get("exit") not in accepted:
            errors.append(f"{name}: missing, incomplete, or failed execution")
    for name in ("ruff", "complexity", "bandit"):
        if back.get("runs", {}).get(name, {}).get("exit_code") not in (0, 1):
            errors.append(f"{name}: missing, incomplete, or failed execution")
    if back.get("bandit", {}).get("errors"):
        errors.append("Bandit could not scan one or more files")
    return errors


def validate_stylelint(rows: list[dict]) -> list[str]:
    errors = []
    for row in rows:
        if row.get("parseErrors") or row.get("invalidOptionWarnings"):
            errors.append(f"Stylelint could not parse or validate {normalized_path(row.get('source', '?'))}")
        if row.get("errored") and not row.get("warnings") and not row.get("parseErrors") and not row.get("invalidOptionWarnings"):
            errors.append(f"Stylelint returned an unexplained error for {normalized_path(row.get('source', '?'))}")
    return errors


def changed_files_with_retained_findings(before: Counter, after: Counter, old_hashes: dict, new_hashes: dict) -> list[str]:
    """Identical rule counts in edited files cannot prove that no flaw was replaced."""
    retained = before & after
    return sorted({key[1] for key in retained
                   if old_hashes.get(key[1]) != new_hashes.get(key[1])})


def gate_status(delta: dict, errors: list[str]) -> str:
    if errors:
        return "incomplete"
    if delta["new_count"]:
        return "regression"
    if delta.get("review_required_files"):
        return "review-required"
    return "clean" if delta["remaining"] == 0 else "no-new-findings-existing-debt"


def run(command: list[str], log: Path, *, timeout: int = 900) -> int:
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=timeout,
                            env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"})
    log.write_text(result.stdout + result.stderr, encoding="utf-8")
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", help="unique lowercase measurement name")
    parser.add_argument("--reports-only", action="store_true", help="compare existing measurements; does not claim tests ran")
    parser.add_argument("--skip-tests", action="store_true", help="static measurements only; tests marked not-run")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9-]+", args.phase) or args.phase in (BASE_FRONT, BASE_BACK):
        parser.error("use a new lowercase measurement name, not the preserved baseline")
    if not args.reports_only and ((FRONT / f"{args.phase}-manifest.json").exists() or (BACK / args.phase / "summary.json").exists()):
        parser.error("measurement name already exists; use a new name to preserve history")
    output = ROOT / "artifacts/quality" / args.phase
    if (output / "summary.json").exists():
        parser.error("this report already exists; do not overwrite measurement history")
    output.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    test_status = "not-run"
    test_runtime = None
    try:
        if not args.reports_only:
            # Serial execution bounds peak memory on the 16 GB presentation PC.
            node = shutil.which("node") or "C:/Program Files/nodejs/node.exe"
            run([node, "frontend/scripts/measure-quality.mjs", args.phase], output / "frontend.log")
            run([sys.executable, "scripts/measure_backend_quality.py", args.phase], output / "backend.log")
            if not args.skip_tests:
                runtime_root = ROOT / "test/fixtures/runtime"
                if runtime_root.resolve() != runtime_root:
                    raise ValueError("Test runtime must not be redirected outside its project path")
                test_runtime = runtime_root / f"quality-{args.phase}-{uuid4().hex}"
                test_runtime.mkdir(parents=True, exist_ok=False)
                exit_code = run([sys.executable, "-m", "pytest", "-c", str(ROOT / "pytest.ini"), "test/backend", "test/tooling", "-q",
                                 f"--basetemp={test_runtime / 'pytest'}", "-o", f"cache_dir={test_runtime / 'cache'}",
                                 f"--junitxml={output / 'tests.xml'}"], output / "tests.log")
                test_status = "passed" if exit_code == 0 else "failed"
                if exit_code:
                    errors.append("Backend/tooling tests failed or did not run")
        front = read_json(FRONT / f"{args.phase}-manifest.json")
        back = read_json(BACK / args.phase / "summary.json")
        errors.extend(validate_measurements(front, back))
        errors.extend(validate_stylelint(read_json(FRONT / f"{args.phase}-stylelint.json")))
        old_front = read_json(FRONT / f"{BASE_FRONT}-manifest.json")
        old_back = read_json(BACK / BASE_BACK / "summary.json")
        if front["configs"] != old_front["configs"]:
            errors.append("Frontend rule configuration differs from the fixed baseline")
        if back["config_sha256"] != old_back["config_sha256"]:
            errors.append("Backend rule configuration differs from the fixed baseline")
        before, after = findings(BASE_FRONT, BASE_BACK), findings(args.phase, args.phase)
        delta = compare(before, after)
        old_hashes = {**{f"src/{k}": v for k, v in old_front["files"].items()},
                      **{normalized_path(k): v for k, v in old_back["files"].items()}}
        new_hashes = {**{f"src/{k}": v for k, v in front["files"].items()},
                      **{normalized_path(k): v for k, v in back["files"].items()}}
        delta["review_required_files"] = changed_files_with_retained_findings(before, after, old_hashes, new_hashes)
    except (OSError, KeyError, ValueError, subprocess.SubprocessError) as exc:
        errors.append(f"Measurement unavailable: {type(exc).__name__}: {exc}")
        delta = {"counts": {}, "new": [], "resolved": [], "remaining": None, "new_count": None}
    status = gate_status(delta, errors)
    report = {"measured_at": datetime.now(timezone.utc).isoformat(), "phase": args.phase,
              "baseline": {"frontend": BASE_FRONT, "backend": BASE_BACK},
              "status": status, "tests": test_status, "errors": errors, **delta,
              "test_runtime": test_runtime.relative_to(ROOT).as_posix() if test_runtime else None,
              "limits": "Static findings are not an app score, certification, security guarantee, or usability test. Existing debt remains visible. No upload or automatic baseline reset."}
    (output / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [f"# 品質測定 {args.phase}", "", f"判定: `{status}` / 動作試験: `{test_status}`", "",
             "| ツール | 改修前 | 今回 | 差分 |", "|---|---:|---:|---:|"]
    for name, counts in delta["counts"].items():
        lines.append(f"| {name} | {counts['before']} | {counts['after']} | {counts['after'] - counts['before']:+d} |")
    lines += ["", "新規指摘・解消指摘・未完了の詳細は同じフォルダのsummary.jsonに保存。", "",
              "既存指摘が残る判定は全面合格ではない。UI・権限・保存の動作試験と別に扱う。"]
    lines += [f"- {error}" for error in errors]
    (output / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"phase": args.phase, "status": status, "tests": test_status, "counts": delta["counts"], "errors": errors}, ensure_ascii=False))
    return 1 if status in ("incomplete", "regression", "review-required") else 0


if __name__ == "__main__":
    raise SystemExit(main())
