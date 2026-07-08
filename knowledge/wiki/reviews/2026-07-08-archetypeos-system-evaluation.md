# ArchetypeOS System Evaluation — Vision, UI/UX, Connectors, and Code Drift

Date: 2026-07-08  
Reviewer: ChatGPT / Lead Architect review lane  
Scope: repository inspection, dashboard/code inspection, uploaded ArchetypeOS context reference, distributed-agents addendum  
Artifact type: strategic system evaluation / review note  
Status: advisory; no runtime changes

## Verification Metadata

Verification Status: Verified with warnings  
Verification Level: Level 1  
Verification Method: Repository inspection through GitHub connector plus uploaded reference material inspection. No local runtime, Playwright, Docker, or visual browser session was available in this review lane.  
Evidence: Inspected current repository state files, build-scope docs, dashboard interface docs, workspace layout docs, web shell, design tokens, CommandDeck, web API client, backend schemas, core models, voice service/routes, research engine/web tier, LLM router/pool, worker dispatch, docker-compose, CI workflow, and PR Guardian. Compared these against the uploaded distributed-agent addendum and ArchetypeOS context reference.  
Limitations: This is not a live visual QA pass. It does not include screenshots, DOM inspection, accessibility tooling output, browser performance profiling, local test execution, or runtime smoke verification. Some visual judgments are inferred from source structure and CSS rather than rendered pixels.  
Required Next Verifier: Operator or Runtime Agent for Level 4 visual/runtime verification on the live dashboard.

## Executive Verdict

ArchetypeOS has not lost the plot. The system is materially ahead of the original v0.1 scope in several important ways: repository ingestion exists, scanner evidence is richer, the Knowledge Distillation and Knowledge Transfer arcs are real, the Agent Council is wired into the decision loop, the Control Tower is becoming a serious operating surface, and voice/research/model-routing work has moved from mock to running architecture.

The risk is no longer “will this become real?” The risk is now “will this become too wide before the product spine is consolidated?” The repo has many strong slices, but the strongest next move is not another surface. It is consolidation: canonical state, first-class node/capability registry, connector registry, richer frontend/API contracts, project-aware voice flow, editable architecture corrections, and a single guided operator loop.

In short:

```text
Strong foundation. Strong direction. Strong velocity.
Primary weakness: integration coherence is lagging behind feature velocity.
```

## Review Basis

This review compared the live repository against the intended ArchetypeOS concept from two reference layers.

### Reference Layer A — Founding Platform Vision

The core idea is an Engineering Intelligence Platform: evidence-backed decisions, architecture-first reasoning, durable memory, local-first execution, human approval for destructive actions, and continuous learning. The intended operating loop is:

```text
Research -> Model -> Decide -> Build -> Verify -> Validate -> Learn -> Evolve
```

The v0.1 implementation was supposed to prove a narrower loop:

```text
Project Registry -> Repository Scan -> Architecture Draft -> Decisions/Research -> PR Guardian -> Nightly Learning -> Dashboard Review
```

### Reference Layer B — Distributed Agent Addendum

The distributed-agent addendum expands ArchetypeOS from a local dashboard into a distributed engineering intelligence network:

```text
Control Plane = decides, stores, routes, scores
Execution Nodes = scan, research, build, test, review
LLMs = reasoning engines
Deterministic tools = verification engines
```

The addendum explicitly calls for node registration, capability declarations, execution-node routing, per-agent contracts, default read-only operation, and auditable actions.

### Repository Layer Inspected

Inspected repo areas included:

- `docs/CURRENT_STATE.md`
- `docs/ACTIVE_WORK.md`
- `docs/HANDOFF.md`
- `docs/V0_1_SCOPE_LOCK.md`
- `docs/CONCRETE_BUILD_PATH.md`
- `docs/RUNTIME_DECISION_RECORD.md`
- `docs/CAPABILITY_MAP.md`
- `docs/DASHBOARD_INTERFACE.md`
- `docs/WORKSPACE_LAYOUT_ENGINE.md`
- `apps/web/src/design/tokens.css`
- `apps/web/src/shell/Shell.tsx`
- `apps/web/src/shell/workspaces.ts`
- `apps/web/src/main.tsx`
- `apps/web/src/features/command/CommandDeck.tsx`
- `apps/web/src/api.ts`
- `packages/aos_core/aos_core/models.py`
- `apps/api/app/schemas.py`
- `packages/aos_core/aos_core/services/voice.py`
- `apps/api/app/routes/voice.py`
- `packages/aos_core/aos_core/services/research.py`
- `packages/aos_core/aos_core/services/research_web.py`
- `packages/aos_core/aos_core/services/llm_router.py`
- `packages/aos_core/aos_core/services/llm_pool.py`
- `packages/aos_core/aos_core/config.py`
- `apps/worker/app/worker.py`
- `docker-compose.yml`
- `.github/workflows/ci.yml`
- `tools/pr_guardian.py`

## High-Level Scores

| Area | Score | Assessment |
| --- | ---: | --- |
| Vision alignment | 8.5/10 | The repo is building the intended platform, not a random app. |
| v0.1 fulfillment | 9/10 | Original v0.1 is exceeded. |
| Distributed-agent maturity | 4/10 | Concepts exist, but Node Registry / Capability Registry are not first-class. |
| UI/UX direction | 7/10 | Strong visual identity and operating-system feel, but IA and contract depth need work. |
| Dashboard product coherence | 6.5/10 | Many good surfaces; not yet a unified guided operator loop. |
| Code architecture | 7/10 | Backend domain seams are improving; frontend root component is becoming too large. |
| Connector/provider discipline | 6/10 | Good provider seams; missing central connector registry/health/privacy policy. |
| Verification culture | 9/10 | PR Guardian, CI, lessons, and verification protocol are standout strengths. |
| State/documentation hygiene | 5.5/10 | Durable docs exist but now contradict each other in places. |
| Safety/governance | 7/10 | Strong philosophy and review-first flows; central Authority Action model not yet enforced. |

## What Is Working Exceptionally Well

### 1. The Repo Is Faithful to the Original Mission

The platform is still clearly about engineering intelligence, not generic automation. The current implementation favors research, evidence, architecture modeling, decision records, PR review, reusable knowledge, and learning loops. That is correct.

The repo has not drifted into a “chatbot that can code.” It is becoming a control plane for engineering judgment.

### 2. The Knowledge Arc Is the Strongest Realized Product Spine

The most valuable current achievement is the “feed a repo -> extract useful knowledge -> reuse it for a target” loop. That is the heart of the original idea. Distillation, reuse recommendations, transfer scoring, embeddings, and provenance-backed reuse cards represent a real differentiated capability.

This is not commodity agent work. This is the first serious ArchetypeOS-specific advantage.

### 3. Verification Culture Is Strong

The Verification Protocol, PR Guardian, CI jobs, lessons, and merge discipline create a system that distrusts unchecked claims. This is exactly right for an AI-native engineering OS.

The repo already has a better governance culture than many mature engineering projects.

### 4. The Dashboard Has a Distinct Visual Language

The ops-deck design system is scoped, tokenized, and visually opinionated. The neon command-deck palette, angular HUD frames, pills, meters, rail shell, and responsive tiers all support the intended “engineering control tower” feel.

The dashboard does not look like a generic CRUD admin panel. That matters.

### 5. The Voice Command Center Is Becoming a Real Capture Layer

Voice now has backend turns, STT path, TTS path, inbox review, and approval-based promotion into draft artifacts. The review-first rule is preserved. That is the right architecture.

### 6. The Research Engine Is Moving From Local Floor to Web Reach

The deterministic local Research Engine floor is well-framed: it ranks evidence, persists research notes, and exercises the privacy guardrail. The web tier then adds discovery/fetch failover while staying off by default and private-safe. This is the correct staged path.

## Major Findings

## Finding 1 — State Truth Drift Is Now a System Risk

### Severity

High

### Evidence

`CURRENT_STATE.md` contains both advanced post-v0.1 state and stale older state. The top status says the founding reuse arc is mature end-to-end, with many later PRs merged. Later sections still describe Phase C / Phase B as if RFC-0008 is merely proposed and queued. The active branch line also references an older UI branch even though much newer voice/research/deploy work has landed.

### Why This Matters

ArchetypeOS relies on durable markdown state files as operational memory. If state files disagree, new agents will plan from false premises. This is not cosmetic. It undermines the system’s own “source of truth” discipline.

### Recommendation

Create `AOS-STATE-RECON-001`:

- Rewrite `CURRENT_STATE.md` to only contain canonical current state.
- Move historical saga detail into `RECENT_CHANGES.md` or release notes.
- Add a “state truth contract” limiting `CURRENT_STATE.md` to:
  - current phase
  - active PRs/branches
  - current objective
  - blockers
  - next recommended task
  - required reading
- Add a doc-staleness check for stale “Current Objective” and “Active Branch” patterns.
- Update stale UI text that says voice capture is still planned.

### Acceptance Criteria

- `CURRENT_STATE.md`, `ACTIVE_WORK.md`, `HANDOFF.md`, and `RECENT_CHANGES.md` agree on current phase, active work, and next task.
- No stale branch is named as active unless it is actually active.
- The dashboard overview no longer says “Voice inbox text capture — planned” while Voice Inbox is live.
- A new session can read the state docs and correctly summarize the current repo status.

## Finding 2 — The Dashboard Has Strong Style but Weak Workflow Guidance

### Severity

Medium-high

### Evidence

The workspace shell is strong. It groups views into Operations, Council, Architect, Research, Executive, and Builder modes. The rail exposes live and “soon” surfaces. The visual system is coherent and responsive.

However, the experience is still mostly surface navigation rather than a guided operating loop. A user sees many places to go, but the dashboard does not yet tell the operator what needs attention first.

### UX Diagnosis

The current UI is a beautiful control room, but not yet a control tower. A control tower should answer:

```text
What changed?
What needs me?
What is blocked?
What should I inspect next?
What is safe to approve?
What is risky?
What has confidence?
What needs evidence?
```

The current shell has the ingredients, but the operator still has to assemble that meaning manually.

### Recommendation

Create a persistent “Operator Status Strip” or “Mission Header” across all workspaces:

- Current project
- Pending approvals
- Failed jobs
- Running jobs
- Open lessons
- CI state
- Provider tier / usage state
- Node/runtime health
- Voice inbox pending count
- Research notes needing review

Then make each workspace landing show:

```text
Now
Next
Blocked
Recently changed
```

### Acceptance Criteria

- The operator can load the dashboard and know the next three things requiring attention without opening every workspace.
- Pending approvals, failed jobs, and voice inbox items are visible globally.
- Each workspace has a landing summary, not just a list of sub-surfaces.

## Finding 3 — “Soon” Surfaces Are Honest but Now Create Cognitive Noise

### Severity

Medium

### Evidence

The workspace map includes many `soon` entries: Observatory, Nodes / Runtime, Claude Code Bridge, Final Judge, PR Guardian Gate, Work Packages, Orchestration, Digital Twin, Tech Fitness, Recommendations, Knowledge Graph, Distillation, Docs/Freshness, Marketplace, and every Builder surface.

This is valuable for roadmap honesty. But as the live surface count grows, “soon” chips compete with the actual operating path.

### UX Diagnosis

“Soon” surfaces were useful when the dashboard was mostly scaffold. Now they risk flattening priority. The operator sees many disabled options and may not know what matters most.

### Recommendation

Keep roadmap visibility, but move most disabled surfaces into a “Planned” drawer or mode footer. The primary rail should emphasize live operator paths.

Suggested IA:

```text
Primary rail: only live surfaces + one Planned button
Planned drawer: grouped future surfaces with status / target phase / owning RFC
```

### Acceptance Criteria

- Live workflows are visually dominant.
- Planned surfaces remain discoverable but do not compete with live tasks.
- Each planned surface links to its RFC/spec/work item.

## Finding 4 — The CommandDeck Is Visually Strong but Functionally Underconnected

### Severity

High

### Evidence

`CommandDeck` posts voice turns with:

```ts
postVoiceTurn(q, 'command-deck')
```

The API client supports an optional `projectId`, and the backend promotion logic no-ops when the voice item has no resolved project. This means a voice command from the CommandDeck may fail to promote into a research note or decision unless the LLM detects the project name exactly.

### Why This Matters

The selected project is already known in the app. Not passing it breaks the operator mental model: “I am in this project; commands should apply to this project.”

It also silently weakens AOS-VOICE-005, because promotion depends on `project_id`.

### Recommendation

Create `AOS-VOICE-PROJECT-001`:

- Pass `selectedProjectId` into `CommandDeck` as a prop.
- Call `postVoiceTurn(q, 'command-deck', selectedProjectId)`.
- Show the selected project in the CommandDeck console.
- If no project is selected, show “global capture” explicitly.
- Add an e2e test proving a command in a selected project creates a promotable voice inbox item.

### Acceptance Criteria

- Voice turns submitted from a selected project carry `project_id`.
- Approving a research/decision voice item from CommandDeck creates the expected draft artifact.
- The UI clearly distinguishes project-scoped capture from global capture.

## Finding 5 — Voice Inbox Is Live but Still Short of the Original Interaction Contract

### Severity

Medium-high

### Evidence

The dashboard vision says Voice Inbox items should support transcript viewing, summary editing, project assignment, intent selection, sending to an agent, conversion to decision/research/issue, and archiving.

Current implementation supports capture, classification, pending/approved/dismissed review state, and promotion for two intents. It does not yet support project reassignment, intent correction, summary editing, archive, issue/task conversion, or full intent mapping.

### Recommendation

Create `AOS-VOICE-INBOX-002`:

- Add project assignment/editing for existing inbox items.
- Add intent correction dropdown from the canonical intent list.
- Add summary editing.
- Add server-side filters: state, project, intent, source device.
- Map remaining intents to concrete draft artifacts where models already exist.
- Add archive state distinct from dismiss.

### Acceptance Criteria

- Operator can fix a bad intent or missing project before approval.
- Approving after correction promotes based on corrected fields.
- Voice Inbox supports filtering pending items by project.
- Remaining mapped intents no longer silently no-op unless intentionally unsupported.

## Finding 6 — Frontend/API Contracts Lag the Backend Model

### Severity

High

### Evidence

The backend `RepositoryDNA` model includes `purpose`, `frameworks`, and `runtime_services`. The API/frontend `RepositoryDnaRead` / `RepositoryDna` contracts omit some of this richer evidence.

The frontend `ArchitectureEdge` type only exposes `id` and `type`, even though the backend schema exposes `from_node_id`, `to_node_id`, `confidence`, `evidence`, and `manual_correction`.

The frontend `ResearchNote` type is thinner than the backend `ResearchNoteRead`, omitting sources/findings/status/version in some paths.

### Why This Matters

The repo has invested in richer intelligence, but the dashboard discards or underuses parts of it. This creates “invisible capability”: the backend knows more than the operator can see.

### Recommendation

Create `AOS-CONTRACT-001`:

- Expose `purpose`, `frameworks`, and `runtime_services` through `RepositoryDnaRead`.
- Update `apps/web/src/api.ts` types accordingly.
- Render these fields in Repositories / Architecture / Reuse context.
- Use full architecture edge fields in the architecture view.
- Render research note sources/findings in Research Inbox detail panels.

### Acceptance Criteria

- Repository DNA page shows purpose, frameworks, runtime services, risk flags, and evidence.
- Architecture view can show edge confidence and evidence.
- Research Inbox cards can expand to show sources and findings.
- TypeScript types match backend schemas.

## Finding 7 — Architecture Studio Is Still Mostly Read Surface, Not Editable Model

### Severity

High

### Evidence

The data model supports `manual_correction` on architecture nodes and edges. The original Architecture Studio vision calls for editable graph data, correction loops, and an engineering digital twin. The current frontend appears to mainly read architecture graph output.

### Why This Matters

A scanner can infer architecture. An Architecture Studio lets the operator correct and improve the model. Without correction, the graph is evidence, not a digital twin.

### Recommendation

Create `AOS-ARCH-STUDIO-001`:

- Add node/edge detail drawer.
- Show evidence, confidence, risks, and correction state.
- Allow operator to set `manual_correction` for nodes/edges.
- Preserve manual corrections across rescans.
- Feed corrected graph state into Council context.

### Acceptance Criteria

- Operator can correct a wrong edge or node label from the dashboard.
- Corrections are persisted and visible after reload.
- Rescan does not erase manual corrections.
- Council/research can cite corrected architecture evidence.

## Finding 8 — Distributed Runtime Vision Is Not Yet First-Class in Code

### Severity

High

### Evidence

The distributed-agent reference calls for a Node Registry and capability declarations. The current repo has skeletal `Agent` and `Engine` models and a robust local Compose runtime, but no first-class `Node` model, no node heartbeat, no capability registry, no node eligibility, and no connected-nodes dashboard.

The Worker dispatch is currently a hardcoded `if/elif` job dispatcher. It does not route jobs based on node capabilities.

### Why This Matters

The original future ArchetypeOS is a distributed engineering OS. Without Node Registry and Capability Registry, the system remains a strong local control plane with providers, not a distributed agent network.

### Recommendation

Create `AOS-NODE-001`:

Add models:

```text
Node
- id
- name
- node_type
- status
- last_seen_at
- endpoint
- max_sensitivity
- write_access
- metadata

NodeCapability
- node_id
- capability
- version
- status
- limits

NodeHeartbeat
- node_id
- health
- observed_at
- metrics
```

Add routes:

```text
POST /nodes/register
POST /nodes/{id}/heartbeat
GET /nodes
GET /nodes/{id}
```

Add UI:

```text
Operations -> Nodes / Runtime
```

### Acceptance Criteria

- A node can register capabilities.
- Dashboard shows node health and capabilities.
- Jobs can declare required capabilities.
- No write-capable node is assumed by default.

## Finding 9 — Connector Drift: Providers Exist, but Connectors Are Not Governed as First-Class Assets

### Severity

High

### Evidence

The repo now has many external connections:

- Claude Code provider
- local OpenAI-compatible provider
- free hosted LLM pool
- Groq TTS
- Sotto STT WebSocket
- Exa
- SearXNG
- crawl4ai
- Firecrawl
- GitHub/CI/PR Guardian integration
- future node connectors

These are configured across `config.py`, `docker-compose.yml`, env vars, and frontend `VITE_*` values. There is no central connector registry that records connector type, privacy class, data egress policy, health, quota, failure mode, or whether the connector is browser-exposed.

### Why This Matters

Connector sprawl is a common failure mode in AI platforms. ArchetypeOS needs connector governance because connectors define where data goes.

### Recommendation

Create `AOS-CONNECTOR-001`:

Add a connector registry model:

```text
Connector
- name
- connector_type
- tier
- enabled
- configured
- privacy_class
- egress_allowed
- browser_exposed
- quota_policy
- last_health_status
- last_error
```

Add a policy file:

```text
docs/CONNECTOR_POLICY.md
```

Add dashboard:

```text
Operations -> Providers & Model Routing -> Connectors tab
```

Specific connector concerns:

- `VITE_SOTTO_TOKEN` is browser-exposed by design. Treat it as a public/client token or proxy Sotto through the API if it is sensitive.
- Free LLM pool keys are env-driven and good, but provider health/quota is not visible.
- Research web services are profile-gated and off by default, good, but their health/policy is not surfaced to the operator.
- Provider exception strings should be treated carefully; avoid surfacing raw upstream bodies that may contain request data.

### Acceptance Criteria

- All external connectors are visible in one dashboard panel.
- Each connector shows privacy class and whether it can receive private data.
- Browser-exposed tokens are explicitly labeled.
- Disabled/unconfigured connectors are visible without causing errors.
- Health checks exist for configured connectors.

## Finding 10 — Authority Model Exists as Data but Not as Enforced Action Policy

### Severity

High

### Evidence

`AuthorityGrant` exists as a model. The decision approval flow is strong. But there is no central Authority Action model that every high-impact operation passes through.

### Why This Matters

As agents gain capabilities, “review-first” must become enforceable infrastructure, not just convention.

### Recommendation

Create `AOS-AUTHORITY-001`:

Define action classes:

```text
capture_only
read_only
draft_artifact
external_network
repo_write
git_commit
deploy
delete_destructive
```

Add a central policy evaluator:

```text
requires_approval(action_type, target, sensitivity, capability)
```

Use it for:

- Voice promotions
- Research web egress
- Future repo write actions
- Deploy jobs
- PR actions
- Connector egress

### Acceptance Criteria

- Every high-impact route declares an action class.
- Routes can ask the Authority Engine whether approval is required.
- Dashboard shows pending authority actions.
- No destructive/write action can bypass authority policy.

## Finding 11 — Worker Dispatch Needs a Handler Registry and Capability-Aware Routing

### Severity

Medium-high

### Evidence

`apps/worker/app/worker.py` dispatches jobs with hardcoded conditionals:

```text
repository_scan
project_digest
council_review
research
else test job
```

This is sufficient for v0.1, but it will not scale to distributed nodes, capability routing, or plugin-style engines.

### Recommendation

Create `AOS-WORKER-ROUTER-001`:

- Introduce a job handler registry.
- Each handler declares:
  - job type
  - required capabilities
  - sensitivity support
  - retry policy
  - timeout policy
- Move job handlers into separate modules.
- Later connect handler eligibility to NodeCapability.

### Acceptance Criteria

- Adding a job type does not require editing a central `if/elif` chain.
- Unknown job type fails clearly rather than running the generic test job.
- Each handler records its capability needs.
- Worker logs include handler identity and job classification.

## Finding 12 — UI Visual System Is Strong but Needs Semantic Signal Expansion

### Severity

Medium

### Evidence

The design tokens intentionally restrict accents to blue/red/cyan/periwinkle. This creates a coherent cybernetic palette. However, warning states are forced into muted red because amber/yellow is banned. That weakens semantic distinction between “caution” and “danger.”

### Visual Diagnosis

The current palette is aesthetically strong. But operational dashboards need instant semantic scanning. If warning and danger are both red-family, the operator must read labels more often.

### Recommendation

Preserve the brand palette, but introduce non-color semantics:

- danger: solid red + filled dot + hard border
- warning: dashed red/periwinkle border + triangle icon + muted background
- info: periwinkle + square dot
- success: cyan + glow
- abstain/insufficient: dashed neutral + italic + hollow dot

Optionally allow one constrained amber token only for operational caution, not brand accent.

### Acceptance Criteria

- Warning and danger are distinguishable without reading text.
- Color-blind users can distinguish status by icon/shape/border.
- Existing red/cyan visual identity remains intact.

## Finding 13 — CommandDeck Inline CSS Is a Governance and Reuse Smell

### Severity

Medium

### Evidence

`CommandDeck.tsx` contains a large inline `<style>` block for a major visual component. The rest of the dashboard has moved toward tokenized shared design primitives.

### Why This Matters

Inline component CSS is fine for rapid mock-to-app porting, but it becomes difficult to audit, theme, reuse, and test as the component becomes central.

### Recommendation

Create `apps/web/src/features/command/CommandDeck.css` or a design-layer module:

- Move styles out of the component.
- Replace hardcoded values with `.aos-*` tokens where possible.
- Add responsive rules for ultrawide/phone directly in CSS.
- Add visual state classes for idle/listening/routing/speaking/error.

### Acceptance Criteria

- `CommandDeck.tsx` contains logic and markup, not a large style blob.
- CommandDeck uses shared tokens consistently.
- The component can be visually adjusted without touching TSX logic.

## Finding 14 — The Overview Surface Is Underpowered for an Executive Workspace

### Severity

Medium

### Evidence

The Executive workspace currently lands on Overview, but the overview appears to show runtime health and active project only, plus stale voice planned text. That does not yet match the Executive workspace vision: portfolio health, risk summary, roadmap, release readiness, major recommendations.

### Recommendation

Create `AOS-EXEC-001`:

Executive Overview should show:

- portfolio health score
- open risks
- pending decisions
- failed jobs
- stale docs/lessons
- highest-confidence reuse opportunities
- release readiness
- latest major changes
- next recommended action

### Acceptance Criteria

- Executive Overview answers “how healthy is the portfolio?”
- It is useful even before selecting a project.
- It links into the detailed workspace surfaces.

## Finding 15 — Research Engine Is Good, but Research Loop Is Not Mature Yet

### Severity

Medium-high

### Evidence

The Research Engine has a deterministic floor and a web tier. The next intended stage is multi-phase research: scope, search, fetch, verify, synthesize, cite, challenge, and update memory.

### Recommendation

Create `AOS-RESEARCH-003`:

Implement multi-phase research plans:

```text
ResearchPlan
- question
- sensitivity
- required_source_types
- search_queries
- verification_steps
- synthesis_policy

ResearchRun
- plan
- sources
- rejected_sources
- findings
- conflicts
- confidence
- open_questions
```

### Acceptance Criteria

- A research job records its search plan before fetching.
- Sources can be accepted/rejected with reason.
- Conflicting evidence is visible, not flattened.
- Synthesis cites sources and records open questions.

## Finding 16 — PR Guardian Is Strong but Needs a First-Class Dashboard Gate

### Severity

Medium

### Evidence

PR Guardian is active in CI and central to the repo. The dashboard has a planned PR Guardian Gate surface, but it is not live.

### Recommendation

Create `AOS-PRG-DASH-001`:

- Surface recent PR Guardian results.
- Show block/warn/pass trends.
- Link findings to lessons and work packages.
- Show accepted warnings and overrides.
- Add “why blocked” explanation for operator review.

### Acceptance Criteria

- Operator can inspect guardian state without opening GitHub Actions.
- Guardian findings can create lessons or work packages.
- Overrides are visible and auditable.

## Finding 17 — The Local/Free LLM Tier Is Well-Started but Needs Operator Policy UI

### Severity

Medium

### Evidence

The LLM router enforces that private tasks never route to free hosted models. That is excellent. But the operator cannot yet easily inspect or alter routing policy from the dashboard.

### Recommendation

Extend Providers & Model Routing:

- Show task class routing table.
- Show sensitivity constraints.
- Show available providers.
- Show last success/failure per provider.
- Show usage/cost/estimated flags.
- Add disabled controls or future toggles for policy editing.

### Acceptance Criteria

- Operator can tell which model tier will handle each task class.
- Private/free-hosted prohibition is visible in UI.
- Provider failures are visible and actionable.

## Vision Drift Review

### Positive Drift

These deviations are good and should stay:

- Moving faster into Knowledge Transfer than originally planned.
- Building the Control Tower visual system earlier than expected.
- Adding voice as a real capture/review layer.
- Adding local/free LLM routing to preserve Claude budget.
- Adding Research Engine web reach behind an explicit policy/off-by-default gate.
- Adding CI-green signal and self-healing workflows.

### Risky Drift

These deviations need control:

- Production-ish auto-deploy exists while “production deployment” remains listed out-of-scope.
- Many dashboard surfaces are live or planned before the core operator loop is simplified.
- Provider/connectors are multiplying without a central connector registry.
- State docs are growing long and contradictory.
- Voice capture is visually central but not reliably project-scoped.
- Agent/Engine/Authority models exist but are not yet enforcement infrastructure.

### True Drift to Avoid

Do not let ArchetypeOS become:

- A generic LLM dashboard.
- A collection of unrelated AI tools.
- A visual shell over ungoverned agents.
- A coding assistant that auto-edits without durable reasoning and approval.
- A repo scanner with a fancy UI but no decision loop.

The safest principle remains:

```text
Every new capability should either strengthen Research, Model, Decide, Verify, Learn, or the Control Plane that governs them.
```

## Connector Drift Review

### Current Connector/Provider Classes

| Connector | Current shape | Drift risk | Recommendation |
| --- | --- | --- | --- |
| Claude Code | Provider / CLI style | Token spend, ambient context, host dependency | show health and policy in Connector Registry |
| Local OpenAI-compatible | configured in settings | node-specific, no node registry | bind to NodeCapability |
| Free hosted LLM pool | env-driven rotating provider | quota/privacy/failure visibility | central connector health and quota status |
| Groq Orpheus TTS | server-side API | external speech data egress | classify as public/voice connector |
| Sotto STT | browser WebSocket | browser-exposed token, tailnet assumption | label token as client-side or proxy through API |
| Exa | discovery provider | rate limit, external egress | connector registry + quota policy |
| SearXNG | self-hosted discovery | config health | node/service health surface |
| crawl4ai | self-hosted fetch | browser runtime resource | profile health and limits |
| Firecrawl | hosted fetch fallback | external egress | explicit policy and disabled-by-default state |
| GitHub CI/PR Guardian | CI connector | strong but external | dashboard PR Guardian Gate |

### Connector Registry Minimum Viable Fields

```text
name
connector_type
enabled
configured
health
privacy_class
can_receive_private_data
browser_exposed
quota_limit
quota_remaining
last_success_at
last_error
policy_doc
```

## UI/UX Deep Review

## Visual Strengths

- The dark command-deck palette is distinctive.
- The scoped `.aos-*` design layer prevents accidental global styling.
- The rail shell makes the product feel like an operating environment.
- The CommandDeck orb creates a strong identity and emotional center.
- The confidence meter and pills are reusable primitives.
- Responsive tiers show awareness of ultrawide, desktop, tablet, and phone usage.
- `prefers-reduced-motion` is respected, which is important for the animated UI.

## Visual Weaknesses

- Too many inactive “soon” controls compete with live work.
- Warning/danger semantics are too close because warnings are red-family.
- The dashboard needs more “attention management”: pending, failed, blocked, needs evidence.
- The CommandDeck is visually dominant but not yet functionally central enough.
- Some legacy/quarantine comments and stale UI copy remain.
- The project selector in the rail may become cramped as project count grows.
- The Executive workspace is underdeveloped.

## Recommended Dashboard Hierarchy

### Global Shell

```text
Topbar:
- current project
- system health
- pending approvals
- failed jobs
- provider tier
- node health
- command palette
```

### Operations

```text
Command
Voice Inbox
Live Activity
Nodes / Runtime
Providers / Connectors
Scheduling
Digest
```

### Council

```text
Awaiting You
Council Reviews
Final Judge
PR Guardian Gate
Work Packages
Authority Log
```

### Architect

```text
Repositories
Architecture Studio
Reuse
Tech Fitness
Recommendations
Digital Twin
```

### Research

```text
Research Inbox
Knowledge
Distillation
Knowledge Graph
Docs Freshness
Signals
```

### Executive

```text
Portfolio Health
Roadmap
Release Readiness
Risk Summary
Reports
```

### Builder

```text
Claude Code Bridge
Work Package Runner
Test/CI
Simulation Lab
```

## Code Architecture Review

## Backend Strengths

- Domain services are emerging cleanly: voice, research, transfer, council, usage, scan, digest.
- Settings are centralized and default to deterministic/off states.
- Read-only repository mounts are preserved in Compose.
- Research web tier is explicitly off by default.
- LLM router enforces privacy against free-hosted models.
- Models capture many future entities already.
- CI is broad and meaningful.

## Backend Weaknesses

- Agent/Engine/Authority models are skeletal and not yet connected to flows.
- Job dispatch is hardcoded and not capability-aware.
- Connector/provider health is not modeled.
- Authority policy is not central.
- Some comments are stale after later slices landed.
- Some API schemas lag core models.

## Frontend Strengths

- Shell and workspace data structure are cleanly separated from rendering.
- Visual system is scoped and tokenized.
- Feature views are being split out for new surfaces.
- Voice/Research/Approvals/Providers/Activity are separate feature modules.
- Error/loading/empty states are considered in recent PRs.

## Frontend Weaknesses

- `main.tsx` is now too large and owns too much state.
- `renderView` centralizes many screens in one component.
- Data fetching is manual and fan-out heavy.
- No URL routing or deep links.
- No query cache / invalidation layer.
- CommandDeck styles are embedded inside TSX.
- Some frontend types are thinner than backend schemas.

## Recommended Frontend Refactor

Create `AOS-WEB-SPINE-001`:

```text
src/app/AppShell.tsx
src/app/projectContext.tsx
src/app/queryClient.ts
src/views/OverviewView.tsx
src/views/RepositoriesView.tsx
src/views/ArchitectureView.tsx
src/views/CouncilView.tsx
src/views/DigestView.tsx
src/views/SchedulingView.tsx
```

Introduce:

- Project context provider.
- View-local hooks.
- A query/cache layer (TanStack Query or a small internal equivalent).
- URL route state for active mode/view/project.
- Shared empty/error/loading primitives.

Acceptance criteria:

- `main.tsx` becomes app bootstrap only.
- Each major view owns its own data fetching.
- Project selection is available via context.
- CommandDeck can access selected project.
- Browser reload preserves active view/project.

## Recommended Work Packages

## P0 — AOS-STATE-RECON-001: Canonical State Reconciliation

Goal: eliminate contradictory state docs and stale UI copy.

Acceptance criteria:

- State docs agree.
- Stale active branch removed.
- Current objective reflects actual post-v0.1 status.
- Overview voice text corrected.
- Review artifact linked from recent changes or appropriate index.

## P0 — AOS-VOICE-PROJECT-001: Project-Scoped CommandDeck Turns

Goal: make CommandDeck voice turns respect selected project.

Acceptance criteria:

- `CommandDeck` receives selected project id/name.
- `postVoiceTurn` includes project id.
- Voice Inbox item is project-linked.
- Approving research/decision commands promotes successfully.
- UI labels global vs project-scoped capture.

## P0 — AOS-CONTRACT-001: Surface Rich Backend Evidence in API/Web

Goal: stop dropping intelligence at API/frontend seams.

Acceptance criteria:

- Repository DNA exposes purpose/frameworks/runtime_services.
- Web types match backend schemas.
- Architecture edges render from/to/confidence/evidence/manual corrections.
- Research notes expose sources/findings/status.
- Tests cover contract rendering.

## P1 — AOS-NODE-001: Node and Capability Registry MVP

Goal: make distributed runtime first-class.

Acceptance criteria:

- Node model and capabilities exist.
- Register/heartbeat/list routes exist.
- Nodes / Runtime dashboard surface is live.
- Default node write access is false.
- Capability declarations can be used by future job routing.

## P1 — AOS-CONNECTOR-001: Connector Registry and Policy Center

Goal: govern external/internal connectors centrally.

Acceptance criteria:

- Connector registry model exists.
- Providers/connectors show configured/enabled/health/privacy/browser-exposed state.
- Sotto token exposure policy is explicit.
- Research and LLM connector health visible.
- Connector policy doc exists.

## P1 — AOS-WORKER-ROUTER-001: Job Handler Registry

Goal: replace hardcoded worker dispatch.

Acceptance criteria:

- Job handlers self-register.
- Unknown job type fails clearly.
- Handlers declare capability/sensitivity/retry policy.
- Worker logs handler identity.
- Ready for NodeCapability matching.

## P1 — AOS-ARCH-STUDIO-001: Editable Architecture Corrections

Goal: convert architecture from read surface into editable model.

Acceptance criteria:

- Node/edge correction drawer.
- Persist manual corrections.
- Rescan preserves corrections.
- Evidence/confidence visible.
- Council can consume corrected graph.

## P2 — AOS-UX-IA-001: Dashboard IA and Attention Management

Goal: make Control Tower guide the operator.

Acceptance criteria:

- Global status strip.
- Planned drawer replaces most `soon` noise.
- Now/Next/Blocked per workspace.
- Semantic status shapes/icons.
- Keyboard command palette.

## P2 — AOS-AUTHORITY-001: Authority Action Policy

Goal: enforce approval requirements as infrastructure.

Acceptance criteria:

- Action classes defined.
- Policy evaluator exists.
- High-impact routes declare action class.
- Pending authority actions visible.
- No destructive/write path bypasses policy.

## P2 — AOS-RESEARCH-003: Multi-Phase Research Loop

Goal: mature research from ranked dossier to repeatable investigation workflow.

Acceptance criteria:

- Research plans are persisted.
- Search/fetch/verify/synthesize phases recorded.
- Rejected sources and conflicts visible.
- Findings cite accepted sources.
- Open questions become follow-up work.

## Recommended Build Order

```text
1. AOS-STATE-RECON-001
2. AOS-VOICE-PROJECT-001
3. AOS-CONTRACT-001
4. AOS-NODE-001
5. AOS-CONNECTOR-001
6. AOS-WORKER-ROUTER-001
7. AOS-ARCH-STUDIO-001
8. AOS-UX-IA-001
9. AOS-AUTHORITY-001
10. AOS-RESEARCH-003
```

Rationale:

- State reconciliation prevents new-agent confusion.
- Voice/project and contract fixes close concrete bugs/gaps immediately.
- Node and connector registries restore the distributed-system vision.
- Worker routing, architecture editing, and authority policy make the platform durable.
- UX/IA cleanup should happen after the core data/contract gaps are fixed.
- Research phase-3 is high value but depends on connector/policy clarity.

## Final Assessment

ArchetypeOS is in a promising but delicate phase. The system has achieved enough that the next mistake would be overbuilding sideways. The repo should now consolidate into a clearer operating spine:

```text
Capture -> Evidence -> Model -> Council -> Decision -> Approval -> Execution -> Verification -> Learning
```

The dashboard should become the operator’s attention engine. The backend should make nodes, connectors, actions, and authority first-class. The frontend should stop dropping rich backend evidence. The state docs should become concise and canonical again.

The current repo is not failing. It is succeeding fast enough that integration discipline is now the product.
