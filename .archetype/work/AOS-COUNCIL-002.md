# AOS-COUNCIL-002 — Agent Council dashboard (Control Tower read surface)

- Status: In Progress
- Owner: laptop session (parallel Orchestrator)
- Branch: `laptop/aos-council-002-dashboard` (cut from `origin/main` @ `0624bf0`)
- Plane: AOS-COUNCIL-002 (to be reflected on the board)

## Verified Baseline (confirmed by inspection)

- The Agent Council backend is complete and its reasoning is **already returned by the API but discarded by the UI**.
  - Endpoints (`apps/api/app/routes/council.py:16-48`): `POST /projects/{id}/council-reviews` (enqueues a `council_review` job), `GET /projects/{id}/council-reviews` → `list[CouncilReviewRead]`, `GET /council-reviews/{id}` → `CouncilReviewRead`.
  - `CouncilReviewRead` (`apps/api/app/schemas.py:366-407`) carries `verdict`, `confidence`, `agreements`, `disagreements`, `unsupported_claims`, `follow_up`, `provider`, `status`, and `agent_outputs: list[CouncilAgentOutputRead]`. Each agent output has `agent_name`, `agent_type`, `status`, `summary`, `findings`, `evidence`, `concerns`, `confidence`.
  - Verdict vocabulary (`aos_core/services/council.py:42-51`): Accept / Accept with warnings / Reject / Defer / Research further / Simulate first / Escalate to human / **Insufficient evidence** (the abstention default; floors at `ABSTAIN_CONFIDENCE=0.35`, `MIN_EVIDENCE=1`). Four agents: research_librarian, architecture_cartographer, technology_fitness_judge, security_agent.
- Current UI (`apps/web/src/main.tsx:1104-1130`, inside the "Decision Loop" subsection) renders reviews as a single line `{verdict} — confidence {confidence} — {question}` and shows none of agreements/disagreements/unsupported_claims/follow_up/agent_outputs. The `api.ts` `CouncilReview` type (`apps/web/src/api.ts:104-110`) is thin (only id/question/verdict/confidence/provider), so the rich fields are dropped at the client.
- Control Tower is a single monolithic `<App/>` in `main.tsx` (no router); sections are conditionally rendered by state, each with `useState` + `useCallback` loaders (e.g. Nightly Digest, Scheduling). Existing council client fns: `fetchCouncilReviews`, `enqueueCouncilReview`, `draftDecisionFromReview` (`api.ts:279-293`).
- Web e2e is guardian-enforced. Pattern: `apps/web/e2e/decision-loop.spec.ts` drives a full worker-backed flow via `apps/web/e2e/serve-api.sh` (fresh sqlite + redis:9999 + uvicorn + worker), using retrying web-first assertions (`toPass`) to poll for async worker output.

## Design (mature-state target, this package a strict subset)

Mature-state target: a Control Tower surface that makes every governed subsystem's reasoning visible and auditable. This package delivers the Agent Council slice of that: surface the reasoning the council already produces.

- **New top-level "Agent Council" section** in `main.tsx`, project-scoped, placed after "Decisions & Research", following the existing section pattern. **Read-focused** (per approved scope): it lists reviews and expands each to full detail. Enqueue stays in the existing Decision Loop (no duplicate form; the decision-loop e2e is untouched).
- **`api.ts`:** enrich `CouncilReview` (add `agreements`, `disagreements`, `unsupported_claims`, `follow_up`, `status`, `agent_outputs`), add a `CouncilAgentOutput` type, and add `fetchCouncilReview(reviewId)` (GET `/council-reviews/{id}`) for guaranteed-full detail. Backend unchanged.
- **Render:**
  - Review list: verdict badge (color-coded; "Insufficient evidence" visually distinct, because honest abstention is a first-class outcome), confidence, question, provider.
  - Expand → **Final Judge panel** (verdict + confidence, agreements, disagreements, unsupported claims, follow-up) + **per-agent cards** (name/type, status badge, summary, findings, evidence, concerns, confidence).
  - Loading / empty / inline-error states mirroring the existing `councilError` pattern.

## In-Scope Files (exact)

- `apps/web/src/api.ts` (enrich council types + `fetchCouncilReview`)
- `apps/web/src/main.tsx` (new Agent Council section + hooks)
- `apps/web/e2e/council-dashboard.spec.ts` (new, worker-driven)
- `docs/CAPABILITY_MAP.md` (Layer 10 Interface: the Agent Council dashboard capability)
- `.archetype/work/AOS-COUNCIL-002.md` (this spec)
- `docs/ACTIVE_WORK.md` (own item) · `docs/RECENT_CHANGES.md` (own entry) — now union-safe (LES-026)

## Out-of-Scope

- Any backend / API / schema / migration change (the API already returns everything).
- The Decision Loop subsection's enqueue/draft/approve/export flow (left untouched).
- An enqueue form in the new section (read-only per the approved scope fork).
- `transfer.py` / `distillation.py` / `repository_scanner.py` / `aos_core/embeddings/` (remote session's zone).
- CURRENT_STATE "Current sprint" line + HANDOFF (remote Orchestrator reconciles).

## Acceptance Criteria (assertions, each with evidence)

1. A new project-scoped "Agent Council" section renders in the Control Tower. — evidence: `council-dashboard.spec.ts` sees the section heading.
2. The review list shows verdict, confidence, question, and provider; the abstention verdict is visually distinct. — evidence: e2e assertions on a rendered review row.
3. Expanding a review renders the Final Judge panel (agreements / disagreements / unsupported claims / follow-up) and at least one per-agent card (summary / findings / evidence / concerns / status / confidence). — evidence: e2e assertions after expand.
4. `api.ts` council types are enriched and `fetchCouncilReview(id)` added; the web typecheck/build passes. — evidence: CI "Web typecheck and build" job.
5. No backend / schema change. — evidence: `git diff --name-only` limited to the in-scope web + docs files.
6. `council-dashboard.spec.ts` passes worker-driven in CI. — evidence: CI "Web e2e (Playwright)" job green.
7. Full gate green: web typecheck/build + e2e, api/worker unaffected, guardian PASS. — evidence: CI run + guardian output in the PR body.

## Verification Plan

- Level 1 (inspection): diff is web + docs only; no backend touched; existing decision-loop UI unchanged.
- Level 2 (local): `npm run build` (tsc typecheck) in `apps/web`; careful review of the new section against the established section pattern. (Playwright e2e runs authoritatively in CI, as with the AOS-20 web fix — the serve-api harness + managed Chromium is the CI path.)
- Level 3: GitHub CI (Web typecheck/build + Web e2e + the rest) green on the head SHA → Manual Merge Gate.

## Board Linkage

- Plane AOS-COUNCIL-002 → In Progress → Done on merge. No lesson expected unless a defect surfaces.
