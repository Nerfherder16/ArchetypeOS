# Decision Lifecycle

## Purpose

Engineering decisions are hypotheses until validated by evidence.

ArchetypeOS should track decisions through their full lifecycle rather than treating decisions as one-time documents.

## Lifecycle

```text
Idea -> Research -> Simulation -> Decision -> Implementation -> Validation -> Measurement -> Knowledge -> Reuse -> Evolution
```

## Stages

### Idea

A proposed direction, feature, technology, pattern, or architecture change.

### Research

Evidence gathering from official docs, reference implementations, benchmarks, internal history, and external sources.

### Simulation

Optional proof lab, benchmark, migration simulation, or what-if analysis.

### Decision

A recorded ADR or decision card with alternatives, tradeoffs, evidence, and acceptance criteria.

**Implemented (RFC-0005 Phase 2, AOS-COUNCIL-PHASEC — the Council → Decision loop).** An advisory `CouncilReview` is drafted into a governed `Decision` that links back to the review (and its per-agent outputs) as evidence; the draft is idempotent — one decision per review. A named human then **approves** (sets `approved_by`/`approved_at`/`status=approved`) or **rejects** (`status=rejected`) it, and every transition is recorded in an `ApprovalRecord` — durable memory (approver, timestamp, rationale, evidence). Pending drafts surface in the nightly digest so the human gate is active, not passive.

**Abstention blocks approval (LES-019).** A decision drafted from an *abstained* review — verdict `Insufficient evidence` or confidence below the abstention floor — is drafted as `needs_evidence` and **cannot be approved** (the approve endpoint returns `409`, naming the evidence-gathering / re-draft path). The operator must gather primary evidence, re-run the council, and re-draft from a cleared-floor review. It may still be rejected.

Service: `packages/aos_core/aos_core/services/decisions.py`. Endpoints: `POST /council-reviews/{review_id}/draft-decision`, `POST /decisions/{decision_id}/approve`, `POST /decisions/{decision_id}/reject`.

**Decision → Knowledge: approved decisions export to a repo-vault ADR (RFC-0002 / RFC-0004, AOS-COUNCIL-PHASEC2A — the Part 2a backend).** An **approved** decision can be rendered into an ADR markdown file under `knowledge/wiki/decisions/` (shaped like `templates/adr.md`, linking back to the decision and its council review) and projected as a re-syncable `KnowledgePage` (`page_type="decision"`) so it also surfaces on the Knowledge dashboard. The repo vault is the source of truth: `sync_knowledge` re-derives the decision page straight from the ADR file, so a DB reset loses nothing. Export is a **separate, explicit step** — its own endpoint `POST /decisions/{decision_id}/adr`, decoupled from `approve_decision` — and is **approved-only** (a `draft`/`needs_evidence`/`rejected` decision returns `409`) and idempotent (re-export overwrites the one file and updates the one page). The write is **local-first**: it targets `settings.knowledge_root` on a writable checkout; the compose stack mounts the vault `:ro`, so in that container the write is unavailable and the endpoint fails **gracefully and explicitly** (`409` naming the local-first-checkout requirement, never a `500`) without ever mutating the approval state. Service: `packages/aos_core/aos_core/services/adr.py`. Rendering into the Control Tower decision-approval view is Part 2b.

### Implementation

The decision is applied through controlled builder workflows.

### Validation

Tests, benchmarks, PR Guardian, user review, security review, and production feedback validate the decision.

### Measurement

ArchetypeOS compares expected outcomes against actual outcomes.

### Knowledge

Results become lessons learned, research updates, benchmark records, or reusable patterns.

### Reuse

Validated knowledge becomes available to other repositories through the Portfolio Knowledge Marketplace.

### Evolution

The decision is periodically re-evaluated against new evidence.

## Principle

A decision is not complete when it is accepted. It is complete when its outcome is measured and its learning is captured.
