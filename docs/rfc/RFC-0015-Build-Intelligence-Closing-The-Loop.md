# RFC-0015 — Build Intelligence: Closing the Loop (Decision → Plan → Execute → Verify → Learn)

## Status

Proposed (2026-07-11). Motivated by AOS-REVIEW-003 (`knowledge/wiki/reviews/2026-07-11-vision-drift-and-recentering.md`), which verified against `main` that the engineering-intelligence loop is wired end-to-end only for its **left-of-decision** half. This RFC anchors the **right-of-decision** arc — the BRAIN complement to the REVIEW-002 shell-integrity wave (RFC-0014, AOS-WORKER-HANDLERS-001, AOS-AUTHORITY-ENVELOPE-001). It does not duplicate that wave; it rides its rails.

## Summary

Today an approved `Decision` is a dead-end: `apps/api/app/routes/decisions.py` ends at ADR export, and the worker registers only `repository_scan, project_digest, council_review, research, research_run, test` (`apps/worker/app/handlers/registry.py:60-67`). There is no path from a decision to an implementation plan, from a plan to a governed build, from a build to runtime verification, or from a failure to a retained lesson. Five of the twelve catalog engines are names without engines (AOS-REVIEW-003 §3).

This RFC introduces **Build Intelligence**: the missing right half of the loop, as five governed, individually-shippable increments that reuse the existing substrate (the durable job queue, the `Provider` seam from RFC-0005, the **already-live** Authority execution envelope, the deterministic verifier, and the self-heal probe machinery). The governing constraints are unchanged: **advisory/draft-by-default, human approval before any write, deterministic verification preferred over inference, hermetic in CI.** No autonomous action is introduced — every write passes the Authority envelope and an explicit human approval.

The end state is one reachable spine:

```
approved Decision → ImplementationPlan (draft) → human approve
→ governed build_execute job (Authority envelope) → BuildRun (diff/result)
→ runtime verification (verifier + Guardian) → VerificationRecord
→ on failure: auto-generated lesson → KnowledgePage
```

## Problem

Verified against `main` (AOS-REVIEW-003, file-anchored):

- **Decision → Plan (hard break).** `services/decisions.py` approves a `Decision` (status `draft → approved`, writes an `ApprovalRecord`) and `services/adr.py export_decision_adr` renders an ADR — but nothing consumes an approved decision to produce an implementation plan. No plan model/service/route exists.
- **Plan → Execute (hard break).** No `build`/`execute` `job_type`; `registry.py` has no builder handler. The "governed agents" under `agents/*/CLAUDE.md` are prose contracts with no runtime dispatch.
- **Execute → Verify (isolation).** `services/verifier.py` and `tools/pr_guardian.py` run only from the CLI/CI; they are unreachable from the worker and never verify a runtime build result.
- **Verify → Learn (break).** Lessons are hand-authored markdown, only ingested by `services/knowledge.py`. Nothing generates a lesson from a runtime failure. (The self-heal nightlies do this for *meta-development* — that machinery is the template.)
- **Research run → Council (data-type mismatch).** `execute_research_run` (`services/research_run.py:68`) writes a `ResearchRun`, but the council evidence selector (`services/council.py:73-92 _select_research`) reads only `ResearchNote` + `Decision`. Deep multi-phase research never becomes council evidence. This starves the very stage (`compare/recommend`) that feeds decisions.

## Goals

- A reachable, governed path from an approved `Decision` to a verified build result, through real API routes and the durable job queue — not CLI tooling.
- Every stage **draft/advisory by default**; every write gated by the Authority execution envelope + explicit human approval (Constitution IX, XIX).
- Deterministic verification of build results **inside the runtime loop**, not only in CI (Article VIII).
- Automatic lesson retention from runtime failures (Article XIII).
- Deep research reaches the council as evidence (fixes the starvation of the compare/recommend stage).
- Hermetic in CI: the deterministic `Provider` drives the whole spine offline; real builders (`ClaudeCodeProvider`) attach behind the seam on the operator's authed node.

## Non-goals

- **No autonomous coding.** The builder never applies a write without an authorized `ActionRequest` and human approval. The first execution slice is **dry-run** (produces a proposed diff, applies nothing).
- **No new authority model.** We reuse `services/authority.py` (`ActionClass`) and `services/authority_envelope.py` (`request_action`/`authorize_action`/`is_authorized`/`mark_executed`) — already live on `enqueue_job` and `routes/repositories.py`.
- **No job-durability work.** RFC-0014 owns leases/outbox/idempotency; the build job declares `idempotency_strategy="origin_job_id"` and inherits that substrate.
- **No new builder infrastructure.** The builder is the RFC-0005 `Provider` (`ClaudeCodeProvider`) invoked on an authed node; CI uses the deterministic provider.
- The depth engines beyond this arc (Design Intelligence, Architecture Spine Graph, full Engineering Evaluation Standard) remain deferred (AOS-REVIEW-003) and get their own RFCs.

## Design

### Mature-state target (per the "design to mature-state" roadmap rule)

An approved decision flows through governed, auditable, draft-first artifacts — `ImplementationPlan`, `BuildRun`, `VerificationRecord` — each a durable row keyed to its predecessor, each promotable only by explicit human approval, each verifiable offline. Every package below is a strict subset of this target. Nothing executes outside the Authority envelope.

### 1. Decision → Plan — `AOS-BUILD-PLAN-001` (Wave B, no execution, safe now)

- New model `ImplementationPlan(AuditMixin, Base)` (`implementation_plans`, migration **0024**): `decision_id` FK, `project_id` FK, `title` String(255), `objective` Text, `tasks: list` JSON (`[{id, description, acceptance, target_paths}]`), `acceptance_criteria: list` JSON, `verification_requirements: list` JSON, `target_repository_id` FK nullable, `risk` Text, `effort` String(128), `evidence: list` JSON. Status rides `AuditMixin.status` with the same vocab as `Decision` (`draft`/`approved`/`rejected`/`superseded`), so the governance gate is uniform.
- `plan_from_decision(db, *, decision_id) -> ImplementationPlan` in `services/build_plan.py`. Requires `decision.status == "approved"` (else 409, mirroring `approve_decision`). Runs the `Provider` over the decision's `context`/`decision`/`consequences`/`evidence` to draft objective + tasks + acceptance criteria. **Draft-only** (`status="draft"`). Idempotent via `meta["decision_id"]` (mirrors `draft_decision_from_review`'s `meta["council_review_id"]` pattern).
- API (`routes/plans.py`): `POST /decisions/{id}/plan` (drafts, 404 if decision missing, 409 if not approved); `GET /plans/{id}`; `GET /projects/{id}/plans`; `POST /plans/{id}/approve` → writes `ApprovalRecord(requested_capability="plan.approve", approval_status="approved")`, sets `status="approved"`, `approved_by/at`.
- **No job_type, no execution** — this package opens the right half safely and is immediately useful (a human can still build the plan by hand).

### 2. Plan → Execute — `AOS-BUILD-EXEC-001` (Wave B, gated, dry-run first)

- New model `BuildRun(AuditMixin, Base)` (`build_runs`, migration 0025): `plan_id` FK, `project_id`, `job_id` FK nullable **unique** (`origin_job_id` idempotency), `mode` String(32) (`dry_run`/`apply`), `provider` String(64), `diff` Text, `artifacts: list` JSON, `logs` Text, `outcome` String(32) (`proposed`/`applied`/`failed`), `evidence: list` JSON.
- New `job_type="build_execute"`, handler `apps/worker/app/handlers/build_execute.py` exporting `SPEC = HandlerSpec(job_type="build_execute", capability="build", sensitivity="private", run=run, idempotency_strategy="origin_job_id", result_schema=("build_run_id","outcome"))` + one line in `registry.py:_HANDLER_MODULES`. `run(job, db)` get-or-creates a `BuildRun` on `job_id`, loads `plan` from `job.payload["plan_id"]`, requires `plan.status=="approved"`, invokes the `Provider`/builder against a working copy, persists the diff/result.
- **Authority gate (the rail, already live):** origination goes through `request_action(db, action_class="draft_artifact"|"repo_write"|"git_commit", ...)` → operator `authorize_action` → `enqueue_job(job_type="build_execute", action_class=..., action_request=<authorized>)`. `enqueue_job` (`services/jobs.py:64-72`) **already refuses** high-impact origination (`repo_write`/`git_commit`/`deploy`/`delete_destructive`) without a matching authorized `ActionRequest`. So no build write can originate without human authorization — enforced today, not aspirationally.
- **Slice order for safety:** Slice 1 = **dry-run** (`mode="dry_run"`, `action_class="draft_artifact"` → auto-authorized, produces a proposed diff, applies nothing). Slice 2 = **apply** (`mode="apply"`, `action_class="git_commit"` → always requires approval) writing to an isolated working copy / branch, never the operator's tree. Inherits RFC-0014 leases/idempotency so a crash cannot double-apply.

### 3. Execute → Verify — `AOS-VERIFY-RUNTIME-001` (Wave B)

- New model `VerificationRecord(AuditMixin, Base)` (or reuse `Evaluation` with `evaluation_type="build_verification"`) attached to a `BuildRun`: `build_run_id` FK, `checks: list` JSON, `passed: bool`, `findings: list` JSON, `evidence: list` JSON.
- After a `build_execute` produces a `BuildRun`, a verification step (same worker, or a chained `verify` job) runs the deterministic `services/verifier.py` + the `tools/pr_guardian.py` check functions against the produced diff/artifact, writing a `VerificationRecord`. This makes `verifier.py`/Guardian reachable from the runtime, closing the "verify is CLI/CI-only" isolation. A failed verification blocks `mode="apply"` promotion.

### 4. Verify → Learn — `AOS-LESSON-AUTO-001` (Wave B, P2)

- On a `VerificationRecord.passed == False` or a `build_execute` `dead_letter`, generate a lesson: upsert a `KnowledgePage(page_type="lesson")` from the failure signal (checks that failed, diff excerpt, decision/plan linkage), reusing the self-heal probe machinery (`session_pain_digest.py` / `coherence_probe.py` write lessons from signals today). Closes the runtime learn-back seam so failures compound into knowledge (Article XIII).

### 5. Research run → Council — `AOS-RESEARCH-COUNCIL-001` (Wave A, cheap, do first)

- `execute_research_run` additionally get-or-creates **one `ResearchNote`** (keyed on `job_id` — the note's `uq_research_notes_job_id` matches the run's `job_id`) summarizing the run: `question=plan.question`, `summary=<synthesis>`, `sources`, `findings`, `confidence`. The council's `_select_research` (`council.py:73-92`) already reads `ResearchNote`, so deep research immediately becomes council evidence — no council change required. Smallest diff, highest leverage; unblocks better decisions upstream of the whole arc.

## Routed delivery plan (model routing per CLAUDE.md)

Opus orchestrates and reviews; each package's mechanical build routes to the cheapest tier that clears the bar; verification is adversarial (builder ≠ verifier). Concurrency note: a sibling session owns the REVIEW-002 shell wave — these packages touch **BRAIN** files (`services/build_plan.py`, `build_execute` handler, `research_run.py`, `council.py`, plans routes) and are disjoint from that wave; each runs in its own worktree/branch.

| Package | Wave | Blocked by | Build tier | Verify tier | Effort |
|---|---|---|---|---|---|
| AOS-RESEARCH-COUNCIL-001 | A | none (ready) | Sonnet (small, mechanical) | Opus review + hermetic test | S |
| AOS-BUILD-PLAN-001 | B | none (ready; no execution) | Sonnet (model+service+routes+tests) | Opus review + API tests | M |
| AOS-BUILD-EXEC-001 | B | RFC-0014 durability (sibling session) | Opus designs handler + gate; Sonnet builds slices | Opus (security-critical) + crash/idempotency tests | L |
| AOS-VERIFY-RUNTIME-001 | B | BUILD-EXEC S1 | Sonnet | Opus + verifier tests | M |
| AOS-LESSON-AUTO-001 | B | VERIFY-RUNTIME | Sonnet (reuses probe machinery) | Opus + test | M |
| AOS-RECO-ENGINE-001 | C | RESEARCH-COUNCIL | Sonnet | Opus | M |
| AOS-EVOLVE-001 | C | none (uses scheduler) | Sonnet | Opus | M |
| AOS-COUNCIL-REALRUN-001 | C | none (authed node) | Sonnet + operator run | Opus | M |

Deterministic tier (no model): migration scaffolds, route-inventory bumps, spec stubs.

**Sequencing:** Wave A (`RESEARCH-COUNCIL-001`) + `BUILD-PLAN-001` start now in parallel (disjoint files). `BUILD-EXEC-001` Slice 1 (dry-run) can start now (uses the live `draft_artifact` auto-authorize path); Slice 2 (apply) waits on RFC-0014 landing on `main`. `VERIFY-RUNTIME → LESSON-AUTO` follow EXEC. Wave C last. Each package = its own RFC-referenced work spec + one PR (roadmap non-negotiable).

## Alternatives considered

- **One monolithic "Build Engine" package.** Faster to a demo, but unreviewable, and couples a safe plan model to risky execution. Rejected — the five-increment split keeps each PR reviewable and lets the safe half ship immediately.
- **Skip the plan artifact; execute directly from a Decision.** Loses the human-approvable, verifiable intermediate and the acceptance-criteria contract the verifier checks against. Rejected — the plan *is* the object verification grades.
- **LLM-as-verifier for build results.** Deferred; the runtime verifier ships deterministic first (Article VIII), a model can assist behind the same seam later — same stance RFC-0005 took for the Final Judge.
- **New execution-authority model for builds.** Rejected — `ActionClass`/`authority_envelope` already model exactly this (`repo_write`/`git_commit`), and are already enforced at `enqueue_job`.

## Evidence

- AOS-REVIEW-003 — the seam inventory and re-centering backlog this RFC implements.
- `services/decisions.py:64,126` + `adr.py:147` — the approved-decision terminus this RFC extends.
- `apps/worker/app/handlers/registry.py:34-67` — `HandlerSpec` + `_HANDLER_MODULES`: the exact extension point for `build_execute`.
- `services/jobs.py:41-96` — `enqueue_job` authority gate (`requires_approval` + `action_request`), the live origination chokepoint.
- `services/authority.py:24-89` (`ActionClass`, `requires_approval`) + `authority_envelope.py:22-92` (`request_action`/`authorize_action`/`is_authorized`/`mark_executed`); live callers `routes/repositories.py:67-90`, `routes/authority.py`.
- `services/research_run.py:68-128` (writes `ResearchRun`, no `ResearchNote`) + `council.py:73-92` (`_select_research` reads `ResearchNote`+`Decision`) — the fixable seam.
- RFC-0005 — the `Provider` seam and deterministic-in-CI stance this arc reuses.
- RFC-0014 — the durability substrate `build_execute` inherits.

## Security impact

- **No new external surface in CI/default.** The deterministic provider drives the spine offline; the `ClaudeCodeProvider` builder runs only on the operator's authed node (subscription auth, no committed keys), same as RFC-0005.
- **Every write is gated.** `build_execute` in `apply` mode originates as `git_commit` → `requires_approval` is always True → `enqueue_job` refuses without an authorized `ActionRequest`. Dry-run mode writes nothing. The builder targets an isolated working copy/branch, never the operator's tree.
- Build artifacts are advisory (`BuildRun.outcome="proposed"`) until a human promotes; verification must pass before `apply`. No autonomy introduced.
- Guardian secret-scan still applies to any produced diff.

## Compliance impact

- Governance-positive: adds durable, auditable artifacts (`ImplementationPlan`, `BuildRun`, `VerificationRecord`, `ApprovalRecord`) and closes the decision→execution→verification→lesson audit trail — directly serving Articles VI, VIII, XIII, XVIII.

## Migration plan

- 0024 `implementation_plans`; 0025 `build_runs`; 0026 `verification_records` (or `Evaluation` reuse). Additive only, single Alembic head preserved (current head `0023`), `import aos_core.models` in each migration. Validated by the no-drift autogenerate probe + compose-smoke `alembic upgrade head` on fresh Postgres. `AOS-RESEARCH-COUNCIL-001` needs **no migration** (reuses `research_notes`).

## Risks

- **BUILD-EXEC is the highest-risk package** (runtime code execution). Mitigations: dry-run slice first; `apply` gated by `git_commit` authority + human approval; isolated working copy; RFC-0014 idempotency prevents double-apply; Opus (not a cheaper tier) designs the handler + gate and adversarially verifies it.
- **Scope creep back into shell work.** Mitigation: this arc is BRAIN-only; the sibling session owns shell.
- **Provider variance** (real builder output nondeterministic). Mitigation: verification is deterministic and blocks promotion; the plan's acceptance criteria are the objective grading oracle.

## Acceptance criteria (this RFC)

- Operator approves the arc; each package delivers as its own work spec + PR with builder ≠ verifier.
- A human can traverse `approved Decision → draft plan → approve plan → dry-run build → verification record` through real API routes, offline in CI, with every write refused absent an authorized `ActionRequest`.
- `execute_research_run` output appears in a subsequent council review's evidence.
- No path performs a write without the Authority envelope + human approval; no autonomous action.
- Every migration passes no-drift + compose-smoke.

## Open questions

1. **Verification as same-worker step vs. chained `verify` job.** Leaning chained job (reuses retry/lease substrate; keeps `build_execute` single-purpose). Resolve at VERIFY-RUNTIME spec time.
2. **`VerificationRecord` new table vs. `Evaluation` reuse.** Leaning reuse `Evaluation(evaluation_type="build_verification")` to avoid table sprawl; confirm the JSON shape fits.
3. **Builder working-copy strategy** for `apply` mode (ephemeral clone vs. worktree vs. node-local checkout). Defer to BUILD-EXEC Slice 2, after RFC-0014.

## Dependencies

- **Reuses (live today):** RFC-0005 `Provider` seam; `authority.py`/`authority_envelope.py` (enforced at `enqueue_job`); `services/verifier.py`; `tools/pr_guardian.py`; self-heal probe machinery.
- **Blocks on (sibling REVIEW-002 wave):** RFC-0014 (durable jobs) for BUILD-EXEC `apply`; AOS-WORKER-HANDLERS-001 (`HandlerSpec.idempotency_strategy`, already present in `registry.py`).
- **Enables:** AOS-RECO-ENGINE-001, AOS-EVOLVE-001, AOS-COUNCIL-REALRUN-001 (Wave C), and a genuinely closed engineering-intelligence loop.

## Final Judge verdict

Pending operator approval. Scoped deliberately so the safe half (plan artifact, research→council seam, dry-run build) ships immediately and the risky half (apply-mode execution) is gated behind both the live Authority envelope and the in-flight durability substrate — evidence over inference, human approval preserved, local-first. Proceed with Wave A + `AOS-BUILD-PLAN-001` on approval.
