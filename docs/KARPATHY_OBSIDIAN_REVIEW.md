# Karpathy Obsidian / LLM Wiki Review

## Purpose

This document evaluates the Karpathy LLM Wiki pattern and related Obsidian implementations for possible adoption into ArchetypeOS.

Reviewed references:

- Obsidian Community Plugin: Karpathy LLM Wiki
- AgriciDaniel/claude-obsidian
- Ar9av/obsidian-wiki

## Core Pattern

The Karpathy LLM Wiki pattern is not ordinary RAG.

The core idea is to compile raw notes, conversations, files, and documents into an interconnected markdown wiki once, keep it current, and query that structured knowledge later.

Instead of repeatedly asking an LLM to search unstructured context, the system continuously distills knowledge into durable pages, wikilinks, indexes, logs, caches, aliases, and maintenance reports.

## Why This Matters To ArchetypeOS

ArchetypeOS needs durable engineering memory.

This pattern maps directly to:

- Engineering Memory
- Knowledge Graph
- Obsidian integration
- Nightly Self Learning Loop
- Repository Intelligence Engine
- Knowledge Distillation Engine
- Portfolio Knowledge Marketplace
- Cross-project knowledge reuse

## Useful Concepts To Adopt

### 1. Sources Folder

Raw notes should land in a raw or sources area before being distilled.

ArchetypeOS equivalent:

```text
knowledge/raw/
knowledge/sources/
```

### 2. Wiki Output Layer

Distilled knowledge should live in a human-readable wiki area.

ArchetypeOS equivalent:

```text
knowledge/wiki/
```

### 3. Index

The wiki should maintain a master catalog.

ArchetypeOS equivalent:

```text
knowledge/wiki/index.md
```

### 4. Hot Cache

Frequently needed or recent context should live in a compact cache that agents read first.

ArchetypeOS equivalent:

```text
knowledge/wiki/hot.md
```

This is extremely useful for Claude Code and local agents because it reduces token cost.

### 5. Append-Only Log

All wiki operations should be logged.

ArchetypeOS equivalent:

```text
knowledge/wiki/log.md
```

### 6. Overview Page

Every vault or project should have an executive summary.

ArchetypeOS equivalent:

```text
knowledge/wiki/overview.md
```

### 7. Delta Tracking

A manifest should track which source files have already been ingested, when they changed, and which wiki pages they produced.

ArchetypeOS equivalent:

```text
knowledge/.manifest.json
```

This avoids reprocessing the same material and enables nightly updates.

### 8. Multi-Agent History Ingest

The Obsidian wiki tools ingest history from Claude, Codex, Hermes, OpenClaw, Pi, ChatGPT exports, Slack logs, meeting transcripts, and arbitrary text.

ArchetypeOS should support the same general idea:

```text
conversation history -> distillation -> engineering memory
```

### 9. Methodology Modes

claude-obsidian supports methodology modes such as LYT, PARA, Zettelkasten, and Generic.

ArchetypeOS should not force one method for every knowledge type.

Recommended modes:

- Engineering Portfolio
- Project Wiki
- Repository Intelligence
- Research Library
- Personal Notes
- Compliance Pack
- Design System

### 10. Query Order

Agents should not blindly read the whole vault.

Recommended order:

```text
hot.md -> index.md -> domain index -> specific page
```

This should be added to ArchetypeOS CLAUDE instructions.

### 11. Wiki Maintenance / Lint

Karpathy LLM Wiki includes lint-style maintenance for duplicates, dead links, empty pages, orphans, missing aliases, and index rebuilds.

ArchetypeOS should have a Knowledge Linter that checks:

- duplicate concepts
- stale pages
- dead links
- orphan pages
- missing aliases
- conflicting claims
- missing evidence
- missing decision links
- missing project ownership

### 12. Alias-Aware Deduplication

The system should understand that the same concept may appear under multiple names.

For ArchetypeOS, this matters for:

- technologies
- vendors
- frameworks
- project names
- internal modules
- abbreviations
- agent names

### 13. Graph Retrieval Before Embeddings

The Karpathy LLM Wiki plugin added Personalized PageRank over wiki links as a graph retrieval layer that can work without embeddings.

ArchetypeOS should evaluate this seriously.

Recommended retrieval cascade:

```text
lexical search -> hot cache -> graph walk / PageRank -> local embeddings -> LLM synthesis
```

### 14. Smart Batch Skip

Batch ingest should skip already-ingested files and only process changed sources.

### 15. Archive And Rebuild

When the wiki drifts too far, archive the current wiki and rebuild from source rather than mutating endlessly.

ArchetypeOS should support:

```text
archive snapshot -> rebuild -> compare -> approve
```

### 16. Multi-Writer Safety

If multiple agents write to the same knowledge page, locking is required.

ArchetypeOS should implement file or row-level locks for knowledge writes.

### 17. Agent Skill Distribution

obsidian-wiki uses agent skills as markdown instructions and installs/symlinks them into many agents.

This directly validates the ArchetypeOS agent CLAUDE.md / skill approach.

ArchetypeOS should support:

- skill source of truth
- per-agent installs
- versioned skill registry
- skill upgrade process
- skill tests

## Recommended ArchetypeOS Vault Structure

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
│   ├── dashboard.base
│   ├── graph.json
│   └── lint-report.md
├── templates/
└── .manifest.json
```

## What Not To Copy Blindly

- Do not make Obsidian the runtime system of record.
- Do not let unvalidated notes become canonical facts.
- Do not let the wiki replace Postgres or the structured graph.
- Do not let automatic linking create false certainty.
- Do not auto-write over knowledge without audit and rollback.

## ArchetypeOS Position

Obsidian should be the human-readable knowledge notebook.

ArchetypeOS should remain the structured reasoning, graph, runtime, and governance system.

The two should sync.

## Adoption Recommendation

Adopt the pattern strongly, but adapt it for engineering governance.

Highest value imports:

1. hot.md recent context cache
2. index.md master catalog
3. append-only log.md
4. .manifest.json delta tracking
5. wiki lint and maintenance
6. archive/rebuild flow
7. multi-agent history ingest
8. alias-aware deduplication
9. graph retrieval / PageRank-style search
10. agent skill distribution model

## Final Judgment

This is one of the strongest external patterns reviewed so far.

It directly strengthens ArchetypeOS's Engineering Memory, Nightly Self Learning Loop, Repository Intelligence Engine, and Portfolio Knowledge Marketplace.
