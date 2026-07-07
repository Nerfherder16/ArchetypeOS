#!/usr/bin/env python3
"""Local-LLM reviewer eval spike (AOS-LLM-LOCAL-001 → seeds AOS-LLM-EVAL-001).

A **manual** harness (NOT collected by pytest — it needs git history and a real
model endpoint). It runs recent merged-PR diffs through the configured
``OpenAICompatibleProvider`` framed as a code reviewer and logs, per diff, the
model's findings + wall-clock latency + input/output sizes. The council's point:
"the log IS your eval harness writing itself" — this is that log.

It answers the open question with data instead of debate: on YOUR real diffs, is a
local 7B/8B reviewer signal or noise, and is it fast enough to keep on? Run it on
the node that has the model (teevee's Ollama):

    LLM_BASE_URL=http://localhost:11434/v1 LLM_MODEL=qwen3:8b \\
        PYTHONPATH=packages/aos_core python scripts/eval/review_spike.py --count 20

Then read the output and eyeball true-positive vs noise. Scoring against a golden
label set (true/false-positive RATE) is the follow-up, AOS-LLM-EVAL-001; this
harness deliberately stops at "observe + log" so a human sets the bar first.

Latency is wall-clock; input/output are char counts (a token proxy — the provider
does not yet surface the endpoint's `usage`; that is an AOS-LLM-EVAL-001 add).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "packages" / "aos_core"))

from aos_core.config import get_settings  # noqa: E402
from aos_core.llm import OpenAICompatibleProvider  # noqa: E402

REVIEW_SYSTEM = (
    "You are a senior Python code reviewer. Review the following unified diff. "
    "Report ONLY real, concrete issues as a short list, each formatted "
    "<file>:<line-or-symbol> | <severity: nit/warn/bug> | <one-line issue>. "
    "Do not restate the code. If there are no real issues, reply exactly: LGTM. "
    "Be concise."
)


def _git(args: list[str]) -> str:
    return subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args], capture_output=True, text=True, check=False
    ).stdout


def _merge_diffs(base: str, count: int, max_lines: int) -> list[tuple[str, str, str]]:
    """Return [(sha, subject, diff)] for the last ``count`` merges on ``base``.

    The PR's net change is the first-parent diff ``<sha>^1..<sha>``. Diffs longer
    than ``max_lines`` are trimmed (a local model degrades on very long input).
    """
    log = _git(["log", "--merges", "--first-parent", base, f"-n{count}", "--format=%H\t%s"])
    out: list[tuple[str, str, str]] = []
    for line in log.splitlines():
        if "\t" not in line:
            continue
        sha, subject = line.split("\t", 1)
        diff = _git(["diff", "--no-color", f"{sha}^1", sha])
        if not diff.strip():
            continue
        lines = diff.splitlines()
        if len(lines) > max_lines:
            diff = "\n".join(lines[:max_lines]) + f"\n... [trimmed at {max_lines} lines]"
        out.append((sha[:8], subject, diff))
    return out


def _provider(args) -> OpenAICompatibleProvider:
    settings = get_settings()
    return OpenAICompatibleProvider(
        base_url=args.base_url or getattr(settings, "llm_base_url", "http://localhost:11434/v1"),
        model=args.model or getattr(settings, "llm_model", "qwen2.5-coder:7b"),
        api_key=args.api_key or getattr(settings, "llm_api_key", ""),
        timeout=args.timeout,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local-LLM reviewer eval spike.")
    parser.add_argument("--count", type=int, default=10, help="How many recent merges to review.")
    parser.add_argument("--base", default="main", help="Branch to pull merges from.")
    parser.add_argument("--max-diff-lines", type=int, default=400)
    parser.add_argument("--max-tokens", type=int, default=2200)
    parser.add_argument("--timeout", type=float, default=190.0)
    parser.add_argument("--model", default=None, help="Override LLM_MODEL.")
    parser.add_argument("--base-url", default=None, help="Override LLM_BASE_URL.")
    parser.add_argument("--api-key", default=None, help="Override LLM_API_KEY.")
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / ".archetype" / "eval" / "review_spike.jsonl",
        help="Append JSONL results here (gitignored).",
    )
    args = parser.parse_args(argv)

    cases = _merge_diffs(args.base, args.count, args.max_diff_lines)
    if not cases:
        print(f"No merge diffs found on {args.base!r}.")
        return 0

    provider = _provider(args)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    print(f"Reviewer: {provider.model} @ {provider.base_url} — {len(cases)} diff(s)\n")

    latencies: list[float] = []
    errors = 0
    with args.out.open("a", encoding="utf-8") as sink:
        for sha, subject, diff in cases:
            t0 = time.time()
            try:
                result = provider.generate(
                    system=REVIEW_SYSTEM,
                    prompt="Diff to review:\n\n" + diff,
                    max_tokens=args.max_tokens,
                )
                dt = time.time() - t0
                latencies.append(dt)
                findings = result.text.strip()
                finish = result.finish_reason
                err = None
            except Exception as exc:  # noqa: BLE001 — a harness reports, never crashes
                dt = time.time() - t0
                findings, finish, err = "", "error", str(exc)
                errors += 1

            print(f"── {sha}  {subject[:70]}")
            print(f"   {dt:.1f}s | finish={finish} | in={len(diff)}c out={len(findings)}c"
                  + (f" | ERROR: {err}" if err else ""))
            if findings:
                for ln in findings.splitlines():
                    print(f"     {ln}")
            print()
            sink.write(json.dumps({
                "sha": sha, "subject": subject, "latency_s": round(dt, 2),
                "finish": finish, "in_chars": len(diff), "out_chars": len(findings),
                "model": provider.model, "findings": findings, "error": err,
            }) + "\n")

    if latencies:
        latencies.sort()
        mean = sum(latencies) / len(latencies)
        median = latencies[len(latencies) // 2]
        print(f"Summary: {len(cases)} diffs, {errors} error(s). "
              f"latency mean {mean:.1f}s / median {median:.1f}s / max {latencies[-1]:.1f}s.")
        print(f"Log appended: {args.out}")
        print("Next: eyeball findings for true-positive vs noise, set a success bar, "
              "then score against golden labels (AOS-LLM-EVAL-001).")
    return 1 if errors and not latencies else 0


if __name__ == "__main__":
    sys.exit(main())
