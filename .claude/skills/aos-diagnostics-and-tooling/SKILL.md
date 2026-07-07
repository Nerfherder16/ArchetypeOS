---
name: aos-diagnostics-and-tooling
description: "Use when running the ArchetypeOS gate tools or interpreting their output and exit codes: a PR Guardian verdict (PASS, PASS_WITH_WARNINGS, BLOCK), doc_staleness verdicts (FRESH, ADVISORY, STALE), HARD vs SOFT drift (roadmap-phase-stale, state-docs-pr-lag), running pre_pr_guardian.sh, post_merge_validation.sh, or reality_test_distillation.py, ModuleNotFoundError No module named aos_core in pytest, or .archetype/reconciliation/PENDING.md appearing after a merge. (Deciding gate policy is aos-change-control; clearing findings with tests/evidence is aos-validation-and-qa.)"
---

# ArchetypeOS Diagnostics and Tooling

## 1. Overview

ArchetypeOS ships deterministic measurement tools so gate status is read from tool output, never eyeballed. This skill is the interpretation manual for each tool: exact invocation, flags (from the argparse in source), output anatomy, exit codes, and what to do with each verdict.

Jargon, defined once:

- **PR Guardian**: the deterministic (no LLM) pre-merge checker at `tools/pr_guardian.py`. It reads a git diff plus the PR body text and prints findings.
- **Finding**: one guardian result line, `[BLOCK|WARN] code: message`. Any BLOCK makes the verdict BLOCK and the exit code 1.
- **Override token**: a `PR_GUARDIAN_OVERRIDE_<KEY>` string in the PR body that suppresses a specific check. It exists in code, and the operating record is that no substantive code BLOCK (tests, secrets, verification metadata, acceptance evidence) has ever been overridden; tokens have appeared in merged PR bodies only as high-risk warn acknowledgments, prophylactic no-ops, and a few early suppressions (audited record: aos-change-control section 8). BLOCKs are fixed in code. Never suggest using one to bypass a gate.
- **Doc-staleness detector**: `tools/doc_staleness.py`, which mechanically cross-checks the state docs against git and reports HARD or SOFT drift.
- **Reality test**: `scripts/reality_test_distillation.py`, the manual portfolio harness that gates distillation and transfer quality by ranked retrieval.
- **State docs**: `docs/CURRENT_STATE.md`, `docs/RECENT_CHANGES.md`, `docs/ACTIVE_WORK.md`, plus `.archetype/roadmap.md`.

All commands below assume cwd = repo root. Several tools use repo-relative paths internally and misbehave from a subdirectory.

## 2. When to use / When NOT to use

Use this skill when you need to:

- Run or interpret PR Guardian, doc_staleness, the local gate scripts, or the reality-test harness.
- Decide whether a PASS_WITH_WARNINGS is acceptable, or what a HARD staleness signal demands.
- Get a one-screen gate status (`scripts/gate_summary.sh` in this skill directory).

Do NOT use this skill for:

- The change-classification policy, merge gate, and override incident history: see `aos-change-control`.
- Triage of runtime failures (API 500s, worker crashes, compose issues): see `aos-debugging-playbook`.
- The evidence bar, golden inventory, and test-addition recipes: see `aos-validation-and-qa`.
- Standing services up, endpoints, artifacts: see `aos-build-run-and-operate`.
- Writing the reconciliation content itself, lesson and RFC authoring: see `aos-docs-and-lessons`.
- Configuration axes the tools read (e.g. `repository_root`): see `aos-config-and-flags`.
- Which model tier runs which task, in general: see `aos-model-routing`.

## 3. tools/pr_guardian.py

### 3.1 Invocation and flags

```bash
cd /path/to/ArchetypeOS
python3 tools/pr_guardian.py --base origin/main --head HEAD --body-file /tmp/pr_body.md
```

| Flag | Required | Meaning |
|------|----------|---------|
| `--base` | yes | Base ref for the diff. Tries `base...head` (merge-base form) first, falls back to `base head` two-point diff. Pass a ref, not a range. |
| `--head` | yes | Head ref for the diff. |
| `--body-file` | no | Path to the PR body text. Missing or absent file = empty body, which trips the verification-metadata BLOCK. |
| `--scan-report` | no | Path to a scanner JSON report. If omitted, the guardian tries an in-repo `scan_repository` via `packages/aos_core` on `sys.path` (no install needed); any failure degrades to "Scanner-informed checks: unavailable" and those checks are skipped. |

CI runs the same script with the PR's base and head SHAs and the PR body written to `/tmp/pr_body.md` (`.github/workflows/ci.yml`, job step "Run PR Guardian").

Must run from the repo root: `check_required_files` tests repo-relative paths like `docs/ENGINEERING_CONSTITUTION.md` with `Path(file).exists()`, so a subdirectory cwd produces false `missing-required-file` BLOCKs.

### 3.2 Output anatomy and exit codes

```
Scanner-informed checks: consulted 3 risk signals.   <- or "unavailable"
# PR Guardian Report

Changed files: 14
- <one line per changed path>

Verdict: PASS | PASS_WITH_WARNINGS | BLOCK
- [BLOCK|WARN] <code>: <message>
```

`Changed files: 0` is a meaningful state, not an error: the `base...head` diff is empty, which happens when the branch has been fully merged into the base (HEAD is an ancestor of `origin/main`) or when head equals base. Confirm with `git merge-base --is-ancestor HEAD origin/main && echo merged` or `git diff --name-only origin/main...HEAD | wc -l`. In this state every diff-driven check (tests, docs, secrets, runtime-junk) trivially cannot fire, so the verdict reflects only the body-text checks (verification metadata, acceptance evidence); a PASS here says nothing about code quality on the branch.

| Exit code | Meaning |
|-----------|---------|
| 0 | PASS (no findings) or PASS_WITH_WARNINGS (warnings only) |
| 1 | BLOCK (at least one BLOCK finding) |
| 2 | argparse usage error (missing `--base`/`--head`) |

### 3.3 Finding catalog: BLOCK codes

Every BLOCK is a hard stop. The fix is always to change the code, tests, docs, or PR body; the override token column is listed for completeness only.

| Code | Trigger | Fix | Override key |
|------|---------|-----|--------------|
| `missing-required-file` | A foundation file (constitution, capability map, compose file, requirements, etc.) is absent from the working tree | Restore the file; also check your cwd is repo root | none |
| `possible-secret` | An added diff line matches AKIA keys, `api_key/secret/token/password = <20+ chars>`, or a PEM private key header | Remove the secret, rotate it | none |
| `runtime-junk` | Changed path contains `__pycache__`, `.pytest_cache`, `node_modules`, `.venv`, `dist/`, or ends `.pyc` | Delete from the change set, gitignore it | none |
| `missing-api-tests` | `apps/api/app/` changed, `apps/api/tests/` did not | Add or update API tests | TESTS |
| `missing-worker-tests` | `apps/worker/app/` changed, `apps/worker/tests/` did not | Add or update worker tests | TESTS |
| `missing-core-tests` | `packages/aos_core/` changed without `packages/aos_core/tests/` or `apps/api/tests/` changes | Add tests (API tests count for core) | TESTS |
| `missing-docs` | Code, `docker-compose.yml`, or `.github/workflows/` changed with no change under `docs/`, `README.md`, `CLAUDE.md`, or `.archetype/` | Update the relevant doc | DOCS |
| `capability-map-not-updated` | A new `docs/*.md` was added (outside the governance allowlist and `docs/rfc/`) without touching `docs/CAPABILITY_MAP.md` | Add a capability map entry | CAPABILITY_MAP |
| `missing-acceptance-evidence` | Code changed and the body has no `## Acceptance Evidence` heading | Add the section, one bullet per criterion | ACCEPTANCE |
| `empty-acceptance-evidence` | The section exists but no bullet under it contains `evidence:` (case-insensitive) | Give each criterion an `evidence:` pointer to a test, command, or CI job | ACCEPTANCE |
| `missing-verification-metadata` | Any of the six fields absent as plain `Field: value` lines (bold or bullet wrappers like `- **Field:** value` do not parse) | Add: Verification Status, Verification Level, Verification Method, Evidence, Limitations, Required Next Verifier | none |
| `invalid-verification-status` | Status not in: Verified, Verified with warnings, Verification pending, Verification unavailable, Verification blocked | Use an allowed status | none |
| `verification-not-mergeable` | Status is Verification unavailable or Verification blocked | Resolve verification first | none |
| `invalid-verification-level` | Level not `Level 0` through `Level 5` | Use an allowed level | none |
| `scanner-secret-path` | Scanner risk signal SECRET_LIKE_FILENAME on a path in the changed set | Remove the credential-looking file | SCANNER |
| `scanner-env-committed` | Scanner risk signal ENV_FILE_PRESENT on a changed path | Remove the `.env`, use `.env.example` | SCANNER |
| `guardian-change-without-lesson` | `tools/pr_guardian.py` changed without a `knowledge/wiki/lessons/` change (RFC-0004) | Add or update the citing lesson in the same change set | LESSON |
| `override-without-lesson-citation` | Body contains any `PR_GUARDIAN_OVERRIDE_` token but no `LES-<n>` ID | Cite the lesson (or better: drop the override and fix the finding) | none |
| `accepted-warning-expired` | An accepted-warnings entry's `review_by` date has passed | Re-decide: renew the registry entry or fix the underlying gap | none |

### 3.4 Finding catalog: WARN codes

| Code | Trigger | What it means |
|------|---------|----------------|
| `web-tests-not-enforced` | `apps/web/src/` changed without `apps/web/e2e/` changes | Web e2e coverage is advisory today; add or update Playwright specs |
| `high-risk-files` | Change touches `docker-compose.yml`, `.env.example`, `.github/workflows/`, or any path containing `auth` or `secret` | PR body should carry explicit risk notes |
| `verification-pending` | Verification Status is `Verification pending` | Legitimate mid-flight state; the PR must NOT merge until the Required Next Verifier records a stronger status |
| `weak-verification-metadata` | Method, Evidence, Limitations, or Required Next Verifier is empty, `n/a`, `none`, `tbd`, or `todo` | The field parsed but says nothing; write concrete detail |
| `scanner-missing-tests` | Scanner reports MISSING_TESTS while the PR adds app code (`.py .ts .tsx .js .jsx` under app prefixes) | Repo-level test gap intersects this PR |
| `scanner-new-ecosystem` | Scanner reports MULTIPLE_ECOSYSTEMS and the PR adds a package manifest (`package.json`, `go.mod`, `Cargo.toml`, ...) | Acknowledge the ecosystem expansion in the PR body |
| `doc-staleness:<signal>` | The doc-staleness detector returned a HARD finding | Advisory surface of section 4; never blocks, fails open if the detector errors; SOFT drift is dropped here |

### 3.5 Accepted warnings registry

`.archetype/guardian/accepted_warnings.json` (a JSON list, `[]` as of 2026-07-06). Each entry `{"code": ..., "review_by": "YYYY-MM-DD", "lesson": "LES-<n>", "rationale": ...}` downgrades matching WARN findings to an annotated WARN (`[accepted per LES-x until date: rationale]`) while `today <= review_by`. After `review_by` the same finding escalates to the BLOCK `accepted-warning-expired`. Entries with an unparseable date are ignored (the plain WARN stands). This only ever applies to `warn` findings; BLOCKs cannot be accepted away.

### 3.6 Acting on a BLOCK vs a warning

- **BLOCK**: stop, fix the cause in the change set, re-run. Do not reach for an override token, do not bypass PR Guardian, the manual merge gate, or the RFC process. If the check itself is wrong, that is a guardian rule change: it needs its own lesson (see `guardian-change-without-lesson`) and goes through `aos-change-control`.
- **WARN**: read it, decide, and leave evidence of the decision in the PR body. A warning you cannot answer in one sentence ("web e2e untouched because the change is API-only") is a smell.

**When is PASS_WITH_WARNINGS acceptable?**

| Warning present | Acceptable to proceed? |
|-----------------|------------------------|
| `verification-pending` on a local pre-PR run with the stub body | Yes: expected; final PR body must carry real evidence and a stronger status |
| `web-tests-not-enforced` on a backend-only PR that happens to touch a shared type under `apps/web/src/` | Yes, with a one-line rationale in the body |
| `high-risk-files` | Yes, only after writing explicit risk notes in the body |
| `weak-verification-metadata` | No: fix the field, it takes one minute |
| `doc-staleness:*` | Proceed with the PR, but the drift must be reconciled (section 4); it does not belong to this PR unless this PR caused it |
| Any warning you have not read | No |

## 4. tools/doc_staleness.py

### 4.1 Invocation and flags

```bash
cd /path/to/ArchetypeOS
python3 tools/doc_staleness.py                      # detect only, read-only
python3 tools/doc_staleness.py --hard-threshold 3   # default shown
python3 tools/doc_staleness.py --fix                # ALSO writes a reconciliation draft
```

| Flag | Default | Meaning |
|------|---------|---------|
| `--repo-root` | the repo containing the tool | Where to read state docs and run `git log` |
| `--hard-threshold` | 3 | PR-lag above this is HARD; at or below (and above 0) is SOFT |
| `--fix` | off | Write a deterministic reconciliation DRAFT to `.archetype/reconciliation/PENDING.md`. It never edits the state docs; the HARD finding stands until a human or LLM applies the draft (repo skill `skills/ci_devops/reconcile_state.md`, invoked as `/reconcile-state`) and updates the docs. Merged via PR #80 (AOS-SELFHEAL-001) |

### 4.2 The two signals

| Signal | Severity | Mechanics (verified in source) |
|--------|----------|--------------------------------|
| `roadmap-phase-stale` | always HARD when tripped | `.archetype/roadmap.md` "Current phase" label starts with an early token (`foundation`, `phase 0`, `documentation foundation`, `scaffold`), the phase text itself carries no completion marker, AND `docs/CURRENT_STATE.md` matches a completion marker (`v0.N complete`, `post-v0.N`, `sprint 1-9`, case-insensitive). This was LES-007: the one Phase-10 Alpha "NO by machine" |
| `state-docs-pr-lag` | SOFT or HARD | lag = (newest `Merge pull request #N` in the last 60 commits of `git log --oneline`) minus (highest `#N` referenced anywhere in `docs/CURRENT_STATE.md` or `docs/RECENT_CHANGES.md`). lag <= 0: no finding. 1 to 3: SOFT (the normal one-PR reconciliation window). Greater than 3: HARD |

### 4.3 Output anatomy and exit codes

```
# Doc-Staleness Report

Verdict: FRESH | ADVISORY | STALE
- [HARD|SOFT] <signal>: <message>
    evidence: <machine-checkable evidence line>
```

| Verdict | Findings | Exit code |
|---------|----------|-----------|
| FRESH | none | 0 |
| ADVISORY | SOFT only | 0 |
| STALE | at least one HARD | 1 |

With `--fix`, a `Wrote reconciliation draft: ...PENDING.md` (or `No reconciliation draft needed`) line prints before the report. The draft lists every merged PR beyond the newest one the state docs reference, with branch provenance.

**HARD vs SOFT interpretation:**

| Severity | Meaning | Action |
|----------|---------|--------|
| SOFT | Normal pipeline lag; the docs are within the reconciliation window | None required now; the next state-doc reconciliation covers it |
| HARD | The docs are lying about reality (wrong phase, or more than 3 PRs behind) | Reconcile before relying on the state docs for any decision; use the `--fix` draft as the checklist. Do not silence the signal by raising `--hard-threshold` |

The detector fails open by design: unreadable files and git errors degrade to empty input and produce no findings, never a crash and never a false alarm. Consequence: a FRESH verdict from a broken checkout proves nothing; confirm the state docs exist if FRESH looks suspicious.

## 5. scripts/reality_test_distillation.py

The regression gate for distillation and transfer quality (AOS-DISTILL-003). Manual: NOT collected by pytest, because it needs the cloned portfolio on disk under `settings.repository_root` (default `./repositories`, gitignored, so a fresh clone does not have it).

```bash
cd /path/to/ArchetypeOS
PYTHONPATH=packages/aos_core python3 scripts/reality_test_distillation.py            # all repos, deterministic
PYTHONPATH=packages/aos_core python3 scripts/reality_test_distillation.py gin kubernetes
PYTHONPATH=packages/aos_core python3 scripts/reality_test_distillation.py --provider claude_code   # opt-in live check
```

- Provider: `--provider <name>` or `AOS_REALITY_PROVIDER` env var (flag wins). `deterministic` (default, hermetic, no model call) or `claude_code` (LES-021-isolated live provider, Orchestrator-only). Anything else is a hard error.
- Per repo directory it registers a scratch Project + Repository in a throwaway sqlite DB under `mkdtemp` (idempotent per slug), runs the real `run_scan`, then `distill_repository`, then runs a FIXED list of 4 `recommend_reuse` needs and prints each repo's `DNA.purpose`, frameworks, and per-need rankings.
- Portfolio: the reality tests were run over a 6-repo portfolio. Five have goldens under `.archetype/portfolio/`: `claude-agent-sdk-python`, `example-voting-app`, `gin`, `kubernetes`, `pydantic-ai`; the sixth, `free-llm-api-resources`, was the original ingestion reality-test repo (LES-021, RFC-0008).
- Exit codes: 1 if no repo directories found, 0 otherwise. A single bad repo prints `! <name>: ingest failed (...)` and does not abort the run.

**The script prints; it does not assert.** The gate lives in its module docstring and you check it by reading the ranking output:

| Gate condition | Regression meaning if it fails |
|----------------|-------------------------------|
| `kubernetes` ranks #1 for "container orchestration and scheduling" | The deterministic purpose floor or the scorer regressed (pre-fix state: no matches, purpose was raw badge markdown) |
| `gin` ranks #1 for "HTTP routing and middleware for a web API" | Generic api/web noise is out-ranking real evidence again (pre-fix: gin was 3rd) |
| `pydantic-ai` purpose is the "Pydantic AI is a Python agent framework ..." sentence, not a FastAPI analogy | `_clean_summary` sentence selection regressed; expect false `web` matches downstream |

**What a reality-test failure means for a scoring change:** if you touched `recommend_reuse`, the scorer, or distillation and any gate row flips, the change damaged evidence quality or ranking, whatever the unit tests say. Do not tune constants until the gate happens to pass; find which layer (purpose text, frameworks, scorer) changed the ranking and fix that. Record a lesson if the defect was self-found (repo CLAUDE.md operating rule).

## 6. scripts/pre_pr_guardian.sh (local gate, in order)

```bash
bash scripts/pre_pr_guardian.sh [BASE_REF] [HEAD_REF] [BODY_FILE]   # defaults: origin/main HEAD <generated stub>
```

`set -euo pipefail`: the first failing step aborts the script, and the script's overall exit code is whatever that step returned. Consequence: a bare exit code is ambiguous without the transcript. Exit 2 is the step-0 base-ref failure ONLY when the transcript ends with `Base ref '<ref>' not found. Run: git fetch origin main`; pytest also exits 2 on interrupted collection or internal error, and that propagates unchanged from steps 4 or 5. Exit 1 can be a Guardian BLOCK (step 2) or a red test suite (steps 4 or 5). Always identify the failing step from the last lines of output, never from the number alone.

Preflight (read-only) to predict which steps will run before invoking the aborting, non-resumable script:

```bash
git rev-parse --verify origin/main >/dev/null 2>&1 && echo "base ok" || echo "step 0 will exit 2: git fetch origin main first"
command -v npm    >/dev/null && echo "step 6 (web build) will run"      || echo "step 6 will be skipped"
command -v docker >/dev/null && echo "step 7 (compose config) will run" || echo "step 7 will be skipped"
```

| Step | Command | Failure meaning |
|------|---------|-----------------|
| 0 | verify `BASE_REF` resolves, else exit 2 | Run `git fetch origin main` |
| 1 | write a stub body (Verification Status: Verification pending, Level 2) if no BODY_FILE given | n/a |
| 2 | `python tools/pr_guardian.py --base ... --head ... --body-file ...` | See section 3; expect PASS_WITH_WARNINGS (`verification-pending`) with the stub body |
| 3 | `python -m compileall apps/api/app apps/api/tests apps/worker/app apps/worker/tests` | Syntax error somewhere; the traceback names the file |
| 4 | `PYTHONPATH=apps/api pytest apps/api/tests` | API suite red |
| 5 | `PYTHONPATH=apps/worker pytest apps/worker/tests` | Worker suite red |
| 6 | `cd apps/web && npm run build` (skipped with a stderr note if npm absent) | Web build broken |
| 7 | `docker compose config >/dev/null` (skipped if docker absent) | Compose file invalid |

Note: steps 4 and 5 assume `aos_core` is importable (the editable install, `pip install -e packages/aos_core`, per `aos-build-run-and-operate`). Without it, collection dies with `ModuleNotFoundError: No module named 'aos_core'`; the workaround is `PYTHONPATH=apps/api:packages/aos_core` (what `gate_summary.sh` does).

Read-only sessions: there is no fully write-free path through the full script. Step 3 (compileall) writes bytecode caches, step 6 (npm build) writes `apps/web/dist/`, and the editable install mutates the environment. The write-free equivalent that covers the substantive gates is: step 2 via `python3 tools/pr_guardian.py ...` directly, step 7 via `docker compose config >/dev/null`, and steps 4 and 5 via these invocations, which need no install and write no artifacts:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=apps/api:packages/aos_core    pytest apps/api/tests    -p no:cacheprovider -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=apps/worker:packages/aos_core pytest apps/worker/tests -p no:cacheprovider -q
```

(`gate_summary.sh` in section 9 only COLLECTS tests; the two commands above actually run them. What the write-free path does not cover: compileall and the web build.)

## 7. scripts/post_merge_validation.sh

```bash
bash scripts/post_merge_validation.sh [TARGET_REF]   # default origin/main
```

Fetches `origin main` (best-effort), exits 2 if the target ref does not resolve, then runs: compileall (same four trees), API pytest, worker pytest, `npm install && npm run build` in `apps/web` (if npm), `docker compose config` (if docker), and prints the latest main CI run via `gh run list --branch main --workflow CI --limit 1` (if gh). Use it after a merge to confirm main is healthy from your machine.

## 8. Installed git hooks

Shipped with AOS-SELFHEAL-001 (merged as PR #80); opt-in per clone:

- `scripts/install-hooks.sh`: run once after cloning. Sets `git config core.hooksPath scripts/hooks` so hooks are versioned with the repo, and chmods them. Verify with `git config core.hooksPath` (expect `scripts/hooks`).
- `scripts/hooks/post-merge`: after any local merge or pull, runs `python3 tools/doc_staleness.py --fix` silently and, if `.archetype/reconciliation/PENDING.md` now exists, prints a notice telling you to apply it via `/reconcile-state` and then delete it. Non-blocking by contract: always exits 0, so it can never break a pull. It writes only the draft, never the state docs.

## 9. Helper: scripts/gate_summary.sh (this skill directory)

One-screen, strictly read-only status of all local gates. It runs PR Guardian against `origin/main..HEAD` with a stub body, the doc-staleness detector (never `--fix`), and pytest collection counts for both suites (`-p no:cacheprovider` and `PYTHONDONTWRITEBYTECODE=1` keep it write-free; `packages/aos_core` is put on `PYTHONPATH` so no install is needed).

```bash
cd /path/to/ArchetypeOS
bash .claude/skills/aos-diagnostics-and-tooling/scripts/gate_summary.sh [BASE_REF] [BODY_FILE]
```

Exit codes: 0 = no blocking gate tripped; 1 = guardian BLOCK and/or HARD staleness; 2 = base ref missing. One display caveat: doc_staleness SOFT messages contain a Unicode em-dash, which the script normalizes to a plain hyphen so quoted output stays paste-safe under house style.

Real output from this repo (branch `laptop/aos-selfheal-doc-loop`, 2026-07-06):

```
===============================================
 ArchetypeOS gate summary  (read-only)
 Range: origin/main..HEAD (96be86b)
===============================================

[1] PR Guardian   exit=0   Verdict: PASS_WITH_WARNINGS
    Changed files: 14
    - [WARN] verification-pending: Verification is pending. This PR must not merge until the required next verifier records a stronger status.

[2] Doc staleness  exit=0   Verdict: ADVISORY
    - [SOFT] state-docs-pr-lag: State docs lag git by 3 PR(s) (newest merged #79, docs at #76) - within the reconciliation window.

[3] Test collection
    api:    206 tests collected in 0.45s
    worker: 7 tests collected in 0.57s

OVERALL: OK (no blocking gate tripped; warnings above still need reading)
```

Reading it: `verification-pending` is the expected stub-body warning; the SOFT lag of exactly 3 sits at the threshold boundary (4 would be HARD); 206 api / 7 worker collected is the branch baseline as of 2026-07-06 (counts grow with every test-adding PR; a sudden DROP in the COLLECTED count or a collection error line is the signal to chase).

Known collect-vs-run offset (verified 2026-07-06): a full api run reports 204 passed + 3 skipped = 207 entries, one more than the 206 collected. This is expected, not drift. `apps/api/tests/test_fastembed_real.py` uses a module-level `pytest.importorskip("fastembed")`: when fastembed is absent, collect-only drops that module's 2 tests from the count entirely, while a real run surfaces the module skip as exactly 1 skipped entry. So with fastembed missing, run-report totals exceed the collected count by 1. The other 2 skips are the pgvector tests (collected, then self-skipped without `AOS_TEST_DATABASE_URL`), which count identically in both modes. The baseline-drop rule applies to the collected count only.

## 10. Task tier guide

Routing home is `aos-model-routing`; these labels are operator guidance, candidate status.

| Task in this skill's scope | Tier |
|----------------------------|------|
| Run gate_summary / any tool and report verdicts verbatim | Haiku |
| Classify a PASS_WITH_WARNINGS as acceptable or not using section 3.6 | Sonnet |
| Fix an ordinary BLOCK (add tests, docs, acceptance evidence, body fields) | Sonnet |
| Apply a doc-staleness reconciliation draft to the state docs | Sonnet |
| Interpret a reality-test ranking flip after a scoring change | Opus |
| Add or change a guardian check or staleness signal (lesson + change control required) | Opus |
| Decide an accepted-warnings registry entry (governance judgment) | Opus |

## 11. Common mistakes

- Running `tools/pr_guardian.py` from a subdirectory: false `missing-required-file` BLOCKs, because required-file checks use cwd-relative paths.
- Formatting verification fields as `- **Verification Status:** ...`: the parser needs plain `Field: value` at line start; bold/bullet wrappers do not parse (the BLOCK message says so too).
- Treating the local stub body's `verification-pending` WARN as final: the real PR body must carry actual evidence and a stronger status.
- Expecting `doc_staleness.py --fix` to update the docs: it only writes the DRAFT at `.archetype/reconciliation/PENDING.md`; the HARD finding stands until the state docs are reconciled and the draft deleted.
- Expecting `reality_test_distillation.py` to fail loudly: it exits 0 even when the ranking gate is broken; you must read the rankings against section 5's table.
- `ModuleNotFoundError: No module named 'aos_core'` during pytest collection: the editable install is missing; either `pip install -e packages/aos_core` or prepend `packages/aos_core` to `PYTHONPATH`.
- Raising `--hard-threshold` to make STALE go away: that games the alarm instead of reconciling; the threshold default of 3 is the deliberate one-PR-window tuning.
- Reaching for a `PR_GUARDIAN_OVERRIDE_*` token on a BLOCK: no substantive code BLOCK has ever been overridden (verified record: aos-change-control section 8, the home of this fact); fix the finding in the change set instead, and remember every override token requires a `LES-<n>` citation anyway.
- Adding an accepted-warnings entry without a valid ISO `review_by` date: the entry is silently ignored and the WARN stands; and after expiry it escalates to a BLOCK.
- Trusting a FRESH doc-staleness verdict from a broken checkout: the tool fails open (empty inputs produce no findings).

## 12. Provenance and maintenance

Authored 2026-07-06 against branch `laptop/aos-selfheal-doc-loop` (HEAD `96be86b`, which merges `origin/main` at PR #79 into the in-review AOS-SELFHEAL-001 work). Derived from: `tools/pr_guardian.py`, `tools/doc_staleness.py`, `scripts/reality_test_distillation.py`, `scripts/pre_pr_guardian.sh`, `scripts/post_merge_validation.sh`, `scripts/install-hooks.sh`, `scripts/hooks/post-merge`, `.github/workflows/ci.yml`, `.archetype/guardian/accepted_warnings.json`, `docs/PR_GUARDIAN.md`, `.archetype/work/AOS-DISTILL-003.md`, `skills/ci_devops/reconcile_state.md`.

Volatile facts and their re-verification commands:

| Fact (as of 2026-07-06) | Re-verify with |
|--------------------------|----------------|
| Guardian flags are exactly `--base --head --body-file --scan-report` | `python3 tools/pr_guardian.py --help` |
| Guardian BLOCK/WARN code list | `grep -n 'Finding(' -A 2 tools/pr_guardian.py` (most findings are multi-line constructions; a bare `Finding("` grep surfaces only 9 of the 29 severity/code pairs) |
| doc_staleness flags are `--repo-root --hard-threshold --fix` | `python3 tools/doc_staleness.py --help` |
| HARD PR-lag threshold is greater than 3 (`DEFAULT_HARD_THRESHOLD = 3`) | `grep -n DEFAULT_HARD_THRESHOLD tools/doc_staleness.py` |
| `--fix` draft path is `.archetype/reconciliation/PENDING.md` | `grep -n 'PENDING.md' tools/doc_staleness.py scripts/hooks/post-merge` |
| `--fix`, install-hooks.sh, post-merge hook merged via PR #80 | `git log origin/main --oneline -- scripts/install-hooks.sh; git show origin/main:tools/doc_staleness.py \| grep -c fix` (fetch origin first; a stale local ref shows them missing) |
| Accepted-warnings registry is empty (`[]`) | `cat .archetype/guardian/accepted_warnings.json` |
| Reality-test needs list and expected rankings | `sed -n '1,50p' scripts/reality_test_distillation.py; grep -n 'NEEDS =' -A6 scripts/reality_test_distillation.py` |
| Reality-test providers: deterministic (default), claude_code (opt-in) | `grep -n '_select_provider' -A12 scripts/reality_test_distillation.py` |
| pre_pr_guardian.sh step order | `cat scripts/pre_pr_guardian.sh` |
| CI guardian invocation and body file | `grep -n pr_guardian .github/workflows/ci.yml` |
| Collected test counts (206 api / 7 worker on this branch) | `PYTHONPATH=apps/api:packages/aos_core pytest apps/api/tests --collect-only -q -p no:cacheprovider \| tail -1` (same pattern for worker) |
| Portfolio goldens (5 dirs) | `ls .archetype/portfolio/` |
| Hooks installed locally | `git config core.hooksPath` |
| gate_summary.sh still runs clean | `bash .claude/skills/aos-diagnostics-and-tooling/scripts/gate_summary.sh; echo $?` |
