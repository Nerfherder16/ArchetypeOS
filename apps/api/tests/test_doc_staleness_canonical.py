"""Tests for the canonical-state drift checks (AOS-STATE-RECON-001 / LES-L09).

Hermetic: every function takes strings / sets, so no test touches git or the
working tree. These lock in the fix for the two masking bugs — squash merges were
invisible to the PR extractor, and CURRENT_STATE's own staleness was hidden by
unioning it with RECENT_CHANGES.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.doc_staleness import (  # noqa: E402
    check_canonical_state,
    derive_canonical,
    extract_merged_prs,
    parse_canonical,
    refresh_canonical_block,
)

_BLOCK = """# Current State

<!-- AOS-CANONICAL:START -->
- Watermark PR: #{wm}
- Active Branch: {ab}
- Current Objective: consolidate
<!-- AOS-CANONICAL:END -->

## Where We Are
prose
"""


def test_extract_merged_prs_catches_squash_and_traditional() -> None:
    log = (
        "abc AOS-VOICE-001: spine (#110)\n"
        "def Merge pull request #42 from x/y\n"
        "ghi AOS-TOIL: probe (#119)\n"
    )
    assert extract_merged_prs(log) == [42, 110, 119]


def test_parse_canonical_reads_fields() -> None:
    c = parse_canonical(_BLOCK.format(wm=121, ab="none (on main)"))
    assert c.watermark == 121
    assert c.active_branch == "none (on main)"


def test_canonical_watermark_lag_is_caught_scoped_to_this_file() -> None:
    # CURRENT_STATE frozen at #79 while git is at #121 — the union check missed
    # this because RECENT_CHANGES was current; the scoped check catches it.
    text = _BLOCK.format(wm=79, ab="none (on main)")
    log = "x AOS-GUARDIAN: fix (#121)\n"
    findings = check_canonical_state(text, log, origin_branches={"main"})
    codes = [f.signal for f in findings]
    assert "canonical-watermark-lag" in codes
    assert findings[0].severity == "hard"


def test_canonical_fresh_watermark_no_finding() -> None:
    text = _BLOCK.format(wm=121, ab="none (on main)")
    log = "x AOS-GUARDIAN: fix (#121)\n"
    assert check_canonical_state(text, log, origin_branches={"main"}) == []


def test_canonical_stale_active_branch_is_caught() -> None:
    text = _BLOCK.format(wm=121, ab="`laptop/aos-ui-008-neon-palette`")
    log = "x fix (#121)\n"
    # The named branch is not among the open origin branches.
    findings = check_canonical_state(text, log, origin_branches={"main", "laptop/live"})
    assert [f.signal for f in findings] == ["canonical-active-branch-stale"]


def test_canonical_active_branch_none_or_open_is_fine() -> None:
    log = "x fix (#121)\n"
    assert check_canonical_state(
        _BLOCK.format(wm=121, ab="none (on main)"), log, origin_branches={"main"}
    ) == []
    assert check_canonical_state(
        _BLOCK.format(wm=121, ab="`laptop/live`"), log, origin_branches={"main", "laptop/live"}
    ) == []


def test_derive_and_refresh_roundtrip() -> None:
    text = _BLOCK.format(wm=79, ab="`old/branch`")
    derived = derive_canonical("x fix (#121)\n", current_branch="main")
    assert derived["watermark"] == 121
    assert derived["active_branch"] == "none (on main)"
    new_text, changed = refresh_canonical_block(text, derived)
    assert changed
    c = parse_canonical(new_text)
    assert c.watermark == 121
    assert c.active_branch == "none (on main)"
    # Idempotent: refreshing again is a no-op.
    _again, changed2 = refresh_canonical_block(new_text, derived)
    assert changed2 is False
