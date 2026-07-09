# Capability Map

## Purpose

The Capability Map defines how ArchetypeOS capabilities fit together.

It prevents the platform from becoming a collection of unrelated ideas. Every engine, agent, dashboard, workflow, and runtime component should map to a coherent capability layer.

## North Star

ArchetypeOS is an Engineering Intelligence Platform that helps users:

```text
Research -> Model -> Decide -> Build -> Verify -> Validate -> Learn -> Evolve
```

## Capability Layers

```text
Layer 0: Constitution and Governance
Layer 1: Knowledge and Memory
Layer 2: Research and Evidence
Layer 3: Architecture and Modeling
Layer 4: Decision and Recommendation
Layer 5: Design and User Experience
Layer 6: Build and Execution
Layer 7: Validation and Release Gates
Layer 8: Self Learning and Evolution
Layer 9: Portfolio and Organizational Intelligence
Layer 10: Interface and Interaction
Layer 11: Runtime and Infrastructure
Layer 12: Orchestration and Work Management
```

## Layer 0: Constitution and Governance

Owns the rules of the system.

Capabilities:

- Engineering Constitution
- RFC process
- Arbiter and Final Judge rules
- decision lifecycle
- human approval model
- authority action policy (AOS-AUTHORITY-001: enforced action-class policy — no write/destructive path bypasses `requires_approval`)
- safety model
- agent contract
- agent hierarchy
- external review triage

Primary artifacts:

- docs/ENGINEERING_CONSTITUTION.md
- docs/CONSTITUTION_AMENDMENTS.md
- docs/RFC_PROCESS.md
- docs/ARBITER_FINAL_JUDGE.md
- docs/DECISION_LIFECYCLE.md
- docs/AUTHORITY_POLICY.md (AOS-AUTHORITY-001: action classes + central requires_approval evaluator; GET /authority/action-classes, POST /authority/evaluate, GET /authority/pending)
- docs/AGENT_HIERARCHY_AND_COMMUNICATION.md
- docs/EXTERNAL_REVIEW_TRIAGE_2026_07_04.md
- agents/UNIVERSAL_AGENT_CONTRACT.md
- knowledge/wiki/reviews/2026-07-08-archetypeos-system-evaluation.md (AOS-REVIEW-001 system evaluation)
- docs/CONSOLIDATION_PLAN.md (AOS-REVIEW-001 phased execution plan / consolidation roadmap)

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

## Layer 2: Research and Evidence

Owns fact gathering and source quality.

Capabilities:

- Research Engine
- Continuous Research Engine
- Research Librarian
- Repository Intelligence Engine
- source ranking
- research notes
- research freshness

Primary artifacts:

- docs/RESEARCH_ENGINE.md
- docs/REPOSITORY_INTELLIGENCE_ENGINE.md
- docs/CONTINUOUS_RESEARCH_ENGINE.md
- docs/REPOSITORY_SCANNER.md
- templates/research_note.md
- agents/research_librarian/CLAUDE.md

## Layer 3: Architecture and Modeling

Owns system structure.

Capabilities:

- Architecture Studio
- Architecture Spine Graph (AOS-ARCH-SEMANTICS-001: beyond directory `contains` edges, the scanner now parses detected Docker Compose files into `service` nodes and `depends_on` edges — both the list form `depends_on: [db, redis]` and the map form `depends_on: {db: {condition: ...}}` — persisted through the generic node/edge path and surfaced in `RepositoryDNA.runtime_services`; parsing is tolerant, so a missing/malformed/non-mapping compose adds a note and never raises. LES-014 compose/service half. **The manifest/dependency half shipped (AOS-ARCH-EDGES-001):** the scanner wires the dormant `_LOCAL_DEP_PARSERS` — `requirements.txt` `-e ./`, `pyproject.toml` poetry/uv `path=`, `package.json` `file:`/`link:`, `go.mod` `replace => ./` — into top-level-granularity `depends_on` edges resolved relative to each manifest's dir, deduped/bounded (`MAX_LOCAL_DEP_EDGES`)/tolerant, with manifest-provenance evidence. Source `import`-graph edges remain a separate follow-up)
- Framework detection from manifest bodies (AOS-DISTILL-003: a deliberate, bounded extension of the "reads no bodies except compose" rule — the scanner now reads the BODIES of detected `package.json` (deps/devDeps), `requirements.txt`, `pyproject.toml` (PEP 621 + poetry dependencies), and `go.mod` (module + requires), byte-capped and tolerant (try/except → skip), and maps a small CURATED table of well-known frameworks — fastapi/flask/django/starlette/pydantic/pydantic-ai/langchain, express/react/next/vue/angular/svelte/nest, gin/echo/fiber/…, and a few more — to normalized names in a new sorted, deduped `frameworks: list[str]` scan key; conservative (only high-confidence curated matches; unknown deps ignored). `run_scan` stamps `RepositoryDNA.frameworks`, feeding the Transfer Engine's technology-match boost. Partially addresses LES-016 (manifest-body deps for python/node/go frameworks); the dotnet/jvm/cargo **ecosystem breadth** is now closed by AOS-SCAN-PRECISION-001 — JVM basenames (`pom.xml`/`build.gradle`/`build.gradle.kts` → `jvm`/maven+gradle), .NET suffix manifests (`.csproj`/`.sln` → `dotnet`), and `dotnet`/`jvm` added to `ECOSYSTEM_KINDS` (rust `Cargo.toml` was already covered). AOS-SCAN-PRECISION-001 also made `SECRET_LIKE_FILENAME` test-fixture-aware (downgrades to `info`, out of `risk_flags`, under `testdata`/`tests`/`fixtures`/… — LES-017))
- Engineering Digital Twin
- Portfolio Architecture
- repository maps
- trust boundaries
- data flow
- Engineering OS strategy
- Source-classified language weighting (AOS-ARCH-SEMANTICS-001: the scan summary derives a `primary_language` from the top **source**-classified language via `LANGUAGE_CLASS` (source/config/markup/data/docs) and ranks `primary_language_hints` source-first, so config/docs-heavy repos are no longer misreported as YAML/Markdown-primary; raw `language_mix` counts retained — LES-013)

Primary artifacts:

- docs/ARCHITECTURE_STUDIO.md
- docs/ENGINEERING_DIGITAL_TWIN.md
- docs/PORTFOLIO_ARCHITECTURE.md
- docs/ENGINEERING_OS_STRATEGY.md
- docs/REPOSITORY_SCANNER.md (compose-derived `service`/`depends_on` edges + source-classified language weighting — AOS-ARCH-SEMANTICS-001)
- agents/architecture_cartographer/CLAUDE.md
- packages/aos_core/aos_core/repository_scanner.py (compose parse → service/depends_on edges; `LANGUAGE_CLASS` → `primary_language`/`language_classes`)

## Layer 4: Decision and Recommendation

Owns engineering choices.

Capabilities:

- Decision Intelligence
- Recommendation Intelligence
- Technology Fitness Engine
- Strategy Engine
- Portfolio Knowledge Marketplace
- Knowledge Transfer Engine (RFC-0009 MVP **shipped** (AOS-TRANSFER-001): `recommend_reuse(db, *, need, exclude_project_id=None, limit=5)` retrieves the portfolio's distilled repositories relevant to a free-text **target need** and returns ranked, provenance-tagged reuse recommendations. Deterministic lexical relevance (hermetic, no model/network): tokenizes the need + each candidate's `KnowledgePage.title` + `RepositoryDNA.purpose`, scores by **need coverage** (AOS-TRANSFER-002: the fraction of the need's meaningful terms the candidate covers via its text or its technologies — `|(need ∩ cand) ∪ (need ∩ tech)| / |need|` — a bounded, intuitive score; tie-break on technology-match count then name) over the DNA's `language_mix`/`package_managers`/`frameworks`; drops zero-score matches and the target project's own repos; each recommendation carries source repository / reusable asset / matched-term reason / evidence (the source distillation's `vault_path` + repo id) / heuristic required-changes + risks / confidence = the coverage score. Advisory + compute-and-return (no new table/migration; a human promotes a chosen one into the `Recommendation`/`Decision` loop). Exposed as `POST /projects/{project_id}/transfer`. Calibration replaced the original Jaccard, which the reality test showed collapsed magnitudes to near-zero even for the correct #1 (LES-023); confidences are now meaningful (kubernetes "container orchestration" 0.333, gin "HTTP routing" 0.800) with rankings intact/sharpened. A provider-reasoned adaptation plan is deferred behind the `score_relevance` seam. **Embedding Relevance Tier Part 1 shipped (RFC-0010 / AOS-EMBED-001): the vector-store + semantic-retrieval infra, fully hermetic and CI-gated, with NO torch.** An `EmbeddingProvider` seam (`aos_core/embeddings/`, mirroring the `llm/` provider seam) resolves `settings.embedding_provider` (default `deterministic`); the only Part-1 backend is `DeterministicEmbedder` (`embed()→None` → lexical fallback, no model, no network). `KnowledgePage` gains a nullable dialect-variant `embedding` column — a real pgvector `Vector(384)` on postgresql, degrading to a benign JSON column on sqlite so `Base.metadata.create_all` (every hermetic test) stays clean and emits no `VECTOR` DDL. Migration `0005` adds the `vector` extension + `embedding vector(384)` + an ivfflat cosine index (Postgres-path, no-op on other dialects); the compose stack moves to `pgvector/pgvector:pg16`. `recommend_reuse` gains a semantic path taken ONLY when the embedder returns a non-None `need` vector AND the dialect is `postgresql`: it orders candidates by `embedding <=> need_vec` and reports a **calibrated** coverage-like confidence — `max(coverage, 0.6·(1−cosine_distance) + 0.4·coverage)`, floored at lexical coverage, never a raw cosine (LES-023) — keeping the lexical `matched_terms` as provenance; otherwise it is byte-identical to today's lexical Layer-0. `distill_repository` embeds title+purpose when a real embedder is injected (deterministic → NULL → unchanged/hermetic). The pgvector SQL/ordering/calibration path is CI-gated via synthetic vectors + a fake embedder on a `pgvector/pgvector:pg16` service (`pytest -m pgvector`), with NO torch in the install. **Embedding Relevance Tier Part 2 shipped (RFC-0010 / AOS-EMBED-002): the real embedder now fills the seam — `FastEmbedEmbedder` (`aos_core/embeddings/_fastembed.py`) runs `all-MiniLM-L6-v2` (384-dim, drop-in for the pgvector column) via `fastembed` (ONNX runtime), NOT torch/sentence-transformers — ~50 MB vs GBs, same model/dim/quality (operator-approved 2026-07-06, torch explicitly rejected for footprint).** `get_embedder("fastembed")` resolves it behind a **lazy** import (fastembed/onnxruntime/torch are absent from `sys.modules` after `import aos_core.embeddings` — asserted by a unit test); `embed(text)` returns an L2-normalized 384-length `list[float]` (unit vector, clean cosine for `vector_cosine_ops`), `None` on empty/whitespace or a per-call embed failure (one bad input never breaks distillation), and raises an actionable error on a load/import failure (a node set to the real tier without fastembed installed is a misconfiguration, not a silent degrade); the loaded model is a module-level singleton (loaded once). fastembed is an **extras** dependency (`apps/api|worker/requirements-embeddings.txt`, pinned — NOT in `requirements.txt`), so the unit CI jobs and the **deterministic default stay genuinely dependency-free**; the Dockerfiles install it unconditionally (light) with an optional `PREDOWNLOAD_EMBEDDING_MODEL` build arg (default `false`, so compose-smoke stays fast) to bake the model in for offline nodes; `docker-compose.yml` keeps `EMBEDDING_PROVIDER` default `deterministic` and documents enabling `fastembed` on api+worker. fastembed being light **enables a real (non-mocked) embedder CI gate** — the new "Embedder tests" job installs the extras (NO torch) and runs `pytest -m embedder`: a real 384-length unit vector + paraphrases closer than unrelated text. The embedding tier is now complete: real fastembed (ONNX) embedder behind the seam, deterministic default keeping CI/light nodes dependency-free, pgvector storage from Part 1.)
- Agent Council (backend seed: four MVP agents produce structured, persisted, evidence-bearing outputs; validated on real external code — first live run over pydantic-ai correctly abstained)
- Final Judge synthesis (deterministic, rule-based verdict + abstention over agent outputs)
- Decision loop (AOS-COUNCIL-PHASEC: a `CouncilReview` drafts a governed `Decision` linked back to the review as evidence; a named human approves/rejects it with an `ApprovalRecord` audit trail; an abstained-review draft is `needs_evidence` and cannot be approved until re-drafted — LES-019 operationalized; pending drafts surface in the digest)
- Decision → Knowledge ADR export (AOS-COUNCIL-PHASEC2A: an approved `Decision` renders into a repo-vault ADR under `knowledge/wiki/decisions/` and projects as a re-syncable `KnowledgePage`; a separate explicit approved-only step — local-first write, `409` (not `500`) on a `:ro` vault, never mutating approval state; `POST /decisions/{decision_id}/adr`)
- LLM provider abstraction (swappable reasoning backend; deterministic default + Claude Code subscription backend; parse seam hardened for live-model Markdown-fenced JSON — LES-018; **`ClaudeCodeProvider` context-isolated — LES-021**: `claude -p` runs in a fresh empty cwd with `--disallowedTools` + `--strict-mcp-config`, so an agent reasons only from the supplied evidence, not the host repo's `CLAUDE.md`/files. **`OpenAICompatibleProvider` — AOS-LLM-LOCAL-001**: one config-driven adapter for any OpenAI-compatible `/chat/completions` covering both a **local** model (Ollama/vLLM on the node — teevee's RTX 3070 at `localhost:11434/v1`) and a **free hosted API** (Groq/Cerebras/OpenRouter from the `free-llm-api-resources` catalog), selected by `LLM_BASE_URL`/`LLM_MODEL`/`LLM_API_KEY`; stdlib `urllib` (no new dep), deterministic stays the CI default so the suite stays hermetic, isolation inherent (HTTP sends only system+prompt). Runs the reasoned tiers off Claude to save subscription tokens; runbook `docs/runbooks/llm-provider.md`)
- **Routed reasoned tier — ADR-0001** (`docs/adr/ADR-0001-routed-reasoned-tier.md`): the reasoned tier is a 4-tier routed pool — deterministic (CI floor) / local 7B (teevee 3070, private) / free hosted (Gemini/Groq/Cerebras/DeepSeek, non-private only) / Claude (highest-stakes + Final Judge). Privacy tiering is a hard guardrail (private code never leaves for a free tier); routing is eval-driven (`AOS-LLM-EVAL-001`, planned). Opportunity map: `docs/reviews/2026-07-07-local-and-free-llm-opportunity-map.md`.
- **Multi-model Council — AOS-LLM-EVAL-001** (RFC-0005): the reasoned tier's router (`services/llm_router.py`, privacy guardrail: private input never reaches a free tier) + a free-API **rotation pool** (`services/llm_pool.py`, 429-fallback across Groq/Cerebras/Gemini/Mistral) let the Agent Council run **each agent on a different free frontier model** (`council_provider` + `run_council` records `agent_model` per agent; opt-in `council_multi_model`), Claude reserved for Final Judge. Genuine model diversity at ~zero cost. Demo: `tools/council_multimodel.py`; ADR-0001.
- **Local code reviewer — AOS-LLM-REVIEW-001** (Tier-1, `packages/aos_core/aos_core/services/code_review.py` + `tools/pr_reviewer.py`): advisory per-category ("pointwise") review of a unified diff on the on-node `qwen2.5-coder-reviewer` model, **layered on the deterministic PR Guardian, never a merge gate, fail-open**. Validated on teevee's 3070: `num_ctx` fix (Ollama's 4096 default truncated large diffs) + structured JSON + rubric gave high precision; per-category passes tripled recall (1/3 → 3/3 on a planted-bug diff). Eval harness `scripts/eval/review_spike.py` (log `.archetype/eval/`).

Primary artifacts:

- docs/TECHNOLOGY_FITNESS_ENGINE.md
- docs/STRATEGY_ENGINE.md
- docs/KNOWLEDGE_TRANSFER_ENGINE.md
- docs/PORTFOLIO_KNOWLEDGE_MARKETPLACE.md
- templates/decision_card.md
- templates/recommendation_card.md
- templates/adr.md
- docs/rfc/RFC-0005-Intelligence-Layer-Agent-Council-Final-Judge.md
- docs/COUNCIL_REALRUN_PYDANTIC_AI.md (first real Council run — reality test + honest gaps)
- docs/LLM_PROVIDER_ABSTRACTION.md
- docs/ARBITER_FINAL_JUDGE.md (verdict set + abstention rule the Final Judge encodes)
- packages/aos_core/aos_core/llm/ (Provider protocol + DeterministicProvider + ClaudeCodeProvider + OpenAICompatibleProvider); docs/runbooks/llm-provider.md
- packages/aos_core/aos_core/services/code_review.py + tools/pr_reviewer.py (AOS-LLM-REVIEW-001 local reviewer tier); docs/adr/ADR-0001-routed-reasoned-tier.md; docs/reviews/2026-07-07-local-and-free-llm-opportunity-map.md
- packages/aos_core/aos_core/services/council.py (run_council + synthesize_verdict; the four agent personas)
- packages/aos_core/aos_core/services/decisions.py (Council → Decision loop: draft_decision_from_review + approve_decision + reject_decision; abstention blocks approval — LES-019)
- packages/aos_core/aos_core/services/adr.py (render_adr_markdown + export_decision_adr; approved decision → repo-vault ADR + re-syncable KnowledgePage — AOS-COUNCIL-PHASEC2A)
- docs/DECISION_LIFECYCLE.md (Decision stage — implemented: draft → approve/reject with ApprovalRecord memory; approved → repo-vault ADR export)

## Layer 5: Design and User Experience

Owns product visual language and workflow usability.

Capabilities:

- Design Intelligence
- Ops-deck design system (AOS-UI-001: a scoped `.aos-*` design-system layer — `apps/web/src/design/tokens.css` — with blue+red tokens, self-hosted Bebas Neue display type, and angular HUD-frame / neumorphic-chip / signal-meter primitives across both themes, scoped under `.aos-surface` so it is inert against the existing Control Tower page. Its first surface is the live **Reuse view** (`apps/web/src/features/reuse/ReuseView.tsx`) wired to `POST /projects/{id}/transfer` — ranked, evidence-backed reuse cards with a signal-strength confidence meter, matched-term chips, and expandable reason/evidence/required-changes/risks/provenance. **The WebGL radar instrument shipped (AOS-UI-002): the Control Tower's first WebGL surface on the `.aos-*` design system** — a react-three-fiber radar (`apps/web/src/features/reuse/Radar.tsx`) over a pure deterministic candidate→polar mapping (`radarLayout.ts`, distance-from-center = `1 − confidence`) that plots the same live reuse candidates: rings, rotating sweep, pulsing core, tier-colored blips (cyan = has matched_terms, periwinkle = lexical-lean), with a WebGL capability probe + error boundary → static-placeholder fallback and a prefers-reduced-motion freeze. `ReuseView` lifts card-expand state up so the radar drives it (click a blip → expand + scroll its card; hover a card → highlight its blip). Deferred superset: a generic reusable `<Radar>` + the full rail-shell migration onto the `.aos-*` system (AOS-UI-003))
- Dashboard Interface
- Workspace Layout Engine
- Visual Engineering Intelligence
- Voice Command Center

Primary artifacts:

- docs/DESIGN_INTELLIGENCE.md
- docs/DASHBOARD_INTERFACE.md
- apps/web/src/design/tokens.css (AOS-UI-001: the scoped `.aos-*` ops-deck design system — tokens, Bebas Neue, HUD/neumorphic/signal-meter primitives, both themes)
- apps/web/src/features/reuse/ReuseView.tsx (AOS-UI-001: the live Reuse view — the design system's first surface, wired to the Transfer Engine) with apps/web/e2e/reuse.spec.ts
- apps/web/src/features/reuse/radarLayout.ts + Radar.tsx (AOS-UI-002: the WebGL radar instrument — pure deterministic candidate→polar mapping + the react-three-fiber `<Canvas>`, the Control Tower's first WebGL surface) with apps/web/e2e/radarLayout.spec.ts + reuse-radar.spec.ts
- docs/WORKSPACE_LAYOUT_ENGINE.md
- docs/VISUAL_ENGINEERING_INTELLIGENCE.md
- docs/VOICE_COMMAND_CENTER.md

## Layer 6: Build and Execution

Owns implementation handoff and execution.

Capabilities:

- Build Intelligence
- Claude Code Bridge
- local LLM routing
- node agents
- proof labs
- builder workflows

Primary artifacts:

- docs/CLAUDE_CODE_BRIDGE.md
- docs/DISTRIBUTED_RUNTIME.md
- docs/LOCAL_LLM_GPU_NODE.md

## Layer 7: Validation and Release Gates

Owns correctness, readiness, and verification.

Capabilities:

- Verification Protocol
- Verification Engine
- Verification Provider abstraction
- Local CLI verification provider
- GitHub Actions verification provider
- Docker verification provider
- Runtime Health verification provider
- Connector Inspection verification provider
- Human Approval verification provider
- PR Guardian
- CI enforcement
- branch protection setup
- branch freshness validation
- WSL local Level 2 verification
- post-merge validation
- doc-staleness detection (deterministic doc-vs-reality drift check; advisory PR Guardian WARN)
- Engineering Evaluation Standard
- Engineering Evolution Score
- benchmarks
- experiments
- risk register
- release readiness
- alpha self-evaluation review (system evaluates its own repository)
- Level 4 dashboard browser-drive verification

Primary artifacts:

- docs/ALPHA_REVIEW_V0_1.md
- .archetype/alpha/ (captured self-evaluation evidence)
- scripts/web_drive/ (headless-Chromium dashboard drives — seed corpus)
- apps/web/e2e/ (enforced Playwright e2e suite; CI web-e2e job)
- .archetype/guardian/accepted_warnings.json
- docs/VERIFICATION_PROTOCOL.md
- docs/PR_GUARDIAN.md
- docs/BRANCH_PROTECTION.md
- docs/POST_MERGE_VALIDATION.md
- docs/BRANCH_ISOLATION_WORKTREE_PROTOCOL.md
- docs/WSL_WIN11_RUNTIME_TARGET.md
- scripts/pre_pr_guardian.sh
- scripts/post_merge_validation.sh
- tools/doc_staleness.py (deterministic doc-staleness detector — AOS-20, closes LES-007)
- .github/workflows/ci.yml
- docs/ENGINEERING_EVOLUTION_SCORE.md
- templates/benchmark_record.md
- templates/experiment_record.md
- templates/risk_register.csv

## Layer 8: Self Learning and Evolution

Owns continuous improvement.

Capabilities:

- Nightly Self Learning Loop
- Learning Feedback Loop (lessons registry; RFC-0004)
- Evolution Intelligence
- Meta Agent
- Prompt and Workflow Evolution
- Engineering Simulation Lab
- Doc-staleness self-heal (AOS-20 detects doc-vs-reality drift; AOS-SELFHEAL-001 closes the loop to *correct* it — `tools/doc_staleness.py --fix` generates a deterministic reconciliation DRAFT from `git log` without editing prose or gaming the alarm (Article XII), a `post-merge` git hook regenerates it when `main` advances, and the `/reconcile-state` skill applies the narrative half for human approval. **AOS-SELFHEAL-002 adds the CI-on-main trigger** — `.github/workflows/doc-staleness-reconcile.yml` runs `--fix` on every merge and idempotently opens/updates (or auto-closes) a single `doc-staleness` tracking issue with the draft, catching drift the PR-Guardian WARN misses when no PR is open; the LLM narrative reconciliation is intended to run from a nightly Claude routine via `/reconcile-state`. **AOS-SELFHEAL-002b runs that narrative half** — a nightly routine (`scripts/nightly/reconcile_state.{sh,prompt.md}`, registered via `/schedule`; runbook `docs/runbooks/nightly-routines.md`) that gates deterministically on the detector, then wakes a headless `claude` to apply the reconciliation and **open a PR for review** (never merges); merging it is the merge that auto-closes the tracking issue. Remaining follow-ups: a Stop hook + in-container nightly-loop/digest wiring (needs a runner→DB path))
- Conflict self-heal (AOS-SELFHEAL-003: the repo learns from its own merge friction. `tools/conflict_digest.py` deterministically harvests the day's conflicts from two git-native substrates — `git rerere`'s rr-cache (marker conflicts + resolution state) and `git reflog` (rebase/merge/reset friction, which catches the union-auto-resolved coordination-doc conflicts rerere misses) — into `.archetype/conflicts/<date>.md`. A nightly routine (`scripts/nightly/conflict_learn.{sh,prompt.md}`, `/schedule`-registered) gates on that signal, then wakes a headless `claude` to distill **recurring** patterns into `LES-L##` draft lessons and **open a PR for review** — one-off noise produces nothing (Article XII). `scripts/install-hooks.sh` enables `rerere` so conflicts are recorded. Realizes the NIGHTLY_SELF_LEARNING_LOOP "detect repeated pain points" mandate for merge friction.)

Primary artifacts:

- docs/rfc/RFC-0004-Learning-Feedback-Loop.md
- knowledge/wiki/lessons/index.md
- tools/doc_staleness.py (AOS-20 detector + AOS-SELFHEAL-001 `--fix` draft generator) with apps/api/tests/test_doc_staleness.py; scripts/hooks/post-merge + scripts/install-hooks.sh; skills/ci_devops/reconcile_state.md
- docs/NIGHTLY_SELF_LEARNING_LOOP.md
- docs/EVOLUTION_INTELLIGENCE.md
- docs/META_AGENT.md
- docs/PROMPT_WORKFLOW_EVOLUTION.md
- docs/ENGINEERING_SIMULATION_LAB.md

## Layer 9: Portfolio and Organizational Intelligence

Owns cross-repository learning.

Capabilities:

- Organizational Intelligence Engine
- Portfolio Architecture
- Knowledge Transfer Engine
- Portfolio Knowledge Marketplace
- Repository DNA
- Repository Intelligence outputs
- Knowledge Distillation outputs
- cross-repository recommendations
- Repository acquisition (`clone_repo` / `scripts/onboard_repo.sh` — the acquire step for the portfolio; AOS-21)
- Portfolio reality test (first external repo scanned end to end — pydantic-ai; AOS-21)

Primary artifacts:

- docs/ORGANIZATIONAL_INTELLIGENCE_ENGINE.md
- docs/PORTFOLIO_ARCHITECTURE.md
- docs/KNOWLEDGE_TRANSFER_ENGINE.md
- docs/PORTFOLIO_KNOWLEDGE_MARKETPLACE.md
- docs/REPOSITORY_INTELLIGENCE_ENGINE.md
- docs/KNOWLEDGE_DISTILLATION_ENGINE.md
- docs/PORTFOLIO_PYDANTIC_AI.md (AOS-21 reality test + honest findings LES-013/LES-014)
- packages/aos_core/aos_core/services/onboarding.py; scripts/onboard_repo.sh
- templates/repository_dna.md

## Layer 10: Interface and Interaction

Owns how users interact with ArchetypeOS.

Capabilities:

- Dashboard
- Command palette
- Voice interface
- agent council dashboard (AOS-COUNCIL-002: a Control Tower "Agent Council" section surfacing the full council reasoning the API already returns — verdict + confidence, a Final Judge panel with agreements/disagreements/unsupported claims/follow-up, and per-agent cards (summary/findings/evidence/concerns/status); the "Insufficient evidence" abstention is rendered distinctly. Read-focused; enqueue stays in the Decision Loop)
- Reuse view (AOS-UI-001: the first surface on the scoped `.aos-*` ops-deck design system — a live Control Tower view wired to the Transfer Engine `POST /projects/{id}/transfer`, rendering ranked evidence-backed reuse cards with a signal-strength confidence meter, matched-term chips, and expandable reason/evidence/required-changes/risks/provenance; see Layer 5)
- Reuse radar instrument (AOS-UI-002: the Control Tower's first WebGL surface — a react-three-fiber radar (`apps/web/src/features/reuse/Radar.tsx`, over pure deterministic `radarLayout.ts`, distance-from-center = `1 − confidence`) plotting the live reuse candidates; the radar and the Reuse cards are one interaction surface (click a blip → expand its card; hover a card → highlight its blip), with WebGL-probe/error-boundary → static-placeholder and reduced-motion fallbacks; see Layer 5)
- Nightly Audits board (AOS-SELFHEAL-OBS-UI: a Control Tower **Operations** surface (`apps/web/src/features/audits/AuditsView.tsx`, view id `audits`) reading `GET /audits/heartbeats` — one row per known self-learn routine (conflict / toil / coherence / session-pain) resolved to a single state: `clean`, `findings` (links its review PR), `failed`, `missed` (a heartbeat older than a day → a skipped nightly is visible, not silent), or `no report` (never checked in). An attention summary counts missed/failed routines; any routine the API returns outside the known set is appended so nothing is hidden. Read-only board over the AOS-SELFHEAL heartbeat observability — see Layer 8.)
- engineering observatory
- multi-monitor layouts

Primary artifacts:

- docs/DASHBOARD_INTERFACE.md
- docs/VOICE_PROVIDER_ADAPTERS.md
- docs/VOICE_SAFETY_MODEL.md
- docs/AGENT_COUNCIL_DASHBOARD.md
- apps/web/src/main.tsx ("Agent Council" Control Tower section — AOS-COUNCIL-002) with apps/web/e2e/council-dashboard.spec.ts
- apps/web/src/features/audits/AuditsView.tsx (AOS-SELFHEAL-OBS-UI: Nightly Audits board) with apps/web/e2e/audits-view.spec.ts
- docs/ENGINEERING_OBSERVATORY.md

## Layer 11: Runtime and Infrastructure

Owns deployment and execution environment.

Capabilities:

- Windows 11 host runtime
- WSL 2 Ubuntu runtime target
- WSL filesystem layout
- WSL Docker runtime verification
- CasaOS or Portainer deployment
- Docker Compose
- Postgres
- Redis
- API
- worker
- web dashboard
- GPU node
- WSL node
- GitHub integration
- database schema migrations (Alembic)

Primary artifacts:

- docs/WSL_WIN11_RUNTIME_TARGET.md
- docs/DISTRIBUTED_RUNTIME.md
- docs/LOCAL_LLM_GPU_NODE.md
- docs/CLAUDE_CODE_BRIDGE.md
- docs/CONNECTOR_POLICY.md (AOS-CONNECTOR-001: connector registry governance — privacy class, egress, browser-exposed, health)
- docs/DATABASE_MIGRATIONS.md
- docker-compose.yml
- .env.example
- apps/web
- apps/api
- apps/api/alembic/ (Alembic migrations; baseline schema)
- apps/api/docker-entrypoint.sh (runs migrations before serving)
- apps/worker
- apps/scheduler (control-plane scheduler: materializes due schedules into jobs; RFC-0007)
- packages/aos_core (shared domain library: config/database/models/scanner + scan/digest/jobs/scheduler services; RFC-0006)
- docs/rfc/RFC-0006-Shared-Core-Domain-Library.md
- docs/rfc/RFC-0007-Scheduling-Control-Plane-Job-Origination.md (schedules-as-data; control plane decides + stores, nodes execute)

## Layer 12: Orchestration and Work Management

Owns cross-agent coordination, durable project state, task sequencing, handoffs, and anti-context-rot workflows.

Capabilities:

- Orchestration Engine
- agent hierarchy
- agent communication protocol
- current state tracking
- active work tracking
- handoff protocol
- verification handoff metadata
- branch isolation protocol
- worktree protocol
- connector fallback branch isolation
- backup head preservation
- branch freshness before ready-for-review
- recent changes log
- session bootstrap generation
- Plane integration
- task lifecycle enforcement
- dependency and blocker tracking

Primary artifacts:

- docs/ORCHESTRATION_ENGINE.md
- docs/ORCHESTRATOR_PLAYBOOK.md
- docs/AGENT_HIERARCHY_AND_COMMUNICATION.md
- docs/BRANCH_ISOLATION_WORKTREE_PROTOCOL.md
- docs/CURRENT_STATE.md
- docs/ACTIVE_WORK.md
- docs/HANDOFF.md
- docs/RECENT_CHANGES.md
- docs/SESSION_BOOTSTRAP.md

## Capability Dependency Graph

```text
Constitution
  -> RFC Process
  -> Agent Contract
  -> Arbiter and Final Judge
  -> Decision Lifecycle
  -> Agent Hierarchy

Engineering OS Strategy
  -> WSL Runtime Target
  -> Runtime Verification
  -> Repository Scanner Loop
  -> Engineering Control Tower

Orchestration
  -> Current State
  -> Active Work
  -> Session Bootstrap
  -> Agent Assignment
  -> Handoff
  -> Branch Isolation
  -> Worktree Protocol
  -> Connector Fallback
  -> Verification Metadata
  -> Plane Sync
  -> PR Lifecycle

Knowledge and Memory
  -> Knowledge Distillation
  -> Research
  -> Architecture
  -> Decision Intelligence
  -> Portfolio Intelligence

Research
  -> Repository Intelligence
  -> Technology Fitness
  -> Design Intelligence
  -> Strategy Engine

Repository Intelligence
  -> Architecture Reverse Engineering
  -> Pattern Mining
  -> Reuse Analysis
  -> Portfolio Knowledge

Architecture
  -> Digital Twin
  -> PR Guardian
  -> Verification Protocol
  -> Release Gates

Decision Intelligence
  -> Build Intelligence
  -> Verification
  -> Validation
  -> Evolution

Verification
  -> Local CLI Provider
  -> GitHub Actions Provider
  -> Docker Provider
  -> Runtime Health Provider
  -> Connector Inspection Provider
  -> Human Approval Provider
  -> Branch Freshness Validation
  -> PR Guardian
  -> Release Gates

Nightly Self Learning
  -> Knowledge Distillation
  -> Meta Agent
  -> Prompt Evolution
  -> Skill Recommendations
  -> Portfolio Knowledge
```

## MVP Path

The first build should not implement every capability.

Minimum coherent product:

1. Project registry
2. WSL Windows 11 runtime target
3. Local Docker runtime verification
4. Repository scan
5. Architecture Spine Graph draft
6. Decision cards and ADRs
7. Research notes
8. PR Guardian first pass
9. Verification Protocol
10. Branch Isolation / Worktree Protocol
11. Nightly self-learning digest
12. Dashboard shell
13. Voice inbox capture
14. Orchestration state files
15. Session bootstrap and handoff protocol

## Later Capabilities

- full marketplace
- full simulation lab
- full strategy engine
- advanced multi-monitor support
- production-grade voice session streaming
- advanced digital twin prediction
- write-capable build workflows after approval gates mature
- live multi-agent communication bus
- full Plane synchronization
- automatic Verification Engine provider selection

## Update Rule

Whenever a new capability, engine, agent, or runtime component is added, this capability map must be updated in the same change set or explicitly marked as not affected.

## Principle

ArchetypeOS should grow from a concrete path, not from scattered features.