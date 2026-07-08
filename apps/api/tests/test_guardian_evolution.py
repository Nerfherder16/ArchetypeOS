"""Tests for the Guardian Evolution checks (AOS-PRG-003, RFC-0004 Phase 2)."""
from __future__ import annotations

import datetime
import json
from pathlib import Path

# The guardian is a repo-root tool, not part of the api package; CI's only
# pytest target is apps/api/tests, so its tests live here with an explicit
# path bootstrap (AOS-PRG-002).
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.pr_guardian import (  # noqa: E402
    Finding,
    apply_accepted_warnings,
    check_guardian_change_lesson,
    check_override_lesson_citation,
    check_tests_for_code_changes,
    check_verification_metadata,
    has_override,
    load_accepted_warnings,
)


def _accepted(review_by: str) -> list[dict]:
    return [
        {
            "code": "web-tests-not-enforced",
            "lesson": "LES-006",
            "rationale": "UI verified per-package by Orchestrator browser drives",
            "review_by": review_by,
        }
    ]


def _web_warn() -> Finding:
    return Finding("warn", "web-tests-not-enforced", "Web source changed. Build is enforced.")


def test_metadata_message_teaches_format() -> None:
    findings = check_verification_metadata("")
    assert [f.code for f in findings] == ["missing-verification-metadata"]
    message = findings[0].message
    assert "Field: value" in message
    assert "do not parse" in message


def test_accepted_warning_annotated() -> None:
    findings = apply_accepted_warnings([_web_warn()], _accepted("2999-01-01"))
    assert len(findings) == 1
    assert findings[0].severity == "warn"
    assert findings[0].code == "web-tests-not-enforced"
    assert "accepted per LES-006 until 2999-01-01" in findings[0].message
    assert "browser drives" in findings[0].message


def test_expired_acceptance_blocks() -> None:
    findings = apply_accepted_warnings([_web_warn()], _accepted("2000-01-01"))
    assert len(findings) == 1
    assert findings[0].severity == "block"
    assert findings[0].code == "accepted-warning-expired"
    assert "web-tests-not-enforced" in findings[0].message
    assert "LES-006" in findings[0].message


def test_expired_acceptance_uses_supplied_today() -> None:
    warn = _web_warn()
    on_boundary = apply_accepted_warnings([warn], _accepted("2026-08-01"), today=datetime.date(2026, 8, 1))
    assert on_boundary[0].severity == "warn"
    after = apply_accepted_warnings([warn], _accepted("2026-08-01"), today=datetime.date(2026, 8, 2))
    assert after[0].severity == "block"


def test_blocks_never_touched() -> None:
    block = Finding("block", "web-tests-not-enforced", "not really this code, but severity block")
    findings = apply_accepted_warnings([block], _accepted("2000-01-01"))
    assert findings == [block]


def test_missing_registry_graceful(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist.json"
    accepted = load_accepted_warnings(missing)
    assert accepted == []
    warn = _web_warn()
    assert apply_accepted_warnings([warn], accepted) == [warn]


def test_invalid_registry_graceful(tmp_path: Path) -> None:
    corrupt = tmp_path / "corrupt.json"
    corrupt.write_text("{ not valid json", encoding="utf-8")
    assert load_accepted_warnings(corrupt) == []

    not_a_list = tmp_path / "obj.json"
    not_a_list.write_text(json.dumps({"code": "x"}), encoding="utf-8")
    assert load_accepted_warnings(not_a_list) == []


def test_registry_file_input(tmp_path: Path) -> None:
    path = tmp_path / "accepted.json"
    path.write_text(json.dumps(_accepted("2999-01-01")), encoding="utf-8")
    accepted = load_accepted_warnings(path)
    assert accepted[0]["code"] == "web-tests-not-enforced"


def test_guardian_change_requires_lesson() -> None:
    blocked = check_guardian_change_lesson(["tools/pr_guardian.py"], "")
    assert [f.code for f in blocked] == ["guardian-change-without-lesson"]
    assert blocked[0].severity == "block"

    with_lesson = check_guardian_change_lesson(
        ["tools/pr_guardian.py", "knowledge/wiki/lessons/LES-006.md"], ""
    )
    assert with_lesson == []

    with_override = check_guardian_change_lesson(
        ["tools/pr_guardian.py"], "PR_GUARDIAN_OVERRIDE_LESSON: refactor only, see LES-006."
    )
    assert with_override == []

    unrelated = check_guardian_change_lesson(["apps/api/app/x.py"], "")
    assert unrelated == []


def test_web_source_without_e2e_warns() -> None:
    findings = check_tests_for_code_changes(["apps/web/src/main.tsx"], "")
    codes = [f.code for f in findings]
    assert "web-tests-not-enforced" in codes
    warn = next(f for f in findings if f.code == "web-tests-not-enforced")
    assert warn.severity == "warn"


def test_web_source_with_e2e_clean() -> None:
    findings = check_tests_for_code_changes(
        ["apps/web/src/main.tsx", "apps/web/e2e/control-tower.spec.ts"], ""
    )
    assert "web-tests-not-enforced" not in [f.code for f in findings]


def test_core_change_requires_tests() -> None:
    findings = check_tests_for_code_changes(["packages/aos_core/services/scan.py"], "")
    codes = [f.code for f in findings]
    assert "missing-core-tests" in codes
    block = next(f for f in findings if f.code == "missing-core-tests")
    assert block.severity == "block"


def test_core_change_with_tests_clean() -> None:
    findings = check_tests_for_code_changes(
        ["packages/aos_core/services/scan.py", "apps/api/tests/test_repository_scan.py"], ""
    )
    assert "missing-core-tests" not in [f.code for f in findings]


def test_override_requires_lesson_citation() -> None:
    blocked = check_override_lesson_citation("PR_GUARDIAN_OVERRIDE_TESTS: rationale")
    assert [f.code for f in blocked] == ["override-without-lesson-citation"]
    assert blocked[0].severity == "block"

    cited = check_override_lesson_citation("PR_GUARDIAN_OVERRIDE_TESTS: rationale per LES-006")
    assert cited == []

    no_override = check_override_lesson_citation("Just a normal body mentioning LES-006 or not.")
    assert no_override == []


def test_override_prose_mention_is_not_an_override() -> None:
    # LES-L08: a body that merely MENTIONS an override token in prose (e.g. a skill
    # or doc that forbids overrides) must NOT trip the lesson-citation block, and
    # must NOT silently activate a gate override.
    prose = "This skill never uses PR_GUARDIAN_OVERRIDE_TESTS tokens to bypass a gate."
    assert check_override_lesson_citation(prose) == []
    assert has_override(prose, "TESTS") is False

    # A real line-start directive still activates (and still needs a lesson cite).
    directive = "PR_GUARDIAN_OVERRIDE_TESTS: intentional, see rationale"
    assert has_override(directive, "TESTS") is True
    assert [f.code for f in check_override_lesson_citation(directive)] == [
        "override-without-lesson-citation"
    ]

    # Bulleted directive form is also honored.
    assert has_override("- PR_GUARDIAN_OVERRIDE_DOCS: docs-only change", "DOCS") is True

    # LES-L08: the laptop LES-L## band now satisfies the lesson-citation gate too
    # (previously only the numeric LES-NNN form matched).
    cited_laptop = check_override_lesson_citation(
        "PR_GUARDIAN_OVERRIDE_TESTS: intentional, see LES-L08"
    )
    assert cited_laptop == []
