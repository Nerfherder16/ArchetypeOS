# AOS-COUNCIL-PHASEC2B — The Control Tower decision-approval view (frontend + worker-driven e2e)

## Status

In Progress

## Origin

Operator direction: "let's do 1" (Phase C Part 2), then — on the e2e-depth fork — **"Full worker-driven loop"**. Parts 2a (PR #56) and the loop (PR #55) built the whole Council → draft → approve/reject → ADR-in-vault arc on the backend. Part 2b is the last piece: **surface it in the Control Tower UI** so a human can run the loop, and prove it with a **worker-driven Playwright e2e** that drives the real enqueue → review → draft → approve → export path end to end. This finishes Phase C.

## Deterministic e2e recipe (proven before speccing)

The `DeterministicProvider` (the CI/e2e default) scales confidence with evidence, so both branches are reproducible:

- **Approvable branch:** a project whose `demo-repo` fixture has been **scanned** yields a review with verdict **"Escalate to human", confidence 0.4** (arch + fitness + security selectors get evidence) — above the 0.35 abstention floor, so `draft_decision_from_review` produces an **approvable `draft`**.
- **Blocked branch:** a project with **no scan** yields an **abstained** review (verdict "Insufficient evidence", confidence 0.0) → a `needs_evidence` draft → `approve` returns **409** (LES-019).

## Verified Baseline

- **No new backend routes.** All endpoints already exist: `GET`/`POST /projects/{id}/council-reviews` (`routes/council.py`), `POST /council-reviews/{id}/draft-decision`, `POST /decisions/{id}/approve`, `POST /decisions/{id}/reject`, `POST /decisions/{id}/adr` (`routes/decisions.py`). So `apps/api/tests/test_route_inventory.py` needs **no change**.
- `apps/web/src/api.ts`: `Decision` type currently `{id,title,decision?,confidence,evidence}` — **missing `status`/`approved_by`/`approved_at`** (the backend `DecisionRead` returns them). Has `fetchDecisions`/`createDecision`; **no council-review or approve/reject/draft/adr functions.**
- `apps/web/src/main.tsx`: a "Decisions & Research" section already renders decisions/notes/recommendations with per-section error isolation; extend it (do not rebuild it).
- `apps/web/e2e/serve-api.sh`: boots uvicorn + an ephemeral Redis on 9999, fresh sqlite per boot, `REPOSITORY_ROOT=fixtures`, `KNOWLEDGE_ROOT=<repo>/knowledge`. **Runs no worker**, so enqueued jobs never complete. The `demo-repo` fixture + scan flow already work in e2e (see `digest.spec.ts`).
- Worker entrypoint: `python -m app.worker` (`apps/worker/app/worker.py` — BLPOP loop, `main()`), uses `get_provider(settings)` → `DeterministicProvider` when no LLM provider is configured.
- `packages/aos_core/aos_core/database.py`: sqlite `connect_args={"check_same_thread": False}`, **no WAL / busy_timeout** — concurrent API+worker writers on one sqlite file risk `database is locked`.

## In-Scope Files

- **`apps/web/src/api.ts`**:
  - Extend `Decision`: add `status: string`, `approved_by?: string | null`, `approved_at?: string | null`.
  - Add `CouncilReview` type (`id, question?, verdict, confidence, provider?`) + `KnowledgePage` is already present.
  - Add: `fetchCouncilReviews(projectId)` (`GET /projects/{id}/council-reviews`), `enqueueCouncilReview(projectId, question)` (`POST /projects/{id}/council-reviews` → `Job`), `draftDecisionFromReview(reviewId)` (`POST /council-reviews/{id}/draft-decision` → `Decision`), `approveDecision(decisionId, approver, rationale?)`, `rejectDecision(decisionId, approver, rationale)` (→ `Decision`), `exportDecisionAdr(decisionId)` (`POST /decisions/{id}/adr` → `KnowledgePage`). Mirror the existing `request<T>` helper. The `request` helper must surface the API error `detail` (for inline 409 messages) — reuse existing error handling if it already does.
- **`apps/web/src/main.tsx`**: extend the Decisions section with a **Decision Loop** block:
  - **Council reviews**: an "Enqueue council review" control (question input + button), a reviews list (each: verdict + confidence, and a **Draft decision** button), and a **Refresh** button (the review is produced asynchronously by the worker).
  - **Decisions**: show a **status badge** per decision (`draft`/`needs_evidence`/`approved`/`rejected`/`active`); on `draft` show an approver input + **Approve** / **Reject**; on `needs_evidence` show **Reject** + a hint ("gather evidence and re-draft"); on `approved` show **Export ADR** + the approver; surface the API error `detail` inline per action (the abstention 409 and the read-only-vault 409 must be human-readable). Refresh decisions after each action. Per-section error isolation (an error here must not blank the page).
  - Keep existing create-decision/research-note forms intact.
- **`apps/web/e2e/serve-api.sh`**: launch `python -m app.worker` alongside uvicorn (add `apps/worker` to `PYTHONPATH`; same `DATABASE_URL`/`REDIS_URL`/env), draining the queue; add its PID to the `cleanup` trap. The worker must share the API's sqlite DB and Redis.
- **`packages/aos_core/aos_core/database.py`**: for **file-based sqlite only** (not `:memory:`), enable `PRAGMA journal_mode=WAL` + `PRAGMA busy_timeout=30000` via a SQLAlchemy `connect` event listener (and/or a `timeout` connect arg), so concurrent API+worker writers don't hit `database is locked`. Guard so `:memory:` and non-sqlite URLs are untouched; must not change existing test behavior.
- **`apps/web/e2e/decision-loop.spec.ts`** (new): drive the full loop against the real stack (worker draining the queue):
  - **Happy path:** create project → register + **scan** the `demo-repo` fixture (reuse the existing scan controls, as `digest.spec.ts` does) → enqueue a council review → **Refresh until the review appears** (retrying web-first assertions — LES-015; never one-shot `await count()`) → **Draft decision** → assert a `draft` status badge → fill approver + **Approve** → assert `approved` + the approver shown → **Export ADR** → assert success (the resulting page / vault_path surfaced).
  - **Blocked path:** a second project with **no scan** → enqueue review → Refresh until it appears → Draft decision → assert `needs_evidence` badge → **Approve** → assert the inline **409** message ("cannot be approved … gather … evidence"). (May be a second `test()` in the same file.)
  - Unique per-run entity names (`uid()`); serial-safe against the shared API/db (match `decisions.spec.ts` conventions). If new controls collide with existing locators (e.g. the Scheduling section's selects/buttons), scope locators tightly (as `decisions.spec.ts` already does).

## Out-of-Scope

- No backend/API/schema/migration change (all endpoints + fields exist; `DecisionRead` already returns `status`/`approved_by`/`approved_at`).
- No change to `test_route_inventory.py` (no new routes).
- Council dashboard as a standalone Control Tower view (AOS-COUNCIL-002) — this reuses the existing project-scoped Decisions section.
- Flipping the compose vault mount to `:rw` (2a decision, unchanged).

## Acceptance Criteria

- From the UI, a human can: enqueue a council review, draft a decision from it, approve/reject it (named approver), and export an approved decision to an ADR — with 409s (abstention-blocks-approval; read-only vault) shown as readable inline errors.
- The worker-driven e2e drives the full happy path (scan → review → draft → **approve** → export) **and** the blocked path (no scan → review → `needs_evidence` → approve → 409), deterministically, headless.
- `apps/web` strict `tsc` + `vite build` exit 0; the **full Playwright suite passes headless** (existing specs + the new one); api + worker suites unchanged and green; ruff full CI scope + compileall clean; guardian PASS. No API/schema/migration change.

## Verification (Orchestrator, independent — builder ≠ verifier)

Re-run the **full Playwright suite headless** (`PW_LOCAL_CHROMIUM`) including `decision-loop.spec.ts` — confirm the worker actually drains the queue (the review appears) and both the approve and the 409 branches assert real state; strict `tsc` + `vite build`; api/worker pytest unchanged; confirm no `apps/api`/schema/migration change and no `test_route_inventory.py` change; ruff full CI scope + compileall; guardian.
