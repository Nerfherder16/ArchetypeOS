# ArchetypeOS Vision Drift & Intelligence-Loop Re-Centering — AOS-REVIEW-003

Date: 2026-07-11
Reviewer: Opus orchestrator (cloud session, `claude/archetypeos-vision-realignment-6psujb`)
Scope: original product vision vs. current `main`; code-reality of the engineering-intelligence loop; re-centering roadmap
Artifact type: strategic system evaluation / re-centering handoff response
Status: advisory; no runtime changes in this change set

## Verification Metadata

Verification Status: Verified with warnings
Verification Level: Level 1 (repository inspection; no runtime/Playwright/Docker/visual QA)
Verification Method: Read of the governing docs (Constitution, Context, System Architecture, Master Roadmap, Engine/Agent catalogs, CURRENT_STATE, RFC-0005) and two delegated read-only code inventories over `apps/`, `packages/aos_core`, `tools/`, cross-checked against RFC-0005, AOS-REVIEW-001 (2026-07-08), and AOS-REVIEW-002 (LES-033). Every engine/seam claim is anchored to a concrete file path.
Evidence: `packages/aos_core/aos_core/services/{scan,research,research_run,council,decisions,adr,digest,knowledge,transfer,verifier,code_review}.py`; `apps/worker/app/handlers/registry.py`; `apps/api/app/routes/{decisions,council,research,research_plans,architecture,knowledge}.py`; `packages/aos_core/aos_core/models.py`; `tools/pr_guardian.py`; `docs/rfc/RFC-0005-...md`; `docs/CURRENT_STATE.md`; `knowledge/wiki/reviews/2026-07-08-archetypeos-system-evaluation.md`; `knowledge/wiki/lessons/LES-033.md`.
Limitations: Static inspection only — no app was launched, no test suite run, no live council/research invocation. "MISSING"/"STUB" verdicts are from grep + source read (high confidence, but the absence of a runtime probe means a well-hidden call site cannot be fully excluded). No claim here about visual/UX quality.
Required Next Verifier: Operator or Runtime Agent to confirm the "no path from approved Decision to a build job" finding by attempting the flow on the live control plane.

---

## Summary

The re-centering handoff's thesis is **correct and corroborated by the repository's own record**: ArchetypeOS has not abandoned its vision. It embodies its founding principles (evidence over opinion, architecture-first, research-before-implementation, local-first, human approval, persistent memory, distributed specialist agents, deterministic verification, model routing). The drift is not conceptual — it is in **sequencing, integration, enforcement, and emphasis**. The system was built outside-in: the shell (control plane, governance, verification, dashboard, registries, deploy) is more mature than the intelligence workflow it exists to serve.

Concrete, evidence-backed refinement of the handoff's estimate:

- **Conceptual alignment: ~78%** — the founding principles are intact and largely encoded.
- **Operational alignment: ~50%** — the *intelligence loop* runs end-to-end only for its **left-of-decision half**.

The defining product workflow —

```
understand → inspect → model → identify risk → research → compare → recommend
→ record decision → plan → execute → verify → observe → retain
```

— is genuinely wired and reachable **only from `inspect` through `record decision`**. Everything to the right of an approved decision (`plan → execute → verify → retain`) is missing or off to the side. This is the same failure mode the operator's own AOS-REVIEW-002 found in the *shell* ("entities exist as data but sit on zero execution paths", LES-033) — reproduced in the *brain*.

The re-centering is therefore not a rebuild and not a simplification. It is: **(1) close five specific broken seams so the loop becomes one runtime spine; (2) give real engines to the intelligence stages that are currently names; (3) do it on top of the enforcement rails the REVIEW-002 wave is already laying.**

---

## Evidence

### 1. The vision is intact and encoded (not drifted conceptually)

- `docs/ENGINEERING_CONSTITUTION.md` (Articles I–XX) and `docs/ARCHETYPEOS_CONTEXT.md` still define ArchetypeOS as "an engineering reasoning platform before it is a build tool."
- The **left-of-decision spine is real and reachable**, not mocked: `scan → architecture model → research note → council → draft decision → human approve → ADR/KnowledgePage → digest`, each behind a real route, a durable job queue, and idempotent worker handlers:
  - inspect: `services/scan.py`, `apps/worker/app/handlers/repository_scan.py`, `POST /scans`
  - model: `services/scan.py` builds `ArchitectureNode`/`ArchitectureEdge`; `routes/architecture.py` GET graph + PATCH corrections
  - research: `services/research.py:417 research()` (deterministic evidence floor) reachable via `POST /projects/{id}/research → enqueue_job("research")`
  - council: `services/council.py` runs 4 personas + Final Judge (RFC-0005), abstains on thin evidence
  - decide: `services/decisions.py draft_decision_from_review()` / `approve_decision`, `services/adr.py export_decision_adr`, gated by `ApprovalRecord` — **the best-wired seam in the system**
- Governance/verification culture is strong: PR Guardian (`tools/pr_guardian.py`), Verification Protocol, lessons (`knowledge/wiki/lessons/`, 57 files), model routing (`services/llm_router.py`, ADR-0001).

This is why the verdict is "re-center," not "rescue."

### 2. The intelligence loop is a left-of-decision spine bolted to disconnected right-of-decision capabilities

Per-stage reality (delegated inventory, file-anchored):

| Stage | Status | Wired? |
|---|---|---|
| inspect repositories | IMPLEMENTED (`scan.py`, `repository_scanner.py`) | → model |
| architecture model | PARTIAL — from repos only; text/image ingestion MISSING | → council |
| identify risk | STUB — DNA `risk_flags` only; `Risk` table unused | weak |
| research | IMPLEMENTED (floor) + PARTIAL (multi-phase run) | note→council; **run→council broken** |
| compare options | STUB — council personas only, no Fitness engine | in-council only |
| recommend | STUB — `Recommendation` CRUD, **no generator** | ISOLATED |
| record decision | IMPLEMENTED (`decisions.py`, `adr.py`) | ✅ core spine |
| implementation plan | **MISSING** — no model/service/job | ❌ hard break |
| execute via governed agents | **MISSING** — no build/execute job type | ❌ hard break |
| verify | ISOLATED — `verifier.py`, `pr_guardian.py` are CLI/CI only | not in runtime loop |
| observe | PARTIAL — `digest.py build_digest` | reads decisions/recs/lessons |
| retain lessons | PARTIAL — lessons hand-authored; no auto-generation | no runtime learn-back |

### 3. Six documented "engines" are names without engines

- **Engineering Evaluation Standard** — reduced to scanner DNA flags; `Evaluation`/`Risk`/`Benchmark`/`Experiment` models exist (`models.py:440-491`) but no service constructs or exposes them.
- **Technology Fitness Engine** — exists only as a council persona string (`council.py:182`); no score, route, or model.
- **Recommendation Intelligence** — `Recommendation` is hand-written CRUD (`routes/decisions.py:136-172`); nothing derives recommendations; only `digest.py` reads them.
- **Design Intelligence** — MISSING (only a voice-intent label `"design_note"`).
- **Evolution Engine** — MISSING; nothing revisits decisions as costs/tools/models change (Article X, Roadmap Phase 7 unbuilt).
- **Architecture Spine Graph** — MISSING; the graph is a flat parent/child node set, not a spine layout.

### 4. The five broken seams (the actionable core)

1. **Decision → Plan (hard break).** An approved `Decision` has no consumer that produces an implementation plan. `routes/decisions.py` ends at ADR export. The loop dead-ends at "record decision."
2. **Plan → Execute (hard break).** No build/execute job type; `handlers/registry.py:60-67` registers only `repository_scan, project_digest, council_review, research, research_run, test`. The "governed agents" (`agents/*/CLAUDE.md`) are prose contracts with no runtime dispatch.
3. **Execute → Verify (isolation).** `verifier.py` / `pr_guardian.py` run only in CLI/CI; unreachable from the API/worker; a runtime build result is never verified inside the loop.
4. **Verify → Retain (break).** Lessons are hand-authored markdown, only *ingested* (`knowledge.py`); nothing generates a lesson from a runtime failure/verification result.
5. **Deep research run → Council (data-type mismatch).** `execute_research_run` persists a `ResearchRun`, but the council evidence selector reads only `ResearchNote`/`Decision` (`council.py:73-92`) — so the multi-phase research output never becomes council evidence. (This is the cheapest fix and the highest immediate leverage.)

### 5. The emphasis record confirms the outside-in sequencing

- The last ~40 PRs were the AOS-REVIEW-001 consolidation backlog (**8 SHELL / 2 BRAIN**) plus a self-healing/nightly-probe infrastructure arc — nodes, connectors, authority, worker-router, contract seam, voice, web-spine, UX-IA.
- The BRAIN core (distillation RFC-0008, transfer RFC-0009, embeddings, council RFC-0005) was **front-loaded and largely merged**, then development rotated to shell/governance/operator-experience.
- AOS-REVIEW-001 named the spine `Capture → Evidence → Model → Council → Decision → Approval → Execution → Verification → Learning` and warned the next failure mode is "overbuilding sideways." AOS-REVIEW-002/LES-033 found the shell's registries/authority "sit on ZERO execution paths." **This review extends that exact finding to the brain's right half.**

---

## Recommendation

Re-center the next development phase on **closing the loop across the decision line**, in three waves, built on the REVIEW-002 enforcement rails. Do **not** re-propose the SHELL packages REVIEW-002 already covers; this roadmap is strictly the BRAIN/right-of-decision complement.

**Wave A — cheap seam repair (unblock the existing spine now, low risk):**

- **AOS-RESEARCH-COUNCIL-001** (P0) — make `execute_research_run` also emit a `ResearchNote` (or teach the council selector to read `ResearchRun`). Closes seam #5. Small, isolated, immediately improves council evidence quality. Also relieves the LES-019 "scan is not research" pressure by letting real research reach the council.

**Wave B — extend the loop across the decision line (the core re-centering):**

- **AOS-BUILD-PLAN-001** (P0) — Build Intelligence, stage 1. An `ImplementationPlan` model + `plan_from_decision()` service + `POST /decisions/{id}/plan`: an approved decision becomes a structured, governed, **draft-only** plan (tasks, acceptance criteria, target repo, risk, required verification). Closes seam #1. **No code execution** — safe to build immediately; useful even while execution stays human.
- **AOS-BUILD-EXEC-001** (P1, high-risk, gated) — a governed `build`/`execute` job handler that hands an approved plan to the `ClaudeCodeProvider`/builder **through the Authority execution envelope**, with mandatory human approval, writing results back. Closes seam #2. **Depends on `AOS-AUTHORITY-ENVELOPE-001` (REVIEW-002 P0-6) and `AOS-JOBS-RELIABILITY-001`** — this is where Articles IX & XIX bite hardest; it must not exist before the enforcement chokepoint does.
- **AOS-VERIFY-RUNTIME-001** (P1) — make the deterministic verifier / Guardian reachable from the worker so a build result is verified inside the loop, producing a verification record on the plan/decision. Closes seam #3.
- **AOS-LESSON-AUTO-001** (P2) — auto-generate a lesson/`KnowledgePage` from a runtime verification failure or build outcome. Closes seam #4. Reuse the self-heal probe machinery, which already does this for meta-development.

**Wave C — deepen the thin middle and close the evolution tail:**

- **AOS-RECO-ENGINE-001** (P2) — turn `Recommendation` from vestigial CRUD into a real generator that derives recommendations from research + scan + a minimal **Technology Fitness** scoring pass. Gives Technology Fitness and Recommendation Intelligence real engines; closes the `compare → recommend` gap.
- **AOS-EVOLVE-001** (P2) — Evolution Engine: decision-staleness detection + scheduled re-evaluation (Article X, Roadmap Phase 7), reusing the existing scheduler.
- **AOS-COUNCIL-REALRUN-001** (P2) — a governed, continuous (scheduled/operator-triggered) real-model council run on the authed node so the brain is *exercised*, not only run deterministically in CI. Builds on the existing pydantic-ai real-run demonstration (`docs/COUNCIL_REALRUN_PYDANTIC_AI.md`).

**Honestly deferred (documented-but-unbuilt; defer with intent, do not pretend they exist):** Design Intelligence (no engine), Architecture Spine Graph (spine rendering), Engineering Evaluation Standard (production-readiness scoring beyond DNA), Architecture Studio text/image ingestion.

**Critical path:** `AOS-RESEARCH-COUNCIL-001` + `AOS-BUILD-PLAN-001` can start now. `AOS-BUILD-EXEC-001` waits on the REVIEW-002 authority/jobs wave. Then `VERIFY-RUNTIME → LESSON-AUTO`. Depth layer (RECO/EVOLVE/REALRUN) last.

---

## Alternatives considered

- **A1 — Keep consolidating the shell (continue the REVIEW-001/002 trajectory).** Pro: finishes runtime integrity; low novelty risk. Con: deepens the exact imbalance both prior reviews warned about — a superbly-governed system that still can't turn a decision into a validated build. Rejected as the *primary* focus (but REVIEW-002 must still finish, as the rails Wave B rides on).
- **A2 — Build the missing engines breadth-first (Fitness, Recommendation, Design, Evolution, Spine Graph all at once).** Pro: makes the catalog "true." Con: re-commits the outside-in mistake at the engine layer — many shallow engines, still no closed loop. Rejected; engines are pulled in by the loop (Wave C) only where a seam needs them.
- **A3 — Jump straight to autonomous build/execute.** Pro: most visibly "finishes the brain." Con: violates Articles IX/XIX if it precedes the authority execution envelope; REVIEW-002/LES-033 shows enforcement is not yet load-bearing. Rejected as a starting point; sequenced behind the rails.
- **Chosen (A4) — Seam-first, rails-aware, loop-closing.** Fix the cheapest broken seam first, open the right half with a no-execution plan model, then add governed execution only atop the enforcement envelope. Preserves all existing architecture; adds the minimum to make the organism behave as one system.

## Pros and cons of the recommendation

- Pros: every package closes a *named, file-anchored* seam; preserves the differentiated architecture (nothing is torn down); reuses REVIEW-002 rails rather than duplicating them; each wave is independently valuable; safety-first sequencing keeps Articles IX/XIX intact.
- Cons: Wave B's execution package is genuinely hard and gated on other in-flight work; the depth engines (Wave C) remain deferred, so the engine catalog stays partly aspirational until then; requires discipline to not rotate back to shell work.

## Risk

- **Highest risk: `AOS-BUILD-EXEC-001`** introduces runtime code execution. Mitigation: mandatory Authority execution envelope + human approval + audit + rollback before any write; build only after `AOS-AUTHORITY-ENVELOPE-001` lands; start read-only/dry-run.
- **Medium: scope creep** back into shell work. Mitigation: this review's backlog is the BRAIN filter — any new capability must strengthen a loop stage.
- **Low: the cheap seam fixes** (Wave A) are near-zero risk and should ship first to demonstrate momentum.

## Effort

- Wave A: small (1 focused package).
- Wave B: medium→large (`BUILD-PLAN` medium; `BUILD-EXEC` large + gated; `VERIFY-RUNTIME`/`LESSON-AUTO` medium).
- Wave C: medium each, deferrable.

## Dependencies

- **In-flight (must finish first for Wave B):** `AOS-AUTHORITY-ENVELOPE-001`, `AOS-JOBS-RELIABILITY-001`, `AOS-SCHEDULER-RELIABILITY-001` (the REVIEW-002 wave).
- Existing substrate reused: durable job queue (`handlers/registry.py`), `ClaudeCodeProvider` seam (RFC-0005), scheduler, self-heal probe machinery, `ApprovalRecord`/`AuthorityGrant`.
- Each Wave-B/C package should get its own RFC (the repo's convention; RFC-0005 is the model for the intelligence layer).

## Acceptance criteria (for the re-centering, not any single package)

- A human can follow a single reachable path from an approved `Decision` to a governed implementation plan to a verified build result to an automatically-retained lesson — through real routes, not CLI tooling.
- `execute_research_run` output reaches the council as evidence.
- `Recommendation` rows are generated by an engine, not only hand-written.
- Every "engine" claimed present in `docs/ENGINE_CATALOG.md` either has a real service behind it or is explicitly marked deferred in that catalog (no silent aspiration).
- No execution path performs a write without passing the Authority envelope + human approval.

## Next steps

1. Land this assessment + the proposed BRAIN backlog in `docs/ACTIVE_WORK.md` (this change set).
2. Operator triage: confirm wave ordering and that Wave B rides the REVIEW-002 rails.
3. On approval, write `RFC-00XX — Build Intelligence (Decision → Plan → Execute)` and start `AOS-RESEARCH-COUNCIL-001` (cheap seam) in parallel with `AOS-BUILD-PLAN-001`.
4. Reconcile `docs/ENGINE_CATALOG.md` to mark the six name-only engines as deferred, so the catalog stops overstating (Article XII, engineering integrity).

## Final Judge verdict

**Re-center, do not rebuild.** The vision holds; the architecture is differentiated and worth preserving. The single most important structural fact is that the engineering-intelligence loop dead-ends at "record decision," and the documented `build → execute → verify → learn` half exists as CLI/CI tooling and empty tables rather than as one governed runtime spine. Finish the loop across the decision line — seam-first, on the enforcement rails the REVIEW-002 wave is laying — and the skeleton, nervous system, immune system, and control room finally get the brain they were built to serve.
