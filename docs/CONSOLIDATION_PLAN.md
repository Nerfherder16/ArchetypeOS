# ArchetypeOS Consolidation Plan (AOS-REVIEW-001 execution)

## Purpose

The 2026-07-08 system evaluation (AOS-REVIEW-001, `knowledge/wiki/reviews/2026-07-08-archetypeos-system-evaluation.md`, PR #117) found ArchetypeOS strong and ahead of scope, with one systemic risk: **integration coherence is lagging feature velocity**. This is the plan to work the eval's findings back into a coherent product spine, in priority order, *without* over-building sideways (the eval's core warning). It is the shared roadmap for all lanes (laptop Orchestrator, cloud session, review lane).

## Definition of "back on track"

The operating spine the eval names becomes real and coherent:

```text
Capture -> Evidence -> Model -> Council -> Decision -> Approval -> Execution -> Verification -> Learning
```

Concretely: the dashboard shows the intelligence the backend already computes; voice/project flow is correct; the distributed-agent vision (nodes, connectors, capability routing) is first-class in code; the operator has one guided loop; and drift (state, contract) can no longer accumulate silently.

## Guiding principles

1. **Consolidation over surface.** No new "soon" surface ships before the coherence gaps behind the live ones are closed.
2. **Convert invisible capability into operator-visible value** before adding new capability.
3. **Review-first, tested, Guardian-gated** per package; each is its own PR (or small PR chain).
4. **One package per lane at a time.** Do not open all ten. The eval itself warns this is the moment over-building would hurt.
5. **Prevent re-drift by construction** (auto-derivation, coherence probes) rather than by discipline alone.

## Standing (already done since the eval)

- ✅ **AOS-STATE-RECON-001** (P0) — canonical `CURRENT_STATE` + auto-derive drift assurance, generalized into the reusable `state-hygiene` action. Finding 1 **closed**. (#122)

## Phased plan

Effort: S (≈1 PR, <½ day) · M (1–2 PRs) · L (multi-PR).

### Phase 1 — Close the concrete gaps (rest of P0)

| Package | Goal | Effort | Why now |
| --- | --- | --- | --- |
| **AOS-VOICE-PROJECT-001** | CommandDeck passes `selectedProjectId` into `postVoiceTurn`; UI distinguishes project-scoped vs global capture | S | A known bug in our own AOS-VOICE-002; silently weakens AOS-VOICE-005 promotion. Cheapest high-value fix. |
| **AOS-CONTRACT-001** | Surface the rich backend evidence at the API/web seam (RepositoryDNA purpose/frameworks/runtime_services; full ArchitectureEdge fields; ResearchNote sources/findings); TS types match schemas | M | "Invisible capability": the backend computes intelligence the UI throws away. Highest visible-value/effort ratio. |

Exit: Finding 4 and Finding 6 closed; the dashboard shows DNA/edge/research evidence; a project-scoped voice command promotes correctly end to end.

### Phase 2 — Make the distributed vision first-class (P1 backbone)

| Package | Goal | Effort | Why now |
| --- | --- | --- | --- |
| **AOS-WORKER-ROUTER-001** | Replace the hardcoded worker `if/elif` with a self-registering handler registry (handlers declare capability/sensitivity/retry) | S–M | Cheap enabler; unknown job types fail clearly; prerequisite for capability-aware node routing. Pull it ahead of the registries. |
| **AOS-NODE-001** | Node + Capability + Heartbeat models, register/heartbeat/list routes, Operations→Nodes surface; default node write-access false | L | The eval's biggest maturity gap (distributed-agent 4/10). Turns "local control plane + providers" into a node network. |
| **AOS-CONNECTOR-001** | Connector registry + policy center (configured/enabled/health/privacy/browser-exposed; explicit Sotto-token policy; LLM/research connector health) | M–L | Governs connectors as first-class assets (Finding 9). Depends on the registry pattern from NODE-001. |

Exit: distributed-agent maturity moves from 4/10 toward first-class; jobs can declare required capabilities; connector health + privacy posture is visible and governed.

### Phase 3 — Editable model + enforced safety

| Package | Goal | Effort | Why now |
| --- | --- | --- | --- |
| **AOS-ARCH-STUDIO-001** | Editable architecture corrections (node/edge drawer, persist `manual_correction`, survive rescan, feed Council) | M | Turns the architecture graph from evidence into a correctable digital twin (Finding 7). |
| **AOS-AUTHORITY-001** | Authority action policy enforced as infrastructure (action classes, policy evaluator, no write path bypasses it) | M–L | Makes "human approval for destructive actions" a system invariant, not a convention (Finding 10). |

### Phase 4 — Operator experience + research depth

| Package | Goal | Effort | Why now |
| --- | --- | --- | --- |
| **AOS-WEB-SPINE-001** | Split `main.tsx` into app bootstrap + per-view modules; project context provider; query/cache layer; URL routing | L | Enabler: the project context it introduces is what AOS-VOICE-PROJECT-001 and the UX work want. Can be pulled earlier if the frontend churn blocks Phase 1. |
| **AOS-UX-IA-001** | Global operator status strip; Planned drawer replaces most "soon" chips; Now/Next/Blocked per workspace; command palette | M | The "control room -> control tower" upgrade (Findings 2/3/12). After data/contract coherence, per the eval. |
| **AOS-RESEARCH-003** | Multi-phase research loop (persisted plan; search/fetch/verify/synthesize recorded; open questions -> follow-ups) | L | Matures research from ranked dossier to repeatable investigation (Finding 15). Depends on connector/policy clarity. |

### Cross-cutting (optional, on-theme)

- **AOS-SELFHEAL-005 — coherence probe.** The self-learn nightly grows a probe that flags contract-lag (frontend type thinner than backend schema) and state-drift signals automatically — so the class of gap the eval found by hand is caught by the system going forward. Ties Phase 1's lessons back into the loop.

## Recommended build order

```text
1. AOS-VOICE-PROJECT-001   (P0, S)   ← start here
2. AOS-CONTRACT-001        (P0, M)
3. AOS-WORKER-ROUTER-001   (P1, S–M)
4. AOS-NODE-001            (P1, L)
5. AOS-CONNECTOR-001       (P1, M–L)
6. AOS-ARCH-STUDIO-001     (P1, M)
7. AOS-AUTHORITY-001       (P2, M–L)
8. AOS-WEB-SPINE-001       (enabler, L)  — pull earlier if UX/voice churn demands it
9. AOS-UX-IA-001           (P2, M)
10. AOS-RESEARCH-003       (P2, L)
```

This tracks the eval's order with two deliberate adjustments: **WORKER-ROUTER pulled ahead** of the registries (cheap, unblocks capability routing), and **WEB-SPINE** flagged as a movable enabler.

## Tandem-lane coordination

- This doc + the eval are the canonical roadmap; the package tickets live in `docs/ACTIVE_WORK.md` (Proposed).
- One package per lane at a time; claim by moving its ACTIVE_WORK entry to In Progress with the owning lane.
- Shared-doc edits stay union-safe (the four `merge=union` coordination docs); state stays canonical (auto-derived).

## How we avoid re-drifting

- State drift: closed by construction (AOS-STATE-RECON-001 auto-derivation).
- Contract drift: AOS-CONTRACT-001 aligns types now; AOS-SELFHEAL-005 (optional) keeps them aligned.
- Scope drift: this plan is the gate — no Phase N+1 package starts while a Phase N coherence gap is open.

## Status

- Phase 0: ✅ complete (AOS-STATE-RECON-001).
- Phase 1: ready to start at AOS-VOICE-PROJECT-001.
