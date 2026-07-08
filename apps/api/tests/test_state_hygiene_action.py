"""Tests for the reusable state-hygiene refresher (AOS-STATE-RECON-001, portable slice).

The self-contained script lives in the composite action dir so it can run in any
managed repo. These lock in the portable refresh logic: squash+traditional PR
detection, marker-scoped block rewrite of the machine fields only, idempotency,
and a configurable marker.
"""
from __future__ import annotations

import sys
from pathlib import Path

_ACTION_DIR = Path(__file__).resolve().parents[3] / ".github" / "actions" / "state-hygiene"
sys.path.insert(0, str(_ACTION_DIR))
import state_hygiene  # noqa: E402

_DOC = """# Current State

<!-- AOS-CANONICAL:START -->
- Watermark PR: #{wm}
- Active Branch: {ab}
- Current Objective: keep this human field untouched
<!-- AOS-CANONICAL:END -->

## Where We Are
prose that mentions #999 but is outside the block
"""


def test_newest_pr_catches_squash_and_traditional() -> None:
    assert state_hygiene.newest_pr("a Title (#110)\nb Merge pull request #42 from x\nc (#119)\n") == 119
    assert state_hygiene.newest_pr("no prs here") is None


def test_refresh_updates_only_machine_fields() -> None:
    text = _DOC.format(wm=79, ab="`old/branch`")
    new_text, changed = state_hygiene.refresh_block(
        text, "AOS-CANONICAL", {"watermark": 121, "active_branch": "none (on main)"}
    )
    assert changed
    assert "- Watermark PR: #121" in new_text
    assert "- Active Branch: none (on main)" in new_text
    # Human field preserved; text outside the block untouched.
    assert "keep this human field untouched" in new_text
    assert "mentions #999 but is outside the block" in new_text


def test_refresh_is_idempotent() -> None:
    text = _DOC.format(wm=121, ab="none (on main)")
    _new, changed = state_hygiene.refresh_block(
        text, "AOS-CANONICAL", {"watermark": 121, "active_branch": "none (on main)"}
    )
    assert changed is False


def test_refresh_no_block_is_noop() -> None:
    _new, changed = state_hygiene.refresh_block(
        "no markers here", "AOS-CANONICAL", {"watermark": 5, "active_branch": "none (on main)"}
    )
    assert changed is False


def test_custom_marker_is_honored() -> None:
    text = "<!-- MY-STATE:START -->\n- Watermark PR: #1\n<!-- MY-STATE:END -->\n"
    new_text, changed = state_hygiene.refresh_block(text, "MY-STATE", {"watermark": 7, "active_branch": ""})
    assert changed
    assert "- Watermark PR: #7" in new_text
