"""Run local tests or explicitly selected live checks, sequentially, with evidence."""
import argparse
import ast
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
BROWSER = ROOT / "test/browser"
INTEGRATION = ROOT / "test/integration"


def main(argv=None):
    parser = argparse.ArgumentParser(description="現行テストを順に実行し、結果をartifactsへ保存する")
    parser.add_argument("--suite", choices=("local", "unit", "syntax", "browser", "integration", "all"), default="local")
    parser.add_argument("--case", action="append", default=[], help="browser/integrationのファイル名（拡張子は省略可）")
    parser.add_argument("--collect-only", action="store_true", help="試験を検出する。稼働アプリの操作は実行しない")
    parser.add_argument("--list", action="store_true", help="利用可能な試験ファイルだけ表示")
    parser.add_argument("--timeout", type=int, default=900, help="各コマンドの制限秒")
    args = parser.parse_args(argv)
    if args.timeout < 1:
        parser.error("timeoutは1秒以上を指定してください")
    browser_files = sorted(path for path in BROWSER.glob("verify-*.mjs") if path.name != "verify-journal-restart.mjs") + [ROOT / "test/tooling/check_board.cjs"]
    integration_files = [INTEGRATION / "test_snapshot.py", INTEGRATION / "verify-deletion-restore.py", INTEGRATION / "audit-personalization.py", BROWSER / "verify-journal-restart.mjs"]
    if args.list:
        print(json.dumps({"unit": ["test/backend", "test/tooling"], "browser": [p.stem for p in browser_files], "integration": [p.stem for p in integration_files]}, ensure_ascii=False, indent=2))
        return 0
    if args.case and args.suite not in ("browser", "integration"):
        parser.error("caseはbrowserまたはintegrationと組み合わせてください")
    selected = browser_files if args.suite == "browser" else integration_files
    if args.case:
        names = {Path(name).stem for name in args.case}
        known = {path.stem for path in selected}
        if names - known:
            parser.error("未登録のcase: " + ", ".join(sorted(names - known)))
        selected = [path for path in selected if path.stem in names]
        if args.suite == "browser":
            browser_files = selected
        else:
            integration_files = selected

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    evidence = ROOT / "artifacts/test-runs" / stamp
    evidence.mkdir(parents=True)
    (ROOT / "artifacts/browser").mkdir(parents=True, exist_ok=True)
    fixtures = ROOT / "test/fixtures/runtime" / stamp
    fixtures.mkdir(parents=True)
    report = {"suite": args.suite, "mode": "collection" if args.collect_only else "execution", "results": [], "not_executed": [], "passed": False}
    node = shutil.which("node") or "node"

    def execute(label, command, input_text=None):
        started = time.monotonic()
        result = {"name": label, "command": command}
        try:
            process = subprocess.run(command, cwd=ROOT, input=input_text, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=args.timeout, check=False)
            result["exit_code"] = process.returncode
            stdout, stderr = process.stdout, process.stderr
        except (OSError, subprocess.TimeoutExpired) as error:
            result["exit_code"] = None
            result["error"] = type(error).__name__
            stdout, stderr = "", str(error)
        result["seconds"] = round(time.monotonic() - started, 3)
        result["passed"] = result["exit_code"] == 0
        for stream, text in (("stdout", stdout), ("stderr", stderr)):
            path = evidence / f"{label}-{stream}.txt"
            path.write_text(text, encoding="utf-8")
            result[stream] = path.relative_to(ROOT).as_posix()
        report["results"].append(result)
        print(f"{'PASS' if result['passed'] else 'FAIL'} {label} ({result['seconds']:.3f}s)", flush=True)
        return result["passed"]

    if args.suite in ("local", "unit", "all"):
        command = [sys.executable, "-m", "pytest", "test/backend", "test/tooling", "-q", "--basetemp=" + str(fixtures / "pytest")]
        command += ["--collect-only"] if args.collect_only else ["--junitxml=" + str(evidence / "pytest.xml")]
        execute("pytest-collect" if args.collect_only else "pytest", command)
    if args.suite in ("local", "syntax", "all"):
        for path in sorted(BROWSER.glob("*.mjs")):
            execute("syntax-" + path.stem, [node, "--check", str(path)])
        execute("syntax-check_board", [node, "--check", str(ROOT / "test/tooling/check_board.cjs")])
        for path in sorted(INTEGRATION.glob("*.py")):
            try:
                ast.parse(path.read_text(encoding="utf-8-sig"))
                report["results"].append({"name": "syntax-" + path.stem, "passed": True, "scope": "Python parse only"})
            except SyntaxError:
                report["results"].append({"name": "syntax-" + path.stem, "passed": False, "scope": "Python parse only"})
        execute("browser-dependencies", [node, "--input-type=module", "-e", "import {createRequire} from 'node:module';import path from 'node:path';const r=createRequire(path.resolve('test/browser/package.json'));r.resolve('@playwright/test');r.resolve('@axe-core/playwright');console.log('Browser dependencies resolve');"])
    live = []
    if args.suite in ("browser", "all"):
        live.extend(browser_files)
    if args.suite in ("integration", "all"):
        live.extend(integration_files)
    for path in live:
        if args.collect_only:
            report["not_executed"].append(path.relative_to(ROOT).as_posix())
            continue
        if path.name == "audit-personalization.py":
            execute(path.stem, ["docker", "compose", "-p", "kou-community", "-f", str(ROOT / "community/compose.yaml"), "exec", "-T", "app", "python", "-"], path.read_text(encoding="utf-8-sig"))
        else:
            execute(path.stem, [node if path.suffix in (".mjs", ".cjs") else sys.executable, str(path)])
    if args.collect_only and live:
        report["results"].append({"name": "live-test-inventory", "passed": all(path.is_file() for path in live), "scope": "File presence only; listed tests were not executed"})
    report["passed"] = all(item["passed"] for item in report["results"])
    report["scope"] = "Collection/syntax is not proof of browser or live database behavior. No build, dependency installation, or app startup is performed."
    output = evidence / "result.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output.relative_to(ROOT).as_posix(), flush=True)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
