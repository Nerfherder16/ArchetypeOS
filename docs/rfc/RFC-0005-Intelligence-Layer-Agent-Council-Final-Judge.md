# RFC-0005 — Intelligence Layer: Agent Council + Final Judge (LLM Provider Abstraction + Council MVP)

## Status

Accepted (operator-directed 2026-07-05: "write RFC-0005 and start AOS-19"). Governs the Intelligence/Council layer seed (AOS-19). Supersedes the "Verification Engine provider abstraction — deferred" open decision by choosing the abstraction shape now.

**Operator decisions (2026-07-05, at package start):** (1) **Provider** — the real reasoning backend is the **Claude Code SDK via the operator's subscription** (headless `claude` / Claude Agent SDK), *not* env-keyed metered API. This deliberately sidesteps the AOS-19 board note's "paid API execution by default → needs budget/opt-in" scope-lock gate: a subscription invocation is not per-token metered spend, so no budget gate is required. A **deterministic default provider** remains the CI/hermetic backend (no auth in CI). (2) **Roster** — four agents + Final Judge. (3) **Persistence** — dedicated council tables. These supersede the leaner one-agent / reuse-existing-tables framing in the original AOS-19 board note.

## Summary

ArchetypeOS has, as of Sprint 5, a complete **control-plane + execution substrate**: `apps/api` (control plane), `apps/worker` (execution), `apps/scheduler` (origination), and `packages/aos_core` (shared domain). What it does not yet have is the layer that makes it *intelligent* — the **Agent Council** (specialized agents that produce structured, evidence-bearing outputs) and the **Final Judge** (which reviews those outputs, surfaces disagreement, and issues a governed verdict). This RFC introduces that layer, seeded by a testable MVP, and — critically — an **LLM provider abstraction** so the reasoning backend is a swappable, local-first concern rather than a hardcoded dependency.

The governing constraint is hermeticity: the council pipeline must be *real and deterministically verifiable in CI today*, with real model backends (local-first Ollama on the RTX 3090 node; hosted APIs as fallback) slotting in behind one interface later. We therefore ship a **deterministic default provider** as the CI-verifiable backend and the `Provider` protocol real backends implement.

## Problem

`docs/CONCRETE_BUILD_PATH.md` Phase 9 ("Agent Council MVP") specifies: *run selected agents · store outputs · show statuses · Final Judge synthesis*, with acceptance *"Research, Architecture, Fitness, Security, and Final Judge can produce structured outputs"* and *"Disagreements are visible."* Today none of that exists in code (`grep -rni council apps/ packages/` → nothing). The vision docs describe the layer in detail — `docs/AGENT_CATALOG.md` (the roster), `docs/ARBITER_FINAL_JUDGE.md` (verdicts + abstention), `docs/AGENT_COUNCIL_DASHBOARD.md` (status states + Final Judge panel), `docs/AGENT_HIERARCHY_AND_COMMUNICATION.md` (agents communicate through durable artifacts) — but the substrate to run it did not exist until Sprint 5. It does now:

- **`aos_core` (AOS-CORE-001)** gives a shared place for a council service and provider abstraction, consumed identically by api/worker/scheduler.
- **The job/queue system (AOS-WORKERRUN-001)** gives a `job_type` dispatch a `council_review` job slots into — council runs are potentially long, so they belong on the worker, not in a request.
- **Alembic (AOS-ALEMBIC-001)** makes the two new council tables a clean migration (`0003`) — explicitly named as an AOS-19 unblock in `.archetype/work/AOS-ALEMBIC-001.md`.
- **Decision / Recommendation / ResearchNote models + API (AOS-DEC-001)** already encode the *output shapes* (they mirror `templates/decision_card.md`, `recommendation_card.md`, `research_note.md`). The council produces these shapes; it does not invent a parallel vocabulary.

The blocker is not substrate — it is that (a) there is no reasoning-backend abstraction, and CI has no GPU and must stay hermetic; and (b) there is no aggregate that ties per-agent outputs to a Final Judge verdict as one auditable run.

## Goals

- A **`Provider` abstraction** in `aos_core` — one interface for text generation — with a **deterministic default provider** that makes the entire council pipeline runnable and assertable offline in CI.
- A **Council service** that runs the four MVP agents named in the Phase-9 acceptance criteria — **Research Librarian, Architecture Cartographer, Technology Fitness Judge, Security Agent** — each emitting a **structured output** (summary, findings, evidence, concerns, confidence, status).
- A **Final Judge** step that synthesizes those outputs into a governed verdict per `docs/ARBITER_FINAL_JUDGE.md`: points of agreement, points of disagreement, unsupported claims, evidence quality, confidence, verdict (`Accept` / `Accept with warnings` / `Reject` / `Defer` / `Research further` / `Simulate first` / `Escalate to human`), and **abstention** (`Insufficient evidence`) when evidence is thin.
- **Durable persistence**: a `CouncilReview` aggregate + `CouncilAgentOutput` rows (migration `0003`) — "agents communicate through durable artifacts," not chat memory.
- **Disagreement is first-class**: the Final Judge output explicitly records where agents disagree; nothing hides it.
- **Human approval preserved**: council output is advisory. Any `Decision`/`Recommendation` it drafts is a *draft* (unapproved: `approved_by` null) — no autonomous action, per the Constitution.
- Triggerable + readable over the API; verifiable in CI without a live model or network.

## Non-goals

- **No real LLM backend runs in CI.** The `ClaudeCodeProvider` (subscription-auth) ships in this seed as a real adapter with a mocked-boundary unit test, but CI selects `deterministic` (no auth). The GPU-node (Ollama/vLLM) and any hosted adapter are later. A live council run is exercised on the operator's authed node, not in CI.
- **No dashboard** in this seed — that is Phase 2 (AOS-19b), mirroring the AOS-SCHED-001 → AOS-SCHED-002 split.
- **No autonomous execution** — the council never builds, merges, or acts; it recommends. Builder Agent / PR integration is out of scope.
- **The full roster is not built now** — Compliance, Design Intelligence, External Repo Scout, PR Guardian-as-council-member, Builder are deferred; the four Phase-9 agents are the MVP.
- **No automated provider *selection*** — selection is a static config setting now; capability-based routing (Phase 5 node types) is later.

## Proposal

### 1. LLM provider abstraction — `aos_core/llm/`

- **`Provider` protocol**: a minimal, duck-typed interface — `generate(self, *, system: str, prompt: str, max_tokens: int = ...) -> ProviderResult`, where `ProviderResult` carries `text` + lightweight metadata (`provider`, `model`, `finish_reason`). No hard dependency on any SDK; adapters live behind the protocol.
- **`DeterministicProvider` (default)**: produces stable, structured, seedless output derived from its inputs (the project scan/DNA, the question, the agent persona). It is not a mock in tests only — it is a *real, shippable* backend that lets ArchetypeOS run a full, reproducible council with zero external calls. This is the local-first, verification-over-inference stance applied to the reasoning layer: deterministic by default, probabilistic when a model is deliberately attached. CI runs this backend.
- **`ClaudeCodeProvider` (real backend, operator's node):** invokes the **Claude Code SDK / headless `claude`** (`claude -p … --output-format json`, or the Claude Agent SDK) using the operator's **subscription** auth — no committed keys, no metered-API budget. Selected via `llm_provider="claude_code"` on an authed node (WSL / `teevee-1`); it is *not* exercised in CI (no auth there). Its process/SDK boundary is unit-tested with a mocked invocation so the adapter is covered without a live call. This is the backend that gives real council reasoning immediately after merge on the operator's machine.
- **Provider selection**: `Settings.llm_provider: str = "deterministic"` in `aos_core.config` (documented values `deterministic` | `claude_code`); a `get_provider(settings)` factory. Further backends (Ollama/vLLM on the deferred GPU node; a hosted fallback) register here later without touching callers.
- **The contract mirrors the existing Verification Provider Interface** (`docs/VERIFICATION_PROTOCOL.md`: declare capabilities/availability → return standardized result). This is the same replaceable-provider shape the platform already uses for verifiers, applied to reasoning — Constitution **Article XI (Modular Intelligence)**: "engines, agents, models, providers … must be replaceable without redesigning the whole platform."
- **Documented interface** in `docs/LLM_PROVIDER_ABSTRACTION.md`: the protocol, how to add a backend, the **local-first routing policy** from `docs/LOCAL_LLM_GPU_NODE.md` (local models for low-risk/repetitive work — first-pass scans, triage, summaries; cloud/premium models reserved for high-stakes architecture/security/compliance reasoning and final recommendations: "use expensive models where they matter; use local models where they are sufficient"), the ordering (Ollama/OpenAI-compatible endpoint on the 3090 node → hosted fallback; the GPU node itself is deferred until the WSL target is verified), and why CI stays deterministic.

### 2. Council service — `aos_core/services/council.py`

- `run_council(db, *, project_id, question, provider, agents=DEFAULT_AGENTS) -> CouncilReview`.
- Each agent is a **persona** (system prompt + a structured extraction of the relevant evidence from the project's latest scan/DNA/decisions) run through the provider, producing a `CouncilAgentOutput`: `agent_name`, `status` (`Complete` / `Needs Evidence` / `Escalated` / `Rejected` per the dashboard's status states), `summary`, `findings` (list), `evidence` (list), `concerns` (list), `confidence` (float).
- **Structured-output contract**: the persona prompt asks the provider for a JSON object with those keys; the service parses it **tolerantly** (a provider that returns unparseable prose → `status="Needs Evidence"`, low confidence, raw text in `summary`). The `DeterministicProvider` emits valid JSON deterministically; the `ClaudeCodeProvider` returns the agent's JSON — both flow through one parser, so the seam is uniform.
- **Final Judge** (`synthesize_verdict(outputs) -> verdict dict`): computes points of agreement / disagreement across agent outputs, flags unsupported claims (findings with no evidence), aggregates confidence, and emits a verdict + required follow-up. Applies the **abstention rule**: below an evidence/confidence floor → `Insufficient evidence` with a list of what must be verified. Deterministic and rule-based over the agent outputs (the *judgment rules* are code — the Arbiter; the *first-pass reasoning* is the provider — the agents), so the judge is auditable and not itself a black box.
- The council **drafts** (never approves) any `Recommendation` it proposes; human approval stays a separate, explicit step.

### 3. Persistence — models + migration `0003`

- `CouncilReview(AuditMixin, Base)` — `project_id` (FK), `question` (Text), `verdict` (String), `confidence` (Float), `agreements`/`disagreements`/`unsupported_claims`/`follow_up` (JSON lists), `provider` (String), `job_id` (FK nullable). The auditable run aggregate.
- `CouncilAgentOutput(AuditMixin, Base)` — `review_id` (FK), `agent_name`, `agent_type`, `status` (the documented status states: `Waiting`/`Running`/`Needs Evidence`/`Blocked`/`Complete`/`Escalated`/`Rejected`), `summary`, `findings`/`evidence`/`concerns` (JSON), `confidence` (Float).
- **Why dedicated rows and not a live bus**: `docs/AGENT_COMMUNICATION_BUS.md` stages the runtime bus (Redis streams / WebSocket inboxes) as *"Runtime Bus Later"*; the operator decision "multi-agent live communication — deferred; durable artifact communication first" (`docs/CURRENT_STATE.md`) means the council's channel *is* the DB row. The typed-message vocabulary (DecisionRequest/DecisionVerdict) maps onto these rows when the runtime bus lands.
- The council's externally-consumable **product** is a *drafted* `Decision` (its `evidence` list links to any `ResearchNote`s produced, per the AOS-DEC-001 typed-evidence convention), left unapproved. The **approve/promote route** (`approved_by`/`approved_at`, gated by `ApprovalRecord`/`AuthorityGrant`) is a deliberate later addition — the seed is advisory only and must not bypass the Authority/Approval rails.
- Alembic migration `0003_council` (`down_revision='0001'`? — no: chained on `0002`), adding both tables; `import aos_core.models` added manually (GUID/JSONField TypeDecorators, per LES on autogenerate). Validated by the no-drift autogenerate probe + compose-smoke applying it on fresh Postgres.

### 4. Worker dispatch + API

- **Worker**: `job_type == "council_review"` → `run_council(...)`, persist, `mark_job` completed with `{review_id, verdict}`. Council runs are long-ish → they belong on the worker (reuses retry/attempts).
- **API** (`apps/api`, consuming `aos_core`):
  - `POST /projects/{project_id}/council-reviews` — body `{question}`; **enqueues** a `council_review` job (returns the job) *and/or* runs synchronously for small MVP inputs (decision recorded in Open Questions). 404 if project missing.
  - `GET /projects/{project_id}/council-reviews` — recent reviews (desc, cap 50).
  - `GET /council-reviews/{review_id}` — the review + its agent outputs + verdict (404 if missing).

### 5. Phasing

- **AOS-19 (this RFC's first package — backend seed):** provider abstraction + `DeterministicProvider` (CI default) + `ClaudeCodeProvider` (subscription backend, mocked-boundary test); `council.py` with the 4 agents + Final Judge; `CouncilReview`/`CouncilAgentOutput` models + migration `0003`; worker `council_review` dispatch; council API (trigger + read); `docs/LLM_PROVIDER_ABSTRACTION.md`; tests (agents produce structured outputs; disagreement surfaced; judge abstains on insufficient evidence; deterministic provider stable; claude_code adapter builds/parses via a mocked invocation; API CRUD; worker dispatch; no-drift; compose-smoke). **No dashboard.**
- **AOS-19b (dashboard):** Agent Council Dashboard — trigger a review; per-agent status/summary/evidence/confidence; **disagreement surfaced** (Final Judge panel: agreements / disagreements / unsupported claims / verdict / follow-up); Playwright e2e. Closes the Phase-9 acceptance ("disagreements are visible") end to end.
- **Later (own packages/RFCs):** real backends behind the protocol (Ollama on the 3090 node; hosted fallback); more agents (Compliance, Design, External Repo Scout); **scheduled** council runs (a `Schedule` row with `job_type=council_review`, RFC-0007 dividend); council → decision-approval → Builder handoff; monthly decision re-evaluation (Phase 7).

## Alternatives

- **Hardcode a single hosted LLM (e.g. call an API directly in the service).** Fastest to a "real" answer, but: breaks CI hermeticity (network + credentials), contradicts local-first, and bakes a provider into the domain layer. Rejected — the abstraction is cheap now and load-bearing later (Phase 5 heterogeneous nodes).
- **Council runs synchronously inside the API request only (no worker/job).** Simpler, but council runs grow long (multi-agent, real models later) and would block requests / time out; also diverges from the "control plane decides, nodes execute" split. We keep the *job* path as the primary; a synchronous path may exist for tiny MVP inputs (Open Question). Not rejected outright — bounded.
- **Reuse the existing `Decision` table as the council aggregate (no new tables).** Tempting (the shapes overlap), but a `Decision` is an *output the judge may draft*, not the *run*; conflating them loses per-agent outputs, statuses, and disagreement — exactly what Phase 9 requires be visible. A dedicated `CouncilReview` + `CouncilAgentOutput` keeps the audit trail. The council still *drafts* `Decision`/`Recommendation` rows as its product.
- **LLM-as-Final-Judge (the judge is itself a model call).** Deferred. The Arbiter's *rules* (evidence sufficiency, abstention, conflict resolution) are governance and must be deterministic/auditable; a model can later assist synthesis behind the same seam, but the verdict logic ships as code first (evidence over inference).

## Evidence

- `docs/CONCRETE_BUILD_PATH.md` Phase 9 — exact MVP feature list + acceptance criteria (four agents + Final Judge, disagreements visible).
- `docs/AGENT_CATALOG.md` — the agent roster and universal rules (evidence over opinion; escalate conflicts to Final Judge).
- `docs/ARBITER_FINAL_JUDGE.md` — verdict set + abstention rule ("Insufficient evidence" with what-to-verify), verbatim.
- `docs/AGENT_COUNCIL_DASHBOARD.md` — status states + Final Judge panel fields (drives the model columns).
- `docs/AGENT_HIERARCHY_AND_COMMUNICATION.md` — "agents communicate through durable artifacts" (drives DB-row persistence, not chat).
- Codebase: `packages/aos_core/aos_core/models.py` (`Decision`/`Recommendation`/`ResearchNote`/`Evaluation`/`Agent` already present), `apps/worker/app/worker.py` (`job_type` dispatch), `apps/api/app/main.py` (decision/recommendation/research CRUD) — the attachment points exist.
- `.archetype/work/AOS-ALEMBIC-001.md` names "AOS-19 (council tables)" as a thing Alembic was adopted to unblock.
- `docs/LOCAL_LLM_GPU_NODE.md` — local-first runtimes (Ollama/vLLM/llama.cpp/OpenAI-compatible) + the local-vs-cloud routing policy the provider abstraction encodes; `docs/VERIFICATION_PROTOCOL.md` — the provider-contract pattern (capabilities → standardized result) this mirrors.
- `docs/SYSTEM_ARCHITECTURE.md` §2–3 — the four-layer model (Control Plane / Intelligence / Council / Execution); this seed builds the Intelligence + Council layers atop the now-complete Control Plane + Execution substrate. `.archetype/agent_registry.json` — the machine-readable roster (source of truth for agent missions).

## Security impact

- **The CI/default path has no external surface** — the deterministic provider makes no network calls, uses no credentials. The `ClaudeCodeProvider` authenticates via the operator's **Claude Code subscription** (the local `claude` install's own auth) — **no API keys are committed or read from repo config**; the adapter shells to the local CLI / SDK. Guardian secret-scan still applies; the blast radius stays isolated to one adapter behind the seam. No metered spend → no budget gate.
- Council output is **advisory and unapproved** — it cannot trigger action; `approved_by` stays null until a human approves. No autonomy is introduced.
- Prompts incorporate repository scan data (already in the system); no new data egress in the deterministic path.

## Compliance impact

- Governance-positive: the council makes reasoning **auditable** (durable per-agent outputs + a recorded verdict + evidence lists), directly serving the Constitution's "every significant decision needs memory" and "evidence over inference." The Compliance Agent itself is deferred to a later roster expansion; this seed does not evaluate regulatory posture.

## Migration plan

- Alembic migration `0003_council` chained on `0002` (schedules): creates `council_reviews` + `council_agent_outputs`. Additive only — no existing table touched. `import aos_core.models` added to the migration manually.
- Validated by: the no-drift autogenerate probe re-run (must report 0 ops after `0003`), and compose-smoke applying `0003` on fresh Postgres via the existing `alembic upgrade head` entrypoint. Pre-existing DBs (teevee-1) upgrade cleanly from `0002`.
- `Settings.llm_provider` defaults to `"deterministic"`; existing deployments need no config change.

## Acceptance criteria (this RFC)

- Operator approved (done). AOS-19 delivers the backend seed; AOS-19b the dashboard.
- The four MVP agents + Final Judge produce **structured, persisted outputs** for a project, runnable **offline in CI**; disagreement is explicitly recorded; the judge **abstains** on insufficient evidence.
- Provider is abstracted behind one interface with a deterministic default; real backends require no caller changes.
- Council output is advisory/draft-only; no autonomous action; human approval unchanged.
- Migration `0003` passes no-drift + compose-smoke.

## Open questions

1. **Trigger mode** — *Resolved: enqueue-primary.* `POST …/council-reviews` enqueues a `council_review` job (consistent with "control plane decides, nodes execute"); the worker runs the council and persists; read endpoints return the persisted review. `run_council` is unit-tested directly (no worker needed for coverage).
2. **Agent evidence source**: the MVP agents read the project's latest scan/DNA/decisions as their evidence substrate. Is that sufficient for a meaningful deterministic output, or should a minimal ResearchNote-gathering step precede? *Leaning: latest scan/DNA is enough for the seed; a research pre-step is a later agent.*
3. **Confidence/abstention thresholds**: the exact evidence floor for `Insufficient evidence`. *Leaning: encode a conservative default constant, documented, tunable later — a candidate future `AuthorityGrant`/Arbiter-config concern.*

## Final Judge verdict

Accepted, operator-directed. Scoped deliberately to a hermetic, deterministic seed so the Intelligence Layer becomes real and *verifiable* before any probabilistic backend is trusted — evidence over inference, local-first, human approval preserved. Proceed with AOS-19 (backend seed), then AOS-19b (dashboard).

## Dependencies

- AOS-CORE-001 (`aos_core`) — the provider + council service live here.
- AOS-WORKERRUN-001 (job dispatch) — `council_review` job_type.
- AOS-ALEMBIC-001 (Alembic) — migration `0003`.
- AOS-DEC-001 (Decision/Recommendation/Research artifacts) — the output shapes the council drafts into.
- Enables: AOS-19b (dashboard), real-backend adapters, scheduled council runs (RFC-0007), Phase 7 decision re-evaluation.
