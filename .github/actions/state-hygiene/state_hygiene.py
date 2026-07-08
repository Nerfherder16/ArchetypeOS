#!/usr/bin/env python3
"""Portable canonical-state refresher (AOS-STATE-RECON-001, reusable slice).

Self-contained (stdlib only, no ArchetypeOS imports) so it can run inside ANY repo
that adopts the `state-hygiene` composite action. It refreshes the machine-owned
fields inside a delimited canonical block in a state doc so they are derived from
git on every merge and therefore cannot drift:

    <!-- AOS-CANONICAL:START -->
    - Watermark PR: #<max merged PR, from git>
    - Active Branch: <none (on main) | `feature/branch`>
    ... human-authored fields left untouched ...
    <!-- AOS-CANONICAL:END -->

The marker name and doc path are configurable, so the same mechanism serves the
ArchetypeOS repo and any repo it builds or onboards. Human fields are never touched.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

_MERGED_PR = re.compile(r"Merge pull request #(\d+)")
_SQUASH_PR = re.compile(r"\(#(\d+)\)")


def _git(repo_root: Path, *args: str) -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(repo_root), *args],
            capture_output=True, text=True, check=False, timeout=20,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def newest_pr(git_log_text: str) -> int | None:
    nums = {int(n) for n in _MERGED_PR.findall(git_log_text)}
    nums |= {int(n) for n in _SQUASH_PR.findall(git_log_text)}
    return max(nums) if nums else None


def derive(repo_root: Path) -> dict:
    log = _git(repo_root, "log", "--oneline", "-200")
    branch = _git(repo_root, "rev-parse", "--abbrev-ref", "HEAD").strip() or "main"
    active = "none (on main)" if branch in ("main", "HEAD", "") else f"`{branch}`"
    return {"watermark": newest_pr(log), "active_branch": active}


def refresh_block(text: str, marker: str, derived: dict) -> tuple[str, bool]:
    block_re = re.compile(
        rf"<!-- {re.escape(marker)}:START -->(.*?)<!-- {re.escape(marker)}:END -->",
        re.DOTALL,
    )
    match = block_re.search(text)
    if not match:
        return text, False
    block = new_block = match.group(1)
    # [ \t]* not \s* — \s matches newlines, and with (?m) ^ also matches at string
    # position 0, so \s* would swallow the line's leading newline and fuse it onto
    # the previous line (LES-L09 addendum).
    if derived.get("watermark") is not None:
        new_block = re.sub(
            r"(?im)^[ \t]*-[ \t]*Watermark PR:[ \t]*#?\d+.*$",
            lambda _m: f"- Watermark PR: #{derived['watermark']}",
            new_block,
            count=1,
        )
    if derived.get("active_branch"):
        new_block = re.sub(
            r"(?im)^[ \t]*-[ \t]*Active Branch:[ \t]*.+$",
            lambda _m: f"- Active Branch: {derived['active_branch']}",
            new_block,
            count=1,
        )
    if new_block == block:
        return text, False
    return text[: match.start(1)] + new_block + text[match.end(1) :], True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Refresh a canonical-state block from git.")
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--doc", default="docs/CURRENT_STATE.md", help="Canonical state doc path.")
    parser.add_argument("--marker", default="AOS-CANONICAL", help="Canonical block marker base.")
    args = parser.parse_args(argv)

    doc_path = args.repo_root / args.doc
    if not doc_path.exists():
        print(f"state-hygiene: no canonical doc at {doc_path} — nothing to do.")
        return 0
    text = doc_path.read_text(encoding="utf-8")
    derived = derive(args.repo_root)
    new_text, changed = refresh_block(text, args.marker, derived)
    if changed:
        doc_path.write_text(new_text, encoding="utf-8")
        print(f"state-hygiene: refreshed watermark #{derived['watermark']}, branch {derived['active_branch']}")
    else:
        print("state-hygiene: canonical block already current (no change).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
