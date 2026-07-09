"""Deterministic session-pain harvester for the self-learn loop (AOS-SELFHEAL-006).

The fourth self-learn probe. Where conflict_digest harvests merge friction,
toil_digest harvests git rituals, and coherence_probe harvests contract-lag, this
one harvests **session pain**: the day's friction visible in the Claude Code
session transcript. A recurring failure, a file edited over and over, a command
retried in a loop, or an explicit user correction is a candidate for a **lesson,
skill, or fix** — the reasoned distiller proposes one; this module only detects.

Signal source: the session transcript JSONL (one record per line). The harvest
functions take already-parsed records (a list of dicts), so tests never read a
real transcript. Four deterministic signals:

- **tool errors** — ``tool_result`` blocks with ``is_error: true``, clustered by
  the failing tool (resolved from the ``tool_use`` that produced the id).
- **file thrash** — the same file passed to Edit/Write at least ``min_edits``
  times (a fix that did not land the first time).
- **command retries** — the same Bash command run at least ``min_retries`` times
  (a loop grinding on the same failure).
- **corrections** — the user's own explicit pain markers (``/wrong``, ``/never``,
  "that's wrong", "doesn't work", ...). These are the highest-signal pain points
  because the human already flagged them by hand.

Stdlib-only and hermetic. Local-only by construction (transcripts never leave the
box). Complementary to Recall (which builds memory) — this builds a friction
digest.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

_DEFAULT_MIN_EDITS = 3
_DEFAULT_MIN_RETRIES = 3

# Explicit user pain markers. The training-skill invocations (/wrong, /never,
# /learn, /exists) are deliberate flags; the phrases are common in-line
# corrections. Matched case-insensitively against user-authored text.
_CORRECTION_MARKERS = (
    "/wrong",
    "/never",
    "/learn",
    "/exists",
    "that's wrong",
    "thats wrong",
    "that is wrong",
    "doesn't work",
    "does not work",
    "that's not right",
    "not what i asked",
    "revert it",
)


@dataclass
class PainSignals:
    tool_errors: list[dict] = field(default_factory=list)
    thrashed_files: list[dict] = field(default_factory=list)
    command_retries: list[dict] = field(default_factory=list)
    corrections: list[dict] = field(default_factory=list)


def parse_transcript(text: str) -> list[dict]:
    """Parse a JSONL transcript into records, skipping malformed lines."""
    records: list[dict] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def _content_blocks(record: dict) -> list:
    content = (record.get("message") or {}).get("content")
    return content if isinstance(content, list) else []


def _tool_name_map(records: list[dict]) -> dict[str, str]:
    """Map each tool_use id → its tool name (to name a failing tool_result)."""
    names: dict[str, str] = {}
    for record in records:
        for block in _content_blocks(record):
            if isinstance(block, dict) and block.get("type") == "tool_use":
                uid = block.get("id")
                if uid:
                    names[uid] = block.get("name", "?")
    return names


def find_tool_errors(records: list[dict]) -> list[dict]:
    """Cluster error tool_results by the failing tool, with a sample + count."""
    names = _tool_name_map(records)
    per_tool: dict[str, list[str]] = {}
    for record in records:
        for block in _content_blocks(record):
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_result" and block.get("is_error"):
                tool = names.get(block.get("tool_use_id"), "?")
                content = block.get("content")
                sample = content if isinstance(content, str) else json.dumps(content)
                per_tool.setdefault(tool, []).append(sample.strip().splitlines()[0] if sample else "")
    errors = [
        {"tool": tool, "count": len(samples), "sample": samples[0]}
        for tool, samples in per_tool.items()
    ]
    errors.sort(key=lambda e: (-e["count"], e["tool"]))
    return errors


def find_file_thrash(records: list[dict], *, min_edits: int = _DEFAULT_MIN_EDITS) -> list[dict]:
    """Files passed to Edit/Write at least ``min_edits`` times."""
    counts: Counter[str] = Counter()
    for record in records:
        for block in _content_blocks(record):
            if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") in ("Edit", "Write"):
                path = (block.get("input") or {}).get("file_path")
                if path:
                    counts[path] += 1
    thrash = [{"path": path, "edits": n} for path, n in counts.items() if n >= min_edits]
    thrash.sort(key=lambda t: (-t["edits"], t["path"]))
    return thrash


def find_command_retries(records: list[dict], *, min_count: int = _DEFAULT_MIN_RETRIES) -> list[dict]:
    """Bash commands run at least ``min_count`` times (a loop on one failure)."""
    counts: Counter[str] = Counter()
    for record in records:
        for block in _content_blocks(record):
            if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") == "Bash":
                command = (block.get("input") or {}).get("command")
                if command:
                    counts[" ".join(command.split())] += 1
    retries = [{"command": cmd, "count": n} for cmd, n in counts.items() if n >= min_count]
    retries.sort(key=lambda r: (-r["count"], r["command"]))
    return retries


def _user_text(record: dict) -> str:
    if record.get("type") != "user":
        return ""
    content = (record.get("message") or {}).get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    return ""


# A genuine correction is a short user turn ("/wrong", "no, that's wrong"). Long
# blocks are system-injected — a compaction summary or a hook context that quotes
# earlier content — and matching a marker inside them is a false positive.
_MAX_CORRECTION_LEN = 2000
_SYSTEM_TEXT_MARKERS = ("This session is being continued", "<system-reminder>", "<local-command-caveat>")


def find_corrections(records: list[dict]) -> list[dict]:
    """Explicit user pain markers in genuine (short, non-system) user turns."""
    corrections: list[dict] = []
    for record in records:
        text = _user_text(record)
        if not text or len(text) > _MAX_CORRECTION_LEN:
            continue
        if any(marker in text for marker in _SYSTEM_TEXT_MARKERS):
            continue
        lowered = text.lower()
        # One correction per message — the first marker flags it; counting the
        # same message once per marker would double-count a single pain point.
        for marker in _CORRECTION_MARKERS:
            if marker in lowered:
                corrections.append({"marker": marker, "text": text.strip()[:200]})
                break
    return corrections


def harvest(
    records: list[dict], *, min_edits: int = _DEFAULT_MIN_EDITS, min_retries: int = _DEFAULT_MIN_RETRIES
) -> PainSignals:
    return PainSignals(
        tool_errors=find_tool_errors(records),
        thrashed_files=find_file_thrash(records, min_edits=min_edits),
        command_retries=find_command_retries(records, min_count=min_retries),
        corrections=find_corrections(records),
    )


def has_signal(signals: PainSignals) -> bool:
    return bool(
        signals.tool_errors
        or signals.thrashed_files
        or signals.command_retries
        or signals.corrections
    )


def digest_payload(*, signals: PainSignals, day_label: str) -> dict:
    """Machine-readable digest for the reasoned tier / lesson queue."""
    return {
        "probe": "session-pain",
        "day": day_label,
        "signal": has_signal(signals),
        "tool_errors": signals.tool_errors,
        "thrashed_files": signals.thrashed_files,
        "command_retries": signals.command_retries,
        "corrections": signals.corrections,
    }


def build_digest(*, signals: PainSignals, day_label: str) -> str:
    """Human-readable markdown digest of the day's session pain."""
    lines = [f"# Session-pain digest — {day_label}", ""]
    if not has_signal(signals):
        lines.append("No session pain detected: no repeated tool errors, file thrash, command loops, or corrections.")
        lines.append("")
        return "\n".join(lines)

    if signals.corrections:
        lines.append(f"## Corrections ({len(signals.corrections)}) — the human flagged these by hand")
        for c in signals.corrections:
            lines.append(f"- `{c['marker']}` — {c['text']}")
        lines.append("")
    if signals.tool_errors:
        lines.append(f"## Repeated tool errors ({len(signals.tool_errors)})")
        for e in signals.tool_errors:
            lines.append(f"- **{e['tool']}** failed {e['count']}×: {e['sample']}")
        lines.append("")
    if signals.thrashed_files:
        lines.append(f"## File thrash ({len(signals.thrashed_files)})")
        for t in signals.thrashed_files:
            lines.append(f"- `{t['path']}` edited {t['edits']}× (a fix that did not land first time)")
        lines.append("")
    if signals.command_retries:
        lines.append(f"## Command retry loops ({len(signals.command_retries)})")
        for r in signals.command_retries:
            lines.append(f"- `{r['command']}` run {r['count']}×")
        lines.append("")
    return "\n".join(lines)


def _today(repo_root: Path) -> str:
    # No wall-clock in the harvest path; the day label comes from git's last commit
    # date (deterministic + hermetic), falling back to a static marker.
    import subprocess

    try:
        out = subprocess.run(
            ["git", "-C", str(repo_root), "log", "-1", "--format=%cs"],
            capture_output=True,
            text=True,
            check=True,
        )
        return out.stdout.strip() or "undated"
    except Exception:
        return "undated"


def _read_transcripts(paths: list[Path]) -> list[dict]:
    records: list[dict] = []
    for path in paths:
        if path.exists():
            records.extend(parse_transcript(path.read_text(encoding="utf-8", errors="replace")))
    return records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Harvest the day's session pain from Claude Code transcripts (AOS-SELFHEAL-006)."
    )
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument(
        "--transcript",
        type=Path,
        action="append",
        default=None,
        help="Transcript JSONL path(s). Repeatable. Default: today's project transcripts.",
    )
    parser.add_argument("--day-label", default=None)
    parser.add_argument("--min-edits", type=int, default=_DEFAULT_MIN_EDITS)
    parser.add_argument("--min-retries", type=int, default=_DEFAULT_MIN_RETRIES)
    parser.add_argument("--out", type=Path, default=None, help="Markdown output (default: .archetype/session-pain/<day>.md).")
    parser.add_argument("--json", type=Path, default=None, help="Also write the JSON payload here.")
    args = parser.parse_args(argv)

    transcripts = args.transcript
    if not transcripts:
        # Default: the current project's transcript directory (mtime-sorted, most
        # recent first). Kept out of the harvest path's determinism via --transcript
        # in tests; this is the operational default only.
        slug = str(args.repo_root).replace("/", "-")
        tdir = Path.home() / ".claude" / "projects" / slug
        transcripts = sorted(tdir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)[:3] if tdir.exists() else []

    records = _read_transcripts(list(transcripts))
    signals = harvest(records, min_edits=args.min_edits, min_retries=args.min_retries)

    day_label = args.day_label or _today(args.repo_root)
    digest = build_digest(signals=signals, day_label=day_label)

    out = args.out or (args.repo_root / ".archetype" / "session-pain" / f"{day_label}.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(digest, encoding="utf-8")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps(digest_payload(signals=signals, day_label=day_label), indent=2),
            encoding="utf-8",
        )

    print(f"Wrote session-pain digest: {out}")
    print(f"signal={'true' if has_signal(signals) else 'false'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
