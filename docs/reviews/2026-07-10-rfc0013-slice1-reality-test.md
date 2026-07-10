# RFC-0013 Slice 1 — capability-extraction reality test (2026-07-10)

Real-provider 5-repo portfolio run, the Slice-1 quality gate. Reasoned tier via the
free 4-provider rotation pool (Groq/Cerebras/Gemini/Mistral, keys from Infisical
Homelab/prod). Scratch sqlite + `/tmp` knowledge root; portfolio shallow-cloned from
`Nerfherder16/{Recall,ArchetypeOS,AiGentOS,insta-ntly,tali-api}`.

## Verdict: MIXED — does not pass as-is. Extraction mechanism is sound; **source
selection is the bottleneck** and there is real provider-to-provider variance.

## Per-repo result (rendered `## Reusable capabilities`)

| Repo | Capabilities | Quality |
|------|-------------|---------|
| **AiGentOS** | Approval Queue, Action Handler/execution engine, Autonomy runtime, Immutable Audit Ledger, Identity & Access Management (each tied to real files) | **Excellent — PASS.** Named the crown jewels; no hallucination. |
| **insta-ntly** | FastAPI app factory, router registration, auth middleware, health-check, dir provisioning | Weak — generic app-shell boilerplate (repo has no README; thin input). |
| **ArchetypeOS** | (empty in the 5-repo run; "Project/Knowledge management" from `main.py` in an isolated re-run) | **FAIL vs the gate.** Never surfaced "LLM provider-routing / tier abstraction". |
| **Recall** | (empty) | FAIL — no capabilities. |
| **tali-api** | (empty) | FAIL — empty despite good files selected (provider variance). |

## Discriminator (hallucination trap): PASS
AiGentOS capabilities are approval/action/autonomy/audit/auth — **zero** LLM-SOP
claims. The extractor did not fabricate LLM usage from context. tali-api (which *does*
use LLMs) had its LLM use captured in the reasoned **purpose** ("using configurable
LLM…"), just not as a capability (empty this run).

## Root causes (two, distinct)

### 1. `select_source_files` is the dominant failure — structural, deterministic
It is `__init__.py`/entry-point-biased and capped at 10 files, so for large/polyglot
repos it starves the extractor of the actual reusable modules. Observed selections:

- **ArchetypeOS (10):** `apps/api/app/main.py`, several `__init__.py`, `apps/web/src/main.tsx`,
  `apps/scheduler/app/main.py`, `packages/aos_core/aos_core/__init__.py` — **and two test
  fixtures** (`apps/api/tests/fixtures/code-repo/app.py`, `…/compose-repo/app.py`).
  It never selected `services/llm_router.py`, `council.py`, `distillation.py`, etc. — so
  "LLM provider-routing" is unnameable.
- **Recall (10):** `dashboard/src/main.tsx`, `mcp-server/index.js`, `monitor/*`, `sdk/*`
  `__init__.py` — peripheral monitor/loadtest/SDK markers, not the core memory pipeline.
- **AiGentOS worked by luck of structure:** its value lives in flat domain packages
  (`aigentos/approvals/__init__.py`, `…/actions/__init__.py`, …) whose `__init__.py`
  re-export the domain API — exactly what the selector picks.

Concrete defects to fix (highest leverage in the whole slice):
- Exclude `tests/`, `fixtures/`, and near-empty `__init__.py` markers from selection.
- Prefer implementation modules by signal (size/symbol-density/docstrings), not just
  entry-point filename patterns.
- Raise / rebalance the 10-file cap for multi-app monorepos, or select per top-level
  package so `packages/aos_core/aos_core/services/*` is reachable.

### 2. Provider variance — non-deterministic
Even with good files selected, the rotating pool sometimes returns payloads that yield
0 capabilities (empty/prose/shape that coerces to `[]`). Same ArchetypeOS input gave 5
generic caps on one call and 0 on another; tali-api had real files selected yet 0 caps.
The pool rebuilds per call starting at Groq and falls through on 429, so which member
serves a given call — and thus formatting/quality — varies within a run. The parser is
NOT the problem: it correctly handled ```json fences (ArchetypeOS parsed built_for/
how_it_works/capabilities/provenance cleanly when a cooperative member answered).

## What this says about the Slice-1 code (PR #183)
The extraction contract + tolerant parse + render are correct and hold up (AiGentOS is
proof). The mechanism is not what's failing. But the end-to-end *quality bar* — "does a
different project get a useful, accurate capability list for every repo" — is not met,
and the fix is upstream in `select_source_files`, plus a reliability decision on the
free pool (order by capacity / retry-on-empty).

## Iteration log — `select_source_files` heuristics (3 attempts, gate still red)

| Attempt | Change | Reality-gate result |
|---|---|---|
| 1 (original) | entry-points-first, then modules by size, cap 10 | ArchetypeOS starved (markers+fixtures fill slots); AiGentOS good by luck |
| 2 | + exclude tests/fixtures, drop empty markers (min-size), package round-robin **ordered by largest-member** | AiGentOS **regressed** (lost approval/action; picked a `.sh`; hallucinated "LLM routing"); ArchetypeOS worse (huge `tools/pr_guardian.py` ate the byte budget) |
| 3 | + exclude `scripts`/`tools`/`docs`; rank **within** package by size, order groups **by name** (fair round-robin) | AiGentOS domain caps back **but hallucinates SOP/LLM/Research from `main.py` imports**; ArchetypeOS **still** misses `llm_router` (Alembic migration `0001_baseline.py` ate the budget); **3/5 repos returned empty caps** (provider variance) |

Unit tests (hermetic) pass for all three; the **reality gate does not**. Execution
verification, not the test suite, is the truth here.

## Two confirmed hard problems (neither is the extraction code)

1. **File-selection is the wrong abstraction.** No size/path/diversity heuristic reliably
   surfaces the one crown-jewel module (`services/llm_router.py`) while excluding noise
   (migrations, `vite.config`, tooling, huge generated files) across heterogeneous repo
   shapes. Worse, feeding the model ~5 *full* files makes it **infer capabilities from
   import names** in an entry file it happens to see (the AiGentOS SOP/LLM/Research
   hallucination) — the opposite of grounded.
2. **Provider variance dominates reliability.** 3/5 repos returned empty capabilities in
   attempt 3 despite good files selected. The free rotation pool frequently yields
   empty/unparseable output; a per-repo feature that silently produces nothing half the
   time is not shippable regardless of selection.

## Revised recommendation — pivot the design (advisor consult)

Stop tuning `select_source_files`; the ceiling is the "pick 5 full files" architecture.
Proposed direction (for advisor review — they hold the context on prompt-tightening):

- **Feed a whole-repo structural digest, not a handful of full files.** `summarize_sources`
  already computes, deterministically and cheaply, every file's top-level symbols +
  docstring/leading-comment. Give the model that **map of the entire repo** (path → role,
  symbols, one-line doc) plus a *few* full high-signal modules — so it reasons over the
  real shape of the codebase and cites modules that actually exist, instead of inferring
  from 5 sampled files. This directly attacks both the selection problem (no need to guess
  the 5 right files) and the hallucination (module/symbol names are given, not inferred).
- **Make the reasoned call reliable:** retry-on-empty within a call and/or order the pool
  by context capacity (the shakedown's suggestion), so "empty capabilities" reflects a
  genuinely capability-less repo, not a flaky provider.
- The uncontroversial wins from attempts 2–3 (exclude tests/fixtures/tooling, drop empty
  markers) are worth keeping in whatever selection remains, but they are **not sufficient**.

Kept the attempt-3 code in the worktree (unit-green) but **not** committed as a fix — it
does not pass this gate, and the pivot above should be agreed with the advisor first.

## Pivot implemented (advisor-greenlit) — results

Shipped on the branch (held from merge): `build_repo_digest` (whole-repo symbol map +
few full modules), digest-based `reason_over_source`, deterministic
`_drop_uncited_capabilities` cite-must-exist filter, retry-on-empty across pool members
+ `extraction_incomplete` marking, and a `max_tokens=2048` bump for the capability call
(the free-tier default was truncating the JSON array mid-stream — the single biggest
reliability fix). Hermetic suite 449 green; ruff clean.

Reality gate (free pool), latest run:

| Repo | Result |
|---|---|
| Recall | **16 grounded capabilities** (LLM/Ollama abstraction, embedding service, temporal knowledge-graph, contradiction detection, memory write guard, …) |
| insta-ntly | **22 grounded capabilities** (Canva OAuth2+PKCE, Supabase Auth, AI provider abstraction, carousel pipeline, …) |
| AiGentOS / ArchetypeOS / tali-api | `extraction_incomplete` (provider variance — a member truncated/empty on the larger prompt; honestly marked, nothing fabricated) |

**Validated:** the digest + cite-must-exist mechanism produces rich, grounded,
hallucination-free capabilities (the two successes are dense and accurate; the cite-filter
structurally removed ungrounded items). **Remaining:** free-provider variance still yields
~3/5 `extraction_incomplete` per run (which repos vary run-to-run). The mechanism is right;
reliability is the last gap.

## Next lever (for the gate to go fully green) — provider reliability

- Order the free pool by context capacity (Gemini/Cerebras big-context members first) so
  the larger digest prompt lands on members that handle it — the advisor's scoped secondary
  lever; touches `llm_pool`, so worth agreeing the approach first.
- Try all pool members on empty (raise the retry bound to the pool size).
- When Claude tiering is enabled, escalate-on-empty via the verifier is the clean upgrade.

Slice 1 is **not** merged until the gate is reliably green on the acceptance repos
(ArchetypeOS → "LLM provider-routing", AiGentOS → "approval queue").
