---
name: aos-validation-and-qa
description: Use when writing the tests and PR-body evidence that CLEAR a Guardian finding, when adding or running ArchetypeOS tests, when a test-coverage or evidence finding blocks (missing-api-tests, missing-core-tests, missing-acceptance-evidence, empty-acceptance-evidence, possible-secret on fixtures), when a PR body needs Verification Status or Verification Level values, when pgvector or embedder marked tests skip unexpectedly, when Playwright e2e hits strict mode violations or flaky counts, or when reality_test_distillation.py rankings or portfolio scan.json are questioned. (Gate policy and override decisions are aos-change-control.)
---

# ArchetypeOS Validation and QA

## 1. Overview

This skill defines what counts as evidence in ArchetypeOS and how to add tests that survive the repo's governance. It covers the PR-body evidence bar enforced by the deterministic PR Guardian (`tools/pr_guardian.py`), the builder-is-not-verifier protocol, the certified portfolio inventory that anchors reuse-ranking regressions, the four test layers with exact run commands, per-layer test-addition recipes, fixture hygiene rules earned through Guardian BLOCKs and CI failures, and the acceptance-threshold discipline for scoring changes.

Nothing here permits bypassing PR Guardian, the head-SHA-pinned manual merge gate, or the RFC process. Across all merged PRs, no substantive code BLOCK (tests, secrets, metadata, acceptance evidence) has ever been overridden to force a merge: BLOCKs are fixed in code, never waved through. The verified override-token record lives in aos-change-control section 8.

## 2. When to use / When NOT to use

Use this skill when:

- Adding a test to any layer (api, worker, web e2e, aos_core) or deciding which layer a test belongs in.
- Writing or fixing the verification metadata and Acceptance Evidence sections of a PR body.
- A Guardian BLOCK names a test or evidence code (`missing-api-tests`, `missing-core-tests`, `missing-acceptance-evidence`, `possible-secret`, etc.).
- A `pgvector` or `embedder` marked test is skipping, or you need the gated CI jobs locally.
- A Playwright spec is flaky, racing a refetch, or hitting a strict-mode violation.
- Judging whether a distillation or transfer change regressed the portfolio rankings.

Do NOT use this skill for:

- Gate mechanics, override tokens, and merge protocol details: see `aos-change-control`.
- Diagnosing why a service or test run fails at runtime: see `aos-debugging-playbook`.
- Full history of the lessons cited here: see `aos-failure-archaeology`.
- Writing the lesson or state-doc entries that accompany a fix: see `aos-docs-and-lessons`.
- Standing up the environment (deps, services, ports) from scratch: see `aos-build-run-and-operate`.
- Designing the experiment behind a scoring change: see `aos-research-methodology`.
- The LES-019 evidence-gathering campaign itself: see `aos-evidence-loop-campaign`.

## 3. The evidence bar: PR verification metadata

Every PR body must contain these six fields as plain `Field: value` lines starting at column 0. Markdown wrappers (`- **Field:** value`) do not parse and produce a `missing-verification-metadata` BLOCK.

```text
Verification Status: <one of the five statuses below>
Verification Level: <Level 0 .. Level 5>
Verification Method: <the command, workflow, inspection, or review used>
Evidence: <concrete output: command results, commit SHA, PR URL, workflow status>
Limitations: <what could not be verified and why>
Required Next Verifier: <GitHub CI | Runtime Agent | Human Reviewer | none | ...>
```

Allowed statuses (exact literals from `ALLOWED_VERIFICATION_STATUSES` in `tools/pr_guardian.py`):

| Status | Mergeable? | Guardian finding |
|---|---|---|
| `Verified` | yes, when all other gates pass | none |
| `Verified with warnings` | yes, when warnings are acknowledged | none |
| `Verification pending` | no (PR may stay open) | warn `verification-pending` |
| `Verification unavailable` | no | block `verification-not-mergeable` |
| `Verification blocked` | no | block `verification-not-mergeable` |

Allowed levels are exactly `Level 0` through `Level 5` (`ALLOWED_VERIFICATION_LEVELS`). Meaning, per `docs/VERIFICATION_PROTOCOL.md`: 0 static reasoning, 1 repository inspection, 2 local execution, 3 GitHub CI, 4 runtime verification, 5 human verification. Report the highest level actually reached. Any other status or level string blocks (`invalid-verification-status`, `invalid-verification-level`). Weak placeholder values (`TBD`, `TODO`, `none`, `n/a`) in Method, Evidence, Limitations, or Required Next Verifier draw a `weak-verification-metadata` warning.

Verification metadata has no override marker. If verification cannot run, say so with the honest status; do not fake `Verified`.

### Acceptance Evidence

When any changed file starts with `apps/api/app/`, `apps/worker/app/`, or `apps/web/src/`, the PR body must also contain an `## Acceptance Evidence` heading, and at least one bullet under it must contain `evidence:` (case-insensitive) mapping an acceptance criterion to a test name, command, or CI job. Otherwise:

- block `missing-acceptance-evidence`: no heading found.
- block `empty-acceptance-evidence`: heading exists but no bullet carries `evidence:`.

This mirrors the per-criterion `evidence:` pointers required in work package specs (`docs/rfc/RFC-0003-Work-Package-Specs.md`, `.archetype/work/<TASK-ID>.md`).

## 4. Builder-is-not-verifier protocol

From `docs/ORCHESTRATOR_PLAYBOOK.md` (role contract): builders (subagents implementing inside exact file boundaries) never commit, never push, never self-certify. Their raw command output is input to the Orchestrator's own re-run, not a substitute for it.

Independent verification by the Orchestrator means re-running the full suite yourself, from the repo root:

```bash
python3 -m ruff check apps/api apps/worker tools        # CI runs ruff check apps/api and apps/worker separately, ruff==0.8.6
python3 -m compileall -q apps tools
PYTHONPATH=apps/api pytest apps/api/tests -q
PYTHONPATH=apps/worker pytest apps/worker/tests -q
```

then reading the actual diff and probing live behavior (Level 4 recipes in the playbook). Two hard-won scope rules:

- Lint at CI scope, never narrower. CI lints `apps/api` (the whole tree including `apps/api/alembic/`); a local `ruff check apps/api/app` reported false-green on an unused import in a migration (LES-012, PR #51 CI failure).
- Passing tests handed back by a builder are claims, not evidence, until re-run in your own shell.

The human operator owns merges (Manual Merge Gate), destructive actions, scope changes, and RFC approval. CI (9 jobs in `.github/workflows/ci.yml`, the ground truth; the job-name list's home is aos-change-control section 11. The 5 required branch-protection checks per docs/PR_GUARDIAN.md are PR Guardian, API tests and lint, Worker tests and lint, Web typecheck and build, and Docker Compose smoke test; note that doc lags ci.yml, which also runs Vector store tests, Embedder tests, Web e2e, and the CI green fan-in) is the next verifier after local execution; the gate comment pins the head SHA and must report every job on it.

## 5. The certified portfolio inventory (golden data)

`.archetype/portfolio/<repo>/scan.json` files are committed, derived scan outputs captured by the Orchestrator during the AOS-21 reality tests. The clones themselves live under `repositories/` and are gitignored; only the scan output is pinned. As of 2026-07-06 the inventory is:

| File | Repo | What it pins |
|---|---|---|
| `.archetype/portfolio/claude-agent-sdk-python/scan.json` | anthropics/claude-agent-sdk-python | Python SDK scan: dna, manifests, language mix incl. `language_mix_python_share_pct`, risk_flags |
| `.archetype/portfolio/example-voting-app/scan.json` | dockersamples/example-voting-app | Polyglot demo: deployment_files, docker_files, multi-manifest architecture |
| `.archetype/portfolio/gin/scan.json` | gin-gonic/gin | Go web framework scan: dna, manifests, language mix, risk_flags |
| `.archetype/portfolio/kubernetes/scan.json` | kubernetes/kubernetes | Scale test: 30,560 files on disk against the `MAX_FILES=20000` cap; `risk_signal_counts`, `scale`, `root_go_mod_found` |
| `.archetype/portfolio/pydantic-ai/scan.json` | pydantic/pydantic-ai | Python agent framework scan: dna, manifests, `language_mix_python_share_pct`, risk_flags |

### The reality-test regression gate

`scripts/reality_test_distillation.py` is the manual regression harness for the scan, distill, transfer sequence (AOS-DISTILL-003). It is NOT collected by pytest: it needs the cloned repos on disk under `settings.repository_root` (default `./repositories`). Run from the repo root:

```bash
cd /path/to/ArchetypeOS
PYTHONPATH=packages/aos_core python scripts/reality_test_distillation.py
# subset: PYTHONPATH=packages/aos_core python scripts/reality_test_distillation.py gin kubernetes
```

It registers each repo in a scratch sqlite DB, runs the real `run_scan`, distills with the deterministic provider (hermetic, no model call), then runs a fixed set of four `recommend_reuse` needs and prints rankings. The script prints; it does not assert. YOU are the assertion: compare output against the documented expected rankings (the acceptance thresholds, from the script docstring, verified as of 2026-07-06):

| Need (exact string in `NEEDS`) | Expected outcome |
|---|---|
| `container orchestration and scheduling` | `kubernetes` ranks #1 (was: no matches before the fix) |
| `HTTP routing and middleware for a web API` | `gin` ranks #1 (was: 3rd behind generic api/web noise) |
| (purpose check) | `pydantic-ai` purpose is the "Pydantic AI is a Python agent framework" sentence, not the FastAPI analogy that produced false `web` matches |

Any change to distillation, DNA, or transfer scoring that breaks these rankings is a regression, regardless of green unit tests. Opt-in real-provider mode (`--provider claude_code` or `AOS_REALITY_PROVIDER=claude_code`) invokes the local `claude` CLI and is Orchestrator-only quality checking, not the reproducible gate.

## 6. Test taxonomy and how to run each layer

Counts collected on 2026-07-06 at the in-review HEAD of `laptop/aos-selfheal-doc-loop` (AOS-SELFHEAL-001, not merged), with fastembed NOT installed locally, using `pytest --collect-only -q`:

| Layer | Location | Collected (2026-07-06) | Gate |
|---|---|---|---|
| API unit/integration | `apps/api/tests/` (28 test modules) | 206 tests | always runs; CI job "API tests and lint" |
| `pgvector` marked | inside `apps/api/tests/test_pgvector_store.py` | 2 tests (subset of the 206) | skips unless `AOS_TEST_DATABASE_URL` points at postgresql; CI job runs `-m pgvector` against `pgvector/pgvector:pg16` |
| `embedder` marked | `apps/api/tests/test_fastembed_real.py` (2 test functions) | 0 collected locally (module-level `importorskip("fastembed")` drops them when fastembed is absent) | CI "Embedder tests" job installs `apps/api/requirements-embeddings.txt` (fastembed, NO torch) and runs `-m embedder` |
| Worker | `apps/worker/tests/` | 7 tests | CI job "Worker tests and lint" |
| Web e2e | `apps/web/e2e/` (10 `.spec.ts` files) | Playwright suite | CI job "Web e2e (Playwright)" |
| Guardian rules | `apps/api/tests/test_guardian_evolution.py`, `test_guardian_scanner.py` | included in the 206 | the guardian is a repo-root tool; its tests live under `apps/api/tests/` because that is the only pytest tree CI runs |

The two markers are declared in the repo-root `pyproject.toml` `[tool.pytest.ini_options]`. Re-collect before trusting these counts (see section 13).

### Exact run commands (cwd: repo root)

Prerequisite once per environment: `pip install -r apps/api/requirements.txt && pip install -e ./packages/aos_core` (CI does exactly this). If `aos_core` is not pip-installed, append `:packages/aos_core` to each PYTHONPATH below.

```bash
# API suite (hermetic: conftest.py pins env vars before app import; Redis pinned to dead port 9999)
PYTHONPATH=apps/api pytest apps/api/tests

# pgvector-gated tests (need a live postgres with pgvector; CI uses pgvector/pgvector:pg16)
AOS_TEST_DATABASE_URL=postgresql+psycopg://archetypeos:archetypeos@localhost:5432/archetypeos_test \
  PYTHONPATH=apps/api pytest apps/api/tests -m pgvector

# embedder-gated tests (fastembed ONNX tier; torch must NOT be installed, CI asserts this)
pip install -r apps/api/requirements-embeddings.txt
PYTHONPATH=apps/api pytest apps/api/tests -m embedder

# Worker suite
PYTHONPATH=apps/worker pytest apps/worker/tests

# Web e2e (Node 22; Playwright boots the whole stack itself, see below)
cd apps/web
npm install
npx playwright install --with-deps chromium   # CI form; local containers set PW_LOCAL_CHROMIUM instead
npm run test:e2e
```

### How the e2e stack boots

`apps/web/playwright.config.ts` declares two webServer entries: `bash ./e2e/serve-api.sh` (health-checked at `http://localhost:8000/health`) and `npm run dev` (Vite on :5173). `apps/web/e2e/serve-api.sh` builds a throwaway stack per run: fresh scratch sqlite DB and artifact dir under a temp dir, `REPOSITORY_ROOT` pointed at the committed `apps/web/e2e/fixtures/` (so the scan flow's `local_path: 'demo-repo'` resolves), a copied throwaway knowledge vault (so ADR export does not dirty the real tree), an ephemeral in-memory Redis on port 9999, plus a worker process draining the queue. Config runs `workers: 1` (serial specs against shared state) with `retries: 1` in CI only.

The full local pre-PR gate (`scripts/pre_pr_guardian.sh`) chains: guardian (injecting temporary `Verification pending` metadata when no body file is given), compileall, both pytest suites, `npm run build`, and `docker compose config`.

## 7. Test-addition recipes

### API unit test (follow `apps/api/tests/conftest.py` conventions)

The `client` fixture builds a per-test sqlite engine under `tmp_path`, overrides `get_db`, and redirects `settings.repository_root` / `settings.artifact_root` into `tmp_path`. Import the app inside the fixture chain, never at module import time before conftest's env pins run.

```python
# apps/api/tests/test_myfeature.py
def test_myfeature_lists_empty(client):
    response = client.get("/myfeature")
    assert response.status_code == 200
    assert response.json() == []
```

When the test needs an on-disk repo, build it under `settings.repository_root` the way `test_scan_endpoint.py` does (its `build_repo` helper), and register it via the API with `local_path=<dirname>`.

### pgvector-marked test

Pattern from `apps/api/tests/test_pgvector_store.py`: mark the whole module and skip at test time unless the env var points at postgres.

```python
import os
import pytest

pytestmark = pytest.mark.pgvector
_DB_URL = os.environ.get("AOS_TEST_DATABASE_URL", "")

def _require_pg():
    if not _DB_URL.startswith("postgresql"):
        pytest.skip("AOS_TEST_DATABASE_URL not set to a postgresql database")
```

### embedder-marked test

Pattern from `apps/api/tests/test_fastembed_real.py`: module-level marker plus `importorskip`, so the module vanishes from collection when the tier is not installed.

```python
import pytest

pytestmark = pytest.mark.embedder
fastembed = pytest.importorskip("fastembed", reason="fastembed not installed (real embedder tier)")
```

Never add torch as a dependency to make an embedder test pass; the CI job hard-fails if torch is importable.

### Web e2e spec (LES-015 and LES-028 patterns)

- Scope every locator to the section that owns the element, or key off a section-unique `data-testid`. A page-global `getByRole('listitem').filter({ hasText: ... })` breaks with a strict-mode violation the moment a second surface renders the same entity (LES-028, PR #74 CI).
- Assert dynamic lists with retrying web-first matchers (`toBeVisible`, `toHaveCount`), never arithmetic on a one-shot `await locator.count()`, which races async refetches (LES-015).

```ts
// scope to the owning section (LES-028)
const decisionRow = page
  .locator('section')
  .filter({ has: page.getByRole('heading', { name: 'Decisions & Research' }) })
  .getByRole('listitem')
  .filter({ hasText: question });
await expect(decisionRow).toBeVisible();      // retries (LES-015)
await expect(excludedRow).toHaveCount(0);     // retries; proves the filter by absence
```

New surfaces should ship a section-unique `data-testid` (the AOS-COUNCIL-002 spec keyed off `data-testid="council-review-row"` and survived the LES-028 breakage untouched).

### Worker test

Add to `apps/worker/tests/test_worker.py` (or a sibling module); run with `PYTHONPATH=apps/worker pytest apps/worker/tests`. Note `apps/worker` ships its own `app` package (`app.worker`), so never mix API and worker PYTHONPATHs in one process.

### Guardian rule test

New guardian rules get tests in `apps/api/tests/test_guardian_evolution.py` or `test_guardian_scanner.py` style (they sys.path the repo root to import `tools/pr_guardian.py`). Remember the meta-rule: any diff touching `tools/pr_guardian.py` must also touch `knowledge/wiki/lessons/` (block `guardian-change-without-lesson`).

## 8. Fixture hygiene

| Rule | Source | Practice |
|---|---|---|
| No credential-shaped strings in fixtures or docs | LES-001 (Guardian `possible-secret` BLOCKs on PRs #33, #36 prep) | Use lexically un-secret-like markers. The house marker is `fake-env-marker-do-not-leak` (see `SCAN_MARKER` in `apps/api/tests/test_scan_endpoint.py` and `test_dna_endpoint.py`, written into a runtime `.env` as `API_KEY=<that marker>`; spelled indirectly here because the literal assignment form would itself match Guardian pattern 2). Fix the string, never the rule. |
| Count-agnostic assertions derived from the fixture/source files | LES-015 and LES-025 family (some spec comments also cite LES-012 for this; the committed LES-012 page is about ruff scope) | Derive expected counts from the data at test time, never hardcode. `apps/api/tests/test_knowledge.py` computes `N_LESSONS = len(_LESSONS)` and `OPEN_IDS`/`N_OPEN` by parsing the live `knowledge/wiki/lessons/index.md`. `knowledge.spec.ts` asserts a floor (`>= 12`) plus presence/absence, not exact counts. |
| Never pin a specific lesson as perpetually open | LES-025 (closing LES-007 broke `test_knowledge.py` and `knowledge.spec.ts` on PR #68 CI) | Assert against live `OPEN_IDS`; use closed lessons as stable anchors (LES-001, LES-007 are closed anchors in `knowledge.spec.ts`). Open status flips the moment a loop consumes the lesson; that is the point of the loop. |
| Committed scanner fixtures | `apps/api/tests/fixtures/` (`code-repo`, `compose-repo`) and `apps/web/e2e/fixtures/demo-repo` | Reuse these for scan/distill/architecture tests instead of inventing new trees; they are already secret-clean and manifest-diverse. |

## 9. The missing-core-tests rule

Any change to `packages/aos_core/` source requires a test change in the same change set, or Guardian blocks with `missing-core-tests`. Verified against `tools/pr_guardian.py`: `core_changed` is any path starting `packages/aos_core/`; the satisfying test globs are ONLY `packages/aos_core/tests/` or `apps/api/tests/`.

Consequences (LES-020, a real BLOCK on AOS-COUNCIL-PHASEC2B):

- A Playwright e2e that happens to exercise the core code does NOT satisfy the rule. `apps/web/e2e/` is not in the guardian's test globs, deliberately: an e2e is not a hermetic unit test of branch logic.
- Even a one-line infra tweak counts. The precedent fix extracted the decision logic into a testable predicate (`_is_file_sqlite`) and pinned its branches in `apps/api/tests/test_database_pragma.py`, in the same PR.
- Never override the rule to get green; add the test. Cite LES-020 if the block fires on an infra-only core change and you are tempted.

## 10. Acceptance-threshold discipline

A change that moves scoring, ranking, or detection must state its expected numbers BEFORE running, in the work package spec or PR body, then compare. This is the pattern the reality-test harness bakes in: the expected rankings (kubernetes #1, gin #1, the pydantic-ai purpose sentence) were written down as the gate before the fix ran, and the harness output is judged against them. "The numbers changed and the new ones look fine" is post-hoc rationalization, not evidence.

Checklist for any scoring/detection change:

1. State the expected outcome per golden input (which repo ranks #1 for which need, which signal fires on which fixture) before executing.
2. Run the relevant gate: unit tests, then `scripts/reality_test_distillation.py` for anything touching distillation or transfer.
3. Record the before/after numbers in the PR body under `## Acceptance Evidence` with `evidence:` pointers.
4. If actuals diverge from stated expectations, that is a finding to explain, not a threshold to silently update. Hypothesis and evidence-bar mechanics live in `aos-research-methodology`.

## 11. Task tier guide

Routing home is `aos-model-routing`; these labels are operator guidance and candidate status as of 2026-07-06.

| Task in this skill's scope | Tier |
|---|---|
| Run a suite and report pass/fail; re-collect test counts | Haiku |
| Fill in PR verification metadata from already-gathered evidence | Haiku |
| Add a unit test following an existing module's pattern (api, worker, marked tests) | Sonnet |
| Write a new e2e spec (section scoping, testid design, retry semantics) | Sonnet |
| Diagnose a flaky e2e or a marker-gate misconfiguration | Sonnet |
| Judge reality-test ranking regressions; set acceptance thresholds for a scoring change | Opus |
| Independent verification of a builder's package (the re-run, diff read, live probe) | Opus |

## 12. Common mistakes

- Formatting verification metadata as markdown bullets or bold. The guardian only parses plain `Field: value` lines; you get `missing-verification-metadata` even though the fields are visibly present.
- Claiming `Verified` on builder output you did not re-run. Builders never self-certify; re-run the commands yourself (section 4).
- Linting `apps/api/app` locally instead of `apps/api`. Alembic migrations under `apps/api/alembic/` slip through and fail CI (LES-012).
- Covering an `aos_core` change with an e2e and expecting the guardian to accept it. Only `packages/aos_core/tests/` or `apps/api/tests/` count (LES-020).
- Realistic-looking secrets in fixtures. The `possible-secret` regex correctly cannot prove a fake is fake; use `fake-...-do-not-leak` markers (LES-001).
- Hardcoding vault counts or pinning an open lesson ID in tests. Derive `OPEN_IDS` live; anchor on closed lessons (LES-025).
- One-shot `await locator.count()` arithmetic on a list that refetches. Use `toHaveCount` / `toBeVisible` (LES-015).
- Page-global locators over dynamic text. Scope to the owning section or a `data-testid` (LES-028).
- Treating a silent `-m embedder` run (0 collected) as a pass. Locally without fastembed the module is skipped at collection; the real gate is the CI "Embedder tests" job.
- Editing the reality-test expected rankings to match new output instead of explaining the divergence (section 10).
- Trying to pytest `scripts/reality_test_distillation.py`. It is a manual harness needing cloned repos on disk; pytest never collects it.

## 13. Provenance and maintenance

Authored 2026-07-06 against branch `laptop/aos-selfheal-doc-loop` (HEAD carries AOS-SELFHEAL-001, since merged as PR #80). AOS-EMBED-002 (PR #73) is merged to origin/main as of 2026-07-06. Derived from: `tools/pr_guardian.py`, `docs/PR_GUARDIAN.md`, `docs/VERIFICATION_PROTOCOL.md`, `docs/ORCHESTRATOR_PLAYBOOK.md`, `scripts/pre_pr_guardian.sh`, `scripts/reality_test_distillation.py`, `.github/workflows/ci.yml`, `pyproject.toml`, `apps/api/tests/` (conftest.py, test_scan_endpoint.py, test_pgvector_store.py, test_fastembed_real.py, test_knowledge.py, test_guardian_evolution.py, test_guardian_scanner.py, fixtures/), `apps/worker/tests/`, `apps/web/playwright.config.ts`, `apps/web/e2e/` (serve-api.sh, knowledge.spec.ts, decision-loop.spec.ts, fixtures/), `.archetype/portfolio/*/scan.json`, `knowledge/wiki/lessons/` (LES-001, LES-012, LES-015, LES-020, LES-025, LES-028, index.md).

Re-verification commands for facts that may drift (run from repo root):

| Fact | Re-verify with |
|---|---|
| Allowed statuses/levels and finding codes | `grep -n "ALLOWED_VERIFICATION\|missing-core-tests\|acceptance-evidence\|possible-secret" tools/pr_guardian.py` |
| API test count (206 as of 2026-07-06) | `PYTHONPATH=apps/api:packages/aos_core pytest apps/api/tests --collect-only -q \| tail -1` |
| Worker test count (7 as of 2026-07-06) | `PYTHONPATH=apps/worker:packages/aos_core pytest apps/worker/tests --collect-only -q \| tail -1` |
| pgvector marker count (2 as of 2026-07-06) | `PYTHONPATH=apps/api:packages/aos_core pytest apps/api/tests --collect-only -q -m pgvector \| tail -1` |
| Marker definitions | `sed -n '/tool.pytest.ini_options/,/]/p' pyproject.toml` |
| CI job commands and names | `grep -n "pytest\|npm\|name:" .github/workflows/ci.yml` |
| Portfolio inventory | `ls .archetype/portfolio/*/scan.json` |
| Reality-test expected rankings and NEEDS | `sed -n '1,70p' scripts/reality_test_distillation.py` |
| e2e spec count (10 as of 2026-07-06) | `ls apps/web/e2e/*.spec.ts \| wc -l` |
| Guardian test-glob rule for core changes | `grep -n "core_tests_changed" tools/pr_guardian.py` |
| Lesson statuses cited here | `grep -n "LES-001\|LES-012\|LES-015\|LES-020\|LES-025\|LES-028" knowledge/wiki/lessons/index.md` |
