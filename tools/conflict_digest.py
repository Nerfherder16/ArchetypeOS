#!/usr/bin/env python3
"""Deterministic conflict-digest harvester (AOS-SELFHEAL-003).

The deterministic *floor* for the conflict self-learn nightly. It reads two
git-native substrates and emits a digest of the day's merge friction. It never
edits code; the reasoned tier (``scripts/nightly/conflict_learn.sh``) distills
recurring patterns into ``LES-L##`` draft lessons.

Substrates
----------
1. **git rerere** (``.git/rr-cache/*/preimage``) — every conflict git emitted
   markers for, with whether it was resolved (a sibling ``postimage`` exists).
   rerere must be enabled (``git config rerere.enabled true``) to record these,
   which ``scripts/install-hooks.sh`` now does. rerere keys conflicts by content
   hash, not path, so records carry a hunk preview rather than a filename.
2. **git reflog** — rebase / merge / reset / pull events in the window. This is
   the "tandem treadmill" friction signal: union-auto-resolved coordination-doc
   conflicts never produce markers (so rerere misses them), but they always leave
   a rebase behind. Counting rebases/merges captures that friction.

Stdlib-only and hermetic: the harvest functions take a directory / reflog string,
so tests never touch the real repo. The CLI wires them to the live repo.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

_MARKER_PREFIXES = ("<<<<<<<", "=======", ">>>>>>>", "|||||||")
_FRICTION_KINDS = ("rebase", "merge", "reset", "pull", "revert", "cherry-pick")
_PREVIEW_LINES = 6


@dataclass
class ConflictRecord:
    """One conflict git recorded via rerere."""

    conflict_id: str
    hunk_preview: str
    resolved: bool


@dataclass
class FrictionEvent:
    """One friction operation (rebase/merge/reset/pull) from the reflog."""

    kind: str
    detail: str
    ref: str


@dataclass
class _Digest:
    records: list[ConflictRecord] = field(default_factory=list)
    friction: list[FrictionEvent] = field(default_factory=list)


# --- harvest ----------------------------------------------------------------


def _preview(preimage_text: str) -> str:
    """Strip conflict markers, keep the first few content lines as a preview."""
    lines = [
        ln.rstrip("\n")
        for ln in preimage_text.splitlines()
        if not ln.startswith(_MARKER_PREFIXES)
    ]
    lines = [ln for ln in lines if ln.strip()]
    return " / ".join(lines[:_PREVIEW_LINES])


def harvest_rerere(rr_cache_dir: Path) -> list[ConflictRecord]:
    """Read every conflict recorded under an rr-cache directory.

    Returns an empty list when the directory does not exist (rerere enabled but
    no conflict has happened yet).
    """
    if not rr_cache_dir.is_dir():
        return []
    records: list[ConflictRecord] = []
    for entry in sorted(rr_cache_dir.iterdir()):
        preimage = entry / "preimage"
        if not preimage.is_file():
            continue
        text = preimage.read_text(encoding="utf-8", errors="replace")
        records.append(
            ConflictRecord(
                conflict_id=entry.name,
                hunk_preview=_preview(text),
                resolved=(entry / "postimage").is_file(),
            )
        )
    return records


def _reflog_kind(subject: str) -> str | None:
    """Classify a reflog subject's leading action, or None if not friction."""
    head = subject.strip().split(":", 1)[0].strip()
    first = head.split(" ", 1)[0].split("(", 1)[0]
    return first if first in _FRICTION_KINDS else None


def parse_reflog(reflog_text: str) -> list[FrictionEvent]:
    """Extract friction events from reflog text, collapsing each rebase run to one.

    A rebase logs start/pick/finish lines; we count one rebase per contiguous run
    so the tally reflects operations, not internal steps.
    """
    events: list[FrictionEvent] = []
    prev_kind: str | None = None
    for line in reflog_text.splitlines():
        line = line.strip()
        if not line or ": " not in line:
            continue
        ref_part, subject = line.split(": ", 1)
        # ref_part looks like "<sha> HEAD@{n}"
        ref = ref_part.split(" ", 1)[1] if " " in ref_part else ref_part
        kind = _reflog_kind(subject)
        if kind is None:
            prev_kind = None
            continue
        if kind == "rebase" and prev_kind == "rebase":
            continue  # same rebase run — already counted
        detail = subject.split(":", 1)[1].strip() if ":" in subject else subject.strip()
        events.append(FrictionEvent(kind=kind, detail=detail, ref=ref))
        prev_kind = kind
    return events


def has_signal(*, records: list[ConflictRecord], friction: list[FrictionEvent]) -> bool:
    """True when there is anything worth distilling (a conflict or any friction)."""
    return bool(records) or bool(friction)


# --- render -----------------------------------------------------------------


def _friction_tally(friction: list[FrictionEvent]) -> dict[str, int]:
    tally: dict[str, int] = {}
    for event in friction:
        tally[event.kind] = tally.get(event.kind, 0) + 1
    return tally


def digest_payload(
    *, records: list[ConflictRecord], friction: list[FrictionEvent], day_label: str
) -> dict:
    """Machine-readable digest for the reasoned tier / knowledge queue."""
    unresolved = [r for r in records if not r.resolved]
    return {
        "day": day_label,
        "conflict_count": len(records),
        "unresolved_count": len(unresolved),
        "friction": _friction_tally(friction),
        "conflicts": [
            {
                "id": r.conflict_id,
                "resolved": r.resolved,
                "preview": r.hunk_preview,
            }
            for r in records
        ],
        "friction_events": [
            {"kind": e.kind, "detail": e.detail, "ref": e.ref} for e in friction
        ],
    }


def build_digest(
    *, records: list[ConflictRecord], friction: list[FrictionEvent], day_label: str
) -> str:
    """Human-readable markdown digest of the day's conflict friction."""
    unresolved = [r for r in records if not r.resolved]
    tally = _friction_tally(friction)

    lines = [f"# Conflict digest — {day_label}", ""]
    if not has_signal(records=records, friction=friction):
        lines.append("No conflicts or merge friction recorded today. Clean day.")
        lines.append("")
        return "\n".join(lines)

    lines.append(
        f"Recorded conflicts: **{len(records)}** "
        f"({len(unresolved)} unresolved). "
        f"Merge friction: "
        + (", ".join(f"{k} ×{v}" for k, v in sorted(tally.items())) or "none")
        + "."
    )
    lines.append("")

    if records:
        lines.append("## Conflicts (git rerere)")
        lines.append("")
        for r in records:
            status = "resolved" if r.resolved else "UNRESOLVED"
            lines.append(f"- `{r.conflict_id[:8]}` ({status}): {r.hunk_preview}")
        lines.append("")

    if friction:
        lines.append("## Friction (git reflog)")
        lines.append("")
        for e in friction:
            lines.append(f"- **{e.kind}** — {e.detail} (`{e.ref}`)")
        lines.append("")

    lines.append("## For the distiller")
    lines.append("")
    lines.append(
        "Look for *recurring* patterns across days (same files/hunks conflicting, "
        "repeated rebases on the same branch pair). A pattern that repeats is a "
        "candidate `LES-L##` lesson — propose the lesson, do not just log the noise."
    )
    lines.append("")
    return "\n".join(lines)


# --- CLI --------------------------------------------------------------------


def _git_reflog(repo_root: Path, since: str) -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(repo_root), "reflog", f"--since={since}"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout
    except OSError:
        return ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Harvest the day's git conflict friction (AOS-SELFHEAL-003)."
    )
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument(
        "--since",
        default="midnight",
        help="git reflog time window (default: midnight — today's session).",
    )
    parser.add_argument("--day-label", default=None, help="Override the digest date label.")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Markdown output path (default: .archetype/conflicts/<day>.md).",
    )
    parser.add_argument("--json", type=Path, default=None, help="Also write the JSON payload here.")
    args = parser.parse_args(argv)

    rr_cache = args.repo_root / ".git" / "rr-cache"
    records = harvest_rerere(rr_cache)
    friction = parse_reflog(_git_reflog(args.repo_root, args.since))

    day_label = args.day_label or _today(args.repo_root)
    digest = build_digest(records=records, friction=friction, day_label=day_label)

    out = args.out or (args.repo_root / ".archetype" / "conflicts" / f"{day_label}.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(digest, encoding="utf-8")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps(
                digest_payload(records=records, friction=friction, day_label=day_label),
                indent=2,
            ),
            encoding="utf-8",
        )

    signal = has_signal(records=records, friction=friction)
    print(f"Wrote conflict digest: {out}")
    print(f"signal={'true' if signal else 'false'}")
    return 0


def _today(repo_root: Path) -> str:
    # Derive the date from git rather than Python's clock so the label matches the
    # reflog window's frame of reference and stays reproducible in tests via --day-label.
    out = subprocess.run(
        ["git", "-C", str(repo_root), "log", "-1", "--format=%cs"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    return out or "today"


if __name__ == "__main__":
    sys.exit(main())
