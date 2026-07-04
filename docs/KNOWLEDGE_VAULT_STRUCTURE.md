# Knowledge Vault Structure

## Purpose

The Knowledge Vault Structure defines how ArchetypeOS stores human-readable engineering memory using a Karpathy-style LLM wiki pattern while preserving structured system-of-record data in Postgres and graph indexes.

## Principle

Obsidian-compatible markdown is the readable notebook. ArchetypeOS remains the governed reasoning system.

## Required Structure

```text
knowledge/
├── raw/
├── sources/
├── wiki/
│   ├── index.md
│   ├── hot.md
│   ├── log.md
│   ├── overview.md
│   ├── projects/
│   ├── repositories/
│   ├── technologies/
│   ├── decisions/
│   ├── research/
│   ├── risks/
│   ├── experiments/
│   ├── benchmarks/
│   ├── lessons/
│   └── patterns/
├── meta/
│   ├── graph.json
│   ├── lint-report.md
│   └── dashboard.md
├── templates/
└── .manifest.json
```

## raw/

Raw captured material before processing.

Examples:

- voice transcripts
- conversation exports
- meeting notes
- repository review dumps
- pasted research

## sources/

Source material that should remain preserved for provenance.

Examples:

- external docs summaries
- imported markdown
- reference repository notes
- research snapshots

## wiki/index.md

Master catalog of the vault.

Agents should read this after `hot.md`.

## wiki/hot.md

Compact high-signal working memory.

Contains:

- current project focus
- current phase
- active decisions
- recent blockers
- important constraints
- top links

Agents should read this first.

## wiki/log.md

Append-only log of knowledge operations.

Records:

- ingest events
- distillation events
- file changes
- archive events
- rebuild events
- conflicts
- validation events

## wiki/overview.md

Human-readable executive overview of the project or portfolio.

## .manifest.json

Tracks ingestion and delta state.

Minimum fields:

- source_id
- source_type
- source_path_or_uri
- checksum
- last_seen
- last_ingested
- generated_pages
- generated_graph_nodes
- confidence
- status

## Knowledge Lint

The vault should be linted for:

- dead links
- orphan pages
- duplicate concepts
- stale pages
- missing aliases
- missing evidence
- missing owner
- conflicting claims
- pages not linked to decisions or projects

## Archive And Rebuild

When the vault drifts too far, ArchetypeOS should support:

```text
snapshot current wiki -> rebuild from sources -> compare -> human approve
```

## Retrieval Protocol

Agents should retrieve knowledge in this order:

```text
hot.md -> index.md -> domain index -> specific pages -> graph search -> embeddings -> LLM synthesis
```

## Safety

Raw notes and extracted notes are not canonical.

Canonical knowledge requires evidence, review, or explicit validation.
