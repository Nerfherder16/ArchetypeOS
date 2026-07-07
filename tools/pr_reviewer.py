#!/usr/bin/env python3
"""Tier-1 local code reviewer CLI (AOS-LLM-REVIEW-001).

Runs the per-category local reviewer (aos_core.services.code_review) over a diff
and prints advisory findings. Layered ON TOP of the deterministic PR Guardian
(tools/pr_guardian.py) — it is **advisory only, never a merge gate**, and stays
out of the Guardian so the Guardian remains deterministic and hermetic.

**Fail-open:** if no local model is configured/reachable, it prints a skip line
and exits 0. It can never fail a build.

Usage:
  python tools/pr_reviewer.py --base origin/main --head HEAD
  python tools/pr_reviewer.py --pr 92 [--comment]      # diff + optional comment via gh

Provider comes from settings (LLM_BASE_URL / LLM_MODEL / LLM_API_KEY), defaulting
to the on-node ``qwen2.5-coder-reviewer`` local model; override with flags.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packages" / "aos_core"))

from aos_core.config import get_settings  # noqa: E402
from aos_core.llm import OpenAICompatibleProvider  # noqa: E402
from aos_core.services.code_review import review_diff  # noqa: E402


def _diff_from_refs(base: str, head: str) -> str:
    # Three-dot = changes on head since it diverged from base (the GitHub PR diff).
    return subprocess.run(
        ["git", "diff", "--no-color", f"{base}...{head}"],
        capture_output=True, text=True, check=False,
    ).stdout


def _diff_from_pr(number: int) -> str:
    return subprocess.run(
        ["gh", "pr", "diff", str(number)], capture_output=True, text=True, check=False
    ).stdout


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Tier-1 local code reviewer (advisory).")
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--pr", type=int, default=None, help="Review a GitHub PR's diff (via gh).")
    parser.add_argument("--comment", action="store_true", help="Post findings as a PR comment.")
    parser.add_argument("--max-tokens", type=int, default=512)
    parser.add_argument("--timeout", type=float, default=190.0)
    parser.add_argument("--model", default=None)
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--api-key", default=None)
    args = parser.parse_args(argv)

    diff = _diff_from_pr(args.pr) if args.pr else _diff_from_refs(args.base, args.head)
    if not diff.strip():
        print("Local reviewer: empty diff — nothing to review.")
        return 0

    settings = get_settings()
    try:
        provider = OpenAICompatibleProvider(
            base_url=args.base_url or getattr(settings, "llm_base_url", "http://localhost:11434/v1"),
            model=args.model or getattr(settings, "llm_model", "qwen2.5-coder-reviewer"),
            api_key=args.api_key or getattr(settings, "llm_api_key", ""),
            timeout=args.timeout,
        )
        findings = review_diff(provider, diff, max_tokens=args.max_tokens)
    except Exception as exc:  # noqa: BLE001 — advisory: never fail the caller
        print(f"Local reviewer unavailable ({exc}) — skipped (advisory, non-blocking).")
        return 0

    if not findings:
        print("Local reviewer: no advisory findings.")
        return 0

    body = (
        "🤖 **Local reviewer (advisory · Tier-1, on-node)** — not a merge gate; "
        "verify each finding.\n\n"
        + "\n".join(f"- {f.as_line()}" for f in findings)
    )
    print(body)
    if args.comment and args.pr:
        subprocess.run(
            ["gh", "pr", "comment", str(args.pr), "--body", body], check=False
        )
        print(f"\nPosted {len(findings)} finding(s) to PR #{args.pr}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
