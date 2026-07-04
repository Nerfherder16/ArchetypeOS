# Obsidian And Graphify Integration

## Purpose

ArchetypeOS should support both human-readable knowledge and structured machine reasoning.

Obsidian is useful as the human-readable knowledge vault. Graphify-style tooling is useful for converting repositories, documents, diagrams, and research into graph structures that agents can query.

## Role Of Obsidian

Obsidian should not be the system of record for all runtime data.

It should be used for:

- research notes
- ADRs
- decision cards
- lessons learned
- architecture notes
- long-form thinking
- project journals
- human-readable knowledge packs

## Role Of Structured Storage

Structured data should live in:

- Postgres
- graph database or graph files
- repository metadata
- knowledge indexes
- report storage

## Role Of Graphify-Style Tools

Graphify-style tools can help create queryable graphs from:

- source code
- documentation
- PDFs
- images
- diagrams
- markdown notes
- architecture docs

## Recommended Architecture

```text
ArchetypeOS
├── Postgres structured data
├── Knowledge graph
├── Obsidian vault
├── Graphify adapter
├── Repository scanner
└── Agent council
```

## Sync Direction

- ArchetypeOS generates structured artifacts.
- Selected artifacts sync to Obsidian as markdown.
- Obsidian notes can be indexed back into ArchetypeOS.
- Graphify-style adapters enrich the knowledge graph.

## Safety

Obsidian notes may contain drafts, opinions, and incomplete thoughts. Agents must label them as human notes unless validated.

## Principle

Obsidian is the readable notebook. ArchetypeOS is the reasoning system. The graph connects both.
