# AOS-KNOW-001 — Knowledge Vault Seed

## Status

In Review

## Verified Baseline

Confirmed by inspection:

- `knowledge/` exists minimally: `knowledge/.manifest.json` and `knowledge/wiki/{hot,index,log,overview}.md`, matching the `wiki/hot.md`, `wiki/index.md`, `wiki/log.md`, `wiki/overview.md`, `.manifest.json` structure named in `docs/rfc/RFC-0002-Knowledge-System.md`.
- `KnowledgePage` (`apps/api/app/models.py`) already exists as a persisted model: `project_id`, `title`, `vault_path`, `page_type`, `validation_state` (default `raw`), `source_refs` (JSON list), `checksum`.
- The repository scanner's report shape is documented in `docs/REPOSITORY_SCANNER.md` (legacy keys plus `manifests`, `docker_files`, `ci_files`, `folder_structure`, `summary`, `risk_signals`, `notes`), so knowledge-vault seeding can consume scan output without guessing at its schema.
- Dependencies named in `docs/ACTIVE_WORK.md` (repository registry model, branch isolation/worktree protocol, scanner output shape) are all satisfied.

## In-Scope Files

- `knowledge/` structure and manifest content
- any API wiring needed to read/write `KnowledgePage` rows consistent with the existing model (no schema change expected)
- documentation updates describing the vault seed

## Out-of-Scope

- graph database / relationship graph work
- changing the `KnowledgePage` schema
- scanner report schema changes
- distillation pipeline automation (future work per RFC-0002)
- the optional `KnowledgePage` API read path is explicitly deferred: the model exists (`apps/api/app/models.py`) but no writer populates the table yet, so a read endpoint would have nothing to read; deferred until a distillation or ingestion path exists

## Acceptance Criteria

- `knowledge/` structure exists and matches RFC-0002's core files — evidence: files present in diff (`knowledge/wiki/hot.md`, `index.md`, `log.md`, `overview.md`, `knowledge/.manifest.json`).
- Manifest schema is defined and documented — evidence: `.manifest.json` content plus a doc section describing its fields.
- Hot/index/log/overview pages exist with at least seed content, not empty stubs — evidence: file contents in diff.
- Verification metadata recorded in handoff and PR — evidence: `docs/HANDOFF.md` entry and PR body Verification Status/Level/Method/Evidence/Limitations/Required Next Verifier fields.

## Verification Plan

Level 0/1 for the vault content itself (documentation/markdown); Level 2 if any API-side read/write path is exercised (`PYTHONPATH=apps/api pytest apps/api/tests -q`); Level 3 via GitHub CI on the opened PR.

## Suggested Delegation

Knowledge Agent: seed `knowledge/wiki/*` with real hot/index/log/overview content derived from current durable state docs, confirm `.manifest.json` schema, and wire any minimal `KnowledgePage` read path needed to expose vault pages — without changing the existing model shape.

## Board Linkage

- Plane: AOS-3 (Knowledge Vault Seed, Todo / status:ready)
- Branch: `claude/aos-runtime-002-scanner-1egyjw`
