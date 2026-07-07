---
name: aos-debugging-playbook
description: Use when an ArchetypeOS (AOS) CI run is red or shows 0 jobs / 0 check-runs, gh pr checks is empty, ruff passes locally but fails CI (F401), GET /health returns 500 instead of degraded, tests flake on Redis or service-down state, Playwright fails with strict mode violation or a one-shot count race, a Council agent returns empty findings with confidence 0.05 or describes ArchetypeOS instead of the target repo, vault tests break after a lesson closes, or you are triaging a PR Guardian BLOCK or a doc-staleness WARN to the right fix path (running the detectors is aos-diagnostics-and-tooling; applying the doc reconciliation is aos-docs-and-lessons).
---

# AOS Debugging Playbook

## 1. Overview

Symptom-to-triage runbook for ArchetypeOS failure modes that have actually happened, each backed by a lesson in `knowledge/wiki/lessons/` (the lessons vault, per RFC-0004). Every row gives: the symptom as you will see it, the likely cause, a discriminating check (a cheap experiment that separates this cause from look-alikes), the fix recipe, and the lesson ID that tells the full story.

All commands run from the repo root (the directory containing `docs/`, `apps/`, `tools/`) unless stated otherwise. All `pytest` reproductions assume the standard environment: `pip install -r apps/api/requirements.txt` (or `apps/worker/requirements.txt`) plus `pip install -e ./packages/aos_core`; without the editable core install, every API test dies at collection with `ModuleNotFoundError: No module named 'aos_core'`. Tooling prerequisite for the YAML parse checks in this skill: PyYAML must be importable by the ambient `python3`. Both requirements files pin `PyYAML==6.0.2`, so the standard environment has it; on a bare interpreter, `pip install pyyaml` first, or the parse check fails with `ModuleNotFoundError: No module named 'yaml'`, which is a tooling gap, not a workflow parse failure. Environment setup lives in `aos-build-run-and-operate`. "Orchestrator" is the human-supervised lead session that verifies builder work; "Council" is the multi-agent review engine in `packages/aos_core/aos_core/services/council.py`; "Guardian" is the deterministic PR gate `tools/pr_guardian.py`.

House rule that shapes every fix here: when you resolve a CI failure, a Guardian BLOCK, a review remediation, or a self-found defect, record a lesson in `knowledge/wiki/lessons/` in the same change set (repo `CLAUDE.md`, RFC-0004).

## 2. When to use / When NOT to use

Use this skill when:

- A CI run is red, empty, or behaving strangely and you need to classify it fast.
- A test passes locally and fails in CI (or the reverse).
- Council output looks degraded, empty, or contaminated.
- You hit a Guardian BLOCK or a doc-staleness WARN and need the triage route.

Do NOT use this skill for:

- Guardian rule details, override policy, or how changes are classified: see `aos-change-control`.
- The full chronicle of all lessons and dead ends: see `aos-failure-archaeology`.
- Setting up the environment or running services from scratch: see `aos-build-run-and-operate`.
- Adding new tests or understanding the evidence bar: see `aos-validation-and-qa`.
- The LES-019 evidence-gathering campaign itself: see `aos-evidence-loop-campaign`.
- Writing the lesson after you fix something: see `aos-docs-and-lessons`.
- Measurement and inspection tooling: see `aos-diagnostics-and-tooling`.

## 3. First 5 minutes on any red CI run

Work this checklist in order before touching code. Steps 1 to 3 are read-only.

1. List runs for your branch and grab the run ID:

   ```bash
   gh run list --branch <your-branch> --limit 5
   ```

2. Check the PR check-run list:

   ```bash
   gh pr checks <pr-number>
   ```

   - Checks listed with one or more failures: normal red run, go to step 3.
   - ZERO check-runs listed, while `gh run list` shows a run that is `completed / failure`: stop. This is the workflow-parse signature (LES-027, row 1 below). Do not re-run, do not treat as flaky.

3. Open the failing run and read the actual job log, not just the summary:

   ```bash
   gh run view <run-id>
   gh run view <run-id> --log-failed
   ```

   A run with 0 jobs in `gh run view` confirms LES-027.

4. Identify which job failed and map it to the triage table below. The CI jobs as of 2026-07-06 (`.github/workflows/ci.yml`): `pr-guardian`, `api-tests` (API tests and lint), `worker-tests`, `vector-store-tests`, `embedder-tests`, `web-build`, `web-e2e` (Web e2e Playwright), `compose-smoke`.

5. Reproduce locally with the exact CI command for that job (each row below gives it). Never "fix" anything you have not reproduced or at least discriminated.

## 4. Master triage table

| # | Symptom | Likely cause | Discriminating check | Fix recipe | Lesson |
|---|---------|-------------|----------------------|------------|--------|
| 1 | CI run `completed / failure` with 0 jobs; PR shows 0 check-runs | Workflow YAML parse failure, typically an unquoted single-line `run:` scalar containing `: ` | Parse every changed workflow file, not just ci.yml (loop in section 5.1); needs PyYAML (section 1) | Rewrite the offending step as a block scalar (`run: \|`); remove or de-colon inline strings | LES-027 |
| 2 | ruff clean locally, CI `api-tests` fails with F401 or similar | Local ruff scope narrower than CI (CI lints all of `apps/api`, including `alembic/`) | Re-run with the exact CI scope: `ruff check apps/api` | Fix the lint finding; always lint at CI scope locally | LES-012 |
| 3 | `GET /health` returns HTTP 500 when Redis or Postgres is down | A dependency probe exception escaping the handler; contract is HTTP 200 with a degraded body | `PYTHONPATH=apps/api pytest apps/api/tests/test_health.py` | Guard each probe independently in `apps/api/app/main.py::health`; report partial failure in the body | LES-005 |
| 4 | `test_health_degraded_redis` (or any service-down test) passes in CI, fails on some machines, or vice versa | Test points at a default service port whose liveness varies by machine | `redis-cli -p 9999 ping` (should refuse); check `apps/api/tests/conftest.py` pins `redis://localhost:9999/0` | Pin service-down tests to a guaranteed-dead address (port 9999 convention), never a default port | LES-004 |
| 5 | Playwright count assertion fails intermittently after a filter click (`14 < 14` style) | One-shot `await locator.count()` raced an async refetch | Does the assertion use `toHaveCount` / `toBeVisible` (retrying) or bare `.count()` arithmetic (one-shot)? | Assert presence/absence of specific rows with retrying web-first matchers | LES-015 |
| 6 | Playwright "strict mode violation: resolved to 2 elements" after a new UI surface ships | Page-global locator over dynamic text; a second surface now renders the same entity | Grep the spec for page-global `getByRole(...).filter({ hasText })` with no section scope | Scope the locator to the owning section (heading filter or section-unique `data-testid`) | LES-028 |
| 7 | Council agent result: `findings: []`, `concerns: []`, `confidence: 0.05`, whole payload dumped into `summary` | Live model wrapped its JSON in a Markdown fence and the parse fell to the prose fallback | `PYTHONPATH=apps/api pytest apps/api/tests/test_council.py -k parse_agent_output` | The tolerant parser `_loads_tolerant` must recover it (fence strip, brace slice); if a new format appears, extend it plus a regression test | LES-018 |
| 8 | Council agent summary describes ArchetypeOS (FastAPI, apps/api, apps/web) while reviewing some other repo | Shelled provider absorbed ambient project context (cwd, CLAUDE.md, tool access) | `PYTHONPATH=apps/api pytest apps/api/tests/test_council.py -k claude_code_provider_mocked` | `ClaudeCodeProvider` must run in an empty temp cwd with `--disallowedTools` and `--strict-mcp-config`; restore isolation if any flag went missing | LES-021 |
| 9 | `test_knowledge.py` and `knowledge.spec.ts` break right after a lesson is closed | Tests pinned a specific lesson ID as perpetually open | Did the failing assertion hardcode a lesson ID plus status? | Derive the open set live (`OPEN_IDS` in `apps/api/tests/test_knowledge.py`); assert the open badge generically; use closed lessons as stable anchors | LES-025 |
| 10 | `pr-guardian` job fails, report says `Verdict: BLOCK` | A deterministic Guardian rule fired (this is the gate working, not a malfunction) | `bash scripts/pre_pr_guardian.sh` locally, or `python tools/pr_guardian.py --base origin/main --head HEAD --body-file <body.md>` | Fix the cause in code/docs, never bypass; see `aos-change-control` for rule-by-rule guidance; record a lesson | n/a |
| 11 | Guardian report carries a `doc-staleness:*` WARN, or `tools/doc_staleness.py` says `Verdict: STALE` | State docs lag merged reality by more than the HARD threshold (3 PRs) | `python3 tools/doc_staleness.py` (exit 1 only on HARD; SOFT lag within 3 PRs is normal) | Reconcile `docs/CURRENT_STATE.md` / `docs/RECENT_CHANGES.md` with the merged PRs (updating `docs/ACTIVE_WORK.md` is good hygiene, but it is not an input to the detector); see `aos-docs-and-lessons` | LES-007 (closed), AOS-20 |
| 12 | Council verdict "Insufficient evidence" with named missing evidence classes | Constitutional abstention: evidence below `MIN_EVIDENCE` (1) or aggregate confidence below `ABSTAIN_CONFIDENCE` (0.35) | Read the review JSON: are the per-agent parses healthy (rule out row 7 first)? | Not a bug. Do NOT lower thresholds. Supply the named evidence class; see `aos-evidence-loop-campaign` (LES-019, open as of 2026-07-06) | LES-019 |

## 5. Failure modes in detail

### 5.1 CI run with 0 jobs / 0 check-runs (LES-027)

Story: AOS-EMBED-002 (PR #73) added an "Embedder tests" job with a single-line step, `run: python -c "... print('ok: no torch')"`. The `: ` inside the unquoted YAML scalar parsed as a mapping-value indicator; GitHub could not build the job graph, so the run failed with zero jobs and the PR showed zero check-runs. Every local gate (ruff, compileall, `docker compose config`, pytest) passed, because none of them parses workflow YAML.

Discriminating check (also the local reproduction). Parse EVERY workflow file the PR added or edited, not just `ci.yml`; the failing file is whichever one the PR touched. As of 2026-07-06 the repo has exactly one workflow (`ci.yml`), so the loop and the single-file form are equivalent today, but the loop stays correct when more workflows appear:

```bash
for f in .github/workflows/*.yml; do
  python3 -c "import yaml, sys; yaml.safe_load(open(sys.argv[1])); print(sys.argv[1], 'parses ok')" "$f"
done
```

A `yaml.scanner.ScannerError: mapping values are not allowed here` reproduces the failure exactly. (Prerequisite: PyYAML importable, see section 1.)

Fix recipe:

1. Rewrite the offending step as a block scalar. The fixed form now in `ci.yml` (embedder-tests job, "Assert no torch" step) is the template: `run: |` with the command on the next indented line, and the message de-coloned to `ok - no torch`.
2. Targeted sweep first, for the actually dangerous case (a `: ` inside an unquoted single-line `run:` value): `grep -nE 'run: [^|>].*: ' .github/workflows/*.yml`. On a healthy `ci.yml` this returns zero hits (verified 2026-07-06); any hit is a candidate to fix or explicitly clear (a value quoted at the YAML level, `run: "..."`, can be safe even with a hit). The broad sweep `grep -n 'run: [^|>]' .github/workflows/*.yml` lists every single-line `run:` (about 22 on a healthy `ci.yml`, all benign) and is only worth eyeballing when the targeted pattern found something or the parse check failed.
3. Re-run the parse check over all workflow files. As of 2026-07-06 a clean `ci.yml` parse yields 9 jobs on live main (8 on a checkout that predates PR #81's `ci-green` fan-in). Do not treat a differing count as an alarm by itself; trust the jobs-list one-liner in section 8 over any remembered number, and check your checkout's vintage first.
4. Standing rule: any change set that touches `.github/workflows/*.yml` gets the parse check as part of verification, because no other gate covers it.

Sibling trap from the same lesson: a literal `|` inside a markdown table cell in `knowledge/wiki/lessons/index.md` shifts the columns and breaks `test_parse_lessons_index`. When editing structured text, escape or avoid that format's delimiter and re-run the consuming parser before pushing.

### 5.2 Lint passes locally, fails CI (LES-012)

Story: PR #51 shipped an alembic migration carrying an unused `import sqlalchemy as sa`. CI's "API tests and lint" job runs `ruff check apps/api` (the whole tree, including `apps/api/alembic/`) and failed with F401. The local pre-push run had used `ruff check apps/api/app`, which never sees the migrations, and reported false-green.

Exact CI lint scopes, quoted from `.github/workflows/ci.yml` as of 2026-07-06:

- api-tests job: `ruff check apps/api` (ruff pinned to `0.8.6`)
- worker-tests job: `ruff check apps/worker`
- `packages/aos_core` and `tools/` are NOT ruff-checked by CI as of 2026-07-06

Fix recipe and local reproduction (matches CI, plus the broader Orchestrator playbook scope):

```bash
pip install ruff==0.8.6
ruff check apps/api
ruff check apps/worker
python3 -m ruff check apps/api apps/worker tools   # docs/ORCHESTRATOR_PLAYBOOK.md step 4 scope
```

Never narrow the scope to make it pass. Alembic-autogenerated migrations often ship a default `import sqlalchemy as sa` that becomes unused when the migration only uses project TypeDecorators; delete the import.

### 5.3 GET /health returns 500 instead of degraded 200 (LES-005)

Story: the Alpha Review live run found that with Redis absent, `/health` crashed with a propagated `redis.ConnectionError`, exactly the condition a health endpoint exists to report. Fixed in PR #39.

Contract (source: `apps/api/app/main.py::health`, as of 2026-07-06): always HTTP 200, each probe guarded independently. Expected degraded payload shape:

```json
{"status": "degraded", "api": true, "database": true, "redis": false}
```

`status` is `"ok"` only when both `database` and `redis` are true; otherwise `"degraded"`. The keys are exactly `status`, `api`, `database`, `redis`.

Local reproduction and verification:

```bash
PYTHONPATH=apps/api pytest apps/api/tests/test_health.py
# or against a live API with Redis stopped:
curl -s http://localhost:8000/health
```

Fix recipe: keep every dependency probe inside its own try/except; report partial failure in the body; never let a probe exception convert "degraded" into "down".

### 5.4 Flaky service-down tests (LES-004)

Story: `test_health_degraded_redis` originally relied on `redis://localhost:6379/0` being refused. True in CI, false on any machine running a real local Redis. Caught in the PR #39 Orchestrator review.

Convention: a test asserting a service is DOWN must point at a guaranteed-dead address. `apps/api/tests/conftest.py` pins `REDIS_URL=redis://localhost:9999/0` (line 16 as of 2026-07-06).

Discriminating check when the degraded test fails locally:

```bash
redis-cli -p 9999 ping   # must fail / refuse for the unit test to pass
```

Known local trap: the Playwright e2e harness (`apps/web/e2e/serve-api.sh`) deliberately starts an ephemeral REAL Redis on port 9999 and reuses one that is already bound. If an e2e stack (or its leftover Redis) is alive while you run the API unit suite, `test_health_degraded_redis` will fail because 9999 is no longer dead. Kill the leftover Redis, then re-run:

```bash
PYTHONPATH=apps/api pytest apps/api/tests/test_health.py::test_health_degraded_redis
```

### 5.5 Playwright one-shot count race (LES-015)

Story: in AOS-21, an Open-filter assertion read `const openCount = await knowledge.getByRole('listitem').count()` immediately after clicking the filter, then asserted `openCount < allCount`. It failed (`14 < 14`) because the click triggers an async refetch and a one-shot `.count()` reads the still-unfiltered list.

Rule: `toHaveCount` and `toBeVisible` are web-first and auto-retry; a bare `await .count()` does not. For any filtered or refetched list, prove the filter by presence/absence of specific rows: the expected row stays `toBeVisible()`, a known excluded row goes `toHaveCount(0)`. Reserve `.count()` for values stable at read time. Never patch with `waitForTimeout`.

Local reproduction (cwd `apps/web`; the config boots the API via `e2e/serve-api.sh`):

```bash
cd apps/web && npm run test:e2e            # full suite
cd apps/web && npx playwright test e2e/knowledge.spec.ts
```

### 5.6 Playwright strict-mode violation from a new surface (LES-028)

Story: PR #74 added the "Agent Council" Control Tower section, which renders the same council reviews the Decision Loop lists. `decision-loop.spec.ts` located its row with a page-global `getByRole('listitem').filter({ hasText: question })`, which silently depended on that text being unique on the page. The new surface made it match 2 elements: strict-mode violation, red `web-e2e` job.

Fix recipe: scope the locator to the section that owns the element. The repaired pattern in `apps/web/e2e/decision-loop.spec.ts`:

```ts
page.locator('section')
  .filter({ has: page.getByRole('heading', { name: 'Decisions & Research' }) })
  .getByRole('listitem')
  .filter({ hasText: question });
```

For NEW surfaces, key off a section-unique `data-testid` from day one (the AOS-COUNCIL-002 spec used `data-testid="council-review-row"` and was unaffected). Do not dodge strict mode with `.first()`; that hides the ambiguity instead of removing it.

Local reproduction: `cd apps/web && npx playwright test e2e/decision-loop.spec.ts`

### 5.7 Council agent: empty findings, confidence 0.05 (LES-018)

Story: on the first real Council run (pydantic-ai review), 3 of 4 agents returned their JSON wrapped in a ```` ```json ```` Markdown fence. The parser called `json.loads` directly, so fenced payloads fell into the prose fallback: `confidence=0.05`, `findings=[]`, `concerns=[]`, and the fenced block dumped verbatim into `summary`. Synthesis ran on empty inputs. The hermetic `DeterministicProvider` never emits fences, so deterministic tests could not catch it.

Where it lives: `_loads_tolerant` and `_parse_agent_output` in `packages/aos_core/aos_core/services/council.py`. Recovery layers: (1) parse as-is, (2) strip a leading/trailing code fence, (3) slice first `{` to last `}`. The prose fallback returns `status="Needs Evidence"` with confidence 0.05, so that exact signature (0.05 plus empty lists plus raw text in summary) means "the parser gave up", not "the model found nothing".

Discriminating check and local reproduction:

```bash
PYTHONPATH=apps/api pytest apps/api/tests/test_council.py -k parse_agent_output
```

(Covers bare / fenced / prose-then-object / true-prose-fallback.) If a live run still shows the 0.05 signature, capture the raw provider text from the review artifact and feed it to `_loads_tolerant` in a REPL; if no layer recovers it, add a new recovery layer plus a regression test in the same change set.

### 5.8 Council describes ArchetypeOS instead of the target repo (LES-021)

Story: reviewing `cheahjs/free-llm-api-resources`, the `technology_fitness_judge`'s evidence array held only the target's fingerprint, yet its summary described ArchetypeOS itself (FastAPI 0.115, apps/api, apps/worker) and complained the scan "missed the JS/TS web app". Root cause: `claude -p` ran in ArchetypeOS's cwd, picked up `CLAUDE.md`, and had filesystem access, so the agent reasoned about the host repo.

Fix as shipped (`ClaudeCodeProvider` in `packages/aos_core/aos_core/llm/__init__.py`): the subprocess runs in a fresh empty temp directory (`tempfile.TemporaryDirectory(prefix="aos-llm-")`), with `--disallowedTools` denying all state-reading/acting tools (`_ISOLATED_DISALLOWED_TOOLS`) and `--strict-mcp-config` ignoring ambient MCP. Output must be a pure function of system + prompt.

Discriminating check (pins isolated cwd, tool-deny, strict-MCP argv):

```bash
PYTHONPATH=apps/api pytest apps/api/tests/test_council.py -k claude_code_provider_mocked
```

If contamination recurs, diff `_build_argv` and the `subprocess.run(..., cwd=isolated_cwd)` call against LES-021's loop-feed paragraph; some flag or the cwd isolation regressed.

### 5.9 Vault tests break when a lesson closes (LES-025)

Story: AOS-20 closed LES-007 (a correct consumption record) and two suites went red in PR #68, because both had hardcoded LES-007 as the canonical open lesson. A lesson's status flips the moment a loop consumes it; that is the point of the learning loop.

Rule: tests over the lessons vault derive the open set live. `apps/api/tests/test_knowledge.py` parses `OPEN_IDS` from the live index and asserts against that set; `apps/web/e2e/knowledge.spec.ts` asserts the `(lesson · open)` badge generically and uses only CLOSED lessons as stable text anchors.

Local reproduction:

```bash
PYTHONPATH=apps/api pytest apps/api/tests/test_knowledge.py
cd apps/web && npx playwright test e2e/knowledge.spec.ts
```

If these fail right after you closed a lesson, the fix is in the test (derive live), never "keep the lesson open to keep tests green".

### 5.10 Guardian BLOCK (route to aos-change-control)

`Verdict: BLOCK` from `tools/pr_guardian.py` is deterministic and rule-based (verdicts: PASS, PASS_WITH_WARNINGS, BLOCK). Triage here is only: reproduce locally, read which rule fired, fix the cause.

```bash
# fast, Guardian only:
python tools/pr_guardian.py --base origin/main --head HEAD --body-file <body.md>
# full local gate (Guardian + compileall + both pytest suites + web build + compose config):
bash scripts/pre_pr_guardian.sh
```

Non-negotiables: never bypass Guardian, the head-SHA-pinned manual merge gate, or the RFC process. Override tokens exist, but no substantive code BLOCK (tests, secrets, verification metadata, acceptance evidence) has ever been overridden; the exact verified record lives in `aos-change-control` section 8. BLOCKs are fixed in code. Every BLOCK gets a lesson in the same change set (RFC-0004). Rule-by-rule details: `aos-change-control`.

### 5.11 Doc-staleness WARN / STALE (AOS-20)

`tools/doc_staleness.py` reads exactly three inputs (`.archetype/roadmap.md`, `docs/CURRENT_STATE.md`, `docs/RECENT_CHANGES.md`; it never reads `docs/ACTIVE_WORK.md`) and compares them against git reality. Severities: HARD vs SOFT. Lag within `DEFAULT_HARD_THRESHOLD = 3` merged PRs is SOFT (normal one-PR reconciliation lag); beyond it is HARD. Guardian's `check_doc_staleness` surfaces HARD findings as non-blocking WARNs only, drops SOFT, and fails open; it can never BLOCK a PR.

```bash
python3 tools/doc_staleness.py    # Verdict: FRESH / ADVISORY / STALE; exit 1 only on HARD
```

Fix recipe: actually reconcile the state docs with the merged PRs. Never edit docs cosmetically to silence the signal. Merged via PR #80 (AOS-SELFHEAL-001): `python3 tools/doc_staleness.py --fix` writes a deterministic reconciliation DRAFT to `.archetype/reconciliation/PENDING.md` (it never edits the state docs), applied via the `/reconcile-state` skill (`skills/ci_devops/reconcile_state.md`); the HARD finding stands until docs are truly reconciled. Full loop: `aos-docs-and-lessons`.

### 5.12 Council abstains with named missing evidence classes (LES-019, open)

"Insufficient evidence" with the review naming what evidence class is missing is the Constitution working, not a defect. Thresholds (`packages/aos_core/aos_core/services/council.py`): `MIN_EVIDENCE = 1`, `ABSTAIN_CONFIDENCE = 0.35`. Triage order: first rule out row 7 (a parser fallback drags aggregate confidence down artificially); if the per-agent parses are healthy, the abstention is legitimate. Never lower the thresholds to force a verdict. The gap (nothing yet gathers the named evidence and re-runs) is the live campaign in `aos-evidence-loop-campaign`. LES-019 is open as of 2026-07-06.

## 6. Task tier guide

Routing home and guardrails: `aos-model-routing`. Tier labels are operator guidance, candidate status, as of 2026-07-06.

| Task in this skill's scope | Tier |
|---|---|
| Run the first-5-minutes checklist, fetch logs, run a discriminating check verbatim | Haiku |
| Run the YAML parse check / ruff at CI scope / a single pytest repro | Haiku |
| Apply a table-row fix recipe (block scalar, scope a locator, derive OPEN_IDS, drop an unused import) | Sonnet |
| Write the accompanying lesson for a fixed failure | Sonnet |
| A symptom not in this table, or one whose discriminating check contradicts its row | Opus |
| Cross-layer root-causing (provider + parser + synthesis, e.g. LES-018/019/021 interplay) | Opus |
| Any change to Guardian rules, abstention thresholds, or the CI job graph | Opus, plus `aos-change-control` |

## 7. Common mistakes

- Re-running a 0-jobs CI run hoping it was flaky. It is a parse failure; re-runs produce the same nothing (LES-027).
- Narrowing the local ruff scope until it passes instead of matching CI's scope (LES-012).
- "Fixing" degraded health by returning 503/500. The contract is HTTP 200 with a degraded body; a 500 is the bug (LES-005).
- Asserting a service is down via a default port (6379, 5432) that happens to be dead on your machine (LES-004).
- Patching an e2e race with `waitForTimeout` or sleeps instead of retrying web-first matchers (LES-015).
- Silencing a strict-mode violation with `.first()` instead of scoping the locator to its owning section (LES-028).
- Reading Council confidence 0.05 plus empty findings as "the model found nothing" instead of "the parser gave up" (LES-018).
- Trusting Council content without checking provider isolation when summaries mention ArchetypeOS internals on a foreign target (LES-021).
- Keeping a lesson open, or reopening one, to keep tests green (LES-025). Fix the test to derive the open set live.
- Lowering `ABSTAIN_CONFIDENCE` or `MIN_EVIDENCE` to convert an abstention into a verdict (LES-019). Supply evidence instead.
- Using a Guardian override token as a triage shortcut. Substantive BLOCKs are never overridden (verified record in `aos-change-control` section 8); fix the cause in code and record a lesson.
- Fixing a failure without recording the lesson in the same change set (repo CLAUDE.md, RFC-0004).
- Local edits without checking whether a leftover e2e Redis on port 9999 is poisoning the "dead port" assumption (section 5.4).

## 8. Provenance and maintenance

Authored 2026-07-06 on branch `laptop/aos-selfheal-doc-loop` (HEAD = AOS-SELFHEAL-001, since merged as PR #80). AOS-EMBED-002 (PR #73) is merged to origin/main.

Derived from:

- `knowledge/wiki/lessons/LES-004.md`, `LES-005.md`, `LES-012.md`, `LES-015.md`, `LES-018.md`, `LES-019.md`, `LES-021.md`, `LES-025.md`, `LES-027.md`, `LES-028.md`, `index.md`
- `.github/workflows/ci.yml`
- `apps/api/app/main.py` (health route), `apps/api/tests/test_health.py`, `apps/api/tests/conftest.py`, `apps/api/tests/test_knowledge.py`, `apps/api/tests/test_council.py`
- `packages/aos_core/aos_core/services/council.py`, `packages/aos_core/aos_core/llm/__init__.py`
- `apps/web/e2e/decision-loop.spec.ts`, `apps/web/e2e/knowledge.spec.ts`, `apps/web/e2e/serve-api.sh`
- `tools/doc_staleness.py`, `tools/pr_guardian.py`, `scripts/pre_pr_guardian.sh`, `docs/ORCHESTRATOR_PLAYBOOK.md`

Re-verification commands for facts that may drift (run from repo root):

| Fact | Re-verify with |
|---|---|
| CI job list and count (9 jobs on live main; 8 before PR #81 added ci-green) | `python3 -c "import yaml; print(list(yaml.safe_load(open('.github/workflows/ci.yml'))['jobs']))"` |
| CI ruff scopes and pinned version | `grep -n "ruff" .github/workflows/ci.yml` |
| Health payload keys and 200-always contract | `sed -n '28,44p' apps/api/app/main.py` |
| Dead-port pin 9999 in unit conftest | `grep -n 9999 apps/api/tests/conftest.py` |
| e2e harness starts a real Redis on 9999 | `grep -n 9999 apps/web/e2e/serve-api.sh` |
| Tolerant parser and fallback confidence 0.05 | `grep -n "_loads_tolerant\|0.05" packages/aos_core/aos_core/services/council.py` |
| Abstention thresholds (0.35 / 1) | `grep -n "ABSTAIN_CONFIDENCE\|MIN_EVIDENCE" packages/aos_core/aos_core/services/council.py` |
| Provider isolation (temp cwd, disallowedTools, strict-mcp-config) | `grep -n "aos-llm-\|disallowedTools\|strict-mcp-config" packages/aos_core/aos_core/llm/__init__.py` |
| OPEN_IDS live derivation | `grep -n OPEN_IDS apps/api/tests/test_knowledge.py` |
| Scoped decision-row locator | `sed -n '20,30p' apps/web/e2e/decision-loop.spec.ts` |
| Guardian verdict strings | `grep -n "Verdict" tools/pr_guardian.py` |
| Doc-staleness HARD threshold (3) and verdicts | `grep -n "DEFAULT_HARD_THRESHOLD\|Verdict" tools/doc_staleness.py` |
| `--fix` merged to main yet? (was merged, PR #80) | `git show origin/main:tools/doc_staleness.py \| grep -c '\-\-fix'` (0 means your local origin/main ref is stale; fetch first) |
| Which lessons are open right now | `grep -n "\bopen\b" knowledge/wiki/lessons/index.md` |
