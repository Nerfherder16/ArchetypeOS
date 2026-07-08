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
- Watermark PR: #129
- Active Branch: none (on main)
- Current Phase: post-v0.1 consolidation (per the AOS-REVIEW-001 system evaluation)
- Current Objective: Consolidate integration coherence before adding more surface — canonical state (AOS-STATE-RECON-001), project-scoped CommandDeck turns (AOS-VOICE-PROJECT-001), and surfacing rich backend evidence in the API/web contracts (AOS-CONTRACT-001), then the node/connector registries that make the distributed-agent vision first-class.
- Blockers: none
- Next: AOS-STATE-RECON-001 (this) → AOS-VOICE-PROJECT-001 → AOS-CONTRACT-001
<!-- AOS-CANONICAL:END -->

## Where We Are

Post-v0.1 and materially ahead of the original scope. Shipped and live: the founding
knowledge arc (scan → distill → transfer/reuse with embeddings), the Agent Council +
decision loop, the Control Tower dashboard (workspace-mode rail shell), the full Voice
Command Center (Sotto STT → `/voice/turns` → Groq Orpheus TTS → Voice Inbox → approve
→ promote to draft ResearchNote/Decision), the Research Engine (local floor + web tier),
the routed reasoned LLM tier (local/free/Claude with a privacy guardrail + usage ledger),
live auto-deploy to teevee, and a two-probe self-learn nightly (conflict → lesson, toil
→ skill). The AOS-REVIEW-001 evaluation (`knowledge/wiki/reviews/2026-07-08-...`) found
the risk is now over-building sideways: integration coherence lags feature velocity.
Consolidation is the current focus. For the full chronological history see
`docs/RECENT_CHANGES.md`.

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
| Distributed runtime (Node/Capability registry) | Proposed | AOS-NODE-001 (P1 in AOS-REVIEW-001); not yet first-class in code. |
| Connector registry / policy center | Proposed | AOS-CONNECTOR-001 (P1); providers exist, connectors not governed centrally. |
| Authority action policy | Proposed | AOS-AUTHORITY-001 (P2); model exists as data, not enforced as policy. |

## Next Recommended Task

Work the AOS-REVIEW-001 P0 set in order: **AOS-STATE-RECON-001** (canonical state + drift assurance — this), then **AOS-VOICE-PROJECT-001** (project-scoped CommandDeck turns), then **AOS-CONTRACT-001** (surface DNA/edge/research evidence the backend already computes). P1/P2 packages (node/connector/worker-router/arch-studio/UX-IA/authority/research-loop) are tracked in `docs/ACTIVE_WORK.md` as Proposed.

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
