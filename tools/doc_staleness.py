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
# Squash merges (this repo's default) put the PR number as "Title (#123)" in the
# commit subject — the traditional _MERGED_PR pattern misses those entirely, which
# is why the lag check under-detected (LES-L09).
_SQUASH_PR = re.compile(r"\(#(\d+)\)")

# The machine-owned canonical block in CURRENT_STATE.md and its two auto-derived
# fields. Scoping the watermark check to THIS block (not the union of all state
# docs) is the fix for the masking bug: keeping RECENT_CHANGES current used to hide
# CURRENT_STATE's own staleness (LES-L09).
_CANONICAL_BLOCK = re.compile(
    r"<!-- AOS-CANONICAL:START -->(.*?)<!-- AOS-CANONICAL:END -->", re.DOTALL
)
# [ \t]* not \s* for the leading indent: \s matches newlines and (?m)^ matches at
# string position 0, so \s* would swallow the line's leading newline during .sub
# and fuse it onto the previous line (LES-L09 addendum).
_WATERMARK_LINE = re.compile(r"(?im)^[ \t]*-[ \t]*Watermark PR:[ \t]*#?(\d+)")
_ACTIVE_BRANCH_LINE = re.compile(r"(?im)^[ \t]*-[ \t]*Active Branch:[ \t]*(.+?)[ \t]*$")
_NOT_A_BRANCH = ("none", "main", "n/a", "-")

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
    """PR numbers from both traditional merge commits and squash-merge subjects."""
    nums = {int(n) for n in _MERGED_PR.findall(git_log_text)}
    nums |= {int(n) for n in _SQUASH_PR.findall(git_log_text)}
    return sorted(nums)


# --- canonical state block (AOS-STATE-RECON-001) ----------------------------


@dataclass(frozen=True)
class Canonical:
    watermark: int | None
    active_branch: str | None


def parse_canonical(current_state_text: str) -> Canonical:
    """Parse the AOS-CANONICAL block's watermark + active branch."""
    match = _CANONICAL_BLOCK.search(current_state_text)
    block = match.group(1) if match else current_state_text
    wm = _WATERMARK_LINE.search(block)
    ab = _ACTIVE_BRANCH_LINE.search(block)
    return Canonical(
        watermark=int(wm.group(1)) if wm else None,
        active_branch=ab.group(1).strip() if ab else None,
    )


def _branch_is_stale(active_branch: str | None, origin_branches: set[str]) -> bool:
    """True when the named active branch is not an open branch on origin."""
    if not active_branch or not origin_branches:
        return False
    lowered = active_branch.lower().lstrip("`").strip()
    if lowered.startswith(_NOT_A_BRANCH):
        return False
    token = active_branch.strip().strip("`").split()[0].strip("`")
    return token not in origin_branches


def derive_canonical(git_log_text: str, current_branch: str | None) -> dict:
    """The auto-derived canonical fields: watermark from git, branch from HEAD."""
    merged = extract_merged_prs(git_log_text)
    active = (
        "none (on main)"
        if current_branch in ("main", "", None)
        else f"`{current_branch}`"
    )
    return {"watermark": max(merged) if merged else None, "active_branch": active}


def refresh_canonical_block(text: str, derived: dict) -> tuple[str, bool]:
    """Rewrite the auto-derived lines inside the canonical block. Returns (text, changed)."""
    match = _CANONICAL_BLOCK.search(text)
    if not match:
        return text, False
    block = match.group(1)
    new_block = block
    if derived.get("watermark") is not None:
        new_block = _WATERMARK_LINE.sub(
            lambda _m: f"- Watermark PR: #{derived['watermark']}", new_block, count=1
        )
    if derived.get("active_branch"):
        new_block = _ACTIVE_BRANCH_LINE.sub(
            lambda _m: f"- Active Branch: {derived['active_branch']}", new_block, count=1
        )
    if new_block == block:
        return text, False
    return text[: match.start(1)] + new_block + text[match.end(1) :], True


def check_canonical_state(
    current_state_text: str,
    git_log_text: str,
    origin_branches: set[str],
    hard_threshold: int = DEFAULT_HARD_THRESHOLD,
) -> list[Finding]:
    """Signal 3: CURRENT_STATE's OWN canonical block vs git (not the union of docs)."""
    findings: list[Finding] = []
    canonical = parse_canonical(current_state_text)
    merged = extract_merged_prs(git_log_text)
    newest = max(merged) if merged else 0
    if canonical.watermark is not None and newest:
        lag = newest - canonical.watermark
        if lag > hard_threshold:
            findings.append(
                Finding(
                    "canonical-watermark-lag",
                    HARD,
                    f"CURRENT_STATE watermark #{canonical.watermark} is {lag} PRs behind git (#{newest}).",
                    f"canonical watermark #{canonical.watermark}; newest merged #{newest}",
                )
            )
    if _branch_is_stale(canonical.active_branch, origin_branches):
        findings.append(
            Finding(
                "canonical-active-branch-stale",
                HARD,
                f"CURRENT_STATE names active branch '{canonical.active_branch}', not an open branch on origin.",
                f"active branch '{canonical.active_branch}' absent from origin branches",
            )
        )
    return findings


# --- signals ----------------------------------------------------------------


def check_roadmap_phase(roadmap_text: str, current_state_text: str) -> list[Finding]:
    """Signal 1: roadmap declares an early phase while reality shows completion."""
    phase = parse_current_phase(roadmap_text)
    if not phase:
        return []
    phase_l = phase.lower()
    # An early-phase LABEL *starts with* an early token (the roadmap "Current phase"
    # is a short label by convention). Substring-matching would false-positive on
    # prose that names an early word as history, e.g. "Post-v0.1 ... runtime
    # foundation ..." (LES-024). Defense in depth: a phase that carries its own
    # completion markers ("v0.1 shipped", "post-v0.1") is self-evidently not early.
    is_early = any(phase_l.startswith(token) for token in EARLY_PHASE_TOKENS)
    phase_self_complete = bool(COMPLETION_MARKERS.search(phase))
    reality_complete = bool(COMPLETION_MARKERS.search(current_state_text))
    if is_early and not phase_self_complete and reality_complete:
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


# --- semantic-label drift (AOS-STATE-SEMANTIC-001, finding P1-4) -------------
# The canonical watermark can be numerically current while the human narrative
# rots: AOS-REVIEW-002 found CURRENT_STATE marking shipped subsystems "Proposed".
# A subsystem whose implementation module exists MUST NOT be labelled Proposed.
# (label keywords, implementation module, display name)
_SEMANTIC_SUBSYSTEMS: tuple[tuple[tuple[str, ...], str, str], ...] = (
    (("node",), "packages/aos_core/aos_core/services/nodes.py", "Node/Capability registry"),
    (("connector",), "packages/aos_core/aos_core/services/connectors.py", "Connector registry"),
    (("authority",), "packages/aos_core/aos_core/services/authority.py", "Authority action policy"),
)
_PROPOSED_TOKENS = ("proposed", "not yet first-class in code", "not yet in code")


def check_semantic_labels(current_state_text: str, present_modules: set[str]) -> list[Finding]:
    """A shipped subsystem marked 'Proposed' in the state docs is HARD drift.

    ``present_modules`` is the set of repo-relative module paths that exist on
    disk — a pure input so this stays fixture-testable.
    """
    findings: list[Finding] = []
    for keywords, module, name in _SEMANTIC_SUBSYSTEMS:
        if module not in present_modules:
            continue  # legitimately proposed — no implementation yet
        for line in current_state_text.splitlines():
            stripped = line.strip()
            # Only the Open Decisions status table (markdown rows) carries the
            # authoritative label — prose that merely mentions the backlog does not.
            if not stripped.startswith("|"):
                continue
            low = stripped.lower()
            if any(k in low for k in keywords) and any(t in low for t in _PROPOSED_TOKENS):
                findings.append(
                    Finding(
                        signal="semantic-label-stale",
                        severity=HARD,
                        message=(
                            f"{name} is labelled 'Proposed' but its implementation exists "
                            f"({module}); relabel it to reflect reality."
                        ),
                        evidence=line.strip(),
                    )
                )
                break
    return findings


def run_checks(
    *,
    roadmap_text: str,
    current_state_text: str,
    recent_changes_text: str,
    git_log_text: str,
    origin_branches: set[str] | None = None,
    hard_threshold: int = DEFAULT_HARD_THRESHOLD,
) -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(check_roadmap_phase(roadmap_text, current_state_text))
    findings.extend(
        check_state_pr_lag(git_log_text, current_state_text, recent_changes_text, hard_threshold)
    )
    findings.extend(
        check_canonical_state(
            current_state_text, git_log_text, origin_branches or set(), hard_threshold
        )
    )
    return findings


# --- self-heal: reconciliation draft (AOS-SELFHEAL-001) ---------------------
# `--fix` closes the AOS-20 loop from detect -> correct WITHOUT gaming the alarm
# (Article XII): it generates the correction CONTENT deterministically from git
# and writes it to a machine-owned draft for a human/LLM to apply. It never edits
# the human narrative docs, and the HARD finding stands until they are reconciled.

_MERGE_PR_LINE = re.compile(r"Merge pull request #(\d+) from (\S+)")


def _merge_pr_labels(git_log_text: str) -> dict[int, str]:
    """Map merged PR number -> its merge-commit source ref (provenance)."""
    return {int(num): ref for num, ref in _MERGE_PR_LINE.findall(git_log_text)}


def build_reconciliation_draft(
    *, git_log_text: str, current_state_text: str, recent_changes_text: str
) -> str | None:
    """Deterministic draft of the state-doc reconciliation, or None if current.

    Lists every merged PR that git carries beyond the newest one the state docs
    reference. Content only — the caller writes it to a draft file; it never
    mutates the prose docs.
    """
    merged = extract_merged_prs(git_log_text)
    if not merged:
        return None
    newest_merged = max(merged)
    referenced = extract_pr_numbers(current_state_text) | extract_pr_numbers(recent_changes_text)
    newest_ref = max(referenced) if referenced else 0
    pending = sorted({pr for pr in merged if pr > newest_ref})
    if not pending:
        return None
    labels = _merge_pr_labels(git_log_text)
    lines = [
        "# Pending state reconciliation",
        "",
        "> Auto-generated by `tools/doc_staleness.py --fix` (AOS-SELFHEAL-001). A DRAFT of the",
        "> correction, derived from `git log` — it does NOT edit the state docs. Apply it via the",
        "> `/reconcile-state` skill (or by hand), then delete this file.",
        "",
        f"State docs reference through PR #{newest_ref}; git has merged through PR #{newest_merged}.",
        "Reconcile `docs/CURRENT_STATE.md` and `docs/RECENT_CHANGES.md` to cover:",
        "",
    ]
    for pr in pending:
        label = labels.get(pr, "")
        lines.append(f"- PR #{pr}" + (f" — {label}" if label else ""))
    lines.append("")
    return "\n".join(lines)


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


def _origin_branches(repo_root: Path) -> set[str]:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_root), "branch", "-r", "--format=%(refname:short)"],
            capture_output=True, text=True, check=False, timeout=15,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return set()
    branches: set[str] = set()
    for line in out.splitlines():
        name = line.strip()
        if not name or "->" in name:
            continue
        branches.add(name.split("/", 1)[1] if name.startswith("origin/") else name)
    return branches


def _current_branch(repo_root: Path) -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, check=False, timeout=15,
        ).stdout.strip() or "main"
    except (OSError, subprocess.SubprocessError):
        return "main"


def evaluate(repo_root: Path = REPO_ROOT, hard_threshold: int = DEFAULT_HARD_THRESHOLD) -> list[Finding]:
    """Gather real inputs from the working tree and run every signal."""
    current_state_text = _read(repo_root / "docs" / "CURRENT_STATE.md")
    findings = run_checks(
        roadmap_text=_read(repo_root / ".archetype" / "roadmap.md"),
        current_state_text=current_state_text,
        recent_changes_text=_read(repo_root / "docs" / "RECENT_CHANGES.md"),
        git_log_text=_git_log(repo_root),
        origin_branches=_origin_branches(repo_root),
        hard_threshold=hard_threshold,
    )
    present = {module for _, module, _ in _SEMANTIC_SUBSYSTEMS if (repo_root / module).exists()}
    findings.extend(check_semantic_labels(current_state_text, present))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Detect doc-vs-reality staleness (AOS-20).")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--hard-threshold", type=int, default=DEFAULT_HARD_THRESHOLD)
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Write a deterministic reconciliation DRAFT to .archetype/reconciliation/PENDING.md "
        "(never edits the state docs; apply via /reconcile-state).",
    )
    parser.add_argument(
        "--refresh-canonical",
        action="store_true",
        help="Rewrite the auto-derived CURRENT_STATE canonical fields (watermark PR, "
        "active branch) from git. Machine-owned; run on every merge so they cannot drift.",
    )
    args = parser.parse_args(argv)

    if args.refresh_canonical:
        cs_path = args.repo_root / "docs" / "CURRENT_STATE.md"
        text = _read(cs_path)
        derived = derive_canonical(_git_log(args.repo_root), _current_branch(args.repo_root))
        new_text, changed = refresh_canonical_block(text, derived)
        if changed:
            cs_path.write_text(new_text, encoding="utf-8")
            print(f"Refreshed canonical block: watermark #{derived['watermark']}, "
                  f"active branch {derived['active_branch']}")
        else:
            print("Canonical block already current (no change).")
        return 0

    if args.fix:
        draft = build_reconciliation_draft(
            git_log_text=_git_log(args.repo_root),
            current_state_text=_read(args.repo_root / "docs" / "CURRENT_STATE.md"),
            recent_changes_text=_read(args.repo_root / "docs" / "RECENT_CHANGES.md"),
        )
        if draft:
            pending = args.repo_root / ".archetype" / "reconciliation" / "PENDING.md"
            pending.parent.mkdir(parents=True, exist_ok=True)
            pending.write_text(draft, encoding="utf-8")
            print(f"Wrote reconciliation draft: {pending}")
        else:
            print("No reconciliation draft needed (state docs current with git).")
        print()

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
