# AOS-ARCH-001 — Architecture Spine Graph API

## Status

Merged (PR #25, merge commit `b9b3024`)

## Verified Baseline

Confirmed by inspection:

- `ArchitectureNode` (`apps/api/app/models.py`) exists with `project_id`, `repository_id`, `label`, `type`, `parent_id`, `confidence`, `evidence`, `risks`, `related_decision_ids`, `manual_correction`, plus AuditMixin fields (`id`, `status`, `version`, timestamps).
- `ArchitectureEdge` exists with `project_id`, `repository_id`, `from_node_id`, `to_node_id`, `type`, `confidence`, `evidence`, `manual_correction`, plus AuditMixin fields.
- `POST /repositories/{id}/scan` (`apps/api/app/main.py`) seeds a repository root node, up to 20 top-level directory nodes, and `contains` edges, all status `draft` — but creates NEW rows on every scan, so rescans duplicate the root/directory nodes and would strand any `manual_correction` on the superseded rows.
- No architecture read or correction endpoints exist; `apps/api/app/schemas.py` has no architecture schemas.
- v0.1 scope lock requires: graph stored as data, node/edge confidence fields, manual correction fields, uncertain relationships marked.

## In-Scope Files

- `apps/api/app/main.py` (scan-endpoint node/edge upsert + new routes)
- `apps/api/app/schemas.py` (architecture read/update schemas)
- `apps/api/tests/test_architecture_api.py` (new)
- state docs + this spec

## Out-of-Scope

- model/schema changes to `ArchitectureNode`/`ArchitectureEdge` tables
- graph visualization UI (placeholder only per scope lock)
- graph database
- node/edge deletion or staleness lifecycle (future package)
- scan report schema changes (`repository_scanner.py` untouched)
- scan run history/persistence (AOS-4)

## Acceptance Criteria

- Graph is queryable per project with optional repository filter — evidence: `test_architecture_graph_query_after_scan`, `test_architecture_graph_repository_filter`.
- Nodes and edges carry confidence and manual-correction fields in responses — evidence: response-shape assertions in `test_architecture_graph_query_after_scan`.
- Manual corrections can be applied via API and persist — evidence: `test_node_manual_correction_persists`.
- Rescan regenerates the graph without duplicating nodes or orphaning corrections (same node ids, corrections retained, confidence/evidence refreshed) — evidence: `test_rescan_preserves_node_ids_and_corrections`.
- Unknown project/node/edge return 404 — evidence: `test_architecture_api_404s`.
- Existing scan response shape unchanged — evidence: existing `test_scan_endpoint_*` tests still green.

## Verification Plan

Level 2 locally: `python3 -m ruff check apps/api apps/worker tools`, `compileall`, `PYTHONPATH=apps/api pytest apps/api/tests -q` (existing 20 + new tests). Level 3 via GitHub CI on the PR; merge under the Manual Merge Gate.

## Suggested Delegation

Runtime Agent (Opus): implement upsert + routes + schemas + tests to this spec. Orchestrator (Fable): spec, review, verification, PR, merge gate.

## Board Linkage

- Plane: AOS-5 (In Progress update pending — Plane temporarily down)
- Branch: `claude/aos-runtime-002-scanner-1egyjw`
