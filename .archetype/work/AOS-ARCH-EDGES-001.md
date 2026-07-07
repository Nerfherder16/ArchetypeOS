# AOS-ARCH-EDGES-001 — Manifest-derived architecture edges (LES-014, non-compose half)

- Status: In Progress
- Owner: laptop session (parallel Orchestrator)
- Branch: `laptop/aos-arch-manifest-edges` (fresh, cut from `origin/main` @ `8a7fd6a`, post-#76)
- Closes: LES-014 (the manifest/dependency half; the compose/service half shipped in PR #59).

## Verified Baseline (confirmed by inspection)

- `packages/aos_core/aos_core/repository_scanner.py`:
  - Architecture **nodes** are: one `repository` root (label = repo dir name), up to 20 top-level `directory` nodes (label = dir name), and compose `service` nodes (:603-644). Nodes are keyed by **label**.
  - Architecture **edges** are: `contains` (repo→dir, :609-612) and `depends_on` (service→service from compose, :652-661). Edge dict shape `{"from": label, "to": label, "type": ..., "confidence": ..., "evidence": [...]}`; edges reference nodes **by label**.
  - The scanner already reads manifest **bodies** (bounded/tolerant) for framework detection (`_detect_frameworks`), and has the `manifests` list `[{path, kind}]`. **Update (2026-07-06): the local/path-dependency PARSERS already exist and are UNUSED** — `_local_deps_requirements` / `_local_deps_pyproject` / `_local_deps_package_json` / `_local_deps_gomod` (:329-417), dispatched by `_LOCAL_DEP_PARSERS` (:420-425), each returning raw local dep path strings (`-e ./`, poetry/uv `path=`, `file:`/`link:`, go.mod `replace => ./`). Confirmed never called. So this package **wires the existing parsers** (extraction is done) + adds resolution + edge emission — it does NOT write new parsers.
- `packages/aos_core/aos_core/services/scan.py` (:94-126): persists edges by resolving `from`/`to` labels via `node_by_label`; **silently skips** an edge whose endpoints don't both resolve to existing nodes. Upsert key `(repository_id, from_node_id, to_node_id, type)`. No schema change needed for a new edge of an existing/!new type.
- `apps/api/tests/test_scanner.py`: the compose test asserts `{(from,to) for depends_on edges} == expected` on the `COMPOSE_REPO` fixture (which has no cross-package manifest path-deps).

## Design (LES-014: internal path-dependency edges)

Emit `depends_on` architecture edges derived from **local/path dependencies** declared in manifests, at the existing **top-level-directory node granularity**.

- **Use the existing `_LOCAL_DEP_PARSERS`** (`_local_deps_{requirements,pyproject,package_json,gomod}`) for extraction — they already return the raw local dep path strings for python/node/go, bounded/tolerant. No new parser is written. (Rust/JVM/.NET path deps remain a follow-up, matching LES-016's ecosystem set.)
  - Read each detected manifest whose basename is in `_LOCAL_DEP_PARSERS` via the existing bounded `_read_capped`; call the parser; skip on any error (tolerant).
- For each parsed local dep: resolve the target path relative to the manifest's directory → repo-relative → take its **top-level segment**; take the manifest's own **top-level segment**. If both top-level segments (a) differ and (b) each match an existing `directory`/`repository` node label, emit `{"from": manifest_top, "to": target_top, "type": "depends_on", "confidence": 0.6, "evidence": ["<manifest_rel> local dependency -> <target_rel>"]}`. Dedup (skip duplicate from/to/type); skip self-loops and unresolved.
- Reuse the `depends_on` type (a package dependency IS a depends_on; provenance is in `evidence`). This does not break the compose test (its fixture has no path-deps), verified by TDD. If a future fixture mixes both, the evidence string distinguishes provenance.

## In-Scope Files (exact)
- `packages/aos_core/aos_core/repository_scanner.py`
- `apps/api/tests/test_scanner.py`
- `.archetype/work/AOS-ARCH-EDGES-001.md`
- `knowledge/wiki/lessons/index.md` (close LES-014) + `LES-014.md`
- `docs/CAPABILITY_MAP.md` (arch-edge note) · `docs/ACTIVE_WORK.md` + `docs/RECENT_CHANGES.md` (own entries — union-safe)

## Out-of-Scope
- Import-graph edges (resolving source `import` statements) — a heavier separate follow-up; LES-014's manifest half is this package.
- Sub-directory `component` nodes (edges stay at top-level-dir granularity, matching today's node model).
- rust/JVM/.NET path deps (python+node+go cover the common monorepo cases; others are a follow-up).
- No schema/migration change; `scan.py` persistence untouched (reuses the generic label→node edge path).
- `transfer.py`/`distillation.py`/embeddings/web (remote's zone); CURRENT_STATE sprint line + HANDOFF.

## Acceptance Criteria (assertions, each with evidence)
1. A synthetic monorepo where `apps/api/requirements.txt` has `-e ../../packages/aos_core`, `web/package.json` has a `file:../shared` dep, and `svc/go.mod` has `replace ... => ../shared` yields `depends_on` edges `apps→packages`, `web→shared`, `svc→shared` (top-level granularity), with manifest-provenance evidence. — evidence: `test_scan_emits_manifest_dependency_edges`.
2. Self-loops and deps whose top-level target has no node are skipped; no duplicate edges. — evidence: same test asserts absence.
3. The existing compose `depends_on` test still passes unchanged (no pollution). — evidence: `test_compose_fixture_yields_service_nodes_and_depends_on_edges` green.
4. Parsing is tolerant: a malformed/binary/absent manifest never raises; a repo with no local deps emits no new edges (self-scan of ArchetypeOS unchanged unless it declares a parseable local path dep). — evidence: tolerance test + self-scan.
5. Full gate green: ruff + compileall + pytest api+worker; guardian PASS. — evidence: CI + guardian.

## Verification Plan
- TDD: write the new edge tests (RED) → implement parser + edge emission → GREEN.
- Level 2 (local): ruff (apps/api packages/aos_core apps/worker tools) + compileall + `pytest apps/api/tests -q`; self-scan of this repo to see whether it declares a parseable local path dep (informational).
- Level 3: CI green → Manual Merge Gate.

## Board Linkage
- Closes LES-014. Plane: AOS-ARCH-EDGES-001 (create as Done on merge; Plane currently 502 — pending).
