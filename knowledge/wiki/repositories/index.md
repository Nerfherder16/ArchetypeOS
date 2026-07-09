# Repositories Index

## Aliases

- keep pile
- external repo register
- repo evaluation register
- repo adoption board

## Status

active

## Owner

Chief Architect / Orchestrator

## Evidence

- `docs/ARCHETYPEOS_CONTEXT.md` — knowledge strategy: GitHub stores source, Postgres stores runtime data, the graph stores relationships, Obsidian stores human-readable research/decision notes
- Full teardowns live in `docs/repo-research/<repo>.md`; this register holds the distilled verdict and the borrow candidates

## Linked Decisions / Projects

- [[../decisions/|decisions]] — a borrow that gets committed to graduates into a decision card or RFC
- [[../lessons/index|lessons]] — evaluation misses feed the learning loop
- Plane module "External Repo Evaluation & Adoption Pipeline" (`c8c0dadf-1922-4a37-8742-55df5fd7bf5e`) tracks the actionable adoption work

## Content

Single register for every external repository evaluated for ArchetypeOS. Each row is a candidate, not a commitment. The heavy evidence stays in `docs/repo-research/`; this table is the queryable, graph-linked judgment layer so current and future repos are compared on the same axes.

Lifecycle: `evaluated` → `queued` → `borrowing` → `borrowed` / `rejected` / `monitor`. A borrow only becomes real work when it graduates into a `decisions/` card, an RFC, or a Plane work item (cite what consumed it). On conflict between a repo page and this table, this table wins.

### Verdict vocabulary

- `adopt` — vendor / install largely as-is
- `partial-borrow` — take specific artifacts, reject the whole
- `reject` — nothing additive over what AOS already has
- `monitor` — not now, re-check later

## Register

| Repo | Verdict | Borrow candidates | AOS engines | Status | Report |
|------|---------|-------------------|-------------|--------|--------|
| [[claude-obsidian]] | partial-borrow | BM25/cosine retrieval scripts (RFC-0010); `think` skill frontmatter + 10-principle framework (ADR) | Knowledge Graph, Research Engine, Decision Intelligence | evaluated | [[../../../docs/repo-research/claude-obsidian\|report]] |
| [[claude-video]] | partial-borrow | video-ingestion capability: URL → download+frames+transcription → structured breakdown (greenlit AOS-62) | Research Engine, Knowledge Vault | borrowing | [[../../../docs/repo-research/claude-video\|report]] |
| [[T3MP3ST]] | partial-borrow | AGPL — no code. GREENLIT: recon as AGPL-isolated external service → EES security sub-score (AOS-64, RFC-first). Candidate patterns (not greenlit): risk-tiered tool catalog, human-veto approval gate, decomposition orchestrator, egress scope containment | Engineering Evaluation Standard | borrowing | [[../../../docs/repo-research/T3MP3ST\|report]] |
| [[notebooklm-py]] | reject / monitor | Unofficial reverse-engineered Google NotebookLM RPC — privacy egress + fragility + non-determinism. MIT but rejected for integration. Reference-only patterns (not greenlit): VCR cassette tests, per-file coverage floors, nightly RPC-health check, atomic 0600 creds | Research Engine (conflicting, not additive) | evaluated | [[../../../docs/repo-research/notebooklm-py\|report]] |
| [[memtrace-public]] | monitor (blueprint deferred) | Closed engine + proprietary EULA + mandatory heartbeat → don't adopt. Novel delta = bi-temporal history layer (replay, cochange, temporal scoring); static half already covered by AOS+jcodemunch. DECIDED: defer Option B, keep as blueprint for the Evolution Engine (AOS-67, Backlog) | Evolution Engine (future), Architecture Spine Graph | evaluated | [[../../../docs/repo-research/memtrace-public\|report]] |
| [[obsidian-skills]] | partial-borrow | GREENLIT: json-canvas emitter for Architecture Studio (AOS-69, RFC-first) + obsidian-markdown skill (AOS-70) + skill-authoring patterns (AOS-71). REJECT cli/bases (need running Obsidian app) + defuddle (Firecrawl dup) | Architecture Studio, Knowledge Vault | borrowing | [[../../../docs/repo-research/obsidian-skills\|report]] |
| [[impeccable]] | partial-borrow | Apache-2.0, local after install. Additive execution/anti-AI-slop layer beneath Design Intelligence: 46 deterministic anti-pattern rules + 5-dim audit rubric. GREENLIT: vendor rules into design-system skill (AOS-73) + install as Claude Code plugin (AOS-74) + design-lint for apps/web (AOS-75, RFC-first) | Design Intelligence, Control Tower (apps/web) | borrowing | [[../../../docs/repo-research/impeccable\|report]] |
