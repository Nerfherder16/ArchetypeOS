#!/usr/bin/env python3
"""Local-LLM reviewer eval spike (AOS-LLM-LOCAL-001 -> seeds AOS-LLM-EVAL-001).

A **manual** harness (NOT collected by pytest — it needs git history and a real
model endpoint). It runs recent merged-PR diffs through the configured provider
framed as a code reviewer and logs, per diff, the findings + wall-clock latency
+ sizes to a gitignored JSONL. The council's line: "the log IS your eval harness
writing itself."

Two review modes (``--mode``):
  * ``structured`` (default) — the deep-research setup: a per-category **rubric**
    (pointwise scoring is measurably less lenient), an inline **2-shot** (one real
    finding + one clean/LGTM), an explicit **anti-false-positive** instruction,
    **JSON output** via ``response_format`` (kills prose rambling), plus a
    **code-only file filter** and **wider diff context** (approximating sliced
    context). Pair with the ``qwen2.5-coder-reviewer`` model (Modelfile in this
    dir) whose ``num_ctx 8192`` stops the large-diff truncation.
  * ``plain`` — the original open-ended "issues or LGTM" prompt, for A/B.

    LLM_BASE_URL=http://<host>:11434/v1 LLM_MODEL=qwen2.5-coder-reviewer \\
        PYTHONPATH=packages/aos_core python scripts/eval/review_spike.py --count 20

Latency is wall-clock; sizes are char counts (token proxy). Golden-label scoring
(true/false-positive RATE) is the follow-up, AOS-LLM-EVAL-001.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "packages" / "aos_core"))

from aos_core.config import get_settings  # noqa: E402
from aos_core.llm import OpenAICompatibleProvider  # noqa: E402

CODE_EXTS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".sh", ".java", ".rb",
    ".c", ".h", ".cpp", ".cs", ".kt", ".sql", ".php",
}

# --- prompts ----------------------------------------------------------------

PLAIN_SYSTEM = (
    "You are a senior Python code reviewer. Review the following unified diff. "
    "Report ONLY real, concrete issues as a short list, each formatted "
    "<file>:<line-or-symbol> | <severity: nit/warn/bug> | <one-line issue>. "
    "Do not restate the code. If there are no real issues, reply exactly: LGTM. "
    "Be concise."
)

# Deep-research setup: per-category rubric + anti-FP + inline 2-shot + JSON.
STRUCTURED_SYSTEM = (
    "You are a precise code reviewer. Review ONLY the added/changed lines (`+`) in "
    "the unified diff. For each category below, decide whether the CHANGED code has "
    "a real, concrete defect:\n"
    "  - correctness: wrong logic, off-by-one, wrong operator/return\n"
    "  - error_handling: unhandled exception/error path that can realistically fire\n"
    "  - resource: leaked file/socket/lock, missing close/cleanup\n"
    "  - security: injection, unsafe eval/exec, secret exposure\n"
    "  - edge_cases: missing null/empty/bounds/zero guard that the code needs\n\n"
    "RULES:\n"
    "1. Flag a category ONLY if the defect is genuinely PRESENT in the shown changed "
    "code. If the code already handles it, do NOT flag it. Never suggest adding "
    "something that is already there.\n"
    "2. Judge only what is shown; do not assume missing cross-file context is a bug.\n"
    "3. Be specific: cite the exact symbol and the concrete defect. No restating, no "
    "summaries, no praise, no style nits.\n"
    "4. An empty findings list is the correct answer for solid code.\n\n"
    "Output JSON ONLY, exactly this shape:\n"
    '{"findings": [{"category": "correctness|error_handling|resource|security|edge_cases", '
    '"severity": "nit|warn|bug", "location": "<file>:<symbol>", "issue": "<one sentence>"}]}\n\n'
    "Examples:\n"
    "Changed code `def div(a, b): return a / b`  ->  "
    '{"findings": [{"category": "edge_cases", "severity": "bug", "location": "x.py:div", '
    '"issue": "no guard for b == 0; raises ZeroDivisionError"}]}\n'
    "Changed code `def add(a: int, b: int) -> int: return a + b`  ->  "
    '{"findings": []}'
)

JSON_FORMAT = {"type": "json_object"}

# Per-category ("pointwise") checks — the research found scoring one defect class
# at a time is measurably LESS lenient than one combined rubric pass, which is the
# recall lever. Each is a focused, anti-FP call; findings are aggregated.
CATEGORY_CHECKS = {
    "correctness": (
        "wrong logic, off-by-one, inverted condition, wrong operator, wrong return value",
        "`return a - b` where addition was intended, or `if x = 5:`",
    ),
    "error_handling": (
        "an error/exception path that can realistically fire and is NOT handled "
        "(file I/O, parsing, network, a missing dict key)",
        "`json.loads(open(p).read())` with no try/except for a missing file or bad JSON",
    ),
    "resource": (
        "a leaked file/socket/lock/handle, or missing close/cleanup/context-manager",
        "`open(p).read()` without closing the handle or using `with`",
    ),
    "security": (
        "injection, unsafe eval/exec/shell, secret exposure, or unvalidated input used in a sink",
        "`os.system('rm ' + user_input)`",
    ),
    "edge_cases": (
        "a missing guard for null/empty/zero/negative/bounds that the code actually needs",
        "`def div(a, b): return a / b` with no guard for `b == 0`",
    ),
}


# --- diff harvesting --------------------------------------------------------


def _git(args: list[str]) -> str:
    return subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args], capture_output=True, text=True, check=False
    ).stdout


def _code_only(diff: str) -> str:
    """Keep only the per-file sections whose path has a code extension.

    Docs/YAML/markdown diffs made both models ramble into prose summaries, and
    they are out of scope for a code reviewer.
    """
    sections = re.split(r"(?=^diff --git )", diff, flags=re.M)
    kept: list[str] = []
    for sec in sections:
        if not sec.strip():
            continue
        m = re.search(r"^\+\+\+ b/(.+)$", sec, flags=re.M) or re.search(
            r"^diff --git a/\S+ b/(\S+)", sec, flags=re.M
        )
        path = m.group(1).strip() if m else ""
        if os.path.splitext(path)[1].lower() in CODE_EXTS:
            kept.append(sec)
    return "".join(kept)


def _merge_diffs(
    base: str, count: int, max_lines: int, context_lines: int, code_only: bool
) -> list[tuple[str, str, str]]:
    log = _git(["log", "--merges", "--first-parent", base, f"-n{count}", "--format=%H\t%s"])
    out: list[tuple[str, str, str]] = []
    for line in log.splitlines():
        if "\t" not in line:
            continue
        sha, subject = line.split("\t", 1)
        diff = _git(["diff", f"-U{context_lines}", "--no-color", f"{sha}^1", sha])
        if code_only:
            diff = _code_only(diff)
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
        model=args.model or getattr(settings, "llm_model", "qwen2.5-coder-reviewer"),
        api_key=args.api_key or getattr(settings, "llm_api_key", ""),
        timeout=args.timeout,
    )


def _run_structured(provider, diff, max_tokens):
    r = provider.generate(
        system=STRUCTURED_SYSTEM,
        prompt="Unified diff:\n\n" + diff,
        max_tokens=max_tokens,
        response_format=JSON_FORMAT,
    )
    findings, parse_ok = [], True
    try:
        data = json.loads(r.text)
        findings = data.get("findings", []) if isinstance(data, dict) else []
    except (json.JSONDecodeError, AttributeError):
        parse_ok = False
    return r, findings, parse_ok


def _run_per_category(provider, diff, max_tokens):
    """One focused, anti-FP JSON pass per defect class; aggregate the findings.

    Trades ~5x latency for recall (each pass is 'pointwise' and less lenient).
    """
    all_findings: list = []
    parse_fail = False
    last = None
    for cat, (guidance, example) in CATEGORY_CHECKS.items():
        system = (
            f"You are checking a code diff for ONE defect class: {cat} — {guidance}. "
            "Review ONLY the added/changed (`+`) lines. Flag a defect ONLY if it is "
            "genuinely PRESENT in the shown changed code; if the code already handles "
            "it, do NOT flag it. Ignore every other defect class. "
            'Output JSON ONLY: {"findings": [{"severity": "nit|warn|bug", '
            '"location": "<file>:<symbol>", "issue": "<one sentence>"}]}. Empty list if none.\n'
            f"Example of a {cat} defect: {example}"
        )
        r = provider.generate(
            system=system,
            prompt="Unified diff:\n\n" + diff,
            max_tokens=max_tokens,
            response_format=JSON_FORMAT,
        )
        last = r
        try:
            data = json.loads(r.text)
            fs = data.get("findings", []) if isinstance(data, dict) else []
        except (json.JSONDecodeError, AttributeError):
            fs, parse_fail = [], True
        for f in fs:
            if isinstance(f, dict):
                f.setdefault("category", cat)
            all_findings.append(f)
    return last, all_findings, not parse_fail


def _fmt_finding(f: dict) -> str:
    return (
        f"[{f.get('severity', '?')}] {f.get('category', '?')} "
        f"{f.get('location', '?')} — {f.get('issue', '')}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local-LLM reviewer eval spike.")
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--base", default="main")
    parser.add_argument(
        "--mode", choices=["structured", "per-category", "plain"], default="structured"
    )
    parser.add_argument("--context-lines", type=int, default=12)
    parser.add_argument("--code-only", action="store_true", default=True)
    parser.add_argument("--all-files", dest="code_only", action="store_false")
    parser.add_argument("--max-diff-lines", type=int, default=600)
    parser.add_argument("--max-tokens", type=int, default=512)
    parser.add_argument("--timeout", type=float, default=190.0)
    parser.add_argument("--model", default=None)
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--api-key", default=None)
    parser.add_argument(
        "--out", type=Path, default=REPO_ROOT / ".archetype" / "eval" / "review_spike.jsonl"
    )
    args = parser.parse_args(argv)

    cases = _merge_diffs(
        args.base, args.count, args.max_diff_lines, args.context_lines, args.code_only
    )
    if not cases:
        print(f"No {'code ' if args.code_only else ''}diffs found on {args.base!r}.")
        return 0

    provider = _provider(args)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    print(f"Reviewer[{args.mode}]: {provider.model} @ {provider.base_url} "
          f"(ctx-lines={args.context_lines}, code_only={args.code_only}) — {len(cases)} diff(s)\n")

    latencies: list[float] = []
    errors = parse_fails = total_findings = 0
    with args.out.open("a", encoding="utf-8") as sink:
        for sha, subject, diff in cases:
            t0 = time.time()
            findings: list = []
            parse_ok = True
            try:
                if args.mode == "structured":
                    result, findings, parse_ok = _run_structured(provider, diff, args.max_tokens)
                    text = "" if parse_ok else result.text.strip()
                elif args.mode == "per-category":
                    result, findings, parse_ok = _run_per_category(provider, diff, args.max_tokens)
                    text = "" if parse_ok else result.text.strip()
                else:
                    result = provider.generate(
                        system=PLAIN_SYSTEM, prompt="Diff:\n\n" + diff, max_tokens=args.max_tokens
                    )
                    text = result.text.strip()
                dt = time.time() - t0
                latencies.append(dt)
                finish, err = result.finish_reason, None
                if not parse_ok:
                    parse_fails += 1
                total_findings += len(findings)
            except Exception as exc:  # noqa: BLE001 — a harness reports, never crashes
                dt, text, findings, finish, err = time.time() - t0, "", [], "error", str(exc)
                errors += 1

            print(f"── {sha}  {subject[:66]}")
            note = "" if err is None else f" | ERROR: {err}"
            note += "" if parse_ok else " | JSON-PARSE-FAIL"
            print(f"   {dt:.1f}s | finish={finish} | in={len(diff)}c | findings={len(findings)}{note}")
            for f in findings:
                print("     " + (_fmt_finding(f) if isinstance(f, dict) else str(f)))
            if args.mode == "plain" and text:
                for ln in text.splitlines():
                    print(f"     {ln}")
            print()
            sink.write(json.dumps({
                "sha": sha, "subject": subject, "mode": args.mode, "latency_s": round(dt, 2),
                "finish": finish, "in_chars": len(diff), "n_findings": len(findings),
                "findings": findings, "raw": text, "model": provider.model,
                "parse_ok": parse_ok, "error": err,
            }) + "\n")

    if latencies:
        latencies.sort()
        mean = sum(latencies) / len(latencies)
        print(f"Summary[{args.mode}]: {len(cases)} diffs, {errors} error(s), "
              f"{parse_fails} JSON-parse-fail, {total_findings} findings total. "
              f"latency mean {mean:.1f}s / median {latencies[len(latencies)//2]:.1f}s / "
              f"max {latencies[-1]:.1f}s.")
        print(f"Log appended: {args.out}")
    return 1 if errors and not latencies else 0


if __name__ == "__main__":
    sys.exit(main())
