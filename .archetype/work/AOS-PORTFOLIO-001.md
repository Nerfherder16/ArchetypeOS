# AOS-PORTFOLIO-001 — Portfolio: onboard + scan a second real repository (pydantic-ai), evaluate every engine

## Status

In Progress

## Origin

Plane **AOS-21** ("Portfolio: register and scan a second real repository"). v0.1 proved the loop on ArchetypeOS itself; "Engineering Intelligence Platform" means portfolio. Operator chose the target: **`pydantic/pydantic-ai`** ("go") — the most beneficial real repo to onboard (an LLM agent framework with a provider abstraction + structured outputs, on AOS's own pydantic/FastAPI stack, and the ideal first real input to the Agent Council). The Fable-5 handoff frames this as "the cheapest reality test of every engine … will generate the next round of honest lessons," and flags a follow-up: architecture-graph semantics (manifest/dependency-derived edges) matter more once two repos are visible. Operator sequence: this (AOS-21) then a definitive-roadmap reevaluation.

## Reality test already run (Orchestrator, in-session — this IS the evaluation half)

The Orchestrator cloned pydantic-ai (proxied HTTPS) into `repositories/pydantic-ai` (gitignored) and ran the **full pipeline** against sqlite: `run_scan` persisted a `RepositoryDNA` + 15 `ArchitectureNode`s + 14 `ArchitectureEdge`s, and `build_digest` ran over the external project. Captured evidence: `.archetype/portfolio/pydantic-ai/scan.json`. Findings (the deliverable's substance):

- **Positive — the scanner generalizes.** 2071 files scanned in 0.1s, no crash/truncation. Correct multi-language detection; **all 8 manifests found** (7 python `pyproject.toml` across the monorepo sub-packages `pydantic_ai_slim`/`pydantic_evals`/`pydantic_graph`/`clai`/`examples` + 1 node `package.json` for docs-site); `package_managers=['npm','python']`; 23 GitHub Actions workflows; `has_ci/has_tests=true`, `has_docker=false` (correct); a correct `MULTIPLE_ECOSYSTEMS` info signal. DNA persisted (`confidence 0.65`, `status draft`); digest produced a "Record the first decision" draft rec for the new project.
- **Gap 1 (→ LES-013): language mix is raw-file-count weighted.** YAML (1183) outranks Python (564) — **Python is only 28% by file count** — for a repo that is obviously a Python library. A DNA/Technology-Fitness read keyed on the top language would misclassify pydantic-ai. `primary_language_hints` partly compensates but still lists Shell/HTML in the top 3. Weighting by lines-of-code or source-vs-config classification is the fix (follow-up).
- **Gap 2 (→ LES-014): architecture edges are tree-only.** 14 edges, all `contains` (directory containment); zero dependency/manifest-derived edges. A real monorepo's inter-package structure (which sub-package depends on which; which manifest declares what) is invisible. This is exactly the Fable-flagged follow-up ("manifest/compose-derived edges"). Scope for a dedicated architecture-semantics package.

## This package's scope

Two deliverables: (1) a repeatable **repo-acquisition capability** (the missing clone step — today the system assumes a repo is already under `repository_root`), and (2) the **evaluation artifact + honest lessons** from the reality test. It does NOT fix Gap 1/Gap 2 — those become scoped follow-ups (as the Fable note itself directs).

## Verified Baseline

- Onboarding today: `POST /projects/{id}/repositories` (registers `local_path`, `safe_repo_path` validates it's under `repository_root`) → `POST /repositories/{id}/scan` → `run_scan` → `scan_repository(path)` (MAX_FILES=20000, ignores `.git`) → persists DNA + architecture. **There is no acquire/clone step** — the repo must already be at `repository_root/<local_path>`.
- `repositories/` is gitignored (the dev repos dir). `safe_repo_path` (`repository_scanner.py:114`) resolves + rejects traversal outside root.
- Core-service code lives in `packages/aos_core/aos_core/services/`; guarded by the missing-core-tests rule (tests under `packages/aos_core/tests/` or `apps/api/tests/`). `git` is available in the runtime.

## In-Scope Files

- `packages/aos_core/aos_core/services/onboarding.py` (new): `clone_repo(url, name, repository_root, ref=None, runner=subprocess.run) -> Path` — validates `name` (single path segment, no `/`/`..`), builds `git clone --depth 1 [--branch <ref>] <url> <dest>` where `dest = repository_root/name`, runs it, returns `dest`. Idempotent (if `dest` exists and is non-empty, return it without recloning). Raises `ValueError` on unsafe name, `RuntimeError` on clone failure / missing git. `runner` is injectable for hermetic tests.
- `scripts/onboard_repo.sh` (new): thin wrapper — `onboard_repo.sh <git-url> <name> [ref]` runs the clone via `python -m` (or calls `git` then prints the register+scan curl commands for a running API). Executable bit set (LES: shell scripts need +x).
- `apps/api/tests/test_onboarding.py` (new): a real `file://` local-repo clone (create a tiny git repo in `tmp_path`, clone it — real git, no network) asserting the dest lands under the root + is populated + idempotent re-run; a path-safety test (`..`/`a/b` name → `ValueError`); a mocked-`runner` test asserting the argv (`git clone --depth 1 …`).
- `.archetype/portfolio/pydantic-ai/scan.json` (captured evidence — already written by the Orchestrator).
- `docs/PORTFOLIO_PYDANTIC_AI.md` (new): the evaluation write-up (findings above, honest gaps, follow-ups).
- `knowledge/wiki/lessons/LES-013.md` + `LES-014.md` + `index.md` rows (the honest lessons).
- `docs/CAPABILITY_MAP.md`, state docs + this spec.

## Out-of-Scope

- **Fixing Gap 1 (language weighting) or Gap 2 (dependency/architecture edges)** — recorded as LES-013/LES-014 + scoped follow-up packages (architecture-semantics is the Fable-named next step). No scanner behavior change here. No API `onboard` endpoint (the script + function suffice for now; an endpoint that clones is a later step needing the vault-mount-style plumbing). No live-clone in CI (network/non-determinism) — the pydantic-ai run is captured evidence, not a CI test. No web change.

## Design

- **`clone_repo`**: pure-ish, injectable-runner, path-safe, idempotent, stdlib `subprocess` (no new dep). The acquire step the portfolio needs; unit-tested hermetically (real `file://` clone + mocked argv + safety).
- **Evaluation** (`docs/PORTFOLIO_PYDANTIC_AI.md`): records the reality test — what worked (generalization, multi-manifest monorepo detection), the two honest gaps with the captured numbers (28% Python by file count; 14 contains-only edges), and the follow-up packages. Cites `.archetype/portfolio/pydantic-ai/scan.json`.
- **Lessons**: LES-013 (file-count language mix misrepresents a library's primary language on a docs/config-heavy repo — quantified on pydantic-ai), LES-014 (architecture graph is directory-tree-only; dependency/manifest edges are needed once >1 repo/monorepo is visible — the Fable-flagged follow-up). Both `open` (they name real, unfixed gaps) so the digest surfaces them — closing the loop the knowledge read path just built.

## Acceptance Criteria

- **Repo acquisition works + is safe** — evidence: `test_onboarding` — a real `file://` clone lands a populated repo under the root and is idempotent on re-run; an unsafe `name` (`..`, `a/b`) raises `ValueError`; the mocked runner receives `git clone --depth 1 …`.
- **The pipeline generalizes to a real external repo** — evidence: `docs/PORTFOLIO_PYDANTIC_AI.md` + `.archetype/portfolio/pydantic-ai/scan.json` record the real run (2071 files, 8 manifests, npm+python, 23 CI, 14 contains edges, DNA persisted) — the Orchestrator's in-session full-pipeline execution.
- **Honest lessons recorded** — evidence: LES-013 + LES-014 pages + index rows (status `open`); the digest now surfaces them (the knowledge read path consumes them).
- **Nothing broken** — evidence: api suite (99 + new) + worker (7) green; ruff (CI scope `apps/api packages/aos_core apps/worker tools`) + compile clean.

## Verification Plan

Level 2: 3.12 venv — ruff (full CI scope, per LES-012) + compile; `pytest apps/api/tests` incl. `test_onboarding`. Level 4 (Orchestrator): independently run `clone_repo` against a throwaway `file://` git repo (dest under root, idempotent, safety raises); re-confirm the captured pydantic-ai evidence by re-running the full `run_scan` pipeline against the clone (DNA + 14 contains edges + 8 manifests). Level 3: CI (api-tests + compose-smoke unaffected — no runtime/compose change). Merge under the Manual Merge Gate; on merge Plane AOS-21 → Done; then the definitive-roadmap reevaluation.

## Learning / Feedback Loop

This package's OUTPUT is lessons (the reality test's purpose). LES-013 + LES-014 are the honest lessons; both `open` so they enter the improvement queue and surface in the digest/dashboard. Any CI failure → additional lesson (apply LES-012: ruff at full CI scope locally).

## Suggested Delegation

Runtime Agent (Opus): `onboarding.py` `clone_repo` + `scripts/onboard_repo.sh` + `test_onboarding.py`. Orchestrator (Opus 4.8): this spec; the reality-test execution + evidence capture (done); `docs/PORTFOLIO_PYDANTIC_AI.md` + LES-013/LES-014; independent `clone_repo` + full-pipeline re-verification; guardian; PR; Manual Merge Gate.

## Board Linkage

- Plane: **AOS-21** (In Progress; **merging closes it**). Follow-ups it spawns: language-mix weighting (LES-013), architecture dependency-edge semantics (LES-014, Fable-flagged).
- Branch: `claude/aos-runtime-002-scanner-1egyjw` (env-pinned). Then the definitive-roadmap reevaluation.
