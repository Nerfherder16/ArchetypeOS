# AOS-DISTILL-003 — Distillation evidence quality: deterministic summary floor + framework detection

## Status

In Progress

## Origin

The **first end-to-end reality test** of the intelligence loop (Orchestrator, 2026-07-06) ran the real service layer (`run_scan` → `distill_repository` → `recommend_reuse`) over the 6 cloned repos (`free-llm-api-resources`, `example-voting-app`, `gin`, `claude-agent-sdk-python`, `pydantic-ai`, `kubernetes`). Verdict: **the loop connects and transfer's ranking is directionally correct, but distillation quality starves it** ("right engine, wrong evidence"). Concrete, reproduced failures:

1. `"container orchestration and scheduling"` → **no matches**, though `kubernetes` is in the portfolio — because its `DNA.purpose` is raw **badge markdown** (`[![CII Best Practices]...`), which has zero meaningful tokens.
2. `"HTTP routing and middleware"` ranks `gin` **third**, behind `free-llm`/`pydantic-ai` matching on generic `api`/`web` noise — `gin`'s purpose is also badge markdown.
3. `pydantic-ai`'s purpose is **"FastAPI revolutionized web development…"** — the extractor grabbed the README's analogy intro, not what PydanticAI is → false `web` matches.
4. **`DNA.frameworks` is empty for all 6** — `run_scan` never populates it, so transfer's technology-match boost is structurally dead.

Root cause (verified against source): `extract_repo_knowledge` sets `summary = _first_paragraph(lines)` with no cleaning; `run_scan` sets `language_mix`/`package_managers`/`runtime_services`/`risk_flags` on the DNA but **not `frameworks`**, and the scanner detects package managers from manifest *names* only, never reading manifest bodies for dependencies.

This is Package 1 of the mature-state sequence (deterministic floor + tech detection now; real-provider reasoned purpose and scorer normalization are separate later packages). No new RFC — this is quality-hardening within RFC-0008 (distillation) + LES-016 (scanner precision).

## In-Scope Files

- **`packages/aos_core/aos_core/services/distillation.py`** — improve the deterministic summary floor (keep it pure, LLM-free, hermetic):
  - Add a helper that, from README lines, drops **noise-only lines** before choosing the summary: lines that are only markdown image-links / badges (`[![alt](img)](href)` runs), bare link lines, HTML comments (`<!-- … -->`), and heading lines. From the cleaned prose, prefer the **first declarative description sentence** — the first sentence matching roughly `^<Name>\b … \bis|are|provides|lets|helps|…` where `<Name>` matches the distilled `title`/repo name (case-insensitive), else the first clean prose paragraph. Never emit a summary that is *only* badge/link markup: if no clean prose exists, emit the honest fallback (`"README present but no prose summary could be extracted."`) — **an empty/honest summary is better than noise** (noise actively mis-ranks transfer).
  - This function must be pure and unit-tested on synthetic READMEs (badge-first, analogy-first, clean). Do not read files here — operate on the passed `readme_text`/lines.
- **`packages/aos_core/aos_core/repository_scanner.py`** — add **framework detection** from manifest **bodies** (bounded — this is a deliberate, scoped extension of the "reads no bodies except compose" rule, to manifests only, aligned with LES-016):
  - Read the detected manifest files (`package.json` deps/devDeps, `requirements.txt`, `pyproject.toml` dependencies, `go.mod` requires) tolerantly (try/except → skip), and map a **small, curated table** of well-known frameworks (e.g. `fastapi`, `flask`, `django`, `starlette`, `express`, `react`, `next`, `vue`, `gin-gonic/gin`→`gin`, `pydantic-ai`, `langchain`, …) to a normalized framework name. Cap the bytes read per manifest. Emit a new `frameworks: list[str]` key in the scan result (sorted, deduped). Keep it conservative — only high-confidence, curated matches; unknown deps are ignored (no guessing).
- **`packages/aos_core/aos_core/services/scan.py`** — `run_scan` must populate `dna.frameworks = scan["frameworks"]` (currently unset). No schema change (`RepositoryDNA.frameworks` column already exists).
- **`apps/api/tests/test_distillation.py`** (or the existing distillation test module) — hermetic unit tests: badge-first README → summary is the real description (not the badge); analogy-first README (`"X revolutionized … PydanticAI is a …"`) → summary is the `<Name> is a …` sentence; all-badge/no-prose README → honest fallback, never badge markup.
- **`apps/api/tests/test_scanner.py`** — framework detection: a fixture manifest with `fastapi`/`react`/etc. → `frameworks` populated; unknown-dep manifest → not guessed; malformed manifest → tolerated (no raise). Use/extend fixtures under `apps/api/tests/fixtures/`.
- **`scripts/reality_test_distillation.py`** (new, committed) — a documented, repeatable portfolio reality-test harness (adapted from the Orchestrator's scratch harness): given the cloned repos under `settings.repository_root`, ingest (scan+distill to a scratch DB, deterministic provider) and run a fixed set of `recommend_reuse` needs, printing per-repo `DNA.purpose` + the rankings. This is the **regression gate** for the mature-state sequence (manual, not CI — needs cloned repos). Include a module docstring stating the expected post-fix rankings (k8s #1 on container orchestration, gin #1 on HTTP routing).
- **Lessons** (`knowledge/wiki/lessons/`, per RFC-0004 — self-found defects in the same change set): a new lesson for the **distillation summary noise defect** (badge/analogy → mis-ranked transfer; the reality-test evidence), and update **LES-016** (scanner precision) noting framework detection delivered. Update `knowledge/wiki/lessons/index.md`.
- **Docs**: `docs/CAPABILITY_MAP.md` (distillation now emits a cleaned summary + detected frameworks), the reality-test findings noted where appropriate, state docs.

## Out-of-Scope (later packages)

- Real (isolated `claude_code`) provider-reasoned `DNA.purpose` + `validation_state` derived/reasoned distinction (Package 2).
- Transfer scorer normalization + folding `runtime_services`/architecture into candidate text (Package 3).
- Import-graph edges (LES-014). Broader manifest/ecosystem coverage beyond the curated framework table.

## Acceptance Criteria

- The deterministic summary floor **never emits badge/link-only markup** as a summary; for real READMEs it prefers the declarative description sentence. Pure + hermetically unit-tested.
- The scanner populates `frameworks` from manifest bodies (curated, conservative, tolerant, byte-capped); `run_scan` stamps `DNA.frameworks`.
- **Reality-test regression gate (the real acceptance):** re-running `scripts/reality_test_distillation.py` over the 6 repos, `kubernetes` ranks **#1** for `"container orchestration and scheduling"` and `gin` ranks **#1** for `"HTTP routing and middleware for a web API"`; `pydantic-ai` no longer false-matches on `web` via the FastAPI analogy.
- api + worker green (CI-scope venv); ruff full CI scope + compileall clean; guardian PASS; lessons recorded in the same change set.

## Verification (Orchestrator, independent — builder ≠ verifier)

Re-run the reality-test harness over the 6 cloned repos and confirm the ranking gate (k8s/gin #1 on their needs; pydantic-ai analogy gone); spot-check the cleaned `DNA.purpose` for gin/k8s/pydantic-ai; confirm `frameworks` populated (fastapi for pydantic-ai/free-llm? gin for gin; react/etc. where present) and that transfer's tech-boost now fires; run api+worker suites, ruff full CI scope + compileall; guardian.
