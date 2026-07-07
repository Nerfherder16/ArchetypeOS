"""Tests for the deterministic conflict-digest harvester (AOS-SELFHEAL-003).

Hermetic: the harvester functions receive a fixture rr-cache directory and a
reflog fixture string, so no test touches the real working tree, git, or
``.git/rr-cache``. Like the other guardian-adjacent tools tests, these live under
apps/api/tests (CI's only pytest target) with an explicit path bootstrap.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools import conflict_digest  # noqa: E402
from tools.conflict_digest import (  # noqa: E402
    ConflictRecord,
    FrictionEvent,
    build_digest,
    digest_payload,
    harvest_rerere,
    parse_reflog,
)

# --- rerere harvest ---------------------------------------------------------


def _write_conflict(rr_cache: Path, cid: str, preimage: str, *, resolved: bool) -> None:
    d = rr_cache / cid
    d.mkdir(parents=True)
    (d / "preimage").write_text(preimage, encoding="utf-8")
    if resolved:
        (d / "postimage").write_text("resolved\n", encoding="utf-8")


def test_harvest_rerere_reads_preimage_and_resolution(tmp_path: Path) -> None:
    rr = tmp_path / "rr-cache"
    _write_conflict(
        rr,
        "aaa111",
        "<<<<<<<\nour change\n=======\ntheir change\n>>>>>>>\n",
        resolved=True,
    )
    _write_conflict(
        rr,
        "bbb222",
        "<<<<<<<\nunresolved ours\n=======\nunresolved theirs\n>>>>>>>\n",
        resolved=False,
    )

    records = harvest_rerere(rr)

    assert len(records) == 2
    by_id = {r.conflict_id: r for r in records}
    assert by_id["aaa111"].resolved is True
    assert by_id["bbb222"].resolved is False
    # The preview strips conflict markers and keeps the conflicting content.
    assert "our change" in by_id["aaa111"].hunk_preview
    assert "<<<<<<<" not in by_id["aaa111"].hunk_preview
    assert ">>>>>>>" not in by_id["aaa111"].hunk_preview


def test_harvest_rerere_empty_when_no_cache(tmp_path: Path) -> None:
    # No rr-cache dir at all (rerere enabled but no conflict has happened yet).
    assert harvest_rerere(tmp_path / "does-not-exist") == []


# --- reflog friction --------------------------------------------------------

REFLOG_FIXTURE = """\
a1b2c3d HEAD@{0}: rebase (finish): returning to refs/heads/laptop/feature-x
e4f5a6b HEAD@{1}: rebase (pick): AOS-FEATURE-X implement the thing
c7d8e9f HEAD@{2}: rebase (start): checkout origin/main
0a1b2c3 HEAD@{3}: pull --ff-only origin main: Fast-forward
4d5e6f7 HEAD@{4}: merge origin/main: Merge made by the 'ort' strategy.
8a9b0c1 HEAD@{5}: commit: AOS-FEATURE-X first cut
2c3d4e5 HEAD@{6}: reset: moving to origin/main
"""


def test_parse_reflog_extracts_friction_events_only() -> None:
    events = parse_reflog(REFLOG_FIXTURE)

    kinds = [e.kind for e in events]
    # rebase (as one logical op), pull, merge, reset are friction; a plain
    # commit is not.
    assert "rebase" in kinds
    assert "pull" in kinds
    assert "merge" in kinds
    assert "reset" in kinds
    assert "commit" not in kinds


def test_parse_reflog_collapses_a_rebase_run_to_one_event() -> None:
    # A rebase emits start/pick/finish lines; the digest should count ONE rebase,
    # not three, so the friction tally reflects operations not internal steps.
    events = parse_reflog(REFLOG_FIXTURE)
    rebases = [e for e in events if e.kind == "rebase"]
    assert len(rebases) == 1


def test_parse_reflog_empty_is_empty() -> None:
    assert parse_reflog("") == []


# --- digest rendering -------------------------------------------------------


def test_build_digest_reports_counts_and_hunks() -> None:
    records = [
        ConflictRecord(conflict_id="aaa111", hunk_preview="our change / their change", resolved=True),
        ConflictRecord(conflict_id="bbb222", hunk_preview="ours / theirs", resolved=False),
    ]
    friction = [
        FrictionEvent(kind="rebase", detail="returning to laptop/feature-x", ref="HEAD@{0}"),
        FrictionEvent(kind="merge", detail="Merge made by ort", ref="HEAD@{4}"),
    ]

    digest = build_digest(records=records, friction=friction, day_label="2026-07-07")

    assert "2026-07-07" in digest
    # Surfaces the unresolved conflict prominently and the counts.
    assert "1 unresolved" in digest or "unresolved: 1" in digest.lower()
    assert "rebase" in digest
    assert "our change" in digest


def test_build_digest_quiet_day_says_no_friction() -> None:
    digest = build_digest(records=[], friction=[], day_label="2026-07-07")
    assert "No conflicts" in digest or "no conflict" in digest.lower()


def test_digest_payload_is_machine_readable() -> None:
    records = [ConflictRecord(conflict_id="aaa111", hunk_preview="x", resolved=False)]
    friction = [FrictionEvent(kind="rebase", detail="d", ref="HEAD@{0}")]
    payload = digest_payload(records=records, friction=friction, day_label="2026-07-07")

    assert payload["day"] == "2026-07-07"
    assert payload["conflict_count"] == 1
    assert payload["unresolved_count"] == 1
    assert payload["friction"]["rebase"] == 1


def test_has_signal_true_only_with_conflicts_or_friction() -> None:
    assert conflict_digest.has_signal(records=[], friction=[]) is False
    assert (
        conflict_digest.has_signal(
            records=[], friction=[FrictionEvent(kind="rebase", detail="d", ref="r")]
        )
        is True
    )
