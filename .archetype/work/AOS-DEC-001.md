# AOS-DEC-001 — Decision and Research Artifacts (Phase 5 CRUD + View)

## Status

Merged (PR #34, merge commit `fe158fd`)

## Verified Baseline

Confirmed by inspection:

- `Decision`, `ResearchNote`, and `Recommendation` models already exist in `apps/api/app/models.py` with rich fields (alternatives/tradeoffs/consequences/evidence/confidence; question/summary/sources/findings/freshness; recommendation/rationale/pros/cons/risk/effort/dependencies/acceptance_criteria/evidence). No API routes or schemas exist for any of them; the dashboard has no decisions/research section.
- v0.1 scope-lock acceptance criteria not yet met: "Decision/research artifacts can be created and viewed", "Research can be linked to decisions", "Recommendations require evidence field".
- `ResearchNote` has no decision foreign key and `Decision` has no research link column; adding columns is out of scope (no migrations exist — `create_all` will not ALTER existing Postgres tables). Linkage therefore uses the existing `Decision.evidence` JSON list with typed entries.

## In-Scope Files

- `apps/api/app/main.py` (nine routes: create/list/read for decisions, research notes, recommendations)
- `apps/api/app/schemas.py` (create/read schemas for the three artifacts)
- `apps/api/tests/test_decisions_api.py` (new)
- `apps/web/src/api.ts`, `apps/web/src/main.tsx` (minimal Decisions & Research section)
- state docs + this spec

## Out-of-Scope

- model/schema (table) changes or migrations
- update/delete routes, approval workflow (`approved_by` stays API-untouched)
- ADR file generation, knowledge-vault writing
- complex UI (no editing, no detail pages; lists + small create forms only)

## Design

- Routes mirror the existing project/repository conventions (404 "Project not found" guards, `created_at` desc ordering):
  - `POST/GET /projects/{project_id}/decisions`, `GET /decisions/{decision_id}`
  - `POST/GET /projects/{project_id}/research-notes`, `GET /research-notes/{note_id}`
  - `POST/GET /projects/{project_id}/recommendations`, `GET /recommendations/{recommendation_id}`
- Scope-lock rules enforced at the API:
  - `RecommendationCreate.evidence` must be a non-empty list (422 otherwise) — "Recommendations require evidence field".
  - `DecisionCreate.research_note_ids: list[str] = []` — each id must reference an existing research note in the same project (404 otherwise); stored into `Decision.evidence` as `{"type": "research_note", "id": <id>}` entries alongside any free-form evidence — "Research can be linked to decisions" without a schema change.
- Dashboard: one "Decisions & Research" section for the selected project — decisions list (title, confidence, linked-research count), research notes list (title, freshness), recommendations list (title, evidence count), plus two minimal create forms (decision: title + decision text + optional research-note select; research note: title + summary). Per-section error isolation as established.

## Acceptance Criteria

- Decisions, research notes, and recommendations can be created and listed/read via API — evidence: `test_decision_crud`, `test_research_note_crud`, `test_recommendation_crud`.
- Recommendations without evidence are rejected — evidence: `test_recommendation_requires_evidence` (422).
- Research links to decisions are validated and stored as typed evidence entries — evidence: `test_decision_research_link` (valid id → evidence entry present; unknown id → 404; cross-project id → 404).
- Unknown project → 404 on all creates/lists — evidence: `test_artifacts_404s`.
- Dashboard shows and creates decisions/research for the selected project — evidence: Orchestrator headless-Chromium drive (create decision via form → appears in list; research note likewise; reload persistence).
- Build/type safety — evidence: strict tsc + vite build exit 0; full API suite green.

## Verification Plan

Level 2: ruff/compileall/pytest (40 existing + new). Level 4 (local): headless-Chromium drive of the new section against live uvicorn+SQLite. Level 3: GitHub CI (guardian now runs scanner-informed checks live); merge under the Manual Merge Gate.

## Suggested Delegation

Runtime Agent (Opus): API + web + tests. Orchestrator (Fable): spec, review, browser verification, PR, merge gate.

## Board Linkage

- Plane: AOS-10 (In Progress), Sprint 3 cycle `9d9c2fd6-3305-419a-a5e8-0c6d4d3c058b`
- Branch: `claude/aos-runtime-002-scanner-1egyjw`
