# RFC-0002 — Knowledge System

## Status

Accepted for v0.1 foundation.

## Summary

ArchetypeOS will use a hybrid knowledge system: Postgres for structured system records, graph data for relationships, and an Obsidian-compatible markdown vault for human-readable engineering memory.

## Problem

Engineering knowledge is often scattered across chats, notes, commits, PRs, research, diagrams, and undocumented decisions. ArchetypeOS needs durable memory that is readable by humans and usable by agents.

## Proposal

Use a Karpathy-style LLM wiki pattern:

```text
raw/sources -> distillation -> wiki pages -> index/hot/log -> graph/metadata
```

Core files:

- `wiki/hot.md`
- `wiki/index.md`
- `wiki/log.md`
- `wiki/overview.md`
- `.manifest.json`

## Goals

- Preserve raw sources.
- Distill durable wiki pages.
- Track provenance and deltas.
- Support Obsidian reading/editing.
- Support agent retrieval protocol.
- Prevent raw notes from becoming canonical without validation.

## Non-Goals

- make Obsidian the runtime database
- replace Postgres
- replace graph indexes
- auto-canonicalize unreviewed notes

## Acceptance Criteria

- Vault structure exists.
- Manifest schema is defined.
- Agents know retrieval order.
- Distillation states are defined.
- Wiki lint requirements are defined.

## Final Judge Verdict

Accepted.
