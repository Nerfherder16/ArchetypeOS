# AOS-DISTILL-001 — RFC-0008 MVP: repository content extraction (distillation)

## Status

In Progress

## Origin

Operator direction: "lets pick up your recommendations" → LES-021 → **RFC-0008**. Step 1 (provider isolation, PR #60) is done; this is Step 2. RFC-0008 (`docs/rfc/RFC-0008-...`) is the operator's founding intent: *feed a repo → extract what's useful → durable knowledge in Obsidian for reuse.* The `free-llm-api-resources` reality test proved the gap — the scanner reads a structural **fingerprint**, never **content**, so a curated-catalog repo (whose value is its README) yields a fingerprint abstention. This package builds the **content-extraction MVP**: read a scanned repo's actual content and distill **provenance-tagged** knowledge into the vault, where it becomes re-syncable `KnowledgePage`s and Council evidence.

## Governing constraints (RFC-0008 + Constitution)

- **Provenance is mandatory** — every extracted claim cites its source file. Verification over inference.
- **Hermetic default, isolated real provider** — a **deterministic content extractor** (parses real README/section content, no LLM) is the CI/default path; the now-isolated `ClaudeCodeProvider` (LES-021, PR #60) is the richer real path on an authed node. No live model in CI.
- **Repo vault = source of truth; `KnowledgePage` = re-syncable projection** (RFC-0002/0004) — the distillation is written to `knowledge/wiki/repositories/<slug>.md` AND `sync_knowledge` re-derives it, so a DB reset loses nothing (the exact pattern AOS-COUNCIL-PHASEC2A established for decisions).
- **Local-first write** — target `settings.knowledge_root`; the `:ro` compose stack returns a clean **409** (never 500), never corrupting state (mirror the ADR-export seam).

## Verified Baseline

- `services/scan.py::run_scan` resolves repo content via `safe_repo_path(settings.repository_root, repository.local_path)`; the scan report already lists `readme_files` (paths) and `manifests`. `RepositoryDNA` has an unused `purpose` field.
- `sync_knowledge` (`services/knowledge.py`) scans `wiki/lessons/index.md` + `wiki/decisions/*.md` and upserts `KnowledgePage`s keyed on `vault_path` — extend it with `wiki/repositories/*.md` (`page_type="repository"`), exactly like `parse_adr`/the decisions branch.
- Council evidence selectors (`_select_research`/`_select_architecture`/`_select_fitness`/`_select_security`) read DB state; a distillation surfaced to the council lets a content-rich repo produce substance instead of a fingerprint abstention.
- `services/adr.py` (AOS-COUNCIL-PHASEC2A) is the reference for the local-first vault write (`OSError` → 409, idempotent upsert keyed on `vault_path`, sha256 checksum, `KnowledgePage` projection). `knowledge/wiki/repositories/` exists (`.gitkeep`).
- `ClaudeCodeProvider` is now context-isolated (LES-021) — safe to shell over real repo content without ambient contamination.

## In-Scope Files

- **`packages/aos_core/aos_core/services/distillation.py`** (new):
  - `distill_repository(db, *, repository_id, knowledge_root) -> KnowledgePage`: load the repository (404 if missing); read a **bounded** slice of its content via `safe_repo_path` — the primary README (cap ~40 KB) plus, if present, a small bounded sample of top-level source/manifest files (cap total bytes + file count). Run the **deterministic content extractor** (`extract_repo_knowledge`, below). Render a provenance-tagged markdown page and write it to `<knowledge_root>/wiki/repositories/<slug>.md` (`OSError` → `HTTPException(409)` naming the writable-checkout requirement, without mutating state). Upsert a `KnowledgePage` (`page_type="repository"`, `validation_state="derived"`, `source_refs=[{"type":"repository","id":...}, {"type":"vault_file","ref": readme_path}]`, sha256 checksum). Set `RepositoryDNA.purpose` from the distilled summary if a DNA row exists. Idempotent (re-distill overwrites the file + updates the one page).
  - `extract_repo_knowledge(readme_text, *, dna=None, sources=None) -> dict` (pure, deterministic, no I/O, no LLM): from real content, derive `title` (first `# ` heading or repo name), `summary` (first non-empty prose paragraph), `key_points` (`##` section headings + their first bullet/line), `technologies` (from `dna.package_managers`/`language_classes` + fenced-code languages in the README), `useful_for` (heuristic signals — e.g. "library"/"cli"/"catalog"/"template" keywords), and `provenance` (each item tagged with its source path/line-ish anchor). Tolerant: empty/missing README → a minimal page citing the absence, never raises.
  - `render_repository_markdown(distillation) -> str` (pure): an Obsidian-friendly page (`# <title>`, `## Summary`, `## What it is / useful for`, `## Key points`, `## Technologies`, `## Provenance`).
- **`packages/aos_core/aos_core/services/knowledge.py`**: extend `sync_knowledge` to also scan `wiki/repositories/*.md` and upsert `page_type="repository"` pages (mirror the decisions branch; fold into `synced`/`created`/`updated`). A malformed/empty file is skipped, never raises.
- **`packages/aos_core/aos_core/services/council.py`**: a new evidence selector `_select_distillation` (or fold into `_select_research`) that surfaces the repository distillation (title/summary/key_points/technologies with provenance) to the council — wire it into `research_librarian`'s evidence (the agent that reasons over distilled knowledge). Keep the change minimal and additive.
- **`apps/api/app/routes/repositories.py`**: `POST /repositories/{repository_id}/distill` → `KnowledgePageRead`, calling `distill_repository(db, repository_id=..., knowledge_root=get_settings().knowledge_root)`; propagate 404/409. Register the route in `test_route_inventory.py` (freeze +1).
- **`apps/api/tests/test_distillation.py`** (new): `extract_repo_knowledge` pulls title/summary/technologies/provenance from a real README string (incl. a `free-llm`-style catalog README → `title`/`summary` name the catalog); `distill_repository` writes `wiki/repositories/<slug>.md` + creates a `KnowledgePage` (`page_type="repository"`) + sets `DNA.purpose`; **idempotent** (one file, one page); a non-writable root → 409 without mutating state; a repo with no README → a minimal page, no raise. **Use `tmp_path` for both `repository_root` and `knowledge_root` — never the real vault.** Add a content-rich README fixture (a small `wiki/repositories`-style catalog).
- **`apps/api/tests/test_knowledge.py`**: count-agnostic assertion that `sync_knowledge` re-derives a `page_type="repository"` page from a `wiki/repositories/*.md` file.
- **Docs**: `docs/CAPABILITY_MAP.md` (Layer 1 — Knowledge Distillation Engine now has a shipped MVP), `docs/rfc/RFC-0008-...` (flip its status note to "MVP landed" / cite AOS-DISTILL-001), `.archetype/work/AOS-DISTILL-001.md`, state docs.

## Out-of-Scope

- **The Knowledge Transfer Engine** — "useful *for* a target repo" (relevance/retrieval) — later RFC. This builds the extraction Transfer will query; no target/need representation, no embeddings/semantic index.
- **Web tools (firecrawl/exa)** and **n8n connectors** — the Research Engine / ingestion-edge RFCs (RFC-0008's recorded boundary).
- **Rich LLM extraction as the default** — the deterministic README extractor is the shipped/CI core; the isolated `claude_code` provider is an available richer path but not required for the MVP's acceptance (keep the LLM pass behind the existing provider seam if wired at all; do not make CI depend on it).
- No new DB tables / migration (reuse `KnowledgePage` + `RepositoryDNA.purpose`).
- No frontend (the Knowledge dashboard already lists `KnowledgePage`s; a repository-page view is a later UI touch).

## Acceptance Criteria

- Distilling a **content-rich, structurally-thin** repo (a `free-llm`-style README fixture) yields a `wiki/repositories/<slug>.md` page + a `KnowledgePage` (`page_type="repository"`) whose `title`/`summary` name **what the repo is** (a catalog), with per-item provenance — not a fingerprint.
- `sync_knowledge` re-derives repository pages from the vault (DB reset loses nothing); distillation is idempotent; a non-writable vault → 409 (not 500) without mutating state; a README-less repo → a minimal page, no raise.
- The council can consume the distillation as evidence (the new selector surfaces it).
- api + worker suites green on the CI-scope venv; ruff full CI scope + compileall clean; guardian PASS/PASS_WITH_WARNINGS. No migration; no frontend.

## Verification (Orchestrator, independent — builder ≠ verifier)

Distill a content-rich README fixture and assert the vault page + `KnowledgePage` + `DNA.purpose` + provenance (using `tmp_path`, never the real vault); confirm `sync_knowledge` re-derives it; confirm idempotency, the 409-on-readonly, and the README-less tolerance; confirm the council selector surfaces the distillation; confirm no migration/frontend; ruff full CI scope + compileall; guardian. Bonus: distill the real `repositories/free-llm-api-resources` and eyeball that the page names the catalog (not a fingerprint).
