# RFC-0011 — Research Engine: ranked evidence dossiers (MVP)

## Status

Proposed — operator-directed 2026-07-08 ("let's work on research" → Research Engine, the flagship).
Builds on RFC-0005 (the Agent Council this feeds), RFC-0008 (the distilled knowledge the
deterministic floor searches), and ADR-0001 (the routed reasoned tier + privacy guardrail this
consumes). The MVP described here is a **strict subset** of the mature-state Research Engine
(`docs/RESEARCH_ENGINE.md`): it ships the whole gather → rank → synthesize → persist → feed-the-Council
pipeline **deterministically over the portfolio's own knowledge**, with live web sources deferred
behind a `ResearchSource` provider seam (slice-2, gated on the network-policy work below).

## Summary

The Agent Council (RFC-0005) judges; the Distillation Engine (RFC-0008) extracts; the Transfer Engine
(RFC-0009) retrieves reusable assets. **Nothing produces research-class evidence** — and without it the
Council abstains. The first real council run abstained (`Insufficient evidence`, confidence 0.0375)
because the only evidence was a *structural scan* of the target repo; the `research_librarian`'s
`follow_up` named exactly what was missing — *research notes, a technology-fitness comparison, a
security/dependency review* (**LES-019**, open). The abstained review drafts a `needs_evidence`
decision, and approving it returns **409** (`services/decisions.py`). The evidence loop is jammed.

The **Research Engine** (`docs/RESEARCH_ENGINE.md`) *"gathers, ranks, summarizes, and preserves
engineering evidence before decisions are made."* Given a research question, it gathers evidence across
a **source-quality ladder** (official docs → standards/RFCs → reference implementations → benchmarks/
papers → security advisories → maintainer discussion → community opinion, labeled), ranks by
**source-quality × relevance**, and produces a **ranked evidence dossier** — persisted `ResearchNote`
rows with populated `sources` + `findings` + confidence + open questions — that (a) feeds the Council's
**research class** (`_select_research`, `council.py:71`) so it clears its abstention floor and unjams
the decision loop (closing LES-019), and (b) feeds Decision / Recommendation / Technology-Fitness
Intelligence. *"Research is reusable knowledge, not disposable search output."*

This is fundamentally an **evidence-production** problem, distinct from the Council (judgment), the
Distillation Engine (extraction from a repo), and the Transfer Engine (portfolio retrieval): given a
question, *assemble and rank the evidence a decision needs*.

## Problem

The pieces exist but nothing produces the evidence class the Council requires:

- `_select_research` (`council.py:71`) reads `ResearchNote` + `Decision` rows — the **research class**.
  `_select_distillation`/`_select_architecture`/`_select_fitness`/`_select_security` read scan/DNA
  rows — the **structural class**. LES-019: a structural scan is the wrong evidence class for an
  adoption question.
- The Council clears its abstention floor only when `total_evidence ≥ MIN_EVIDENCE (1)` **and**
  `aggregate_confidence ≥ ABSTAIN_CONFIDENCE (0.35)` (`council.py:40-41,353-369`). The deterministic
  provider yields confidence `0.0` / status `Needs Evidence` when the prompt evidence array is empty
  (`llm/__init__.py:172-192`). So the Council needs **real `ResearchNote` rows for the project**
  before it runs — and nothing creates them except a human typing into the add-note form
  (`main.tsx:501`, title + summary only; `sources`/`findings` never populated).
- The `ResearchNote` model already has `sources` / `findings` / `question` / `freshness` /
  `confidence` columns (baseline migration `0001`) — **inert**. The dossier structure is modeled; no
  engine fills it.

## Goals (MVP scope)

- A **`research(db, *, project_id, question, sensitivity=PUBLIC, source=None, limit=8)`** service
  (`packages/aos_core/aos_core/services/research.py`) that gathers candidate evidence, ranks it by
  **source-quality × relevance**, synthesizes a dossier, and **persists a `ResearchNote`** with
  structured `sources` (each: `{ref/url, title, tier, tier_rank, quality, relevance, matched_terms,
  label}`), `findings` (each cited to a source), calibrated `confidence`, `freshness`, and an
  `open_questions` finding when evidence is thin/conflicting.
- **A `ResearchSource` provider seam** (mirrors the LLM provider seam): `gather(question, sensitivity,
  limit) -> list[SourceDoc]`. Two implementations planned; **one shipped**:
  - **`LocalCorpusSource` — the hermetic floor (shipped in this MVP).** Gathers candidate evidence
    from the portfolio's **own knowledge**: repository distillations (`KnowledgePage`
    `page_type="repository"`), prior `ResearchNote`s, and recorded `Decision`s. No network, no model
    — deterministic and CI-runnable. Genuinely useful: *"what does my portfolio already know about
    X, and how strong is that evidence?"* is real research-class evidence.
  - **`WebResearchSource` — the real tier (deferred, slice-2).** Fetches + labels external sources
    across the ladder. Behind the same seam, opt-in, network-gated. **Not built here** (see the
    network-policy dependency in Non-goals + Dependencies).
- **Deterministic source-quality × relevance ranking (the hermetic floor):** a source's ladder
  position (`docs/RESEARCH_ENGINE.md` §Source Priority, 7 tiers) gives a `tier_rank`/`quality` weight;
  relevance reuses the calibrated lexical scorer pattern from `transfer.py`
  (`score_relevance` = need-coverage, LES-023) over the source's title/summary/text. Composite score
  ranks the dossier. No model, no network — reproducible.
- **Runs as a job.** `POST /projects/{project_id}/research` (body `{question, sensitivity?}`) enqueues
  a `job_type="research"` job (mirrors `council.py`'s `council_review` enqueue); the worker's new
  `research` branch runs `research(...)` with `make_ledger_sink(context="research")` and returns
  `result={"note_id": ...}`. This is the **permanent async shape** (the web tier is slow) even though
  the floor is fast — designing to the mature-state target, not scaffolding.
- **Privacy guardrail enforced in code.** The service selects its provider via
  `route("research", sensitivity, settings)` (`llm_router.py:106`) — becoming the **first production
  caller of `route()`** — so a `PRIVATE` question can never reach Tier-2 free hosted
  (`llm_router.py:114-116`). (The deterministic floor uses no provider; the seam is wired so slice-2's
  reasoned synthesis inherits the guardrail for free.)
- **Advisory + provenance-first.** Every finding cites a source; the engine persists evidence and
  never decides or acts. The payoff: after a research run, the Council's `_select_research` returns the
  new notes → the review clears the abstention floor → the drafted decision is approvable (no 409).
- **The closing test (the reason this exists):** seed a project with distillations, run
  `research(question)`, assert a `ResearchNote` is persisted with ladder-ranked sources + provenance +
  calibrated confidence; then run `run_council` on the adoption question and assert it **no longer
  abstains** (`total_evidence ≥ 1`, confidence ≥ 0.35) — LES-019's stated close condition, exercised.

## Non-goals (explicitly deferred)

- **Live web fetching / search API (`WebResearchSource`)** — the real tier behind the `ResearchSource`
  seam. It is the first arbitrary-host egress in the system and needs a **network-policy RFC**
  (egress allowlist, per-host rate limits + timeouts, robots handling, key management, worker-service
  env wiring — none of which exist today: `docker-compose.yml:71` gives the worker no egress config or
  keys). Deferred to **slice-2**, gated on operator infra provisioning (teevee worker egress + keys).
- **Reasoned LLM synthesis of the dossier** — the `route("research", …)` real tier that writes the
  narrative summary / reconciles conflicting evidence in prose. The MVP floor synthesizes
  deterministically (template over the ranked sources). The seam is wired; the reasoned pass is the
  same deterministic-vs-real split as Distillation/Council. Deferred.
- **Continuous Research Engine** (`docs/CONTINUOUS_RESEARCH_ENGINE.md`) — ecosystem-watch / CVE /
  release-monitoring signals. A sibling engine, later; *"findings become recommendations, not
  automatic changes."*
- **Embeddings / semantic source ranking** — lexical + tier-weight floor now; embeddings behind the
  same `score_relevance` seam later (per RFC-0010).
- **A dedicated dossier frontend view** — the **Research Inbox** (AOS-RES-001, #107) already renders
  `ResearchNote` rows ranked by confidence; it will surface engine-produced notes with no UI change. A
  richer per-dossier view (source ladder, conflicting-evidence panel) is a follow-up UI package.
- **Auto-persist-and-decide / auto-approval** — advisory only; a human still approves the decision the
  evidence unblocks. No new authority.
- **Any edit to the contended council / router / pool seams** — the Research Engine **consumes**
  `route()` read-only and feeds the Council via **new `ResearchNote` data**; it never edits
  `council.py`, `llm_router.py`'s table, or `llm_pool.py` (active laptop-session surface).

## Design

- **New** `packages/aos_core/aos_core/services/research.py`:
  - `SourceDoc` (dataclass/TypedDict): `{ref, title, text, tier, tier_rank, label, published?}`.
  - `SOURCE_TIERS` — the 7-rung ladder from `docs/RESEARCH_ENGINE.md` mapped to `tier_rank`/`quality`
    weights; `"community"` carries `label="opinion"` (the spec's labeling requirement).
  - `ResearchSource` protocol: `gather(db, *, project_id, question, sensitivity, limit) ->
    list[SourceDoc]`. `LocalCorpusSource` implements it over `KnowledgePage`/`ResearchNote`/`Decision`
    (each mapped to its ladder rung: a distillation = reference-impl class, a prior decision =
    maintainer-discussion class, etc. — documented in code).
  - `score_source(question_tokens, source) -> (relevance, matched_terms)` — the calibrated
    need-coverage scorer (reused pattern from `transfer.py`; LES-023). `composite = f(relevance,
    quality)` — relevance-dominant, quality as a tie-break/boost so an official doc outranks a forum
    post at equal relevance.
  - `synthesize_dossier(question, ranked_sources) -> {summary, findings, open_questions,
    conflicting_evidence, confidence, freshness}` — deterministic template floor; calibrated
    confidence bounded to `[0,1]` from coverage × top-source quality (LES-023 discipline: intuitive,
    never near-zero for a strong match). Emits an `open_questions` finding when coverage is thin and a
    `conflicting_evidence` note when top sources disagree on labeled stance.
  - `research(db, *, project_id, question, sensitivity=Sensitivity.PUBLIC, source=None, limit=8) ->
    ResearchNote` — resolve `source` (default `LocalCorpusSource`) → `gather` → `score`/rank → drop
    zero-score → `synthesize_dossier` → construct + persist a `ResearchNote` (`sources`/`findings`
    populated, provenance-tagged) → return it. Tolerant: empty corpus / empty question → a persisted
    note with an explicit "no evidence found" open question + confidence 0 (never raises).
- **New** `apps/api/app/routes/research.py`: `POST /projects/{project_id}/research` (body
  `ResearchRequest{question, sensitivity?}`) → `enqueue_job(job_type="research", project_id,
  payload={question, sensitivity})` → returns the `JobRead` (mirrors `council.py:23`). 404 the project.
  A `GET` is unneeded — the notes surface through the existing `GET /projects/{id}/research-notes`.
- **Additive** worker branch (`apps/worker/app/worker.py`): `elif job_type == "research":` reads
  `payload["question"]`/`["sensitivity"]`, calls `research(db, ...)` with
  `make_ledger_sink(context="research")` wired into the (slice-2) provider, `mark_job("completed",
  result={"note_id": ...})`. Retry semantics inherit `MAX_ATTEMPTS=3`.
- **Schemas** (`apps/api/app/schemas.py`): `ResearchRequest` (question required, sensitivity optional
  enum). `ResearchNoteRead` already exposes `sources`/`findings` — no model/table/migration change for
  the floor (the structured `sources` entries are JSON, already accommodated).
- **Hermetic tests** (`packages/aos_core/tests/test_research.py`): (1) ranking — seed distillations of
  differing relevance/tier, assert order + matched-term provenance + calibrated confidence + tier
  labels; (2) **the LES-019 close** — seed a project, run `research`, then `run_council` on the
  adoption question and assert the verdict clears the abstention floor (was `Insufficient evidence`);
  (3) tolerance — empty corpus/question → a graceful "no evidence" note, no raise; (4) **guardrail** —
  `research(..., sensitivity=PRIVATE)` resolves a provider via `route()` that is never `FREE_HOSTED`.
  All deterministic, no network, no model.

## Alternatives considered

- **Web-first MVP (rejected).** Ship the `WebResearchSource` now for "real" research. Rejected: it is
  non-hermetic, adds the first arbitrary-host egress + a network dependency that would fire in CI, and
  needs undeclared infra (worker egress/keys/allowlist) the operator must provision first. The
  local-corpus floor ships the entire pipeline value — closing LES-019 — with zero network, and the
  web tier drops in behind the seam once the network-policy RFC lands. Same deterministic-floor-first
  discipline as RFC-0008/0009.
- **Skip the job; run synchronously like Transfer (rejected).** The floor is fast enough to run inline,
  but the mature-state web tier is slow (multi-source fetch). Designing to the mature-state target
  (roadmap operating rule) means the async job shape is permanent, not scaffolding — so build it once,
  now, mirroring `council_review`.
- **Reimplement tier selection inside the engine (rejected).** The privacy guardrail lives only in
  `route()`. Reimplementing tier logic would fork the guardrail (the exact gap the Council's
  documentation-only guarantee has today). The engine calls `route()` and inherits it in code.
- **Feed the Council by editing `council.py` selectors (rejected).** The Council is the laptop
  session's active seam and LES-019's design says feed it *data*, not new selectors. The engine
  persists `ResearchNote` rows the existing `_select_research` already reads — zero council.py churn.
- **A new `dossiers` table (rejected for MVP).** `ResearchNote` already models `sources`/`findings`/
  `confidence`/`question`. Reuse it (it is exactly what `_select_research` and the Research Inbox
  read); a first-class `Dossier` aggregate is a later enrichment if multi-note dossiers need grouping.

## Acceptance criteria

- Given a project with distilled repositories, `research(db, project_id, question)` persists a
  `ResearchNote` whose `sources` are **ranked by source-quality × relevance** with per-source ladder
  tier + label + matched-term provenance, `findings` each cite a source, and `confidence` is
  calibrated (bounded, intuitive; never near-zero for a strong match). Advisory; no auto-decision.
- **LES-019 close, exercised:** after a `research` run, `run_council` on the adoption question **no
  longer abstains** (`total_evidence ≥ 1`, aggregate confidence ≥ 0.35) — versus an abstain on the
  same question with no notes. This test is the engine's reason for existing.
- **Privacy guardrail in code:** a `PRIVATE` research call resolves its provider via `route()` and
  never selects `FREE_HOSTED` (tested).
- Deterministic + hermetic: no model, no network in tests; `DeterministicProvider`/no-provider floor;
  tolerant of empty corpus/question; the web tier is absent (seam only).
- api + worker + core green; ruff full CI scope + compileall clean; compose smoke green (new route
  mounted, no new service); **Guardian PASS**; a `LES-*` recorded for any BLOCK/CI failure.

## Dependencies

- **RFC-0005** (Agent Council — the consumer this unjams) — landed.
- **RFC-0008** (repository distillations — the local-corpus floor's primary source) — landed.
- **ADR-0001** (routed reasoned tier + privacy guardrail — `route("research", …)`) — accepted.
  The `"research"` task class already exists in `ROUTING_TABLE`.
- **LES-019** (open) — this RFC's MVP is its close condition; the lesson is updated/closed in the
  slice-1 change set.
- **Slice-2 only:** a **network-policy RFC** + operator provisioning of worker-service egress
  (allowlist, timeouts, rate limits) and free-API / search keys on teevee. The MVP floor has **no**
  such dependency.
- **Seam coordination:** consumes `route()` / `get_provider()` read-only; must not edit `council.py`,
  `llm_router.py`'s `ROUTING_TABLE`, or `llm_pool.py` (active laptop-session surface). New
  `services/research.py` + new route + additive worker branch are low-contention.

## Next steps (beyond the MVP)

1. **Slice-2 — `WebResearchSource`** behind the seam, gated on the network-policy RFC: multi-source
   fetch across the ladder, robots/rate-limit/timeout discipline, per-source freshness, key mgmt.
2. **Slice-3 — reasoned synthesis** via `route("research", …)`: LLM-written dossier summary +
   conflicting-evidence reconciliation, cited to sources, usage-metered (`context="research"`).
3. **Embeddings source ranking** behind `score_relevance` (RFC-0010 seam).
4. **Continuous Research Engine** (`docs/CONTINUOUS_RESEARCH_ENGINE.md`) — ecosystem watch feeding
   Recommendation Intelligence.
5. **A per-dossier Control Tower view** (source ladder + conflicting-evidence panel) extending the
   Research Inbox.
6. Wire research feeds into the **Technology Fitness Engine** and **Decision Intelligence** as
   `docs/RESEARCH_ENGINE.md` §Integration specifies.
