"""Tests for the scanner-informed PR Guardian checks (AOS-PRG-002)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

# The guardian is a repo-root tool, not part of the api package; CI's only
# pytest target is apps/api/tests, so its tests live here with an explicit
# path bootstrap (AOS-PRG-002).
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.pr_guardian import check_scanner_signals, load_scan_report  # noqa: E402


def _scan(signals: list[dict]) -> dict:
    return {"risk_signals": signals}


def test_secret_path_blocks() -> None:
    scan = _scan([{"severity": "warning", "code": "SECRET_LIKE_FILENAME", "path": "key.pem", "message": "x"}])
    findings = check_scanner_signals(["key.pem"], scan, "")
    assert [f.code for f in findings] == ["scanner-secret-path"]
    assert findings[0].severity == "block"
    assert check_scanner_signals(["other.py"], scan, "") == []


def test_env_committed_blocks() -> None:
    scan = _scan([{"severity": "warning", "code": "ENV_FILE_PRESENT", "path": ".env", "message": "x"}])
    findings = check_scanner_signals([".env"], scan, "")
    assert [f.code for f in findings] == ["scanner-env-committed"]
    assert findings[0].severity == "block"
    assert check_scanner_signals(["app.py"], scan, "") == []


def test_missing_tests_warns() -> None:
    scan = _scan([{"severity": "warning", "code": "MISSING_TESTS", "path": None, "message": "x"}])
    findings = check_scanner_signals(["apps/api/app/new.py"], scan, "")
    assert [f.code for f in findings] == ["scanner-missing-tests"]
    assert findings[0].severity == "warn"
    assert check_scanner_signals(["docs/x.md"], scan, "") == []


def test_new_ecosystem_warns() -> None:
    scan = _scan([{"severity": "info", "code": "MULTIPLE_ECOSYSTEMS", "path": None, "message": "x"}])
    findings = check_scanner_signals(["Cargo.toml"], scan, "")
    assert [f.code for f in findings] == ["scanner-new-ecosystem"]
    assert findings[0].severity == "warn"
    assert check_scanner_signals(["apps/api/app/x.py"], scan, "") == []


def test_override_skips() -> None:
    scan = _scan([{"severity": "warning", "code": "SECRET_LIKE_FILENAME", "path": "key.pem", "message": "x"}])
    assert check_scanner_signals(["key.pem"], scan, "PR_GUARDIAN_OVERRIDE_SCANNER: rationale") == []


def test_scan_report_file_input(tmp_path: Path) -> None:
    report = {"risk_signals": [{"severity": "warning", "code": "MISSING_TESTS", "path": None, "message": "x"}]}
    path = tmp_path / "scan.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    assert load_scan_report(path) == report

    corrupt = tmp_path / "corrupt.json"
    corrupt.write_text("{ not valid json", encoding="utf-8")
    assert load_scan_report(corrupt) is None


def test_in_repo_scan_fallback() -> None:
    scan = load_scan_report(None)
    assert scan is not None
    assert "risk_signals" in scan


def test_graceful_degradation() -> None:
    assert check_scanner_signals(["apps/api/app/x.py"], None, "") == []
