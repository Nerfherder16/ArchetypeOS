# Portfolio Reality Test — pydantic/pydantic-ai (AOS-21)

## Purpose

v0.1 proved the ArchetypeOS loop on ArchetypeOS itself. This is the first **portfolio** reality test: run the existing pipeline (Repository Registry → Scanner → DNA → Architecture graph → Digest) against a **real repository the system did not write**, and report honestly what each engine did and did not understand. Per the Fable-5 handoff, this "is the cheapest reality test of every engine and will generate the next round of honest lessons."

**Target (operator-chosen): `pydantic/pydantic-ai`** — an LLM agent framework with a model/provider abstraction and structured outputs, on AOS's own pydantic/FastAPI stack; the most relevant possible input to the Agent Council (AOS-COUNCIL-001) and the External Repo Scout's charter realized.

## Method

The Orchestrator cloned pydantic-ai (`git clone --depth 1`, proxied HTTPS) into `repositories/pydantic-ai` (gitignored) and ran the **full persisted pipeline** in a Python 3.12 venv against an in-memory sqlite: register a `Repository` (`local_path=pydantic-ai`) → `run_scan` (persists `RepositoryDNA` + `ArchitectureNode`s/`ArchitectureEdge`s) → `build_digest` over the external project. Derived output captured at `.archetype/portfolio/pydantic-ai/scan.json` (the clone itself is not committed).

## What the engines produced

| Engine | Result |
| --- | --- |
| **Scanner** | 2071 files / 163 dirs in 0.1s, no crash, no `MAX_FILES` truncation. Languages: Python, YAML, Markdown, TypeScript, JavaScript, HTML, CSS, Shell. |
| **Manifests** | **All 8 found** — 7 python `pyproject.toml` across the monorepo sub-packages (`pydantic_ai_slim`, `pydantic_evals`, `pydantic_graph`, `clai`, `examples`, root) + 1 node `package.json` (docs-site). `package_managers = ['npm', 'python']`. |
| **CI / Docker** | 23 GitHub Actions workflows detected (`has_ci=true`); `has_docker=false` (correct — no Dockerfile); `has_tests=true`. |
| **Risk signals** | 1 — `MULTIPLE_ECOSYSTEMS` (info): "Manifests span multiple language ecosystems" (correct: python + node). `risk_flags = []`. |
| **DNA** | Persisted: `language_mix`, `package_managers`, `scan_summary`, `confidence=0.65`, `status=draft`. |
| **Architecture** | 15 nodes (1 `repository` + 14 `directory`), 14 edges — **all `contains`**. |
| **Digest** | Ran over the external project: "1 repositories, 1 scan runs, 0 decisions …; 1 draft suggestion" → *Record the first decision for this project*. |

## Verdict

**The scanner generalizes.** It ingested an unfamiliar, real, multi-package monorepo cleanly and correctly identified its languages, all sub-package manifests, its ecosystems, CI, and test presence — with no tuning and no failure. The read-only-scan + draft-DNA discipline held. This is a genuine pass on "understand a codebase the system did not write" at the structural level.

**Two honest gaps surfaced** (the point of the exercise). Neither is fixed here — each becomes a recorded lesson + a scoped follow-up (the Fable note itself directs the architecture-semantics one as a follow-up).

### Gap 1 — language mix is raw-file-count weighted (→ LES-013)

`language_mix` counts files, so YAML (1183) outranks Python (564): **Python is only 28% of files** in a repo that is unambiguously a Python library. `primary_language_hints` (`[Python, Shell, HTML]`) partly compensates but still elevates config/scripting noise. Any downstream read that keys on "the top language" (a naive Technology-Fitness or DNA summary) would **misclassify pydantic-ai**. Real-world repos are config/docs-heavy; file-count language mix is a misleading primary signal. Fix (follow-up): weight by lines-of-code and/or classify source vs. config/docs before ranking.

### Gap 2 — the architecture graph is directory-tree-only (→ LES-014)

All 14 edges are `contains` (folder containment). There are **no dependency or manifest-derived edges** — the monorepo's real structure (which sub-package depends on which; what each `pyproject.toml` declares; import/service relationships) is invisible. For a single self-scan this was tolerable; with a real monorepo it is the dominant missing signal. This is precisely the Fable-flagged follow-up: *"architecture-graph semantics (manifest/compose-derived edges) matter much more once two repos are visible."* Fix (dedicated follow-up package): derive edges from manifests (workspace/dependency declarations), compose files, and import graphs.

## Follow-ups this test generates

- **LES-013 → language-mix weighting package**: LoC/source-classified language ranking (fixes the "YAML repo" misread).
- **LES-014 → architecture-semantics package**: manifest/dependency/compose-derived edges (the Fable-named next step; higher value now that a real monorepo is visible).
- **Council over pydantic-ai** (stretch, later): the captured DNA/architecture is the first real, non-self-referential input for an AOS-COUNCIL run (Research/Architecture/Fitness/Security) — and pydantic-ai's own provider-abstraction + structured-output patterns are exactly what the Council's evolution should mine.

## Evidence

- `.archetype/portfolio/pydantic-ai/scan.json` — the captured derived scan (summary, language_mix, manifests, ci, risk_signals, DNA, architecture counts/types).
- Reproduce: `scripts/onboard_repo.sh https://github.com/pydantic/pydantic-ai.git pydantic-ai` (acquires the clone), then register + scan via the API (the script prints the curl commands).
