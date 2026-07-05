# ArchetypeOS Knowledge Vault Index

This vault stores human-readable engineering memory for ArchetypeOS.

## Core Pages

- [[hot]]
- [[overview]]
- [[log]]

## Domains

- projects
- repositories
- technologies
- decisions
- research
- risks
- experiments
- benchmarks
- lessons
- patterns

## Meta

- `meta/graph.json` — relationship graph seed
- `meta/lint-report.md` — knowledge lint status
- `meta/dashboard.md` — vault page counts and manifest status

## Templates

- `templates/page-template.md` — required shape for new wiki pages

## Manifest

- `.manifest.json` — ingestion and delta tracking (see schema in `docs/KNOWLEDGE_VAULT_STRUCTURE.md`)

## Retrieval Order

Agents should retrieve knowledge in this order:

```text
hot.md -> index.md -> domain index -> specific pages -> graph search -> embeddings -> LLM synthesis
```
