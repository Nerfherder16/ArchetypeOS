#!/usr/bin/env python3
"""Deterministic doc-vs-reality staleness detector (AOS-20, closes LES-007).

Doc staleness was previously caught only by human review — the one Phase-10
Alpha "NO by machine" (LES-007): ``.archetype/roadmap.md`` sat at "Foundation"
long after v0.1 shipped, and CURRENT_STATE lagged a merge. This tool cross-checks
the signals it can *mechanically verify* against ground truth and reports drift.

Design (the deterministic floor of a larger "doc verifier" target; extend it by
adding pure ``check_*`` functions, never by rewriting this one):

- Pure check functions take strings so they are trivially/hermetically testable.
- A thin IO layer reads the real files and shells ``git log``, degrading to empty
  input on any failure (fail-open — never crash a caller, never a false alarm).
- Findings carry a ``severity`` of ``"hard"`` or ``"soft"``. The CLI exits non-zero
  only on HARD staleness; thresholds are tuned so the normal one-PR reconciliation
  lag stays SOFT.

Stdlib-only and hermetic. Usable standalone (CI/manual) or as an advisory,
non-blocking PR Guardian WARN (see tools/pr_guardian.check_doc_staleness).
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

HARD = "hard"
SOFT = "soft"

# An early-phase roadmap label paired with a completed reality is definitive drift.
EARLY_PHASE_TOKENS = ("foundation", "phase 0", "documentation foundation", "scaffold")
# Ground-truth completion markers that CURRENT_STATE carries once real work ships.
COMPLETION_MARKERS = re.compile(r"v0\.\d+\s+complete|post-v0\.\d+|sprint\s+[1-9]", re.IGNORECASE)

_PR_REF = re.compile(r"#(\d+)")
_MERGED_PR = re.compile(r"Merge pull request #(\d+)")

# Lag beyond this many PRs between git and the state docs is HARD; within it, SOFT.
DEFAULT_HARD_THRESHOLD = 3


@dataclass(frozen=True)
class Finding:
    signal: str
    severity: str  # "hard" | "soft"
    message: str
    evidence: str


# --- pure helpers (fixture-testable) ---------------------------------------


def parse_current_phase(roadmap_text: str) -> str | None:
    """Return the first non-empty line under a ``## Current phase`` heading."""
    lines = roadmap_text.splitlines()
    for i, line in enumerate(lines):
        if line.strip().lower().lstrip("#").strip() == "current phase":
            for follow in lines[i + 1 :]:
                if follow.strip():
                    return follow.strip().rstrip(".").strip()
            return None
    return None


def extract_pr_numbers(text: str) -> set[int]:
    return {int(n) for n in _PR_REF.findall(text)}


def extract_merged_prs(git_log_text: str) -> list[int]:
    return [int(n) for n in _MERGED_PR.findall(git_log_text)]


# --- signals ----------------------------------------------------------------


def check_roadmap_phase(roadmap_text: str, current_state_text: str) -> list[Finding]:
    """Signal 1: roadmap declares an early phase while reality shows completion."""
    phase = parse_current_phase(roadmap_text)
    if not phase:
        return []
    phase_l = phase.lower()
    is_early = any(token in phase_l for token in EARLY_PHASE_TOKENS)
    reality_complete = bool(COMPLETION_MARKERS.search(current_state_text))
    if is_early and reality_complete:
        marker = COMPLETION_MARKERS.search(current_state_text)
        return [
            Finding(
                "roadmap-phase-stale",
                HARD,
                f".archetype/roadmap.md 'Current phase' is '{phase}' but CURRENT_STATE shows completed work.",
                f"roadmap phase='{phase}'; CURRENT_STATE matched '{marker.group(0) if marker else ''}'",
            )
        ]
    return []


def check_state_pr_lag(
    git_log_text: str,
    current_state_text: str,
    recent_changes_text: str,
    hard_threshold: int = DEFAULT_HARD_THRESHOLD,
) -> list[Finding]:
    """Signal 2: newest merged PR in git vs newest PR referenced in the state docs."""
    merged = extract_merged_prs(git_log_text)
    if not merged:
        return []
    newest_merged = max(merged)
    referenced = extract_pr_numbers(current_state_text) | extract_pr_numbers(recent_changes_text)
    newest_ref = max(referenced) if referenced else 0
    lag = newest_merged - newest_ref
    if lag <= 0:
        return []
    evidence = f"newest merged PR #{newest_merged}; newest referenced in state docs #{newest_ref} (lag {lag})"
    if lag > hard_threshold:
        return [
            Finding(
                "state-docs-pr-lag",
                HARD,
                f"State docs are {lag} PRs behind git (newest merged #{newest_merged}, docs at #{newest_ref}).",
                evidence,
            )
        ]
    return [
        Finding(
            "state-docs-pr-lag",
            SOFT,
            f"State docs lag git by {lag} PR(s) (newest merged #{newest_merged}, docs at #{newest_ref}) — within the reconciliation window.",
            evidence,
        )
    ]


def run_checks(
    *,
    roadmap_text: str,
    current_state_text: str,
    recent_changes_text: str,
    git_log_text: str,
    hard_threshold: int = DEFAULT_HARD_THRESHOLD,
) -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(check_roadmap_phase(roadmap_text, current_state_text))
    findings.extend(
        check_state_pr_lag(git_log_text, current_state_text, recent_changes_text, hard_threshold)
    )
    return findings


# --- IO layer (kept thin; degrades to empty input, never raises) ------------


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _git_log(repo_root: Path, limit: int = 60) -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(repo_root), "log", "--oneline", f"-{limit}"],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def evaluate(repo_root: Path = REPO_ROOT, hard_threshold: int = DEFAULT_HARD_THRESHOLD) -> list[Finding]:
    """Gather real inputs from the working tree and run every signal."""
    return run_checks(
        roadmap_text=_read(repo_root / ".archetype" / "roadmap.md"),
        current_state_text=_read(repo_root / "docs" / "CURRENT_STATE.md"),
        recent_changes_text=_read(repo_root / "docs" / "RECENT_CHANGES.md"),
        git_log_text=_git_log(repo_root),
        hard_threshold=hard_threshold,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Detect doc-vs-reality staleness (AOS-20).")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--hard-threshold", type=int, default=DEFAULT_HARD_THRESHOLD)
    args = parser.parse_args(argv)

    findings = evaluate(repo_root=args.repo_root, hard_threshold=args.hard_threshold)

    print("# Doc-Staleness Report")
    print()
    if not findings:
        print("Verdict: FRESH")
        print("No doc-staleness signals tripped.")
        return 0

    hard = [f for f in findings if f.severity == HARD]
    print(f"Verdict: {'STALE' if hard else 'ADVISORY'}")
    print()
    for finding in findings:
        print(f"- [{finding.severity.upper()}] {finding.signal}: {finding.message}")
        print(f"    evidence: {finding.evidence}")
    return 1 if hard else 0


if __name__ == "__main__":
    sys.exit(main())
