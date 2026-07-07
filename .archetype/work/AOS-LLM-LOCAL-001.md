# AOS-LLM-LOCAL-001 — Local / free LLM provider (OpenAI-compatible)

- Status: In Review
- Owner: laptop session (parallel Orchestrator)
- Branch: `laptop/aos-llm-local` (fresh, from `origin/main`)
- Motivated by: the operator running low on Claude subscription tokens — move
  ArchetypeOS's reasoned tiers onto a local model (teevee's RTX 3070) and/or a
  free hosted API from the `free-llm-api-resources` catalog.

## Design

A third backend on the existing `llm_provider` seam
(`packages/aos_core/aos_core/llm/__init__.py`), whose docstring already
anticipated it ("Ollama / vLLM on the GPU node; a hosted fallback").

**`OpenAICompatibleProvider`** — one config-driven adapter for **any**
OpenAI-compatible `/chat/completions` endpoint, covering both:
- a **local** model on the node (Ollama/vLLM/LM Studio — teevee's 3070 at
  `http://localhost:11434/v1`), and
- a **free hosted API** (Groq/Cerebras/OpenRouter from the catalog),

with the same code — only `LLM_BASE_URL` / `LLM_MODEL` / `LLM_API_KEY` differ.
Stdlib `urllib` only (no new dependency; CI stays hermetic). Selected via
`llm_provider=openai_compatible`; callers (distillation, council) are unchanged
(`get_provider(get_settings())`).

Config fields added to `Settings`: `llm_base_url`, `llm_model`, `llm_api_key`
(the key is read from the env, never committed).

## Contract compliance (deterministic-floor-plus-real-tier)

- The **deterministic** provider remains the default — CI never selects this
  backend, so the suite stays offline/hermetic.
- Isolation (LES-021) is inherent: an HTTP provider transmits only `system` +
  `prompt` — there is no working directory or ambient `CLAUDE.md` to absorb.
- `is_real_provider` (`name != "deterministic"`) treats it as a real provider, so
  distillation stamps `validation_state="reasoned"` when it is used.

## In-Scope Files
- `packages/aos_core/aos_core/llm/__init__.py` (new provider + `get_provider`
  branch)
- `packages/aos_core/aos_core/config.py` (`llm_base_url` / `llm_model` /
  `llm_api_key`)
- `apps/api/tests/test_council.py` (6 new hermetic tests — LES-020: core change
  ships its test)
- `.env.example` + `docs/runbooks/llm-provider.md` (local + free-API profiles)
- `docs/CAPABILITY_MAP.md` · `docs/ACTIVE_WORK.md` + `docs/RECENT_CHANGES.md`

## Out-of-Scope
- Per-use-site provider routing UI (config/env selects the backend for now).
- Pulling a model onto teevee's Ollama (operator infra step; runbook documents
  `ollama pull qwen2.5-coder:7b`).
- Pointing the nightly routines / a research agent at this provider (a follow-up
  now unblocked by the seam).

## Acceptance Criteria
1. `openai_compatible` selectable via `get_provider`; unit tests pass (6 new,
   hermetic — request shape, bearer-when-keyed, no-auth-when-local, HTTP-error,
   missing-content). — evidence: pytest.
2. No new dependency (stdlib `urllib`); ruff clean; full council suite green (no
   regressions). — evidence: pytest + ruff.
3. Live smoke: a real `generate()` against the homelab Ollama returns text. —
   evidence: `TEXT: 'ready'`, finish `stop`, model `qwen3:14b`.
4. Guardian PASS / PASS_WITH_WARNINGS.

## Verification Plan
- Level 2: TDD (RED→GREEN) 6 hermetic tests + ruff + full council suite.
- Level 3 (live): `generate()` against `http://100.70.195.84:11434/v1`
  (qwen3:14b) returned `'ready'` — the teevee-local path is identical code, a
  different `base_url`.

## Board Linkage
- Plane: AOS-47 (In Progress → Done on merge). Unblocks running reasoned tiers +
  future nightly/research agents off Claude.
