# AOS-DISTILL-004 — Distillation reasoned tier: a real-provider `DNA.purpose` (the quality tier)

## Status

Queued (fires after AOS-DISTILL-003 / Package 1 merges — both touch `distillation.py` and the reality-test harness; one PR = one package, restart from `main` first)

## Origin

Operator rule "design to the mature-state target — why build things twice?" (2026-07-06, recorded in `docs/ORCHESTRATOR_PLAYBOOK.md`). This is **Package 2** of the distillation mature-state target: the **reasoned quality tier**. Package 1 (AOS-DISTILL-003) landed the honest deterministic floor + framework evidence; this makes `DNA.purpose` genuinely good by having the **isolated `claude_code` provider** reason a concise "what this is / what it's useful for" from README + bounded source — the two-tier pattern already ratified for the Council and the Phase-2 narrative. The floor remains the CI-safe / offline / local-first fallback; the reasoned tier is the primary quality source when a real provider is present.

## Verified Baseline (confirmed by inspection)

- `packages/aos_core/aos_core/services/distillation.py`:
  - L936 `dna.purpose = distillation["summary"]` — `DNA.purpose` is **always** the deterministic floor summary today.
  - L882 `narrative = reason_over_source(files, provider) if getattr(provider, "name", "") != "deterministic" else {}` — the reasoned tier runs **only** for a real (non-deterministic) provider; `reason_over_source` (L701) returns `{"built_for","how_it_works","reusable","provenance"}` and is parsed with the council's tolerant `_loads_tolerant`.
  - `validation_state` is hardcoded `"derived"` (L922, L931) for the `KnowledgePage`.
  - `get_provider(get_settings())` (L868) resolves the provider; `ClaudeCodeProvider` is LES-021-isolated (empty cwd + `--disallowedTools` + `--strict-mcp-config`).
- `RepositoryDNA` has a `purpose` column; `KnowledgePage.validation_state` exists (default `"raw"`).

## Mature-state target this lands (the subset)

Two-tier `DNA.purpose`: **reasoned** (real provider, primary) with the **deterministic floor as fallback**, and `validation_state` honestly marking which tier produced the knowledge (`derived` vs `reasoned`). No throwaway: the floor from Package 1 stays as the permanent fallback; this only *adds* the reasoned primary.

## In-Scope Files

- **`packages/aos_core/aos_core/services/distillation.py`**:
  - Extend the reasoned tier so it emits a concise **`purpose`** (one declarative sentence: what the repo is + what it's useful for), reasoned from README + the already-selected bounded `sources` — either by extending `reason_over_source`'s returned dict with a `"purpose"` key or a sibling helper `reason_purpose(readme, files, provider)`. Reuse the isolated-provider call pattern + `_loads_tolerant`. Must return `""`/absent gracefully on empty/garbled model output (no fabrication).
  - In `distill_repository`: when a **real** provider produced a non-empty reasoned purpose, set `dna.purpose` from it and set the page `validation_state="reasoned"`; **otherwise** keep the Package-1 clean floor (`distillation["summary"]`) and `validation_state="derived"`. Deterministic provider (CI default) → always the floor path → `"derived"` (CI stays hermetic; no live model). The reasoned purpose should also be what the rendered page's summary reflects when present (single source of truth).
  - Keep idempotent + the 409-on-`:ro`-vault behavior unchanged.
- **`apps/api/tests/test_distillation.py`** — hermetic (no live model): a **fake real provider** (a stub whose `.name != "deterministic"` and whose `.generate` returns canned JSON with a `purpose`) → `dna.purpose` is the reasoned line and `validation_state="reasoned"`; the deterministic provider → floor summary + `"derived"`; a real provider returning empty/garbled purpose → **falls back** to the floor + `"derived"` (no fabrication). Assert `getattr(provider,"name","")` gating so CI never shells a model.
- **`scripts/reality_test_distillation.py`** — add an **opt-in real-provider mode** (e.g. `--provider claude_code` / env flag) that distills with the isolated `ClaudeCodeProvider` for the live check; **default stays deterministic/hermetic** so the Package-1 ranking gate is unchanged and reproducible.
- **Lessons** — only if a defect is self-found during build/verification (record per RFC-0004 in the same change set); otherwise none.
- **Docs**: `docs/CAPABILITY_MAP.md` (distillation `DNA.purpose` now has a reasoned tier + `validation_state` derived/reasoned). State docs are Orchestrator-owned.

## Out-of-Scope (later)

- Transfer scorer normalization + folding `runtime_services`/architecture into candidate text (Package 3).
- Embeddings/semantic relevance. Import-graph edges (LES-014). Broader manifest ecosystem breadth (LES-016).

## Acceptance Criteria

- Deterministic (CI) path unchanged: `DNA.purpose` = clean floor summary, `validation_state="derived"`, fully hermetic; a fake-real provider path sets the reasoned purpose + `"reasoned"`; empty/garbled reasoned output falls back to the floor (no fabrication). All hermetically unit-tested.
- **Live validation (Orchestrator, real isolated provider):** distilling a real repo (e.g. `kubernetes`/`gin`/`free-llm`) via `ClaudeCodeProvider` yields a genuinely descriptive `DNA.purpose` (k8s → about container orchestration/management; not badges, not analogy) with **zero ArchetypeOS contamination** (LES-021 holds), and `validation_state="reasoned"`. Re-running the Package-1 deterministic ranking gate still passes.
- api + worker green; ruff full CI scope + compileall clean; guardian PASS; lessons (if any) in the same change set.

## Verification (Orchestrator, independent — builder ≠ verifier)

Hermetic: run the suites with the fake-real provider stub + deterministic default; confirm the derived/reasoned branching + fallback. Live: run `scripts/reality_test_distillation.py --provider claude_code` (isolated) over ≥1 real repo; eyeball the reasoned `DNA.purpose` for quality + contamination-freeness; confirm the deterministic gate (Package 1) is untouched. ruff full CI scope + compileall; guardian.
