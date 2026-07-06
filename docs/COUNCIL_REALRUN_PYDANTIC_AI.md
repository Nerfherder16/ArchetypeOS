# Council Reality Test — First Real Agent Council Run (pydantic-ai)

## Purpose

Records the **first real Agent Council run over external code**: the RFC-0005
Council executed with the live `claude_code` provider (real Claude reasoning, not
the hermetic `DeterministicProvider`) over a question about `pydantic/pydantic-ai`.
This is the reality test for Intelligence Phase 1 — the analogue of the AOS-21
scanner portfolio test, applied to the Council.

## Run

- **Provider:** `claude_code` (`claude -p … --output-format json`, subscription auth)
- **Agents:** 4 (research_librarian, architecture_cartographer, technology_fitness_judge, security_agent) + rule-based Final Judge
- **Wall time:** 132 s (4 sequential live calls)
- **Question (adoption):** "Should ArchetypeOS adopt pydantic-ai as the foundation for its Agent Council's LLM provider abstraction and structured-output layer? Assess production-readiness, architecture fit, technology fitness, and security from the available evidence."
- **Evidence supplied to the agents:** the latest structural scan of `pydantic-ai` (via `run_scan`) surfaced through the per-agent evidence selectors.
- **Captured evidence:** `.archetype/council/pydantic-ai-review.json`

## Result — correct abstention

- **Verdict:** `Insufficient evidence` — **confidence 0.0375**, below the documented `ABSTAIN_CONFIDENCE` floor (0.35).
- The Council **refused to manufacture a recommendation** it could not support and emitted precise follow-ups (gather research notes / a technology-fitness comparison / a security review for pydantic-ai; re-run once evidence clears the floor).
- `research_librarian` cited the Engineering Constitution by name ("Research before implementation; Evidence over opinion") and RFC-0004.

**This is the Intelligence Layer working as designed.** Asked "should we adopt X?"
with only a structural scan of X in hand, the correct answer is *not yet — here is
the evidence to gather first*, and that is what it produced.

## Two gaps surfaced (the reality test doing its job)

### 1. Fenced-JSON parse defect — fixed in this change set (LES-018)

`claude -p --output-format json` returns the model's text in `.result`, and for
**3 of the 4 agents** that text was wrapped in a ` ```json … ``` ` Markdown fence.
`_parse_agent_output` called `json.loads` directly, so those three degraded to the
prose fallback (`confidence=0.05`, empty `findings`/`concerns`). Re-parsing the
captured raw output with the fix recovers the real content (architecture_cartographer
`0→6` findings / `0→8` concerns; technology_fitness_judge `conf 0.05→0.35`). The
aggregate still abstains (avg ≈ 0.16), so the verdict was unaffected — but the
synthesis had been running on empty inputs. Fixed via `_loads_tolerant`
(fence + prose + brace-slice recovery) with a fenced-payload regression test. The
`DeterministicProvider` never emits a fence, so only a real run could surface this.

### 2. Evidence-class mismatch — design input for Phase C (LES-019)

A structural scan of the *target* repo is the wrong evidence class for an *adoption*
question. The Council recognized this and abstained. The fix is upstream: an
adoption question needs a research/decision corpus (fitness comparison, production
notes, security review), not a target-repo scan. The Council's `follow_up` is
itself the specification for what the **Phase C decision loop** must assemble.

## Assessment

Intelligence Phase 1 is validated end to end on real external code: four agents
produced genuine, persona-appropriate reasoning through the live provider, and the
rule-based Final Judge synthesized a **governed, constitution-faithful abstention**.
The run hardened the provider seam (LES-018) and produced a concrete design input
for the decision loop (LES-019). No verdict was manufactured; every gap is recorded
and loop-visible.
