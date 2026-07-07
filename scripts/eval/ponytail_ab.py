#!/usr/bin/env python3
"""Ponytail A/B token harness — measure ponytail's dev-time effect for THIS repo.

Runs each fixed coding task through ``claude -p --output-format json`` twice —
**OFF** (bare prompt) and **ON** (ponytail's rules prepended, its 'rules file'
mode) — in an isolated empty cwd, and reports the OUTPUT-token / cost / result-LOC
delta from Claude's own usage accounting. This gives a real number on OUR task
profile instead of the vendor's benchmark (measured against a bare, unconstrained
model — not against a repo that already enforces YAGNI/DRY like this one).

Important: each ``claude -p`` carries a large FIXED CLI overhead (~$0.10, a big
cached system prompt), so total cost is dominated by that. The meaningful signal
is the **output-token and result-LOC delta**, which is where ponytail acts.

Tasks deliberately mix an *over-build trap* (where ponytail should help) and an
*already-minimal* task (where the authors admit it may not help, or may cost more)
so the aggregate is honest for a real mix. Add more tasks in ``TASKS``.

    PYTHONPATH=. python scripts/eval/ponytail_ab.py [--model sonnet] \
        [--tasks over_build,minimal] [--runs 1]

Costs real Claude tokens (that is the measurement). Defaults are small; scale with
--runs for a tighter median. Not pytest-collected.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RULES = (REPO_ROOT / "scripts" / "eval" / "ponytail_rules.md").read_text(encoding="utf-8")

# Fixed tasks. over_build/fastapi have an "over-build trap"; minimal is already
# tight (ponytail's own caveat: it may not help / may cost more on these).
TASKS = {
    "over_build": "Write a Python function to validate an email address.",
    "minimal": "Write a Python function that returns the sum of a list of numbers.",
    "fastapi": 'Write a FastAPI endpoint GET /health that returns {"status": "ok"}.',
    "debounce": "Write a JavaScript debounce function.",
}


def run_claude(prompt: str, model: str | None, timeout: float = 240) -> dict | None:
    """One isolated `claude -p` call; return its usage/cost/LOC, or None on failure."""
    argv = ["claude", "-p", prompt, "--output-format", "json"]
    if model:
        argv += ["--model", model]
    try:
        with tempfile.TemporaryDirectory(prefix="ponytail-ab-") as cwd:
            t0 = time.time()
            out = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, cwd=cwd)
            dt = time.time() - t0
        data = json.loads(out.stdout)
    except Exception:
        return None
    items = data if isinstance(data, list) else [data]
    result = next(
        (it for it in items if isinstance(it, dict) and it.get("type") == "result"),
        items[-1] if items else {},
    )
    usage = result.get("usage", {}) or {}
    text = result.get("result", "") or ""
    loc = len([ln for ln in text.splitlines() if ln.strip()])
    return {
        "out": usage.get("output_tokens", 0),
        "in": usage.get("input_tokens", 0),
        "cost": result.get("total_cost_usd", 0.0),
        "loc": loc,
        "secs": round(dt, 1),
    }


def _pct(new: float, old: float) -> float:
    return (100.0 * (new - old) / old) if old else 0.0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ponytail on/off token A/B.")
    parser.add_argument("--model", default="sonnet")
    parser.add_argument("--tasks", default="over_build,minimal")
    parser.add_argument("--runs", type=int, default=1)
    args = parser.parse_args(argv)

    tasks = [t.strip() for t in args.tasks.split(",") if t.strip() in TASKS]
    if not tasks:
        print(f"No known tasks in {args.tasks!r}. Known: {', '.join(TASKS)}")
        return 1
    print(f"Ponytail A/B — model={args.model}, tasks={tasks}, runs={args.runs}")
    print("OFF = bare prompt · ON = ponytail rules prepended (its 'rules file' mode)\n")

    agg = {"off": {"out": 0, "cost": 0.0, "loc": 0}, "on": {"out": 0, "cost": 0.0, "loc": 0}}
    for task in tasks:
        base = TASKS[task]
        for run in range(args.runs):
            off = run_claude(base, args.model)
            on = run_claude(RULES + "\n\nTask: " + base, args.model)
            if not off or not on:
                print(f"  {task} (run {run + 1}): a call failed — skipped\n")
                continue
            print(f"── {task} (run {run + 1})")
            print(f"   OFF: out={off['out']:5} tok | ${off['cost']:.4f} | {off['loc']:3} LOC | {off['secs']}s")
            print(f"   ON : out={on['out']:5} tok | ${on['cost']:.4f} | {on['loc']:3} LOC | {on['secs']}s")
            print(f"   Δ  : output {_pct(on['out'], off['out']):+.0f}% | "
                  f"cost {_pct(on['cost'], off['cost']):+.0f}% | LOC {_pct(on['loc'], off['loc']):+.0f}%\n")
            for arm, d in (("off", off), ("on", on)):
                agg[arm]["out"] += d["out"]
                agg[arm]["cost"] += d["cost"]
                agg[arm]["loc"] += d["loc"]

    if agg["off"]["out"]:
        print("── Aggregate (ON vs OFF, negative = ponytail saved) ──")
        print(f"   output tokens: {_pct(agg['on']['out'], agg['off']['out']):+.0f}%   ← where ponytail acts")
        print(f"   total cost:    {_pct(agg['on']['cost'], agg['off']['cost']):+.0f}%   (dominated by fixed CLI overhead)")
        print(f"   result LOC:    {_pct(agg['on']['loc'], agg['off']['loc']):+.0f}%")
        print("\n   Read the output-token + LOC deltas, not total cost: the fixed ~$0.10/call")
        print("   CLI overhead swamps cost. Against this repo's already-minimalist CLAUDE.md,")
        print("   expect a smaller effect than ponytail's vendor benchmark (measured vs a bare model).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
