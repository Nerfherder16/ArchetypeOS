# Handoff

## Purpose

This file records the latest durable handoff for ArchetypeOS work.

Every engineering session should end by updating this file or creating a dated handoff artifact.

## Latest Handoff

### Date

2026-07-06

### Agent

Runtime Agent (Opus) under Orchestrator (Opus 4.8)

### Task

First real Agent Council run over external code + provider parse hardening (AOS-COUNCIL-PHASEA). (Prior: AOS-PORTFOLIO-001 merged PR #53 / `b64db41` — AOS-21 Done, 5-repo reality test; AOS-KNOW-003 PR #52 / AOS-23; AOS-KNOW-002 PR #51; AOS-APIROUTES-001 PR #50 / AOS-24; AOS-COUNCIL-001 PR #49 / AOS-19.)

### Branch

`claude/aos-runtime-002-scanner-1egyjw` (restarted from `main` at `894e418` after the PR #54 merge; env-pinned — see branch note above)

### PR

#54 — **Merged** as `894e418` (merge commit). CI run 28764871261 all 6 jobs green on head `225f8b4`.

### Status

Merged — the **first real Agent Council run over external code** validated Intelligence Phase 1. Run over `pydantic/pydantic-ai` with the live `claude_code` provider (4 agents, real Claude reasoning, 132 s), the RFC-0005 Council returned a **constitution-faithful abstention** (`Insufficient evidence`, conf 0.0375): it refused to manufacture an adoption verdict it could not support and named the exact evidence it needed. The reality test surfaced two honest findings — **LES-018** (live-model JSON is Markdown-fenced; the tolerant parser now strips it — **fixed**, validated against the captured raw run) and **LES-019** (a structural scan is the wrong evidence class for an *adoption* question — **recorded, open**; the design input for Phase C). Branch restarted from `main` at `894e418`. **Next: operator picks the next build — recommended Phase C (the decision loop), which LES-019 directly motivates.**

### Note — GitHub connector expired mid-session

The GitHub MCP OAuth token expired during PR #53 (long session). git push/CI were unaffected (separate proxy auth); only PR comments/reads were blocked. Operator re-authorized; the gate was posted late. If it recurs: reconnect GitHub via `/mcp` or claude.ai connector settings — git operations keep working regardless.

### Orchestrator Transition

- Outgoing: Fable 5 (Sprints 1–4, PRs #1–#41 + this pack). Incoming: Opus 4.8, same session context.
- Boot order for any fresh orchestrator session: `CLAUDE.md` → `docs/CURRENT_STATE.md` → `docs/ACTIVE_WORK.md` → `docs/HANDOFF.md` → `docs/ORCHESTRATOR_PLAYBOOK.md` → `knowledge/wiki/lessons/index.md` → active spec in `.archetype/work/`.
- Non-negotiables that must survive the transition: builder ≠ verifier (Orchestrator independently re-runs everything); never weaken the guardian (it now enforces its own evolution discipline); head-SHA-pinned Manual Merge Gates; markdown state files win over Plane; lessons recorded in the same change set; no scope expansion without RFC.
- **Branch name is env-pinned, not stale-by-neglect:** `claude/aos-runtime-002-scanner-1egyjw` is fixed by the session config; each package restarts it from `main` (one PR = one package, clean history). A per-package scheme (`opus/aos-<pkg>`) is adopted only if the operator reconfigures the env / grants explicit permission. See the Role-contract note in `docs/ORCHESTRATOR_PLAYBOOK.md` (Lead-Architect critique 2026-07-05, operator Decision 2a).
- Escalate back to the operator (or a Fable session) for: RFC-grade architecture decisions, sprint planning at inflection points, alpha-style self-evaluations.

### Completed

- **First real Agent Council run over external code.** `run_council(db, project_id, question, provider=ClaudeCodeProvider(timeout=180))` over `pydantic/pydantic-ai` — 4 agents, live Claude reasoning, 132 s. Constitution-faithful **abstention** (`Insufficient evidence`, conf 0.0375). Captured to `.archetype/council/pydantic-ai-review.json`; evaluated in `docs/COUNCIL_REALRUN_PYDANTIC_AI.md`.
- `packages/aos_core/aos_core/services/council.py`: **LES-018 fix** — `_loads_tolerant` (parse as-is → strip a Markdown code fence → slice first `{` … last `}`) + `_strip_code_fence`; `_parse_agent_output` routed through it. Behavior-preserving for bare JSON and true prose; recovers findings/confidence from live-model fenced/prose-wrapped JSON.
- `apps/api/tests/test_council.py`: 4 regression tests (bare / fenced / prose-then-object / true-prose-fallback).
- Lessons: `LES-018.md` (closed — fix + tests same change set) + `LES-019.md` (open — evidence-class mismatch → Phase C input) + `index.md` rows (vault 17→19).
- Docs: `docs/COUNCIL_REALRUN_PYDANTIC_AI.md` (new evaluation), `docs/CAPABILITY_MAP.md` (Council + provider-seam entries), `.archetype/work/AOS-COUNCIL-PHASEA.md` (spec), state files.

### Files changed

- `packages/aos_core/aos_core/services/council.py`, `apps/api/tests/test_council.py`
- `.archetype/council/pydantic-ai-review.json` (captured evidence), `.archetype/work/AOS-COUNCIL-PHASEA.md` (spec)
- `docs/COUNCIL_REALRUN_PYDANTIC_AI.md` (new), `docs/CAPABILITY_MAP.md`
- `knowledge/wiki/lessons/LES-018.md` (new), `LES-019.md` (new), `index.md`
- `docs/ACTIVE_WORK.md`, `docs/CURRENT_STATE.md`, `docs/HANDOFF.md`, `docs/RECENT_CHANGES.md`

### Tests run

- On a 3.12 venv: `PYTHONPATH=apps/api:packages/aos_core pytest apps/api/tests -q` → **106 passed** (+4 new parser tests); `apps/worker/tests` → **7 passed**; `ruff check apps/api packages/aos_core apps/worker tools` clean; `compileall` clean.
- The LES-018 fix was validated against the **captured raw run output** (not only synthetic fixtures): re-parsing the 3 fenced agents recovers architecture_cartographer `0→6` findings / `0→8` concerns, technology_fitness_judge `conf 0.05→0.35`, security_agent `0→4` findings; aggregate still abstains.

### Known Risks

- The live Council run uses the subscription-auth `claude_code` provider — it is captured evidence, not a hermetic CI test. The fix is proven in CI by the parser tests; a live re-run needs an authed node with the `claude` CLI.
- LES-019 (evidence-class mismatch) is recorded, not fixed — adoption questions need a research/decision corpus, not a target-repo scan (Phase C).

### Blockers

- None.

### Verification Status

Verified (PR #54 merged as `894e418`; AOS-COUNCIL-PHASEA Done)

### Verification Level

Level 3

### Verification Method

CI run 28764871261 all 6 jobs green on head `225f8b4`, plus the Orchestrator's independent live Council run over pydantic-ai (4 agents via `claude_code`, 132 s, captured to `.archetype/council/pydantic-ai-review.json`) with the LES-018 fix validated against that captured raw output; `PYTHONPATH=apps/api:packages/aos_core pytest apps/api/tests` → **106 passed**; `apps/worker/tests` → **7 passed**; `ruff check apps/api packages/aos_core apps/worker tools` clean; `compileall` clean. Builder ≠ verifier. Branch restarted from `main` at `894e418`.

### Evidence

- Council abstained correctly (`Insufficient evidence`, conf 0.0375); parse fix recovers 0→6 / 0→4 findings from the 3 fenced agents while the aggregate still abstains (avg ≈ 0.16 < 0.35); api 106 / worker 7 green; ruff full CI scope + compileall clean.

### Limitations

The live Council run is captured evidence, not a hermetic CI test (subscription-auth `claude_code` provider); the fix itself is proven in CI by the parser tests. LES-019 (evidence-class mismatch) is recorded, not fixed — the input for Phase C.

### Required Next Verifier

None — PR #54 merged as `894e418` and reconciled.

### Next Recommended Step

**Phase C — the decision loop (recommended).** PR #54 proved Intelligence Phase 1 on real external code and, via LES-019, showed the highest-signal next move: feed the Council the *right evidence class*. Phase C is Council → gather/record research → **draft decision** → human-approve → knowledge, closing the exact gap the pydantic-ai run exposed (it abstained and named the evidence it needed). Alternatives: **Phase B** — architecture semantics (LES-014 dependency/compose edges; `example-voting-app` ready test) + language weighting (LES-013); the **Council dashboard** (AOS-COUNCIL-002). Scanner backlog also open: LES-016 (manifest/ecosystem coverage), LES-017 (secret-signal precision). Other open: AOS-20 (doc-staleness), AOS-22 (backups). Operator's call.

## Handoff Template

```text
Date:
Agent:
Task:
Branch:
PR:
Status:
Completed:
Files changed:
Tests run:
Docs updated:
Worktree or connector fallback used:
Base ref:
Head SHA:
Backup head, if any:
Freshness check:
Verification Status:
Verification Level:
Verification Method:
Evidence:
Limitations:
Required Next Verifier:
Risks:
Blockers:
Next recommended step:
Required reader context:
```

## Rule

A task is not complete until the handoff is durable and verification metadata is recorded.