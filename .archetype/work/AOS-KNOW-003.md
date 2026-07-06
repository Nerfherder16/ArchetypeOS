# AOS-KNOW-003 — Knowledge dashboard: Control Tower Knowledge view + compose vault mount (closes AOS-23)

## Status

In Progress

## Origin

Plane **AOS-23** dashboard phase (23b) — the deferred half of the knowledge read path. AOS-KNOW-002 (PR #51) shipped the backend (sync + read API + digest rule); this adds the **operator-facing Knowledge view** and makes `POST /knowledge/sync` work in the shipped compose stack (a `./knowledge:ro` mount). **Merging this closes AOS-23.** Operator-directed sequence: "2 then 1" — this (finish the knowledge dashboard) before AOS-21 (second repo). Frontend + compose only; no new API, no schema, no migration.

## Verified Baseline

Confirmed by inspection:

- **Backend (AOS-KNOW-002, merged):** global routes `POST /knowledge/sync` (runs `sync_knowledge(db, settings.knowledge_root)`, returns `{synced, created, updated, open_lessons}`), `GET /knowledge/pages?page_type=&validation_state=` (desc `updated_at`, cap 100), `GET /knowledge/pages/{id}`. `KnowledgePage`: id, project_id (nullable), title, vault_path, page_type, validation_state, source_refs, checksum, created_at, updated_at. Lessons are `page_type="lesson"`, `validation_state` in `{open, closed}` (LES-007 the sole open). `settings.knowledge_root` default `./knowledge`.
- **Web** (`apps/web/src`, AOS-WEB-001 has guardian-enforced Playwright): `main.tsx` is a single non-routed `App()` with vertical `<section style={sectionStyle}>` blocks. **Runtime Health (`main.tsx:533`) is a GLOBAL, non-project-scoped section** — the template for Knowledge (lessons have no project). Project-scoped sections gate on `selectedProjectId`; Knowledge must NOT. `api.ts`: typed models + fetch fns over `API_BASE_URL`; `fetchHealth()` is the global-fetch precedent, `fetchDigests(projectId)`/`fetchDecisions` the list precedent.
- **e2e** (`apps/web/e2e`): Playwright `*.spec.ts` (`uid()` helper; drive by role/placeholder; assert headings + body; reload to prove persistence). `serve-api.sh` boots a throwaway API: it exports PYTHONPATH/DATABASE_URL/ARTIFACT_ROOT/REPOSITORY_ROOT/REDIS_URL, then **`cd "${SCRATCH_DIR}"`** before `uvicorn`. Because of that `cd`, `knowledge_root="./knowledge"` would resolve to the scratch dir (no vault) — **serve-api.sh MUST export `KNOWLEDGE_ROOT="${REPO_ROOT}/knowledge"`** (abs) so sync finds the real vault. `REPO_ROOT` is already computed in the script.
- **compose**: the `api` service has `volumes: [archetype_data:/data, ${HOST_REPOSITORY_ROOT:-./repositories}:/repositories:ro]` and an `environment:` block. No knowledge mount yet, so `POST /knowledge/sync` in the container has no vault. compose-smoke ups `api` (so a new mount/env is exercised at boot; LES-011 family — a bind mount is not a new service, but keep it in the api service compose-smoke already builds/ups).

## In-Scope Files

- `docker-compose.yml` (api service: add `${HOST_KNOWLEDGE_ROOT:-./knowledge}:/knowledge:ro` volume + `KNOWLEDGE_ROOT: ${KNOWLEDGE_ROOT:-/knowledge}` env)
- `apps/web/src/api.ts` (types `KnowledgePage`, `KnowledgeSyncResult`; `fetchKnowledgePages(params?)`, `syncKnowledge()`)
- `apps/web/src/main.tsx` (a global "Knowledge" section)
- `apps/web/e2e/knowledge.spec.ts` (new), `apps/web/e2e/serve-api.sh` (export `KNOWLEDGE_ROOT`)
- `docs/CAPABILITY_MAP.md`, state docs + this spec

## Out-of-Scope

- Any backend/API/schema/migration change (KNOW-002 shipped it). Ingesting non-lesson vault domains. Per-page detail drill-down beyond what the list shows. Auth. The council/other dashboards. No `ci.yml` change (web-e2e + compose-smoke already run; serve-api.sh is the e2e harness, not CI config).

## Design

- **compose**: api service gains a read-only vault mount `- ${HOST_KNOWLEDGE_ROOT:-./knowledge}:/knowledge:ro` and `KNOWLEDGE_ROOT: ${KNOWLEDGE_ROOT:-/knowledge}`. Now `POST /knowledge/sync` reads `/knowledge` in the container. Mirrors the existing `repositories` mount pattern exactly.
- **api.ts**: `KnowledgePage` type (fields above; `project_id: string | null`); `KnowledgeSyncResult` (`synced/created/updated/open_lessons: number`); `fetchKnowledgePages(params?: { page_type?: string; validation_state?: string })` → `GET /knowledge/pages` with query string; `syncKnowledge()` → `POST /knowledge/sync`. Use the existing request helper / fetch conventions.
- **main.tsx — a GLOBAL "Knowledge" section** (renders unconditionally, like Runtime Health; NOT gated on `selectedProjectId`): a heading, a **"Sync from vault"** button (calls `syncKnowledge()` then reloads the list; shows the returned counts e.g. "synced 12 · 1 open"), a **list of pages** (title, `page_type`, `validation_state`) with **open lessons visually emphasized** (e.g. an "open" badge), a lightweight filter (All / Open) that refetches with `validation_state`, and per-section error isolation (its own error state, never crashes the page). Place it as its own global section (suggest after Runtime Health, grouping the two global surfaces, or just before the v0.1 Placeholders — builder's call, but it must render with no project selected). Follow `sectionStyle` + the health/digest rendering idioms.
- **serve-api.sh**: add `export KNOWLEDGE_ROOT="${REPO_ROOT}/knowledge"` alongside the other exports (before the `cd`), so the e2e sync finds the committed vault.

## Acceptance Criteria

- **Compose sync works in-container** — evidence: `docker-compose.yml` api service has the `:/knowledge:ro` mount + `KNOWLEDGE_ROOT`; compose config valid; compose-smoke boots api with the mount (green).
- **Knowledge view renders globally** — evidence: `knowledge.spec.ts` loads the dashboard with **no project selected** and sees the "Knowledge" heading + Sync control.
- **Sync populates + lists lessons** — evidence: the spec clicks "Sync from vault", then asserts lesson rows appear (≥ the known lessons) and that the doc-staleness lesson (LES-007) shows as **open** (badge/state); a reload still shows them (persistence).
- **Open filter works** — evidence: the spec toggles All → Open and sees the open lesson remain while closed ones drop (or asserts the open-only list length).
- **Type/build safety** — evidence: strict `tsc` + `vite build` exit 0.
- **Nothing broken** — evidence: full Playwright suite green headless (existing specs + the new one); api/worker suites unaffected (no backend change).

## Verification Plan

Level 4 (Orchestrator): run the **full Playwright suite headless** in-container (`PW_LOCAL_CHROMIUM=/opt/pw-browsers/chromium npm run test:e2e`) incl. the new `knowledge.spec.ts` (sync → lessons visible → LES-007 open → reload); strict `tsc` + `vite build`; `docker compose config` valid + confirm the api mount. Level 3: CI web-e2e (Playwright on ubuntu) + compose-smoke (api boots with the vault mount). Merge under the Manual Merge Gate; **on merge AOS-23 → Done**.

## Learning / Feedback Loop

Record a lesson only on a guardian BLOCK / CI failure / self-found defect. Watch the LES-012 family: run the FULL CI-scope checks locally (web build + the whole Playwright suite headless), not a subset. The serve-api.sh `KNOWLEDGE_ROOT` export is the load-bearing detail — if the e2e can't see lessons, check it first.

## Suggested Delegation

Runtime/Frontend Agent (Opus): compose mount + api.ts + main.tsx Knowledge section + serve-api.sh export + knowledge.spec.ts. Orchestrator (Opus 4.8): this spec; independent full-suite headless Playwright re-run + compose config check; guardian; PR; Manual Merge Gate; on merge close AOS-23.

## Board Linkage

- Plane: **AOS-23** (In Progress — this is the dashboard phase; **merging closes it**). Then AOS-21 (second repo) per the operator sequence, then a definitive-roadmap review.
- Branch: `claude/aos-runtime-002-scanner-1egyjw` (env-pinned). Implements RFC-0002 (read surface, UI).
