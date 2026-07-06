# AOS-ARCH-SEMANTICS-001 — Phase B: architecture semantics (compose-derived edges) + language weighting

## Status

In Progress

## Origin

Operator direction: after Phase C completed and RFC-0008 was queued, "continue on with what we were doing … to keep in line with the roadmap." Phase B is the roadmap item that makes the scanner's **structural evidence** richer — directly improving what the Council/fitness agents reason over (complementary to RFC-0008's future *content* extraction). It consumes two open reality-test lessons:

- **LES-014** — the architecture graph is **directory-tree-only** (`contains` edges); dependency/compose-derived edges are the missing signal (`example-voting-app`'s compose file has a service graph the scanner ignores).
- **LES-013** — `language_mix` is **raw-file-count** weighted, so config/docs-heavy repos misreport their primary language (pydantic-ai reads 28% Python by file count; `free-llm` reads Markdown-dominant).

## Verified Baseline

- `repository_scanner.py::scan_repository` builds `architecture_nodes` = `[repository] + top-level directories` and `architecture_edges` = **only `contains`** (repo → each dir). It already **detects** compose files (`COMPOSE_FILES`, `_docker_kind`) but never parses them. It classifies languages by extension (`EXTENSIONS` → `language_counts`); `primary_language_hints` = top-3 by file count minus an ad-hoc `LANGUAGE_HINT_EXCLUDE = {"Markdown","YAML"}`. **It never reads file bodies** (no `read_text`) — so LES-013 must use **classification**, not line counting.
- `services/scan.py` persists nodes/edges **generically by `type`** (any new `type` string just works) and writes `RepositoryDNA` — which already has a `runtime_services` (list) field (currently unused) and a `scan_summary` (dict) field carrying `primary_language_hints`. `ArchitectureNode.type`/`ArchitectureEdge.type` are `String` — **new type values need no migration**; new `scan_summary` keys are JSON — **no migration**.
- **PyYAML is not a declared dependency** of the scanner's runtimes (`apps/api`, `apps/worker`) — it must be added for robust compose parsing (list- and map-form `depends_on`).
- `_select_architecture`/`_select_fitness` council selectors read architecture nodes + DNA language signals, so this enrichment also improves Council evidence.

## In-Scope Files

- **`packages/aos_core/aos_core/repository_scanner.py`**:
  - **LES-014 (compose edges):** for each detected compose file, parse it with `yaml.safe_load` and derive **service nodes** (`{label: <service>, type: "service", confidence, evidence: [compose path]}`) and **`depends_on` edges** (`{from: <service>, to: <dep>, type: "depends_on", confidence, evidence}`), handling both the list form (`depends_on: [db, redis]`) and the map form (`depends_on: {db: {condition: ...}}`). Optionally a repo→service `defines` edge. **Tolerant**: missing/malformed/ës non-dict compose → no service nodes, never raises (wrap parse in try/except; a broken compose file adds a `note`, not an exception). Bound the number of services/edges (reuse the existing node caps).
  - **LES-013 (language weighting):** add a `LANGUAGE_CLASS` map classifying each `EXTENSIONS` language into `source` / `config` / `markup` / `data` / `docs`. Derive `primary_language` = highest-count language among **source**-classified languages (fallback: overall top if none). Rebuild `primary_language_hints` to rank **source** languages first (retiring the ad-hoc `LANGUAGE_HINT_EXCLUDE`). Keep `language_mix` (raw counts) unchanged for backward compatibility; add `primary_language` and `language_classes` to the returned `summary`.
- **`packages/aos_core/aos_core/services/scan.py`**: populate `RepositoryDNA.runtime_services` from the compose services; ensure `scan_summary` carries the new `primary_language`. (Node/edge persistence already generic — confirm `service`/`depends_on` flow through unchanged.)
- **`apps/api/requirements.txt`** and **`apps/worker/requirements.txt`**: add `PyYAML` (pinned, matching the installed 6.0.x).
- **`apps/api/tests/test_scanner.py`**: assert (a) a compose fixture yields `service` nodes + `depends_on` edges matching its `depends_on` graph, and populates `runtime_services`; (b) a docs/config-heavy fixture reports `primary_language` as the **source** language (e.g. Python), not Markdown/YAML; (c) tolerant cases — no compose file → no service nodes; a malformed compose → a note, no exception. Count-agnostic where counts are derived from the fixture.
- **`apps/api/tests/fixtures/…`** (new): a minimal multi-service `docker-compose.yml` (e.g. `web depends_on [db, redis]`, `worker depends_on [db]`) + a couple of source/config/docs files so the language classification is exercised. (Place under an api tests fixtures dir; do not disturb `apps/web/e2e/fixtures/demo-repo`.)
- **Lessons**: **close LES-013** (language weighting shipped) citing this package; **update LES-014** — the **compose/service edge** half is delivered; **manifest/dependency + import-graph edges remain** (a smaller follow-up), so LES-014 stays **open** with its Status/Consumed-by updated to reflect the partial consumption. (No new lesson unless the build surfaces one.)
- **Docs**: `docs/CAPABILITY_MAP.md` (Layer 3 — architecture now includes compose/service edges; Layer-3/DNA language weighting), `.archetype/work/AOS-ARCH-SEMANTICS-001.md` (this spec), state docs.

## Out-of-Scope

- **Manifest/workspace dependency edges and import-graph edges** (the monorepo half of LES-014 — `pyproject`/`package.json` workspace resolution) — a follow-up; LES-014 stays open for it.
- **LoC-based language weighting** — rejected (the scanner does not read file bodies; classification achieves the fix without new I/O).
- No new DB tables / no Alembic migration (new node/edge `type` strings + JSON `scan_summary`/`runtime_services` are schema-compatible).
- No frontend change (the architecture API already renders whatever nodes/edges exist; a richer graph view is a later UI package).

## Acceptance Criteria

- Scanning a repo with a multi-service compose file yields **`service` nodes + `depends_on` edges** reflecting the compose `depends_on` graph (both list and map forms), and populates `RepositoryDNA.runtime_services` — verified on a fixture.
- A config/docs-heavy repo reports a **source-classified `primary_language`** (not Markdown/YAML) — verified on a fixture.
- Tolerant: no/broken compose never raises; `language_mix` stays backward-compatible.
- api + worker suites green on the CI-scope venv; ruff full CI scope + compileall clean; **compose-smoke still builds** with the new PyYAML dep; guardian PASS. No migration.

## Verification (Orchestrator, independent — builder ≠ verifier)

Re-run api+worker; scan the compose fixture and assert the `depends_on` edge set + `runtime_services`; scan a docs-heavy fixture and assert `primary_language`; confirm tolerant behavior on a malformed compose; confirm PyYAML is declared where the scanner runs; confirm no migration and no frontend change; ruff full CI scope + compileall; guardian. (Bonus: re-scan `free-llm-api-resources` / `example-voting-app` from `repositories/` to sanity-check real output.)
