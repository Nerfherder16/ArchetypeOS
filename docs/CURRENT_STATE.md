# Current State

## Purpose

The single canonical snapshot of where ArchetypeOS is **right now**: current phase,
what is active, what is next, and what to read first. It is deliberately short.
The chronological saga lives in `docs/RECENT_CHANGES.md`, not here — this file must
never grow back into a frozen narrative (that is exactly the drift AOS-STATE-RECON-001
fixed; see LES-L09).

<!-- AOS-CANONICAL:START -->
<!-- Watermark PR and Active Branch are AUTO-DERIVED on every merge to main by the
     `state-canonical-refresh` workflow (tools/doc_staleness.py --refresh-canonical).
     Do NOT hand-edit those two lines — they cannot drift because a human never owns
     them. The other fields are human-authored and kept short. -->
- Watermark PR: #217
- Active Branch: none (on main)
- Current Phase: post-AOS-REVIEW-002 runtime-integrity remediation (the July-10 evaluation, LES-033)
- Current Objective: Close the runtime-integrity gaps LES-033 named — the registries/evaluators exist but must be ON the execution path. The AOS-REVIEW-002 wave is landing: durable job fencing (AOS-JOB-FENCING-001), operator+node auth boundary (AOS-AUTH-BOUNDARY-001), node-enforced execution (AOS-NODE-EXECUTION-001), hardened one-use authority envelope (AOS-AUTHORITY-HARDEN-001), reproducible web build (AOS-WEB-LOCK-001) are merged; state reconciliation (AOS-STATE-RECON-002) and capability-level reuse (RFC-0013) close it out.
- Blockers: none
- Next: AOS-STATE-RECON-002 (this) → RFC-0013 capability-level reuse (Slices 2-4 + portfolio benchmark)
<!-- AOS-CANONICAL:END -->

## Where We Are

Post-v0.1 and materially ahead of the original scope. Shipped and live: the founding
knowledge arc (scan → distill → transfer/reuse with embeddings), the Agent Council +
decision loop, the Control Tower dashboard (workspace-mode rail shell), the full Voice
Command Center (Sotto STT → `/voice/turns` → Groq Orpheus TTS → Voice Inbox → approve
→ promote to draft ResearchNote/Decision), the Research Engine (local floor + web tier),
the routed reasoned LLM tier (local/free/Claude with a privacy guardrail + usage ledger),
live auto-deploy to teevee, and a two-probe self-learn nightly (conflict → lesson, toil
→ skill). A second evaluation (AOS-REVIEW-002, July-10, recorded in `knowledge/wiki/lessons/LES-033.md`)
found the deeper risk: feature completeness had outrun runtime integrity — the Node
registry, Connector catalog, and Authority evaluator existed but sat off the execution
path, and the job substrate was not durable under crashes. The AOS-REVIEW-002 remediation
wave closes those gaps and is the current focus: durable job fencing, an authenticated
control plane, node-enforced execution, and a hardened one-use authority envelope are
merged. For the full chronological history see `docs/RECENT_CHANGES.md`.

## CI / Governance

- CI (GitHub Actions) runs on every PR: API/worker/embedder/vector tests, web typecheck+build, Playwright e2e, Docker Compose smoke, and the **PR Guardian** gate.
- Verification Protocol active; lessons recorded in `knowledge/wiki/lessons/` (cloud `LES-NNN` band, laptop `LES-L##` band).
- Auto-rebase Action keeps open PRs merge-clean; union-merge on the four shared coordination docs.
- Self-learn nightly: conflict probe (→ lesson PR) + toil probe (→ skill/script PR); reconcile nightly keeps state docs honest.
- Deploy: live auto-deploy poller on teevee (WSL2, Tailscale `100.123.29.114`); dashboard at `http://100.123.29.114:5173`.

## Out Of Scope Now

- Plane two-way sync automation
- Desktop / browser automation, wake word
- Autonomous coding without approval gates
- Production (public) deployment

## Open Decisions

| Decision | Status | Notes |
| --- | --- | --- |
| PR approval guard | Lifted 2026-07-08 | Opening PRs no longer needs per-PR approval; merge-safety (green + Guardian PASS) stays. See `~/.claude/rules/git-operations.md`. |
| Distributed runtime (Node/Capability registry) | Enforced on the execution path | Node registry + per-node identity (`X-Node-Token`, AOS-NODE-IDENTITY-001) shipped; the worker claims through `claim_job_for_node`, which routes at origination and enforces node assignment + capability/sensitivity/write/health at claim time (AOS-NODE-AGENT-001 + AOS-NODE-EXECUTION-001, merged). Remote HTTPS execution across machines is the remaining follow-up. |
| Connector registry / policy center | Unified runtime | `GET /connectors` is read-only, config truth is unified API↔worker, and reachability is an active probe (AOS-CONNECTOR-RUNTIME-001, merged); connector write routes carry a token gate. |
| Authority action policy | Structural gate (enforced) | The authority envelope is mandatory at job origination and hardened: server-owned action classification, atomic one-use consume, target/expiry binding, distillation approve-and-resume (AOS-AUTHORITY-ENVELOPE-001 + AOS-AUTHORITY-HARDEN-001, merged). Extending it to council/research egress is a follow-up. |

## Next Recommended Task

Finish the AOS-REVIEW-002 runtime-integrity wave (LES-033): **AOS-STATE-RECON-002** (this — reconcile these canonical docs to the merged wave and harden the semantic drift detector), then **RFC-0013 capability-level reuse** (Slice 2 `RepositoryCapability` persistence, Slice 3 per-capability embeddings, Slice 4 capability-match `recommend_reuse` with provenance, and the automated five-repo portfolio benchmark). The merged wave — durable job fencing, operator+node auth boundary, node-enforced execution, hardened authority envelope, reproducible web build — is recorded in `docs/RECENT_CHANGES.md`.

## Required Reading For New Sessions

1. `docs/CURRENT_STATE.md` (this file — the canonical snapshot)
2. `docs/ACTIVE_WORK.md`
3. `docs/RECENT_CHANGES.md`
4. `docs/CAPABILITY_MAP.md`
5. `knowledge/wiki/reviews/2026-07-08-archetypeos-system-evaluation.md` (AOS-REVIEW-001)
6. `docs/VERIFICATION_PROTOCOL.md`
7. Relevant RFCs and domain docs

## Update Rule

This file is the **canonical current-state contract**. Keep it short:

- The `AOS-CANONICAL` block's Watermark PR and Active Branch are machine-owned — the `state-canonical-refresh` workflow rewrites them on every merge; never hand-edit them.
- The human fields (Current Phase / Objective / Blockers / Next) are updated when direction changes — keep each to a line or two.
- Never paste chronological history here; it belongs in `RECENT_CHANGES.md`. `tools/doc_staleness.py` flags this file specifically (not the union of state docs) when its watermark lags git or it names a stale active branch (LES-L09).
