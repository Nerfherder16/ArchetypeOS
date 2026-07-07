"""Local-LLM code reviewer (AOS-LLM-REVIEW-001) — the Tier-1 reasoned reviewer.

Advisory findings on a unified diff, layered ON TOP of the deterministic PR
Guardian (never a replacement). Design, validated by the AOS-LLM-LOCAL-001 eval:

- **Per-category ("pointwise") passes** — one focused JSON pass per defect class.
  The research + our eval found this measurably less lenient than one combined
  pass (recall tripled on a planted-bug diff) while holding precision.
- **Anti-false-positive** instruction + **JSON output** — precision (near-zero FP
  on real merged PRs) and no prose rambling.
- **Code-only file filter** — docs/YAML are out of scope for a code reviewer.
- **Fail-open** — any provider/parse error yields fewer/no findings and NEVER
  raises to the caller. This is advisory; it must never block a merge.

Runs on the configured local model (teevee's 3070 via the OpenAICompatibleProvider
+ the `qwen2.5-coder-reviewer` Modelfile). Deterministic-safe: given a provider
whose output is empty/unparseable, it simply returns no findings.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

CODE_EXTS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".sh", ".java", ".rb",
    ".c", ".h", ".cpp", ".cs", ".kt", ".sql", ".php",
}

# One focused check per defect class. Pointwise scoring is the recall lever.
CATEGORY_CHECKS: dict[str, tuple[str, str]] = {
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

_JSON_FORMAT = {"type": "json_object"}


@dataclass
class ReviewFinding:
    category: str
    severity: str
    location: str
    issue: str

    def as_line(self) -> str:
        return f"[{self.severity}] {self.category} {self.location} — {self.issue}"


def filter_code_files(diff: str) -> str:
    """Keep only the per-file sections whose path has a code extension."""
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


def _category_system(category: str, guidance: str, example: str) -> str:
    return (
        f"You are checking a code diff for ONE defect class: {category} — {guidance}. "
        "Review ONLY the added/changed (`+`) lines. Flag a defect ONLY if it is "
        "genuinely PRESENT in the shown changed code; if the code already handles it, "
        "do NOT flag it. Ignore every other defect class. "
        'Output JSON ONLY: {"findings": [{"severity": "nit|warn|bug", '
        '"location": "<file>:<symbol>", "issue": "<one sentence>"}]}. Empty list if none.\n'
        f"Example of a {category} defect: {example}"
    )


def _parse_findings(text: str, category: str) -> list[ReviewFinding]:
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return []
    raw = data.get("findings", []) if isinstance(data, dict) else []
    out: list[ReviewFinding] = []
    for f in raw if isinstance(raw, list) else []:
        if not isinstance(f, dict):
            continue
        out.append(
            ReviewFinding(
                category=str(f.get("category", category)),
                severity=str(f.get("severity", "nit")),
                location=str(f.get("location", "")),
                issue=str(f.get("issue", "")),
            )
        )
    return out


def review_diff(provider, diff: str, *, max_tokens: int = 512, code_only: bool = True) -> list[ReviewFinding]:
    """Run the per-category reviewer over a unified diff. Fail-open, never raises.

    ``provider`` is any object with ``generate(*, system, prompt, max_tokens,
    response_format=...) -> result`` whose ``.text`` is the model output.
    """
    subject = filter_code_files(diff) if code_only else diff
    if not subject.strip():
        return []

    findings: list[ReviewFinding] = []
    for category, (guidance, example) in CATEGORY_CHECKS.items():
        try:
            result = provider.generate(
                system=_category_system(category, guidance, example),
                prompt="Unified diff:\n\n" + subject,
                max_tokens=max_tokens,
                response_format=_JSON_FORMAT,
            )
        except Exception:  # noqa: BLE001 — advisory: a failed pass yields no findings
            continue
        findings.extend(_parse_findings(getattr(result, "text", ""), category))
    return findings
