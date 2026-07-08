"""Tests for the deterministic toil-digest harvester (AOS-SELFHEAL-004).

Hermetic: the harvester functions receive reflog fixture strings and action
lists, so no test touches the real working tree or git. Like the other
guardian-adjacent tools tests, these live under apps/api/tests (CI's only pytest
target) with an explicit path bootstrap.

Toil = a recurring multi-step git ritual (e.g. branch -> commit -> merge repeated
many times a day) that a skill or script could capture.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.toil_digest import (  # noqa: E402
    Ritual,
    build_digest,
    digest_payload,
    find_rituals,
    has_signal,
    parse_reflog_actions,
)


# --- reflog → action sequence ----------------------------------------------


def test_parse_reflog_actions_classifies_leading_verbs() -> None:
    reflog = "\n".join(
        [
            "abc123 HEAD@{0}: checkout: moving from main to laptop/foo",
            "def456 HEAD@{1}: commit: AOS-FOO-001 do the thing",
            "aaa111 HEAD@{2}: merge origin/main: Merge made by the 'ort' strategy.",
            "bbb222 HEAD@{3}: pull --ff-only origin main: Fast-forward",
            "ccc333 HEAD@{4}: reset: moving to HEAD~1",
            "ddd444 HEAD@{5}: some noise with no colon action",
        ]
    )
    actions = parse_reflog_actions(reflog)
    assert actions == ["checkout", "commit", "merge", "pull", "reset"]


def test_parse_reflog_actions_collapses_consecutive_duplicates() -> None:
    # Several commits in a row on a branch normalise to one 'commit' so the ritual
    # shape is stable regardless of how many commits a branch carried.
    reflog = "\n".join(
        [
            "1 HEAD@{0}: checkout: moving from main to br",
            "2 HEAD@{1}: commit: a",
            "3 HEAD@{2}: commit: b",
            "4 HEAD@{3}: commit: c",
            "5 HEAD@{4}: merge origin/main: done",
        ]
    )
    assert parse_reflog_actions(reflog) == ["checkout", "commit", "merge"]


def test_parse_reflog_actions_empty_is_empty() -> None:
    assert parse_reflog_actions("") == []


# --- ritual detection -------------------------------------------------------


def test_find_rituals_detects_a_repeated_ritual() -> None:
    # checkout -> commit -> merge, done three times.
    actions = ["checkout", "commit", "merge"] * 3
    rituals = find_rituals(actions, min_len=3, min_count=3)
    assert rituals, "a 3x-repeated 3-step ritual is toil"
    top = rituals[0]
    assert top.actions == ("checkout", "commit", "merge")
    assert top.count == 3


def test_find_rituals_quiet_when_below_threshold() -> None:
    actions = ["checkout", "commit", "merge", "checkout", "commit", "merge"]
    # Only twice — not yet a habit worth automating.
    assert find_rituals(actions, min_len=3, min_count=3) == []


def test_find_rituals_prefers_longest_and_dedups_subgrams() -> None:
    # A 4-step ritual repeated 3x should be reported; its 3-step sub-grams must not
    # also be reported as separate rituals.
    actions = ["checkout", "commit", "merge", "pull"] * 3
    rituals = find_rituals(actions, min_len=3, min_count=3)
    assert any(r.actions == ("checkout", "commit", "merge", "pull") for r in rituals)
    # No reported ritual is a contiguous sub-sequence of the 4-gram.
    four = ("checkout", "commit", "merge", "pull")
    for r in rituals:
        if r.actions != four:
            assert not _is_subseq(r.actions, four)


def _is_subseq(small: tuple, big: tuple) -> bool:
    return len(small) < len(big) and any(
        big[i : i + len(small)] == small for i in range(len(big) - len(small) + 1)
    )


# --- render + signal --------------------------------------------------------


def test_has_signal_only_with_rituals() -> None:
    assert has_signal([]) is False
    assert has_signal([Ritual(actions=("checkout", "commit", "merge"), count=4)]) is True


def test_build_digest_reports_rituals() -> None:
    rituals = [Ritual(actions=("checkout", "commit", "merge"), count=6)]
    md = build_digest(rituals=rituals, day_label="2026-07-08")
    assert "Toil digest" in md
    assert "2026-07-08" in md
    assert "checkout" in md and "×6" in md
    assert "For the distiller" in md


def test_build_digest_quiet_day() -> None:
    md = build_digest(rituals=[], day_label="2026-07-08")
    assert "No recurring" in md or "Clean" in md
    assert "For the distiller" not in md


def test_digest_payload_is_machine_readable() -> None:
    rituals = [Ritual(actions=("checkout", "commit", "merge"), count=5)]
    payload = digest_payload(rituals=rituals, day_label="2026-07-08")
    assert payload["day"] == "2026-07-08"
    assert payload["ritual_count"] == 1
    assert payload["rituals"][0]["actions"] == ["checkout", "commit", "merge"]
    assert payload["rituals"][0]["count"] == 5
