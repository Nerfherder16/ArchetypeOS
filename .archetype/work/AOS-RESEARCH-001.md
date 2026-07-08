# AOS-RESEARCH-001 — Research Engine MVP: ranked evidence dossiers (deterministic floor)

## Status

In Review — RFC-0011 slice-1 built (2026-07-08). Backend engine floor; explicit operator merge
approval (not auto-merge). Engine + route + worker branch + tests + LES-019 close landed on branch
`claude/aos-research-001-engine`; api/core 277 passed, worker 9 passed, ruff + compileall clean.
Test lives at `apps/api/tests/test_research.py` (the aos_core service tests run under
`apps/api/tests/`, not `packages/aos_core/tests/` — the spec's stated path was corrected).

## Verified Baseline

Confirmed by inspection (2026-07-08):

- `packages/aos_core/aos_core/models.py:148` — `ResearchNote` has `project_id, title, question, summary,
  sources (JSON list), findings (JSON list), freshness, confidence`. `sources`/`findings` are **inert**
  today (the add-note UI sends title+summary only). Baseline migration `0001` — **no new table/migration**.
- `packages/aos_core/aos_core/services/council.py:71` — `_select_research(db, project_id)` reads
  `ResearchNote` + `Decision` rows → `{kind, detail, ref}`. `_select_research_librarian` (:111) =
  `_select_research` + `_select_distillation`. `DEFAULT_AGENTS` (:166) = **4 agents** (research_librarian,
  architecture, fitness, security).
- `council.py:320` `synthesize_verdict`: `total_evidence = sum(len(o.evidence))`;
  `aggregate_confidence = mean(confidences)` **over all 4 agents**; abstains if `total_evidence < 1` OR
  `aggregate_confidence < 0.35` (`ABSTAIN_CONFIDENCE=0.35`, `MIN_EVIDENCE=1`, :40-41).
- `llm/__init__.py:142` `DeterministicProvider.generate`: evidence count 0 → confidence `0.0`, status
  `Needs Evidence`; count ≥1 → `base = 0.4 + 0.1*min(count,4)` (0.5..0.8) minus `0.1*min(concerns,3)`.
- `services/llm_router.py:106` `route(task_class, sensitivity, settings)`; `"research"` task class
  exists (`[FREE_HOSTED, CLAUDE]`); guardrail (:114) strips `FREE_HOSTED` when `Sensitivity.PRIVATE`.
  Always returns a provider (deterministic fallback). `Sensitivity` enum at :34.
- `services/jobs.py:16` `enqueue_job(db, client, *, job_type, project_id, repository_id, payload,
  priority)`. `apps/api/app/routes/council.py:16` is the enqueue-route pattern to mirror (`POST` →
  `enqueue_job(..., redis.Redis.from_url(settings.redis_url), job_type=..., payload=...)` → `JobRead`).
- `apps/worker/app/worker.py:39` `run_job` dispatches on `job_type` (`repository_scan`,
  `project_digest`, `council_review`, else test). `council_review` branch (:65) is the template.
- `services/transfer.py` — the calibrated deterministic scorer to reuse: `_tokenize` (lowercase,
  `[a-z0-9]+`, drop stopwords + len<3), **need-coverage** relevance (LES-023; never a raw cosine).
- `apps/api/app/schemas.py:239` — `ResearchNoteCreate`/`ResearchNoteRead` already expose
  `sources`/`findings`. `docs/RESEARCH_ENGINE.md` — the 7-rung source ladder + outputs.

## In-Scope Files

- **New** `packages/aos_core/aos_core/services/research.py` — the engine (`SourceDoc`, `SOURCE_TIERS`,
  `ResearchSource` protocol, `LocalCorpusSource`, `score_source`, `synthesize_dossier`, `research`).
- **New** `apps/api/app/routes/research.py` — `POST /projects/{project_id}/research` (enqueue).
- **New** `packages/aos_core/tests/test_research.py` — hermetic tests (incl. the LES-019-close).
- `apps/worker/app/worker.py` — **additive** `elif job_type == "research":` branch only.
- `apps/api/app/schemas.py` — add `ResearchRequest{question: str, sensitivity: str = "public"}`.
- `apps/api/app/main.py` (or wherever routers mount) — register the research router (mirror council).
- `docs/rfc/RFC-0011-Research-Engine-Ranked-Evidence-Dossiers.md` — already drafted (leave as-is).
- `knowledge/wiki/lessons/LES-019.md` + index — update to Closed (this MVP is its close condition).
- `.archetype/roadmap.md`, `docs/RECENT_CHANGES.md`, `.archetype/work/AOS-RESEARCH-001.md` — state/docs.

## Out-of-Scope

- **Any edit to `council.py`, `llm_router.py` (`ROUTING_TABLE`/`route`), `llm_pool.py`, `usage.py`,
  `services/council.py`** — consume `route()`/`get_provider()` read-only; feed the council via **new
  `ResearchNote` data**. These are the laptop session's active seams.
- `WebResearchSource` / any outbound HTTP / new network dependency (`httpx`/`requests`/`bs4`) — slice-2.
- Reasoned LLM dossier synthesis — floor is deterministic; the `route()` seam is wired for slice-3.
- Any frontend change — the Research Inbox (#107) already renders `ResearchNote`s.
- New DB table / migration — reuse `ResearchNote.sources`/`findings` (JSON).

## Acceptance Criteria

- `research(db, *, project_id, question, sensitivity=Sensitivity.PUBLIC, source=None, limit=8)` persists
  a `ResearchNote` whose `sources` are ranked by **source-quality × relevance**, each carrying `{ref,
  title, tier, tier_rank, quality, relevance, matched_terms, label}` (community labeled `"opinion"`),
  `findings` each cite a source, `confidence` is calibrated (bounded [0,1], intuitive, never near-zero
  for a strong match) — evidence: `test_research.py::test_ranks_by_quality_and_relevance`.
- **LES-019 close (the centerpiece):** a scenario that abstains **for want of research-class evidence**
  (structural agents have evidence but the research class is empty, dragging the mean under 0.35) is
  constructed; after a `research()` run adds research-class evidence, `run_council` on that question
  **no longer returns `Insufficient evidence`** and the research_librarian agent's output is non-empty
  (status `Complete`, confidence > 0). The test must be HONEST — establish the abstain baseline
  empirically against the real `synthesize_verdict`, not a staged constant — evidence:
  `test_research.py::test_research_run_clears_council_abstention`.
- **Privacy guardrail in code:** `research(..., sensitivity=Sensitivity.PRIVATE)` resolves its provider
  via `route()` and the resolved tier is never `FREE_HOSTED` (assert on `route()`'s result) — evidence:
  `test_research.py::test_private_never_routes_to_free_hosted`.
- Tolerant: empty corpus / empty question → a persisted "no evidence found" note (explicit open
  question, confidence 0.0), never raises — evidence: `test_research.py::test_empty_corpus_graceful`.
- `POST /projects/{id}/research` enqueues a `research` job (404s a missing project); the worker's
  `research` branch runs `research(...)` with `make_ledger_sink(context="research")` and completes with
  `result={"note_id": ...}` — evidence: an api route test + the worker branch (compileall + smoke).
- Deterministic + hermetic (no model, no network); api + worker + core suites green; ruff full CI scope
  + compileall clean; compose smoke green; **Guardian PASS** — evidence: `scripts/pre_pr_guardian.sh`
  / CI. A `LES-*` recorded for any BLOCK/CI failure (per CLAUDE.md).

## Verification Plan

- Level 3 (independent, builder ≠ verifier): Orchestrator re-runs `python -m pytest` for aos_core +
  api + worker from a clean tree; ruff + `python -m compileall`; `docker compose config`; the local
  PR Guardian. The LES-019-close test is re-read for honesty (real abstain baseline, not a constant).

## Suggested Delegation

Build `packages/aos_core/aos_core/services/research.py`:

1. `SourceDoc` (dataclass or TypedDict): `ref, title, text, tier (str), tier_rank (int), label (str),
   published (str|None)`. `SOURCE_TIERS`: the 7 ladder rungs from `docs/RESEARCH_ENGINE.md` mapped to
   `(tier_rank, quality_weight)` — official docs (rank 1, highest quality) … community (rank 7, lowest,
   `label="opinion"`). A helper `_tier_for_local(kind)` maps a local-corpus item to a rung: a
   repository distillation → "reference-implementation" class; a prior `ResearchNote` → keep its own
   tier if recorded else "reference"; a `Decision` → "maintainer-discussion" class. Document the mapping.
2. `ResearchSource` protocol with `gather(db, *, project_id, question, sensitivity, limit) ->
   list[SourceDoc]`. `LocalCorpusSource` implements it: query `KnowledgePage` (`page_type="repository"`,
   title+summary+vault_path), prior `ResearchNote`s (title+summary+question), and `Decision`s
   (title+decision text) for the project → build `SourceDoc`s. No network. Tolerant of empty results.
3. `score_source(question_tokens, source) -> (relevance, matched_terms)` — reuse the `transfer.py`
   tokenizer + **need-coverage** relevance (fraction of question terms the source covers). `composite =
   relevance-dominant blend with the tier quality as a boost/tie-break` (an official-doc source outranks
   a community post at equal relevance; keep it calibrated per LES-023 — never emit a raw score that
   reads as near-zero for a genuine match).
4. `synthesize_dossier(question, ranked) -> dict` — deterministic: a template `summary` naming the top
   sources; `findings` = one `{claim, source_ref, tier, label}` per top-N source; `open_questions` when
   coverage is thin; `conflicting_evidence` note if top sources carry opposing labeled stances (keep
   simple for MVP — detect on a lightweight signal, document the heuristic); `confidence` = calibrated
   coverage × top-source quality, bounded [0,1]; `freshness` from the freshest source's `published` or
   a generated "as-of local corpus" marker (NO wall-clock in aos_core — accept an injected timestamp or
   omit; do not call datetime.now in the hermetic path).
5. `research(db, *, project_id, question, sensitivity=Sensitivity.PUBLIC, source=None, limit=8) ->
   ResearchNote` — resolve `source` (default `LocalCorpusSource()`), `gather` → `score`/rank (drop
   zero-relevance) → `synthesize_dossier` → construct + persist a `ResearchNote` (title derived from the
   question; `question`, `summary`, `sources` [ranked, structured], `findings`, `confidence`,
   `freshness`), commit, return it. **Resolve the provider via `route("research", sensitivity,
   get_settings())` even though the floor's synthesis is deterministic** — so the guardrail is exercised
   and slice-3 inherits it. Tolerant: empty gather → persist a graceful "no evidence found" note.

Route `apps/api/app/routes/research.py`: mirror `routes/council.py` exactly — `POST
/projects/{project_id}/research` with `ResearchRequest` → 404-guard the project → `enqueue_job(db,
redis.Redis.from_url(settings.redis_url), job_type="research", project_id=project_id,
payload={"question": ..., "sensitivity": ...})` → return `JobRead`. Register the router where
council's is registered.

Worker `apps/worker/app/worker.py`: add `elif job_type == "research":` after the `council_review`
branch — read `payload["question"]`/`["sensitivity"]`, call `research(db, project_id=project_id,
question=question, sensitivity=Sensitivity(...))`, `mark_job(job_id, "completed", result={"note_id":
note.id})`. Keep it thin; no synchronous web work.

Tests `packages/aos_core/tests/test_research.py` — 4 hermetic tests matching the Acceptance Criteria.
For `test_research_run_clears_council_abstention`: seed a project so that WITHOUT notes `run_council`
(deterministic provider) returns `Insufficient evidence` because the research class is empty and drags
the 4-agent mean under 0.35 — the reliable construction is a project whose research_librarian selector
returns nothing (no notes, no distillations) so its agent confidence is 0, with the other agents also
thin enough that the mean < 0.35 (an empty/near-empty project abstains trivially: all 4 at 0). Then run
`research()` to add research-class evidence and assert the research_librarian agent is now non-empty and
the verdict is no longer `Insufficient evidence`. **If a single note cannot flip your chosen baseline
(because the mean is over 4 agents), either (a) produce enough research-class evidence, or (b) pick a
baseline where research is genuinely the deciding class — but NEVER stage the baseline with a constant;
it must run the real `synthesize_verdict`.** If you discover research-alone cannot clear a fully-empty
project, record that finding in the PR body's Limitations (it is honest and expected) and make the test
assert the concrete, real transition you CAN demonstrate (research_librarian rises from empty→Complete,
total_evidence increases, and the verdict changes on a scenario where it genuinely does).

Do NOT commit/push/touch git — leave the tree for the Orchestrator. Run `python -m pytest` for the
three suites + ruff + compileall yourself and report results, but the Orchestrator re-verifies.

## Board Linkage

- Plane:
- Branch: claude/aos-research-001-engine
