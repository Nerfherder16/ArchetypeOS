# AOS-COUNCIL-PHASEA — First real Agent Council run (pydantic-ai) + provider parse hardening

## Status

In Progress

## Origin

Operator direction: "confirm phase a" — run the RFC-0005 Agent Council over a real
external repository with the live `claude_code` provider (not the hermetic
`DeterministicProvider`), the way AOS-21 (PR #53) was the reality test for the
scanner. This is the reality test for **Intelligence Phase 1** (AOS-COUNCIL-001,
PR #49, AOS-19): does the Council produce genuine, governed reasoning on real code,
and what gaps does a live provider surface that deterministic tests cannot?

## Reality test already run (Orchestrator, in-session — this IS the evaluation half)

The Orchestrator scanned `pydantic/pydantic-ai` and ran `run_council` with
`ClaudeCodeProvider(timeout=180)` over an adoption question. Real run: 4 agents,
live Claude reasoning, 132 s. Captured evidence: `.archetype/council/pydantic-ai-review.json`;
full write-up: `docs/COUNCIL_REALRUN_PYDANTIC_AI.md`.

- **Positive — the Council works and is constitution-faithful.** Verdict
  `Insufficient evidence` (confidence 0.0375, below the 0.35 abstention floor): the
  Council **refused to manufacture a recommendation** it could not support, and
  emitted precise follow-ups. `research_librarian` cited the Engineering
  Constitution and RFC-0004 by name. Asked "should we adopt X?" with only a
  structural scan of X, the correct answer *is* "not yet — gather this evidence."
- **Gap 1 (→ LES-018): fenced-JSON parse defect.** `claude -p --output-format json`
  wrapped 3 of 4 agents' JSON in a ` ```json ` fence; `_parse_agent_output` called
  `json.loads` directly and degraded them to the prose fallback (conf 0.05, empty
  findings/concerns). Verified against the captured raw output. **Fixed in this
  change set** (only a real provider run could surface it — the deterministic
  provider never emits a fence).
- **Gap 2 (→ LES-019): evidence-class mismatch.** A structural scan of the *target*
  repo is the wrong evidence class for an *adoption* question. The Council correctly
  abstained; the fix is upstream (feed a research/decision corpus). Scoped design
  input for the Phase C decision loop, not fixed here.

## This package's scope

Two deliverables: (1) **harden the provider parse seam** so live-model JSON
formatting (Markdown fences, prose preambles) no longer silently degrades agent
output — the one code fix the reality test earned; and (2) the **evaluation artifact
+ honest lessons** from the first real run. It does NOT build the decision loop
(Phase C) or the Council dashboard (AOS-COUNCIL-002) — those stay scoped follow-ups.

## Verified Baseline

- `_parse_agent_output` (single funnel both providers flow through) called
  `json.loads(text)` directly; on any non-JSON it returned the prose fallback
  (`confidence=0.05`, empty lists, raw text in `summary`).
- `ClaudeCodeProvider._extract_claude_text` already pulls `.result` from the CLI
  envelope; the fence is *inside* `.result` (the model's own formatting), so the fix
  belongs in the shared parser, not the provider.
- Council synthesis (`synthesize_verdict`) consumes findings/concerns/confidence;
  with the defect those were empty for 3 agents, so agreement/disagreement/
  unsupported-claim detection ran on degraded inputs (verdict still correct because
  agents self-reported "Needs Evidence").

## In-Scope Files

- `packages/aos_core/aos_core/services/council.py`: add `_loads_tolerant(text)`
  (layered recovery — parse as-is → strip a leading/trailing Markdown fence →
  slice first `{` … last `}`) + `_strip_code_fence`; route `_parse_agent_output`
  through it. Behavior-preserving for bare JSON and true prose.
- `apps/api/tests/test_council.py`: 4 `_parse_agent_output` regression tests
  (bare / fenced / prose-then-object / true-prose-fallback).
- `.archetype/council/pydantic-ai-review.json` (captured evidence — the real run).
- `docs/COUNCIL_REALRUN_PYDANTIC_AI.md` (new): the evaluation write-up.
- `knowledge/wiki/lessons/LES-018.md` (closed) + `LES-019.md` (open) + `index.md` rows.
- `docs/CAPABILITY_MAP.md` (new-doc rule), state docs + this spec.

## Out-of-Scope

- The Phase C decision loop (Council → research → draft decision → human-approve → knowledge) — LES-019 is its input, not built here.
- The Council dashboard (AOS-COUNCIL-002).
- Re-running the full live Council (132 s, subscription cost) — a hermetic fenced-payload test proves the fix; a second live run would still abstain and change nothing.
- Evidence-selector redesign (LES-019) and scanner gaps (LES-013/014/016/017).

## Acceptance Criteria

- `_parse_agent_output` recovers findings/confidence from a Markdown-fenced JSON payload (regression test) and from a prose-wrapped JSON object; bare JSON and true prose are unchanged.
- The captured real run is committed as evidence with an honest evaluation doc; both lessons (LES-018 closed, LES-019 open) are recorded in the same change set and surface in the digest/Knowledge dashboard.
- api + worker tests green on the CI-scope venv; ruff full CI scope + compileall clean; guardian PASS/PASS_WITH_WARNINGS.

## Verification

Orchestrator re-runs everything independently (builder ≠ verifier): fenced/prose
parse recovery demonstrated against the **captured raw run output** (not just a
synthetic fixture), full api+worker pytest, ruff full CI scope, compileall, guardian.
