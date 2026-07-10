## Layer 1: Knowledge and Memory

Owns durable knowledge.

Capabilities:

- Engineering Memory
- Knowledge Graph
- Knowledge Distillation Engine (repository **content extraction** — RFC-0008 MVP **shipped** (AOS-DISTILL-001): `distill_repository` reads a scanned repo's actual README, a deterministic LLM-free extractor derives provenance-tagged `title`/`summary`/`key_points`/`technologies`/`useful_for`, writes `wiki/repositories/<slug>.md` + a re-syncable `KnowledgePage` (`page_type="repository"`, `validation_state="derived"`), and stamps `RepositoryDNA.purpose`; `sync_knowledge` re-derives the page so a DB reset loses nothing, and a council selector surfaces it as research evidence. Motivated by the `free-llm-api-resources` reality test where a structural fingerprint yielded an abstention. **RFC-0008 Phase 2 shipped (AOS-DISTILL-002): distillation now reads bounded, provenance-tagged source, not just the README.** `select_source_files` picks entry points + the largest source-classified files + the primary manifest (capped by file count and total bytes; tolerant of unreadable/binary/absent source). Two code-derived layers mirror the council's deterministic/real-provider split: a **deterministic structural summary** (`summarize_sources`, pure stdlib `ast`+regex — always emitted as `## Components (from source)`, each component citing its file) and, only on an authed node with a real (LES-021-isolated) provider, a **reasoned narrative** (`reason_over_source` → `## How it works / Built for`, citing files; the deterministic provider fabricates nothing, so CI stays hermetic). **Distillation evidence hardening shipped (AOS-DISTILL-003): the deterministic summary floor now emits a cleaned summary — it drops noise-only lines (badge/image-link runs, bare links, HTML comments, headings) and prefers the first declarative description sentence (`<Name> is/are/provides/… a …`, subject matching the distilled title/repo name), else the first clean prose paragraph, and NEVER emits badge/link-only markup (honest fallback instead). This replaces the old `_first_paragraph` floor that stamped raw badge markdown / analogy intros into `RepositoryDNA.purpose` and starved the Transfer Engine (the first end-to-end reality test: kubernetes missed on "container orchestration", gin ranked 3rd on "HTTP routing", pydantic-ai false-matched `web` via a FastAPI analogy — LES-022). The scanner also now detects `frameworks` from manifest bodies and `run_scan` stamps `RepositoryDNA.frameworks`, so the Transfer Engine's technology-match boost is live. Regression gate: `scripts/reality_test_distillation.py` (manual — needs the cloned portfolio).** **Reasoned `DNA.purpose` tier shipped (AOS-DISTILL-004): `DNA.purpose` is now two-tier — a real (LES-021-isolated, non-deterministic) provider reasons a concise one-sentence purpose (what the repo is + what it is useful for) from README + bounded source via `reason_purpose`, and when non-empty it becomes the page summary + `DNA.purpose` (single source of truth) with the page marked `validation_state="reasoned"`; otherwise — the deterministic CI provider, or empty/garbled reasoned output — the Package-1 clean deterministic floor summary is kept and the page stays `validation_state="derived"` (fully hermetic, no live model, no fabrication). The real-provider branch is gated on `getattr(provider, "name", "") != "deterministic"` and unit-tested hermetically with a fake non-deterministic provider stub; the reality-test harness adds an opt-in `--provider claude_code` mode (default stays deterministic) for the live quality check.** Non-goals still open: the Knowledge Transfer Engine (relevance-to-a-target), embeddings/semantic index, and web tools.)
- Obsidian integration
- Graphify-style ingestion
- documentation lifecycle
- repository knowledge standard
- knowledge packs
- Knowledge read path (AOS-KNOW-002: vault lessons synced to `KnowledgePage`, a DB read projection with a global read API; open lessons surface in the digest)
- Knowledge dashboard (AOS-KNOW-003: the global Control Tower Knowledge view — Sync-from-vault, lesson list with open-lesson emphasis, All/Open filter; compose `./knowledge:ro` vault mount so in-container sync works)
- Decision ADR projection (AOS-COUNCIL-PHASEC2A: approved decisions export to an ADR under `knowledge/wiki/decisions/` and project as re-syncable `KnowledgePage` `page_type="decision"`; `sync_knowledge` re-derives decision pages from the vault so a DB reset loses nothing)
- External repository evaluation register — "keep pile" (AOS-59..72; evaluated so far: claude-obsidian, claude-video, T3MP3ST, notebooklm-py, memtrace-public, obsidian-skills, impeccable. `knowledge/wiki/repositories/index.md` + one page per externally-evaluated repo records verdict, borrow candidates, and links to the full teardown in `docs/repo-research/<repo>.md` and the Plane "External Repo Evaluation & Adoption Pipeline" tracking item. Distinct from the Distillation Engine — that extracts content from *onboarded* repos, this records *evaluation judgment* on candidate repos — but they share the `wiki/repositories/` directory, so `sync_knowledge` derives register entries as `page_type="repository"` too. Verdict vocabulary: adopt / partial-borrow / reject / monitor.)

Primary artifacts:

- docs/ENGINEERING_MEMORY.md
- docs/KNOWLEDGE_GRAPH.md
- docs/KNOWLEDGE_DISTILLATION_ENGINE.md
- docs/rfc/RFC-0008-Knowledge-Distillation-Engine-Repository-Content-Extraction.md (MVP landed — AOS-DISTILL-001: content-extraction MVP + the "tools upstream, not in judges" decision; LES-021 prerequisite)
- packages/aos_core/aos_core/services/distillation.py (AOS-DISTILL-001: `extract_repo_knowledge` deterministic extractor + `render_repository_markdown` + `distill_repository` local-first vault write → re-syncable `KnowledgePage`); apps/api/app/routes/repositories.py (POST /repositories/{id}/distill)
- docs/KARPATHY_OBSIDIAN_REVIEW.md
- docs/OBSIDIAN_GRAPHIFY_INTEGRATION.md
- docs/DOCUMENTATION_LIFECYCLE_ENGINE.md
- docs/REPOSITORY_KNOWLEDGE_STANDARD.md
- packages/aos_core/aos_core/services/knowledge.py (parse_lessons_index + sync_knowledge; vault → KnowledgePage upsert, repo stays source of truth)
- apps/api/app/routes/knowledge.py (POST /knowledge/sync, GET /knowledge/pages, GET /knowledge/pages/{id})
- knowledge/wiki/repositories/index.md (external repo evaluation register / keep pile) + docs/repo-research/<repo>.md (full teardowns) + docs/PLANE_PROJECT_BLUEPRINT.md (Board ID Registry: External Repo Evaluation & Adoption Pipeline module, AOS-59..62)
- apps/web/src/main.tsx (global "Knowledge" Control Tower section: sync + lesson list + open badge + All/Open filter) with apps/web/e2e/knowledge.spec.ts; docker-compose.yml api service `${HOST_KNOWLEDGE_ROOT:-./knowledge}:/knowledge:ro` mount + `KNOWLEDGE_ROOT`

