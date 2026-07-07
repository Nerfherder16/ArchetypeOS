#!/usr/bin/env python3
"""Headless multi-model Agent Council demo (AOS-LLM-EVAL-001 flagship, RFC-0005).

Runs the REAL council agents — each on a DIFFERENT free frontier model from the
rotation pool — then the deterministic Final Judge synthesis. This is the payoff
of the routed reasoned tier: genuine model diversity (the actual point of a
council, not one model role-played N times) at ~zero cost, with Claude reserved
for Final Judge only.

It is headless (no DB): it feeds the real agent system prompts a sample question
+ a hand-built evidence list, so it demonstrates the mechanism without standing up
a project. Wiring this into the DB-backed `run_council` route (per-agent model
persisted) is the productionization follow-up.

Keys are read from ~/.config/aos/<provider>.key. Public/non-sensitive questions
ONLY — the privacy guardrail forbids private input on the free tier.

    PYTHONPATH=packages/aos_core python tools/council_multimodel.py
"""
from __future__ import annotations

import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "packages" / "aos_core"))

from aos_core.models import CouncilAgentOutput  # noqa: E402
from aos_core.services.council import (  # noqa: E402
    DEFAULT_AGENTS,
    _build_prompt,
    _parse_agent_output,
    synthesize_verdict,
)
from aos_core.services.llm_pool import build_free_pool  # noqa: E402

_KEYFILES = {
    "groq": "GROQ_API_KEY",
    "cerebras": "CEREBRAS_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "mistral": "MISTRAL_API_KEY",
}

SAMPLE_QUESTION = "Should we adopt FastAPI + PostgreSQL + Redis for a new internal service?"

# A plausible shared evidence set (the format the DB evidence_selectors emit). Each
# agent's system prompt focuses it on the relevant slice.
SAMPLE_EVIDENCE = [
    {"kind": "framework", "detail": "FastAPI 0.115 (async, Pydantic v2)", "ref": "dna:1"},
    {"kind": "framework", "detail": "PostgreSQL 16", "ref": "dna:1"},
    {"kind": "framework", "detail": "Redis 7", "ref": "dna:1"},
    {"kind": "language", "detail": "Python 3.12 (92% of the codebase)", "ref": "dna:1"},
    {"kind": "research_note", "detail": "FastAPI is production-proven for async APIs; strong docs and ecosystem", "ref": "note:1"},
    {"kind": "maturity", "detail": "unit tests + CI present; no load testing yet", "ref": "dna:1"},
    {"kind": "risk_flag", "detail": "no rate limiting configured on public endpoints", "ref": "dna:1"},
]


def _load_env() -> dict:
    d = pathlib.Path.home() / ".config" / "aos"
    env = {}
    for name, var in _KEYFILES.items():
        f = d / f"{name}.key"
        if f.exists():
            env[var] = f.read_text().strip()
    return env


def main() -> int:
    pool = build_free_pool(_load_env(), timeout=60)
    if len(pool) < 2:
        print(f"Need >=2 free models for a multi-model council (have {len(pool)}). "
              "Add more keys under ~/.config/aos/.")
        return 1
    print(f"Multi-model Council — {len(pool)} models: {', '.join(n for n, _ in pool)}")
    print(f"Q: {SAMPLE_QUESTION}\n")

    outputs: list[CouncilAgentOutput] = []
    for i, agent in enumerate(DEFAULT_AGENTS):
        member_name, provider = pool[i % len(pool)]
        prompt = _build_prompt(agent, SAMPLE_QUESTION, SAMPLE_EVIDENCE)
        t0 = time.time()
        try:
            result = provider.generate(
                system=agent["system_prompt"], prompt=prompt, max_tokens=2000
            )
            parsed = _parse_agent_output(result.text)
            outputs.append(CouncilAgentOutput(
                agent_name=agent["name"], agent_type=agent["agent_type"],
                status=parsed["status"], summary=parsed["summary"], findings=parsed["findings"],
                evidence=parsed["evidence"], concerns=parsed["concerns"], confidence=parsed["confidence"],
            ))
            print(f"● {agent['name']:26} via {member_name:9} ({result.model[:26]:26}) {time.time()-t0:5.1f}s")
            print(f"    status={parsed['status']} conf={parsed['confidence']} | {parsed['summary'][:120]}")
            if parsed["concerns"]:
                print(f"    concerns: {', '.join(str(c) for c in parsed['concerns'][:2])[:120]}")
        except Exception as exc:  # noqa: BLE001 — one model hiccup shouldn't kill the demo
            print(f"● {agent['name']:26} via {member_name:9}  FAIL: {str(exc)[:90]}")
        print()

    if not outputs:
        print("No agent produced output.")
        return 1

    v = synthesize_verdict(outputs)
    print("── Final Judge (deterministic synthesis) ──")
    print(f"  VERDICT: {v['verdict']}  (confidence {v['confidence']})")
    def _fmt(items):
        return "; ".join(str(x) for x in items[:3])[:220]

    if v["agreements"]:
        print(f"  agreements: {_fmt(v['agreements'])}")
    if v["disagreements"]:
        print(f"  disagreements: {_fmt(v['disagreements'])}")
    if v["follow_up"]:
        print(f"  follow-up: {_fmt(v['follow_up'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
