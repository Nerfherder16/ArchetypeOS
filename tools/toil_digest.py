"""Deterministic toil harvester for the self-learn loop (AOS-SELFHEAL-004).

The second self-learn probe (sibling of ``conflict_digest.py``). Where the
conflict probe harvests merge *friction*, this one harvests **toil**: a recurring
multi-step git ritual repeated many times in a session (e.g. checkout -> commit
-> merge, done six times to ship six PRs). A ritual repeated often enough is a
candidate for a **skill or script** that captures it — the reasoned distiller
proposes one; this module only detects the pattern.

Signal source: ``git reflog`` for the window. Each entry's leading verb
(checkout / commit / merge / pull / reset / rebase / ...) is the action; the
ordered action sequence is scanned for the longest contiguous k-gram that repeats
at least ``min_count`` times. Consecutive duplicate actions collapse (N commits on
a branch -> one ``commit``) so the ritual shape is stable.

Stdlib-only and hermetic: the harvest functions take a reflog string / action
list, so the tests never touch git or the working tree.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Reflog leading verbs worth counting as a ritual step. "rebase (finish)" etc.
# normalise to "rebase" via the "(" split in _reflog_action.
_ACTION_VERBS = (
    "checkout",
    "commit",
    "merge",
    "pull",
    "reset",
    "rebase",
    "cherry-pick",
    "revert",
    "clone",
    "branch",
)

_DEFAULT_MIN_LEN = 3
_DEFAULT_MAX_LEN = 8
_DEFAULT_MIN_COUNT = 3


@dataclass
class Ritual:
    """A recurring contiguous sequence of git actions and how often it repeated."""

    actions: tuple[str, ...]
    count: int


def _reflog_action(subject: str) -> str | None:
    """Classify a reflog subject's leading action verb, or None if not a verb."""
    head = subject.strip().split(":", 1)[0].strip()
    first = head.split(" ", 1)[0].split("(", 1)[0]
    return first if first in _ACTION_VERBS else None


def parse_reflog_actions(reflog_text: str) -> list[str]:
    """Ordered action verbs from reflog text, collapsing consecutive duplicates."""
    actions: list[str] = []
    for line in reflog_text.splitlines():
        line = line.strip()
        if not line or ": " not in line:
            continue
        _ref_part, subject = line.split(": ", 1)
        action = _reflog_action(subject)
        if action is None:
            continue
        if actions and actions[-1] == action:
            continue  # collapse a run of the same action (e.g. many commits)
        actions.append(action)
    return actions


def _is_contiguous_subseq(small: tuple[str, ...], big: tuple[str, ...]) -> bool:
    if len(small) >= len(big):
        return False
    return any(big[i : i + len(small)] == small for i in range(len(big) - len(small) + 1))


def _canonical_rotation(gram: tuple[str, ...]) -> tuple[str, ...]:
    """The lexicographically smallest rotation — a stable id for a rotation class."""
    return min(tuple(gram[i:] + gram[:i]) for i in range(len(gram)))


def _dominant_cycle(
    actions: list[str], min_len: int, max_len: int, min_count: int, min_coverage: float
) -> Ritual | None:
    """The smallest period p that the sequence (mostly) repeats with, or None.

    A ritual done over and over is a *cycle*: the action sequence is ~periodic with
    period p. Scanning smallest-p-first yields the fundamental ritual (one clean
    cycle) rather than a doubled window or its phase-shifted rotations.
    """
    n = len(actions)
    for p in range(min_len, min(max_len, n) + 1):
        periods = n // p
        if periods < min_count:
            continue
        total = n - p
        if total <= 0:
            continue
        matches = sum(1 for i in range(total) if actions[i] == actions[i + p])
        if matches / total >= min_coverage:
            return Ritual(actions=tuple(actions[:p]), count=periods)
    return None


def find_rituals(
    actions: list[str],
    *,
    min_len: int = _DEFAULT_MIN_LEN,
    max_len: int = _DEFAULT_MAX_LEN,
    min_count: int = _DEFAULT_MIN_COUNT,
    min_coverage: float = 0.6,
) -> list[Ritual]:
    """Recurring multi-step git rituals worth automating.

    Primary: dominant-cycle detection (smallest period the session repeats with) —
    the right model for "I did the same dance N times." Fallback: for a block that
    recurs without tiling the whole session, the shortest k-gram repeating at least
    ``min_count`` times, deduped across rotations. Deterministic throughout.
    """
    cycle = _dominant_cycle(actions, min_len, max_len, min_count, min_coverage)
    if cycle is not None:
        return [cycle]

    n = len(actions)
    for k in range(min_len, min(max_len, n) + 1):
        counts: dict[tuple[str, ...], int] = {}
        for i in range(0, n - k + 1):
            gram = tuple(actions[i : i + k])
            counts[gram] = counts.get(gram, 0) + 1
        qualifying = [(gram, c) for gram, c in counts.items() if c >= min_count]
        if not qualifying:
            continue
        qualifying.sort(key=lambda gc: (gc[1], gc[0]), reverse=True)
        accepted: list[Ritual] = []
        seen_rotations: set[tuple[str, ...]] = set()
        for gram, c in qualifying:
            rotation = _canonical_rotation(gram)
            if rotation in seen_rotations:
                continue
            if any(_is_contiguous_subseq(gram, a.actions) for a in accepted):
                continue
            seen_rotations.add(rotation)
            accepted.append(Ritual(actions=gram, count=c))
            if len(accepted) >= 3:
                break
        return accepted
    return []


def has_signal(rituals: list[Ritual]) -> bool:
    """True when at least one recurring ritual worth automating was found."""
    return bool(rituals)


# --- render -----------------------------------------------------------------


def _ritual_label(ritual: Ritual) -> str:
    return " -> ".join(ritual.actions)


def digest_payload(*, rituals: list[Ritual], day_label: str) -> dict:
    """Machine-readable digest for the reasoned tier / skill queue."""
    return {
        "day": day_label,
        "ritual_count": len(rituals),
        "rituals": [
            {"actions": list(r.actions), "count": r.count} for r in rituals
        ],
    }


def build_digest(*, rituals: list[Ritual], day_label: str) -> str:
    """Human-readable markdown digest of the day's toil."""
    lines = [f"# Toil digest — {day_label}", ""]
    if not has_signal(rituals):
        lines.append("No recurring multi-step ritual today. Clean day (no toil to automate).")
        lines.append("")
        return "\n".join(lines)

    lines.append(f"Recurring rituals: **{len(rituals)}** (repeated {_DEFAULT_MIN_COUNT}+ times).")
    lines.append("")
    lines.append("## Rituals (git reflog)")
    lines.append("")
    for r in rituals:
        lines.append(f"- **{_ritual_label(r)}** ×{r.count}")
    lines.append("")
    lines.append("## For the distiller")
    lines.append("")
    lines.append(
        "A ritual repeated this often is TOIL — propose a **skill** "
        "(`.claude/skills/<name>/SKILL.md`) or a **script** (`scripts/<name>.sh`) that "
        "captures the whole sequence, so it becomes one command. Only if the ritual is a "
        "genuine, generalizable workflow — do NOT manufacture automation for a one-off "
        "(Article XII). Review-first: open a PR, never wire it into anything automatically."
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


def _today(repo_root: Path) -> str:
    out = subprocess.run(
        ["git", "-C", str(repo_root), "log", "-1", "--format=%cs"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    return out or "today"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Harvest the day's recurring git toil rituals (AOS-SELFHEAL-004)."
    )
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument(
        "--since",
        default="midnight",
        help="git reflog time window (default: midnight — today's session).",
    )
    parser.add_argument("--day-label", default=None, help="Override the digest date label.")
    parser.add_argument("--min-count", type=int, default=_DEFAULT_MIN_COUNT)
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Markdown output path (default: .archetype/toil/<day>.md).",
    )
    parser.add_argument("--json", type=Path, default=None, help="Also write the JSON payload here.")
    args = parser.parse_args(argv)

    actions = parse_reflog_actions(_git_reflog(args.repo_root, args.since))
    rituals = find_rituals(actions, min_count=args.min_count)

    day_label = args.day_label or _today(args.repo_root)
    digest = build_digest(rituals=rituals, day_label=day_label)

    out = args.out or (args.repo_root / ".archetype" / "toil" / f"{day_label}.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(digest, encoding="utf-8")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps(digest_payload(rituals=rituals, day_label=day_label), indent=2),
            encoding="utf-8",
        )

    print(f"Wrote toil digest: {out}")
    print(f"signal={'true' if has_signal(rituals) else 'false'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
