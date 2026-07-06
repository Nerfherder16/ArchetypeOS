# AOS-DISTILL-002 — RFC-0008 Phase 2: code-aware distillation

## Status

In Progress

## Origin

Operator feedback on the MVP (AOS-DISTILL-001, PR #61): *"reading the readme doesn't really nail down its usefulness. Sometimes the nuance lays elsewhere like the codebase, how each component works, what it was built for."* Correct — the README captures a repo's *claim*; the *substance* lives in the code. This package reads the actual **source** (bounded, meaningful) and adds a code-derived understanding to the distillation. It is the layer LES-021 (provider isolation, PR #60) and Phase B (the architecture graph) were setup for.

## Design — two code-derived layers (hermetic floor + reasoned nuance)

Mirror the council's deterministic-default / real-provider split:

1. **Deterministic structural summary (always, CI-tested):** parse a bounded set of selected source files and extract, per file, a **component** — module docstring first line + top-level symbols (functions/classes/exports) + whether it's an entry point — each item **provenance-tagged to its file**. Python via `ast` (stdlib); other languages via lightweight top-level-symbol heuristics. This is a real, hermetic "Components" section that never needs a model.
2. **Reasoned narrative (optional, real provider, authed node):** when a real provider is configured (`ClaudeCodeProvider`, now context-isolated — LES-021), run it over the selected source to reason about *what the repo was built for*, *how the components work together*, and *what's reusable* — **citing files**. In CI the provider is `DeterministicProvider`, so this section is minimal/absent; the deterministic Components section carries the hermetic guarantee. The real narrative is validated **live** by the Orchestrator (as with LES-021/free-llm).

## Bounded, meaningful file selection (the key to not drowning in noise)

`select_source_files(repository, *, dna, cap_files, cap_bytes)`:
- **Entry points** by filename (per language): `main.*`, `__init__.py`, `cli.*`, `app.*`, `index.*`, `lib.rs`, `mod.rs`, `cmd/**`, plus manifest-declared entry points where cheap.
- **Core modules**: the largest **source-classified** files (using Phase-B's `LANGUAGE_CLASS`), ranked by size, filling the remaining budget.
- **Manifests**: the primary `pyproject.toml`/`package.json`/`go.mod` (declares purpose/deps/scripts).
- Read via `safe_repo_path`; **bounded** — `cap_files` (~10) and `cap_bytes` (~40 KB total); skip unreadable/binary/huge files. Tolerant — a repo we cannot read yields no source, never raises.

## Verified Baseline

- `services/distillation.py` (AOS-DISTILL-001): `extract_repo_knowledge(readme_text, *, dna, sources=None)` — **`sources` is the unused Phase-2 hook**; `render_repository_markdown(distillation)` is section-based; `distill_repository(db, *, repository_id, knowledge_root)` orchestrates + writes the vault page + `KnowledgePage` (`page_type="repository"`) + `DNA.purpose`. `safe_repo_path(root, local_path)` resolves repo content; the scan already classifies languages (`LANGUAGE_CLASS`, Phase B).
- `ClaudeCodeProvider` is context-isolated (LES-021, PR #60) — safe to read a codebase without ambient contamination. `get_provider(settings)` → `DeterministicProvider` in CI.
- `RepositoryDNA` carries `language_mix`/`scan_summary` (primary_language/language_classes) to guide source selection.

## In-Scope Files

- **`packages/aos_core/aos_core/services/distillation.py`**:
  - `select_source_files(repository, *, dna=None, cap_files=10, cap_bytes=40_000) -> list[dict]` — bounded selection (entry points + largest source files + primary manifest), each `{"path": rel, "text": content, "is_entry_point": bool}`; reads via `safe_repo_path(get_settings().repository_root, repository.local_path)`; tolerant.
  - `summarize_sources(files) -> dict` (pure, deterministic, stdlib): per file, a **component** — `{"path", "role"("entry_point"/"module"/"manifest"), "docstring"(first line, if any), "symbols"(top-level def/class/export names, capped), "provenance": path}`. Python via `ast.parse` (tolerant of SyntaxError → regex fallback); JS/TS/Go/Rust/etc. via top-level-symbol regex. Returns `{"components": [...], "entry_points": [...]}`.
  - `reason_over_source(files, provider) -> dict` — build a bounded, path-labeled prompt from `files` and run `provider.generate(...)`; parse (reuse the council's tolerant `_loads_tolerant`/fenced handling) into `{"built_for", "how_it_works", "reusable", "provenance"}`. Only called when a **real** provider is supplied; `DeterministicProvider` yields a minimal/empty narrative (do not fabricate). Never raises out of distillation (provider error → no narrative + a note).
  - Extend `render_repository_markdown` with `## Components (from source)` (always, from `summarize_sources`, each citing its file) and `## How it works / Built for` (only when the narrative is non-empty), and extend `## Provenance` with the source files read.
  - Extend `distill_repository`: add an optional `provider=None` param; select source files, run `summarize_sources` (always), and — if `provider` is a real backend (not deterministic) — `reason_over_source`; merge both into the rendered page + the distillation dict. Keep the README-derived sections. Idempotent + local-first (unchanged). If `provider is None`, default to `get_provider(get_settings())` so the endpoint uses the configured backend (deterministic in CI).
- **`apps/api/app/routes/repositories.py`**: `POST /repositories/{id}/distill` unchanged in shape (still `KnowledgePageRead`); it now passes `provider=get_provider(get_settings())`. No new route.
- **`apps/api/tests/test_distillation.py`**: add tests — `select_source_files` picks entry points + largest source, respects caps, is tolerant; `summarize_sources` extracts a Python module's docstring + top-level `def`/`class` names with provenance (and a non-Python file via regex); `distill_repository` on a **code-centric fixture** renders a `## Components (from source)` section citing files; the deterministic provider produces no fabricated narrative. Hermetic — `tmp_path` for repo + vault; never the real vault/repos.
- **`apps/api/tests/fixtures/code-repo/`** (new): a tiny multi-module repo — an entry point (`app.py` with a module docstring + a couple of top-level functions/classes), a core module, a `pyproject.toml`, and a thin `README.md` (so the code section clearly adds signal the README lacks).
- **Docs**: `docs/CAPABILITY_MAP.md` (Layer 1 — distillation now reads source, not just README), `docs/rfc/RFC-0008-...` (Phase 2 note), `.archetype/work/AOS-DISTILL-002.md`, state docs.

## Out-of-Scope

- **Knowledge Transfer Engine** (relevance-to-a-target), embeddings/semantic index, web tools/n8n — later RFCs (RFC-0008 non-goals).
- Import-graph-based core-module ranking (LES-014's manifest/import half) — use size + entry-point heuristics for now; the dependency graph can refine selection in a follow-up.
- No new DB tables/migration (reuse `KnowledgePage` + the page markdown). No frontend.
- The live `claude_code` narrative is not CI-reproducible — CI tests the deterministic structural layer; the narrative is Orchestrator-live-validated.

## Acceptance Criteria

- Distilling a **code-centric** repo (thin README, real modules) produces a `## Components (from source)` section naming the entry point + modules with **per-file provenance**, adding understanding the README alone did not.
- Source selection is **bounded** (caps honored) and **tolerant** (unreadable/binary/absent source → no crash, README path still works).
- The real `claude_code` provider (authed node) yields a "How it works / Built for" narrative citing files; the deterministic provider fabricates nothing.
- Idempotent + local-first (unchanged); `sync_knowledge` still re-derives the page; api + worker green; ruff full CI scope + compileall clean; guardian PASS. No migration/frontend.

## Verification (Orchestrator, independent — builder ≠ verifier)

Distill the code-centric fixture and assert the Components section + provenance + caps + tolerance; confirm the deterministic provider adds no fabricated narrative; **live-validate** the real `claude_code` narrative by distilling a real code-centric repo from `repositories/` (eyeball that "built for / how it works" is grounded in the actual files, not hallucinated, and cites them); confirm idempotency + re-sync + no migration/frontend; ruff full CI scope + compileall; guardian.
