"""Tests for the deterministic doc-staleness detector (AOS-20, closes LES-007).

Hermetic: the pure check functions receive fixture strings, so no test touches
the real working tree or git. The guardian-hook test monkeypatches
``doc_staleness.evaluate`` so the guardian never reads the live repo either.

Like the other guardian-adjacent tools tests, these live under apps/api/tests
(CI's only pytest target) with an explicit path bootstrap (see
test_guardian_scanner.py).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools import doc_staleness  # noqa: E402
from tools.doc_staleness import (  # noqa: E402
    Finding,
    check_roadmap_phase,
    check_state_pr_lag,
    run_checks,
)

# --- fixtures ---------------------------------------------------------------

STALE_ROADMAP = "# Machine Roadmap\n\n## Current phase\n\nFoundation.\n\n## Objectives\n"
FRESH_ROADMAP = "# Machine Roadmap\n\n## Current phase\n\nPost-v0.1 (Intelligence arc).\n"
CURRENT_STATE_COMPLETE = (
    "## Status\n\n"
    "- Phase: v0.1 COMPLETE (2026-07-05); post-v0.1 development underway\n"
    "- Current sprint: Sprint 5 delivered (PRs #43-#48)\n"
)
CURRENT_STATE_EARLY = "## Status\n\n- Phase: Foundation; docs still being written\n"
# A fixed roadmap whose phase names an early word ("foundation") only as HISTORY.
# Must NOT trip signal 1 (regression for the substring false positive, LES-024).
POST_V01_ROADMAP = (
    "# Machine Roadmap\n\n## Current phase\n\n"
    "Post-v0.1 — Intelligence layer maturing. v0.1 shipped 2026-07-05 "
    "(runtime foundation, scanner, Control Tower, learning loop).\n"
)

GIT_LOG_66 = "\n".join(
    f"abc123 Merge pull request #{n} from Nerfherder16/x" for n in (60, 62, 64, 66)
)


def _hard(findings: list[Finding]) -> list[Finding]:
    return [f for f in findings if f.severity == "hard"]


def _soft(findings: list[Finding]) -> list[Finding]:
    return [f for f in findings if f.severity == "soft"]


# --- Signal 1: roadmap phase vs reality ------------------------------------


def test_roadmap_phase_stale_is_hard() -> None:
    findings = check_roadmap_phase(STALE_ROADMAP, CURRENT_STATE_COMPLETE)
    assert _hard(findings), "early roadmap phase + completed reality must be HARD"
    assert findings[0].signal == "roadmap-phase-stale"


def test_roadmap_phase_fresh_passes() -> None:
    assert check_roadmap_phase(FRESH_ROADMAP, CURRENT_STATE_COMPLETE) == []


def test_roadmap_phase_early_reality_not_flagged() -> None:
    # Roadmap says Foundation AND reality is genuinely early -> no drift.
    assert check_roadmap_phase(STALE_ROADMAP, CURRENT_STATE_EARLY) == []


def test_roadmap_phase_history_word_not_flagged() -> None:
    # A fixed phase that names "foundation" only as history must not false-positive
    # (regression: the early-token match is a startswith on the label, not a
    # substring scan over prose; LES-024).
    assert check_roadmap_phase(POST_V01_ROADMAP, CURRENT_STATE_COMPLETE) == []


# --- Signal 2: state-doc PR lag --------------------------------------------


def test_pr_lag_one_is_soft() -> None:
    findings = check_state_pr_lag(GIT_LOG_66, "top merged PR #65", "PR #65 merged", hard_threshold=3)
    assert _soft(findings) and not _hard(findings), "the normal 1-PR reconciliation lag is SOFT"


def test_pr_lag_far_is_hard() -> None:
    findings = check_state_pr_lag(GIT_LOG_66, "we are at PR #60", "PR #60", hard_threshold=3)
    assert _hard(findings), "a lag beyond the threshold (66 vs 60) is HARD"


def test_pr_lag_current_is_clean() -> None:
    assert check_state_pr_lag(GIT_LOG_66, "latest PR #66 reconciled", "PR #66", hard_threshold=3) == []


def test_pr_lag_no_merges_is_clean() -> None:
    assert check_state_pr_lag("no merges here", "PR #1", "PR #1", hard_threshold=3) == []


# --- run_checks composition + exit code ------------------------------------


def test_run_checks_composes_both_signals() -> None:
    findings = run_checks(
        roadmap_text=STALE_ROADMAP,
        current_state_text=CURRENT_STATE_COMPLETE,
        recent_changes_text="PR #60",
        git_log_text=GIT_LOG_66,
        hard_threshold=3,
    )
    signals = {f.signal for f in findings}
    assert "roadmap-phase-stale" in signals
    assert "state-docs-pr-lag" in signals


def test_main_exits_nonzero_only_on_hard(monkeypatch) -> None:
    monkeypatch.setattr(doc_staleness, "evaluate", lambda **kw: [Finding("state-docs-pr-lag", "soft", "m", "e")])
    assert doc_staleness.main([]) == 0, "soft-only findings must not fail the build"
    monkeypatch.setattr(doc_staleness, "evaluate", lambda **kw: [Finding("roadmap-phase-stale", "hard", "m", "e")])
    assert doc_staleness.main([]) == 1, "a HARD finding must exit non-zero"
    monkeypatch.setattr(doc_staleness, "evaluate", lambda **kw: [])
    assert doc_staleness.main([]) == 0


# --- guardian hook: additive, WARN-only, never blocks ----------------------


def test_guardian_doc_staleness_warns_never_blocks(monkeypatch) -> None:
    from tools import pr_guardian

    monkeypatch.setattr(
        pr_guardian._doc_staleness,
        "evaluate",
        lambda **kw: [Finding("roadmap-phase-stale", "hard", "roadmap drift", "evidence")],
    )
    findings = pr_guardian.check_doc_staleness(["docs/CURRENT_STATE.md"])
    assert findings, "a HARD doc-staleness result should surface in the guardian"
    assert all(f.severity == "warn" for f in findings), "the guardian hook must never emit block"
    # render() must treat it as a non-blocking warning (exit 0), not a BLOCK.
    assert pr_guardian.render(findings, ["docs/CURRENT_STATE.md"]) == 0


def test_guardian_doc_staleness_soft_is_silent(monkeypatch) -> None:
    from tools import pr_guardian

    monkeypatch.setattr(
        pr_guardian._doc_staleness,
        "evaluate",
        lambda **kw: [Finding("state-docs-pr-lag", "soft", "1-PR lag", "evidence")],
    )
    assert pr_guardian.check_doc_staleness(["docs/CURRENT_STATE.md"]) == [], "SOFT drift stays quiet in the guardian"


def test_guardian_doc_staleness_fails_open(monkeypatch) -> None:
    from tools import pr_guardian

    def _boom(**kw):
        raise RuntimeError("git unavailable")

    monkeypatch.setattr(pr_guardian._doc_staleness, "evaluate", _boom)
    # Never crash the guardian and never block on a detector failure.
    assert pr_guardian.check_doc_staleness(["docs/CURRENT_STATE.md"]) == []


# --- self-heal: reconciliation draft generator (AOS-SELFHEAL-001) ----------

GIT_LOG_72_76 = "\n".join(
    [
        "aaa1111 Merge pull request #76 from Nerfherder16/claude/aos-runtime-002-scanner",
        "bbb2222 Merge pull request #74 from Nerfherder16/laptop/aos-council-002-dashboard",
        "ccc3333 Merge pull request #72 from Nerfherder16/laptop/playbook-union-note",
    ]
)


def test_reconciliation_draft_lists_unreferenced_prs() -> None:
    from tools.doc_staleness import build_reconciliation_draft

    draft = build_reconciliation_draft(
        git_log_text=GIT_LOG_72_76,
        current_state_text="reconciled through PR #71",
        recent_changes_text="",
    )
    assert draft is not None
    assert "#72" in draft and "#74" in draft and "#76" in draft
    assert "- PR #71" not in draft  # the already-referenced PR is not in the pending list
    # provenance from the merge line
    assert "aos-council-002-dashboard" in draft


def test_reconciliation_draft_none_when_current() -> None:
    from tools.doc_staleness import build_reconciliation_draft

    assert (
        build_reconciliation_draft(
            git_log_text=GIT_LOG_72_76,
            current_state_text="current through PR #76",
            recent_changes_text="",
        )
        is None
    )


def test_reconciliation_draft_none_without_merges() -> None:
    from tools.doc_staleness import build_reconciliation_draft

    assert (
        build_reconciliation_draft(git_log_text="no merges here", current_state_text="PR #1", recent_changes_text="")
        is None
    )


def test_fix_writes_pending_draft_never_edits_prose(tmp_path, monkeypatch) -> None:
    from tools import doc_staleness

    monkeypatch.setattr(doc_staleness, "_git_log", lambda *a, **k: GIT_LOG_72_76)
    (tmp_path / "docs").mkdir()
    (tmp_path / ".archetype").mkdir()
    (tmp_path / "docs" / "CURRENT_STATE.md").write_text("through PR #71", encoding="utf-8")
    (tmp_path / "docs" / "RECENT_CHANGES.md").write_text("log", encoding="utf-8")
    (tmp_path / ".archetype" / "roadmap.md").write_text("## Current phase\n\nPost-v0.1.\n", encoding="utf-8")
    before_cs = (tmp_path / "docs" / "CURRENT_STATE.md").read_text(encoding="utf-8")
    before_rc = (tmp_path / "docs" / "RECENT_CHANGES.md").read_text(encoding="utf-8")

    rc = doc_staleness.main(["--fix", "--repo-root", str(tmp_path)])

    pending = tmp_path / ".archetype" / "reconciliation" / "PENDING.md"
    assert pending.exists(), "--fix must write the reconciliation draft"
    assert "#76" in pending.read_text(encoding="utf-8")
    # never edits the human prose docs (draft-only; Article XII)
    assert (tmp_path / "docs" / "CURRENT_STATE.md").read_text(encoding="utf-8") == before_cs
    assert (tmp_path / "docs" / "RECENT_CHANGES.md").read_text(encoding="utf-8") == before_rc
    assert rc == 1, "HARD drift still stands until the docs are actually reconciled"
