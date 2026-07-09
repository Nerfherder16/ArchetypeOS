"""Tests for the session-pain harvester (AOS-SELFHEAL-006).

Hermetic: the harvest functions receive parsed transcript records (a list of
dicts, as one Claude Code session JSONL yields), so no test reads a real
transcript. Like the other tool tests, these live under apps/api/tests with an
explicit path bootstrap.

Session pain = the day's friction visible in the session transcript: repeated
tool errors, a file edited over and over (thrash), a command retried in a loop,
and the user's own explicit corrections (/wrong, "that's wrong").
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.session_pain_digest import (  # noqa: E402
    build_digest,
    digest_payload,
    find_command_retries,
    find_corrections,
    find_file_thrash,
    find_tool_errors,
    harvest,
    has_signal,
    parse_transcript,
)


def _tool_use(uid: str, name: str, **inp) -> dict:
    return {"type": "assistant", "message": {"role": "assistant", "content": [
        {"type": "tool_use", "id": uid, "name": name, "input": inp}
    ]}}


def _tool_error(uid: str, content: str) -> dict:
    return {"type": "user", "message": {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": uid, "is_error": True, "content": content}
    ]}}


def _user_text(text: str) -> dict:
    return {"type": "user", "message": {"role": "user", "content": text}}


def test_parse_transcript_skips_bad_lines() -> None:
    text = '{"type":"user"}\nnot json\n{"type":"assistant"}\n'
    records = parse_transcript(text)
    assert [r["type"] for r in records] == ["user", "assistant"]


def test_find_tool_errors_names_the_failing_tool() -> None:
    records = [
        _tool_use("t1", "Bash", command="npm test"),
        _tool_error("t1", "Exit code 1\nnpm ERR test failed"),
        _tool_use("t2", "Bash", command="npm test"),
        _tool_error("t2", "Exit code 1\nnpm ERR test failed again"),
    ]
    errors = find_tool_errors(records)
    # Two Bash errors → one cluster with count 2, naming the tool.
    assert len(errors) == 1
    assert errors[0]["tool"] == "Bash"
    assert errors[0]["count"] == 2
    assert errors[0]["sample"]


def test_find_file_thrash_flags_repeatedly_edited_files() -> None:
    records = [
        _tool_use("e1", "Edit", file_path="/x.ts"),
        _tool_use("e2", "Edit", file_path="/x.ts"),
        _tool_use("e3", "Write", file_path="/x.ts"),
        _tool_use("e4", "Edit", file_path="/y.ts"),
    ]
    thrash = find_file_thrash(records, min_edits=3)
    assert len(thrash) == 1
    assert thrash[0]["path"] == "/x.ts"
    assert thrash[0]["edits"] == 3


def test_find_command_retries_flags_repeated_commands() -> None:
    records = [
        _tool_use("c1", "Bash", command="pytest -q"),
        _tool_use("c2", "Bash", command="pytest -q"),
        _tool_use("c3", "Bash", command="pytest -q"),
        _tool_use("c4", "Bash", command="ls"),
    ]
    retries = find_command_retries(records, min_count=3)
    assert len(retries) == 1
    assert retries[0]["command"] == "pytest -q"
    assert retries[0]["count"] == 3


def test_find_corrections_detects_explicit_user_pain() -> None:
    records = [
        _user_text("<command-name>/wrong</command-name>"),
        _user_text("no, that's wrong — revert it"),
        _user_text("great, thanks!"),  # not a correction
    ]
    corrections = find_corrections(records)
    markers = {c["marker"] for c in corrections}
    assert "/wrong" in markers
    assert "that's wrong" in markers
    assert len(corrections) == 2


def test_find_corrections_ignores_system_injected_text() -> None:
    # A marker inside a long compaction summary / system-reminder is NOT a live
    # correction — those blocks quote earlier content. Only genuine short user
    # turns count.
    summary = _user_text("This session is being continued from a previous conversation. " + "x" * 3000 + " /wrong")
    reminder = _user_text("<system-reminder> the user said doesn't work earlier </system-reminder>")
    assert find_corrections([summary, reminder]) == []


def test_harvest_and_signal() -> None:
    records = [
        _tool_use("t1", "Bash", command="npm test"),
        _tool_error("t1", "Exit code 1"),
        _tool_use("t2", "Bash", command="npm test"),
        _tool_error("t2", "Exit code 1"),
        _user_text("/wrong"),
    ]
    signals = harvest(records, min_edits=3, min_retries=2)
    assert has_signal(signals) is True
    assert has_signal(harvest([], min_edits=3, min_retries=2)) is False

    payload = digest_payload(signals=signals, day_label="2026-07-09")
    assert payload["probe"] == "session-pain"
    assert payload["signal"] is True
    assert payload["tool_errors"][0]["tool"] == "Bash"


def test_build_digest_clean_and_dirty() -> None:
    clean = build_digest(signals=harvest([], min_edits=3, min_retries=2), day_label="2026-07-09")
    assert "No session pain" in clean

    records = [_user_text("/wrong the fix broke the build")]
    dirty = build_digest(signals=harvest(records, min_edits=3, min_retries=2), day_label="2026-07-09")
    assert "correction" in dirty.lower()


def test_real_shape_roundtrips_through_json() -> None:
    # A line-oriented JSONL string (as a real transcript is) parses + harvests.
    lines = "\n".join(
        json.dumps(r)
        for r in [_tool_use("t1", "Bash", command="x"), _tool_error("t1", "boom")]
    )
    signals = harvest(parse_transcript(lines), min_edits=3, min_retries=2)
    assert signals.tool_errors[0]["tool"] == "Bash"
