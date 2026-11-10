"""Regression gates must not hide missing scans or offset one new flaw with a fix."""
from collections import Counter
import importlib.util
from pathlib import Path
import json
import pytest
import sys

spec = importlib.util.spec_from_file_location("quality_check", Path(__file__).resolve().parents[2] / "scripts/quality_check.py")
quality = importlib.util.module_from_spec(spec)
spec.loader.exec_module(quality)


def test_new_issue_is_not_cancelled_by_an_unrelated_resolution():
    before = Counter({("ruff", "a.py", "A", "old"): 1})
    after = Counter({("ruff", "b.py", "B", "new"): 1})
    result = quality.compare(before, after)
    assert result["new_count"] == 1
    assert len(result["resolved"]) == 1
    assert quality.gate_status(result, []) == "regression"


def test_existing_debt_is_not_called_clean():
    issues = Counter({("stylelint", "src/a.css", "rule", "message"): 2})
    assert quality.gate_status(quality.compare(issues, issues), []) == "no-new-findings-existing-debt"


def test_missing_or_failed_tool_never_passes():
    errors = quality.validate_measurements({}, {})
    assert len(errors) == 6
    assert quality.gate_status({"remaining": None, "new_count": None}, errors) == "incomplete"


def test_bandit_scan_errors_are_not_zero_findings_success():
    front = {"results": {name: {"exit": 0} for name in ("oxlint", "stylelint", "tsc")}}
    back = {"runs": {name: {"exit_code": 0} for name in ("ruff", "complexity", "bandit")}, "bandit": {"errors": ["unreadable"]}}
    assert quality.validate_measurements(front, back)


def test_paths_normalize_platform_prefix_but_preserve_file_identity():
    assert quality.normalized_path('C:\\work\\community\\backend\\app\\posts.py') == 'community/backend/app/posts.py'
    assert quality.normalized_path('/work/src/Composer.tsx') == 'src/Composer.tsx'


def test_duplicate_new_finding_is_detected():
    key = ("bandit", "app.py", "B608", "SQL")
    assert quality.compare(Counter({key: 1}), Counter({key: 2}))["new_count"] == 1


def test_same_count_in_edited_file_requires_review_instead_of_false_pass():
    key = ("oxlint", "src/App.tsx", "react(rule)", "same text")
    findings = Counter({key: 1})
    delta = quality.compare(findings, findings)
    delta["review_required_files"] = quality.changed_files_with_retained_findings(
        findings, findings, {key[1]: "before-hash"}, {key[1]: "after-hash"})
    assert delta["review_required_files"] == ["src/App.tsx"]
    assert quality.gate_status(delta, []) == "review-required"


def test_stylelint_parse_or_config_errors_are_not_clean():
    for key in ("parseErrors", "invalidOptionWarnings"):
        assert quality.validate_stylelint([{"source": "src/a.css", key: [{"text": "bad"}], "warnings": []}])
    assert quality.validate_stylelint([{"source": "src/a.css", "errored": True, "warnings": []}])
    assert quality.validate_stylelint([{"source": "src/a.css", "warnings": [], "errored": False}]) == []


def fake_reports(tmp_path, monkeypatch, bad_css=False):
    monkeypatch.setattr(quality, "ROOT", tmp_path)
    monkeypatch.setattr(quality, "FRONT", tmp_path / "front")
    monkeypatch.setattr(quality, "BACK", tmp_path / "back")
    def write(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")
    for name in (quality.BASE_FRONT, "current"):
        write(quality.FRONT / f"{name}-manifest.json", {"configs": {}, "files": {}, "results": {k: {"exit": 0 if k != "stylelint" or not bad_css else 2} for k in ("oxlint", "stylelint", "tsc")}})
        write(quality.FRONT / f"{name}-oxlint.json", {"diagnostics": []})
        write(quality.FRONT / f"{name}-stylelint.json", [{"source": "src/a.css", "warnings": [], "parseErrors": ["broken CSS"] if bad_css and name == "current" else []}])
    for name in (quality.BASE_BACK, "current"):
        write(quality.BACK / name / "summary.json", {"config_sha256": "fixed", "files": {}, "runs": {k: {"exit_code": 0} for k in ("ruff", "complexity", "bandit")}, "bandit": {"errors": []}})
        for tool in ("ruff", "complexity"):
            write(quality.BACK / name / f"{tool}.json", [])
        write(quality.BACK / name / "bandit.json", {"results": []})
    monkeypatch.setattr(sys, "argv", ["quality_check.py", "current", "--reports-only"])


def test_real_report_path_rejects_stylelint_parse_failure(tmp_path, monkeypatch):
    fake_reports(tmp_path, monkeypatch, bad_css=True)
    assert quality.main() == 1
    report = json.loads((tmp_path / "artifacts/quality/current/summary.json").read_text())
    assert report["status"] == "incomplete"


def test_reports_only_never_overwrites_prior_report(tmp_path, monkeypatch):
    fake_reports(tmp_path, monkeypatch)
    assert quality.main() == 0
    path = tmp_path / "artifacts/quality/current/summary.json"
    original = path.read_bytes()
    with pytest.raises(SystemExit) as error:
        quality.main()
    assert error.value.code == 2
    assert path.read_bytes() == original
