# Portfolio Reality Test — pydantic-ai + claude-agent-sdk-python (AOS-21)

## Purpose

v0.1 proved the ArchetypeOS loop on ArchetypeOS itself. This is the first **portfolio** reality test: run the existing pipeline (Repository Registry → Scanner → DNA → Architecture graph → Digest) against **real repositories the system did not write**, and report honestly what each engine did and did not understand. Per the Fable-5 handoff, this "is the cheapest reality test of every engine and will generate the next round of honest lessons."

**Targets (operator-chosen):**
1. **`pydantic/pydantic-ai`** — an LLM agent framework with a model/provider abstraction and structured outputs, on AOS's own pydantic/FastAPI stack; the most relevant possible input to the Agent Council (AOS-COUNCIL-001). A **docs-heavy multi-package monorepo**.
2. **`anthropics/claude-agent-sdk-python`** — the SDK AOS's own `ClaudeCodeProvider` targets. A **lean, source-heavy single-package SDK** — a deliberately different shape, to test the scanner on both extremes. Acquired by dogfooding this package's own `clone_repo` (a real network clone).

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

## Second repo — `anthropics/claude-agent-sdk-python` (a deliberately different shape)

Acquired via this package's `clone_repo` (a real network clone — dogfood). Evidence: `.archetype/portfolio/claude-agent-sdk-python/scan.json`.

| Engine | Result |
| --- | --- |
| **Scanner** | 130 files, no crash. Languages Python (92), YAML (12), Markdown (11), Shell (4), JS (1). |
| **Manifests / pkg mgrs** | 1 manifest (`pyproject.toml`); `package_managers=['python']`. |
| **Docker / CI** | `has_docker=true` (`Dockerfile.test`); 11 CI files. |
| **Risk signals** | **`DOCKER_WITHOUT_ENV_TEMPLATE` (warning)** — a correct, actionable signal that did **not** fire on pydantic-ai (no Docker there). Risk detection works. |
| **DNA** | `package_managers=['python']`, `confidence 0.65`, draft. |
| **Architecture** | 8 nodes, 7 edges — **all `contains`** (LES-014 confirmed again). |

## Cross-repo comparison

| | pydantic-ai (monorepo) | claude-agent-sdk-python (lean SDK) |
| --- | --- | --- |
| Files | 2071 | 130 |
| **Python share (by file count)** | **28%** (YAML-dominated) | **77%** (source-dominated) |
| Manifests | 8 (multi-package) | 1 |
| Docker | none | `Dockerfile.test` → risk signal ✅ |
| Architecture edges | 14 `contains` | 7 `contains` |

The contrast is the real payoff: **LES-013 is repo-dependent** — file-count language mix misreads the docs/config-heavy monorepo (28% Python) but reads the lean SDK **correctly** (77% Python). So the gap bites exactly on config/docs-heavy real-world repos. **LES-014 is universal** — tree-only edges on both. And a real risk signal (`DOCKER_WITHOUT_ENV_TEMPLATE`) fired correctly on the repo that warranted it.

## Verdict

**The scanner generalizes across shapes.** It ingested both a large docs-heavy multi-package monorepo and a lean single-package SDK cleanly — correct languages, all manifests, ecosystems, CI, Docker, test presence, and an actionable risk signal where warranted — with no tuning and no failure. The read-only-scan + draft-DNA discipline held on both. A genuine structural pass on "understand a codebase the system did not write."

**Two honest gaps surfaced** (the point of the exercise). Neither is fixed here — each becomes a recorded lesson + a scoped follow-up (the Fable note itself directs the architecture-semantics one as a follow-up).

### Gap 1 — language mix is raw-file-count weighted (→ LES-013)

`language_mix` counts files, so on pydantic-ai YAML (1183) outranks Python (564): **Python is only 28% of files** in a repo that is unambiguously a Python library. Any downstream read that keys on "the top language" (a naive Technology-Fitness or DNA summary) would **misclassify pydantic-ai**. The second repo makes the gap precise: claude-agent-sdk-python reads **correctly** (77% Python) because it is source-heavy — so the misread is **repo-dependent**, biting specifically on config/docs/CI-heavy real-world repos. Fix (follow-up): weight by lines-of-code and/or classify source vs. config/docs before ranking.

### Gap 2 — the architecture graph is directory-tree-only (→ LES-014)

All 14 edges are `contains` (folder containment). There are **no dependency or manifest-derived edges** — the monorepo's real structure (which sub-package depends on which; what each `pyproject.toml` declares; import/service relationships) is invisible. For a single self-scan this was tolerable; with a real monorepo it is the dominant missing signal. This is precisely the Fable-flagged follow-up: *"architecture-graph semantics (manifest/compose-derived edges) matter much more once two repos are visible."* Fix (dedicated follow-up package): derive edges from manifests (workspace/dependency declarations), compose files, and import graphs.

## Follow-ups this test generates

- **LES-013 → language-mix weighting package**: LoC/source-classified language ranking (fixes the "YAML repo" misread).
- **LES-014 → architecture-semantics package**: manifest/dependency/compose-derived edges (the Fable-named next step; higher value now that a real monorepo is visible).
- **Council over these repos** (stretch, later): the captured DNA/architecture is the first real, non-self-referential input for an AOS-COUNCIL run (Research/Architecture/Fitness/Security) — and both targets' own provider-abstraction + structured-output patterns are exactly what the Council's evolution should mine.

## Evidence

- `.archetype/portfolio/pydantic-ai/scan.json` and `.archetype/portfolio/claude-agent-sdk-python/scan.json` — the captured derived scans (summary, language_mix, manifests, ci, risk_signals, DNA, architecture counts/types).
- Reproduce: `scripts/onboard_repo.sh <git-url> <name>` (acquires the clone via `clone_repo`), then register + scan via the API (the script prints the curl commands). Targets: `https://github.com/pydantic/pydantic-ai.git pydantic-ai` and `https://github.com/anthropics/claude-agent-sdk-python.git claude-agent-sdk-python`.
