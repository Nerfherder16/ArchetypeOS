# Knowledge Distillation Engine

## Purpose

The Knowledge Distillation Engine turns raw information into durable engineering knowledge.

It is different from search and different from summarization. It extracts concepts, entities, relationships, decisions, risks, lessons, and reusable patterns, then writes them into the knowledge system with links and provenance.

## Inputs

- conversations
- voice notes
- repository reviews
- Git diffs
- pull requests
- issues
- research notes
- external repositories
- meeting transcripts
- Slack exports
- ChatGPT exports
- Claude Code history
- Codex history
- Obsidian notes
- PDFs and documents

## Outputs

- wiki pages
- index entries
- hot cache updates
- log entries
- knowledge graph updates
- decision candidates
- ADR candidates
- recommendation cards
- lessons learned
- reusable patterns
- repository DNA updates
- portfolio marketplace candidates

## Distillation Pipeline

```text
Raw input
-> classify source
-> extract entities and concepts
-> detect relationships
-> detect decisions and tradeoffs
-> detect reusable patterns
-> merge with existing pages
-> update aliases
-> update index
-> update hot cache
-> update graph
-> log operation
```

## Knowledge Validation States

- raw
- extracted
- linked
- reviewed
- validated
- canonical
- deprecated
- archived

## Delta Tracking

Every source should be tracked in a manifest.

Minimum fields:

- source path or URI
- source type
- checksum
- last ingested
- generated pages
- generated graph nodes
- confidence
- reviewer

## Conflict Handling

When new knowledge conflicts with existing knowledge, the engine should not overwrite silently.

It should create a conflict item for review.

## Safety

Raw notes and extracted notes are not automatically canonical.

Canonical knowledge requires evidence or review.

## Principle

The value of a knowledge system is not the amount of text it stores. It is the quality of distilled, linked, reusable knowledge it preserves.
