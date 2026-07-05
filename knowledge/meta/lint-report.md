# Knowledge Lint Report

## Status

No lint pass has run yet. This is a stub. Populate this file once a lint pass over `knowledge/wiki/` is implemented.

## Lint Dimensions

Per `docs/KNOWLEDGE_VAULT_STRUCTURE.md`, a lint pass must check for:

- dead links
- orphan pages
- duplicate concepts
- stale pages
- missing aliases
- missing evidence
- missing owner
- conflicting claims
- pages not linked to decisions or projects

## Notes

- The domain directories (`projects/`, `repositories/`, `technologies/`, `decisions/`, `research/`, `risks/`, `experiments/`, `benchmarks/`, `lessons/`, `patterns/`) currently contain only placeholder `.gitkeep` files, so lint findings on individual pages are not yet applicable.
- No `KnowledgePage` rows exist yet (see `.manifest.json` — `generated_graph_nodes` is empty and no distillation pipeline has run), so this report cannot cross-check the vault against a persisted read path.
