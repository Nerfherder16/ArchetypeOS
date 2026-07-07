---
name: aos-model-routing
description: Use when deciding which model tier (Haiku, Sonnet, Opus) should run an ArchetypeOS task, when spawning or delegating a session for a work package, gate run, doc reconciliation, RFC, or campaign phase, when a cheaper session hits a PR Guardian BLOCK, an unexpected gate outcome, or a governance file, when a task has failed 3 times in a row, or when a sibling AOS skill's Task tier guide needs its routing home.
---

# ArchetypeOS Model Routing

## 1. Overview

This skill is the routing home for ArchetypeOS: it maps task classes to Haiku, Sonnet, or Opus class sessions, defines the guardrails a cheaper model must obey, and defines the escalation protocol. Every sibling AOS skill carries a "Task tier guide" section; those tables are scoped excerpts of this policy, and this file is where the policy itself lives.

Honest framing, recorded from the operator on 2026-07-06:

- Current practice is mainly Opus and Sonnet sessions. Haiku is to be introduced for the tasks it handles best, starting with the HAIKU-CANDIDATE class below.
- Every tier assignment in this skill and in every sibling skill is operator guidance with candidate status. None has been validated by measured experiments in this repo. Treat rows as defaults to try, not as proven capability claims.
- No benchmark numbers about model capabilities appear here because none exist for these tasks. When a routing choice is validated or falsified in practice, record it (a lesson per RFC-0004 in `knowledge/wiki/lessons/`, or a note in this file) and update the row.

Terms used throughout:

- PR Guardian: the deterministic gate `tools/pr_guardian.py`, verdicts PASS, PASS_WITH_WARNINGS, BLOCK.
- Local gate: `scripts/pre_pr_guardian.sh`, which runs Guardian plus compileall, both pytest suites, the web build, and a compose config check.
- Manual Merge Gate: the head-SHA-pinned verification comment protocol (see `aos-change-control`); required because branch protection cannot enforce status checks on this repo's plan.
- Governance files: `tools/pr_guardian.py`, `docs/ENGINEERING_CONSTITUTION.md`, `docs/RFC_PROCESS.md`, `docs/rfc/`, `.github/workflows/ci.yml`, `scripts/pre_pr_guardian.sh`, `.archetype/guardian/accepted_warnings.json`, `CLAUDE.md`.

## 2. When to use / When NOT to use

Use this skill when:

- Choosing which model tier to spawn or delegate for a concrete ArchetypeOS task.
- A cheaper session must decide whether it is allowed to proceed or must hand up.
- Writing or revising the Task tier guide section of any sibling skill.
- Auditing whether a past misfire was a routing error (wrong tier for the task).

Do NOT use this skill for:

- The mechanics of gates, overrides, and merges: see `aos-change-control`.
- What evidence a PR needs: see `aos-validation-and-qa`.
- Diagnosing why a task is failing (as opposed to who should retry it): see `aos-debugging-playbook`.
- The content of any domain task; this skill routes work, the sibling skills define it.

## 3. Routing principles

1. Route by verifiability, not by perceived difficulty. A task is cheap-safe when a deterministic gate or a fixed checklist verifies the output, so a wrong answer is caught mechanically.
2. The gate does the judging, the model does the typing. Haiku candidates are exactly the tasks where correctness is decided by Guardian, pytest, ruff, or a diff, not by the model's own judgment.
3. Judgment about governance is never delegated down. Anything that changes what the gates enforce is Opus class with human involvement, per the RFC process (`docs/RFC_PROCESS.md`).
4. Escalation is cheap, silent failure is not. A cheaper model that hands up early costs one context switch; one that pushes through an unexpected gate outcome can cost a bad merge.

## 4. HAIKU-CANDIDATE tasks

Mechanical, checklist-driven, output verifiable by a gate or a diff. All rows are candidate status as of 2026-07-06: Haiku is not yet in routine use here.

| Task | Exact command (cwd: repo root) | Why Haiku can hold it | Verification |
|---|---|---|---|
| Run the local gate and report the verdict verbatim | `bash scripts/pre_pr_guardian.sh origin/main HEAD` | Zero judgment: run, copy the `Verdict:` line and any BLOCK codes | The script's own exit code and output |
| Run the doc-staleness detector and report | `python tools/doc_staleness.py` | Deterministic tool, verdicts FRESH / ADVISORY / STALE, exit nonzero only on HARD findings | Tool output |
| Regenerate the deterministic reconciliation draft | `python tools/doc_staleness.py --fix` (writes `.archetype/reconciliation/PENDING.md`, never edits state docs; AOS-SELFHEAL-001, merged as PR #80) | The draft is machine-generated from `git log`; the model only runs and reports | Re-run shows "No reconciliation draft needed" once docs are reconciled |
| Rename credential-shaped fixture strings to obvious-fake markers | Edit fixtures to the LES-001 pattern, e.g. `fake-env-marker-do-not-leak` | Pure string substitution with a fixed target pattern | Guardian `possible-secret` BLOCK clears; tests still pass |
| Apply mechanical ruff fixes | `ruff check apps/api` and `ruff check apps/worker` (CI pins `ruff==0.8.6`) | Lint output names the file, line, and rule; fixes are local | `ruff check` exits 0 |
| Append an already-drafted entry to `docs/RECENT_CHANGES.md` | Add the dated `## YYYY-MM-DD` section verbatim under the existing format | Verbatim transcription of prose someone else wrote | Diff review; note the file uses a union merge driver |
| Execute Provenance re-verification commands from any sibling skill | The one-liners listed in each skill's Provenance section | Each command has a stated expected output to compare against | Match or mismatch against the stated expectation |
| Look up constants, ports, LES status, DO NOT RETRY entries | Per `aos-config-and-flags`, `aos-failure-archaeology`, `aos-architecture-contract` | Read-only retrieval from named files | Source file is the answer |

Boundary notes:

- Applying the reconciliation draft to the state docs is NOT Haiku work. `--fix` only writes the draft; the narrative application (`/reconcile-state`, `skills/ci_devops/reconcile_state.md`) is Sonnet per `aos-docs-and-lessons`.
- Composing a new RECENT_CHANGES entry (deciding what to say about a merge) is Sonnet per `aos-docs-and-lessons`. Only verbatim appending of a pre-drafted entry is a Haiku candidate.
- A ruff finding whose fix changes behavior (unused variable that was load-bearing, import cycle) stops being mechanical: escalate.

## 5. SONNET-CLASS tasks

Standard engineering work following existing, documented patterns. This is the default tier for implementation.

| Task | Why Sonnet class | Pattern source |
|---|---|---|
| Execute a standard work package (`.archetype/work/AOS-*.md`, template `.archetype/work/TEMPLATE.md`) that follows an existing pattern | Needs code judgment inside a fixed spec; the package's acceptance criteria and the gates bound the blast radius | `aos-change-control` |
| Author tests per the four-layer recipes (api, worker, web e2e, aos_core) | Requires reading the module's existing test idiom and TDD discipline, not novel design | `aos-validation-and-qa` |
| CI triage: map a red job to a known failure mode and apply the table-row fix | Judgment is bounded by a symptom-to-fix table; unlisted symptoms escalate | `aos-debugging-playbook` |
| State-doc updates: apply a reconciliation pass, write RECENT_CHANGES narrative, index rows | Requires summarizing real changes accurately; verified by `doc_staleness.py` returning FRESH | `aos-docs-and-lessons` |
| Add a scanner signal, ecosystem, or risk reclassification via the constant tables plus tests | Extends enumerated tables with test coverage; edge-semantics redesign is Opus | `aos-scanner-dna-reference` |
| Write the lesson page for a Guardian catch or CI failure | Extracting the transferable rule needs judgment; contested root causes go to Opus | `aos-docs-and-lessons`, `aos-failure-archaeology` |
| Wire or debug the fastembed tier, run reality-test rankings | Operational judgment over a documented pipeline | `aos-knowledge-transfer-reference` |

Guardrails for Sonnet sessions: all of section 7 applies. Additionally, a Sonnet session executing a work package must keep the package a strict subset of its subsystem's mature-state target (operator rule in `docs/ORCHESTRATOR_PLAYBOOK.md`: no scaffolding that later work tears out; if a spec step would be torn out, flag it up instead of building it).

## 6. OPUS-CLASS tasks

Open-ended design, governance, and anything where the model's own judgment is the verification.

| Task | Why Opus class |
|---|---|
| RFC authoring or review (`docs/RFC_PROCESS.md`, `docs/rfc/RFC-0000` through `RFC-0010` as of 2026-07-06) | Sets policy that gates later enforce; errors propagate to every future PR |
| Campaign phases with decision gates (see `aos-evidence-loop-campaign`, the LES-019 evidence assembly loop) | Each gate is a judgment call on incomplete evidence, the hardest live problem in the repo |
| Calibration math and scoring analysis (see `aos-proof-and-analysis-toolkit`) | Wrong-but-plausible math passes every mechanical gate |
| Architecture contract changes: new layers, seams, invariant amendments (`aos-architecture-contract`) | Load-bearing decisions with repo-wide blast radius |
| Any change to Guardian rules, staleness signals, CI job graph, or other governance files | Changes what the gates catch; requires a lesson trail per RFC-0004 and change control |
| Anything touching `docs/ENGINEERING_CONSTITUTION.md` or `CLAUDE.md` | Constitutional; human approval required |
| Adjudicating a proposed override of a BLOCK, or an accepted-warnings registry entry | The house record: no substantive code BLOCK (tests, secrets, verification metadata, acceptance evidence) has ever been overridden; override tokens do appear in a minority of merged PR bodies as high-risk warn acknowledgments, prophylactic no-ops, and early capability-map suppressions. Audited home of the record: aos-change-control section 8 |
| Deciding a settled battle is not settled: reopening a closed lesson or challenging a DO NOT RETRY entry | Overturns accumulated evidence; RFC-level per `aos-failure-archaeology` |
| Independent verification of a builder's package (re-run, diff read, live probe) | Builder-is-not-verifier protocol per `aos-validation-and-qa` |

## 7. Hard guardrails for cheaper models

These are absolute for any Haiku or Sonnet session, and they restate, never relax, the repo's standing rules:

1. NEVER override Guardian. Do not add any `PR_GUARDIAN_OVERRIDE_*` token to a PR body. The override mechanism exists in `tools/pr_guardian.py` (`has_override`), and the record is that no substantive code BLOCK (tests, secrets, verification metadata, acceptance evidence) has ever been overridden; tokens appear in some merged PR bodies only as warn acknowledgments and no-op markers (audited record: aos-change-control section 8). BLOCKs are fixed in code, always.
2. NEVER merge. The Manual Merge Gate (head-SHA-pinned verification comment, then human merge) is not delegated to any model tier, and especially not down.
3. NEVER edit governance files (list in section 1). Read them freely; any change is Opus class plus the RFC or change-control path.
4. NEVER add or renew entries in `.archetype/guardian/accepted_warnings.json`. Deciding a warning is acceptable is a governance judgment (Opus per `aos-diagnostics-and-tooling`).
5. Escalate any BLOCK you cannot map to an existing lesson. If the BLOCK code and situation match a lesson in `knowledge/wiki/lessons/` (check `index.md`, or the symptom table in `aos-debugging-playbook`), apply the known fix. If not, stop and hand up: a novel BLOCK is by definition new information about the gates.
6. Never suggest bypassing PR Guardian, the Manual Merge Gate, or the RFC process, at any tier. There is no task class for which bypass is the answer.

## 8. Escalation protocol

Hand the task up one tier (Haiku to Sonnet, Sonnet to Opus, Opus to the human operator) when ANY of these fires:

| Trigger | Rule |
|---|---|
| 3 failed attempts | Three failed fix attempts on the same problem means the approach is wrong, not the typing. Stop, summarize the three attempts and their evidence, hand up. |
| Unexpected gate outcome | Any Guardian verdict, CI result, or tool exit that the runbook you are following did not predict. Includes: a BLOCK with no matching lesson, a PASS where you expected BLOCK, a STALE verdict right after reconciliation. |
| Governance-file change needed | The moment a fix appears to require touching a governance file, the task changes class. Do not make the edit and ask forgiveness. |
| Scope escape | The task grows beyond the work package's stated scope or stops being a subset of the mature-state target. |
| Contested root cause | Evidence supports two incompatible explanations. Per repo rule, disagreement escalates to Final Judge rather than forcing a premature decision (repo `CLAUDE.md`). |

Escalation handoff must include: what was attempted (commands verbatim), what the gates said (verdict lines verbatim), which lesson or skill section was consulted, and the specific question the next tier must answer. A handoff without evidence forces the next tier to redo the work.

## 9. Task tier guide

Routing home is this skill. Labels are operator guidance, candidate status as of 2026-07-06. Tasks in THIS skill's scope (routing itself):

| Task in this skill's scope | Tier |
|---|---|
| Look up the tier for a task that matches a row in sections 4 to 6 | Haiku |
| Execute the escalation handoff format (assemble evidence, post it) | Haiku |
| Classify a task with no exact row by analogy to existing rows | Sonnet |
| Draft or revise a sibling skill's Task tier guide table | Sonnet |
| Change this skill's routing policy, guardrails, or escalation triggers | Opus |
| Decide a borderline governance-adjacent route (is this file governance?) | Opus |

## 10. Per-skill tier expectations

One-line summary of each sibling's Task tier guide. The sibling's own table wins on detail, except where it conflicts with the hard guardrails in section 7, which are absolute; this is the index.

| Skill | Tier expectations in one line |
|---|---|
| aos-change-control | Haiku runs gates and formats PR metadata; Sonnet fixes BLOCKs, authors work packages and lessons; Opus changes Guardian rules, drafts RFCs, adjudicates overrides and scope disputes. |
| aos-debugging-playbook | Haiku runs checklists and discriminating checks verbatim; Sonnet applies table-row fixes and writes the lesson; Opus takes unlisted symptoms, cross-layer root causes, and any gate change. |
| aos-failure-archaeology | Haiku looks up LES status and DO NOT RETRY entries; Sonnet maps new symptoms to workstreams and drafts lessons; Opus argues for reopening closed lessons or challenging DO NOT RETRY (RFC-level). |
| aos-architecture-contract | Haiku looks up invariants and re-verifies; Sonnet adds floor-tier tests and implements behind existing seams; Opus designs layers and seams, amends invariants, adjudicates Constitution conflicts. |
| aos-scanner-dna-reference | Haiku looks up constants and reads scan.json or DNA rows; Sonnet adds ecosystems and signals and diagnoses false positives; Opus designs edge semantics and the read-content policy. |
| aos-knowledge-transfer-reference | Haiku looks up constants, formulas, endpoints; Sonnet runs reality tests and wires fastembed; Opus changes scoring, confidence calibration, or the evidence-assembly loop (LES-019). |
| aos-config-and-flags | Haiku looks up defaults and runs re-verification; Sonnet changes ports, env vars, and full config axes; Opus decides warning acceptability (including renewing an accepted-warnings entry, which is a re-decision) and designs new gates or tier defaults. |
| aos-build-run-and-operate | Haiku runs health checks and scripts verbatim; Sonnet does from-scratch builds, repo onboarding, compose and CI changes; boot mysteries escalate via aos-debugging-playbook. |
| aos-diagnostics-and-tooling | Haiku runs tools and reports verdicts verbatim; Sonnet classifies warnings, fixes ordinary BLOCKs, applies reconciliation drafts; Opus interprets ranking flips and changes checks or the accepted-warnings registry. |
| aos-validation-and-qa | Haiku runs suites and fills PR metadata from gathered evidence; Sonnet authors tests and diagnoses flakes; Opus judges ranking regressions, sets thresholds, and independently verifies builders. |
| aos-docs-and-lessons | Haiku runs doc_staleness and inspects PENDING.md; Sonnet writes RECENT_CHANGES entries, reconciliation passes, and lessons; Opus authors RFCs and resolves state-doc conflicts. |
| aos-research-frontier | Haiku runs harnesses and extracts traceability data; Sonnet builds baseline scorers and labels relevance sets; Opus designs taxonomies and signs any externally facing claim with the operator. |
| aos-research-methodology | Haiku checks the lessons index, re-runs committed harnesses, and runs the local gate; Sonnet drafts lessons, work packages, and discriminating checks; Opus frames hypotheses with predicted numbers, judges mechanisms, decides adopt vs retire, and authors RFCs. |
| aos-evidence-loop-campaign | Haiku polls jobs, runs the curl phases, quotes the artifact, and counts coverage; Sonnet writes corpus content and executes the campaign end to end, comparing predictions vs observed; Opus interprets GATE 1 failures and owns Phase 4 taxonomy/selector/RFC design. |
| aos-proof-and-analysis-toolkit | Haiku runs the reality harness and `pytest -m embedder` and reports output; Sonnet back-derives score behavior, writes hermetic/real test pairs, and drafts predicted numbers; Opus designs calibration formulas, classifies evidence classes, and promotes scratch tests to regression gates. |

## 11. Common mistakes

- Treating tier labels as validated capability claims. Every assignment here is candidate status; no benchmark backs them. When one is proven wrong in practice, that is a lesson, not an embarrassment.
- Routing by difficulty instead of verifiability. "Easy" judgment calls (is this warning acceptable?) are Opus; "hard-looking" mechanical work (long ruff runs, gate reruns) is Haiku-candidate.
- Letting a cheap session fix a novel BLOCK creatively. If the BLOCK has no matching lesson, the correct output is an escalation handoff, not a workaround.
- Confusing draft generation with draft application. `doc_staleness.py --fix` (write PENDING.md) is Haiku-candidate; applying it to the state docs is Sonnet narrative work.
- Adding an override token "just to test". The token string in a PR body IS the override; there is no dry-run form, and prophylactic no-op tokens have already polluted merged PR bodies exactly this way (see aos-change-control section 8). Keep the no-substantive-override record intact by never typing a token.
- Skipping the handoff evidence. An escalation that says only "it failed" forces full rework one tier up and doubles the cost the routing was meant to save.
- Citing this table outside ArchetypeOS. The task classes are repo-specific; the verifiability principle travels, the rows do not.

## 12. Provenance and maintenance

Written 2026-07-06 against branch `laptop/aos-selfheal-doc-loop` (HEAD: AOS-SELFHEAL-001, since merged as PR #80). Operator routing intent recorded 2026-07-06. Derived from:

- `tools/pr_guardian.py` (verdicts, `has_override`, `check_doc_staleness`, accepted-warnings path)
- `scripts/pre_pr_guardian.sh` (local gate contents and arguments)
- `tools/doc_staleness.py` (verdicts, `--fix` draft behavior; `--fix` merged via PR #80)
- `knowledge/wiki/lessons/LES-001.md` (fixture marker pattern), `knowledge/wiki/lessons/index.md`
- `.archetype/work/` (package shapes, `TEMPLATE.md`), `docs/ORCHESTRATOR_PLAYBOOK.md` (mature-state rule)
- `docs/RFC_PROCESS.md`, `docs/rfc/` (RFC-0000 to RFC-0010), `docs/BRANCH_PROTECTION.md`, `docs/PR_GUARDIAN.md`, repo `CLAUDE.md`
- `.github/workflows/ci.yml` (ruff pin and scope), sibling skill Task tier guides under `.claude/skills/`

Re-verification commands (run from repo root; expected result in parentheses):

| Fact | Command |
|---|---|
| Guardian verdict strings | `grep -n "Verdict:" tools/pr_guardian.py` (PASS, BLOCK, PASS_WITH_WARNINGS) |
| Override token format | `grep -n "PR_GUARDIAN_OVERRIDE_" tools/pr_guardian.py` (has_override key prefix) |
| Local gate steps | `cat scripts/pre_pr_guardian.sh` (guardian, compileall, api+worker pytest, web build, compose config) |
| doc_staleness --fix target | `python tools/doc_staleness.py --help` (draft to .archetype/reconciliation/PENDING.md) |
| LES-001 marker pattern | `grep -n "fake-env-marker" knowledge/wiki/lessons/LES-001.md` |
| Ruff pin and scope | `grep -n "ruff" .github/workflows/ci.yml` (ruff==0.8.6; apps/api, apps/worker) |
| RFC range | `ls docs/rfc/` (RFC-0000 through RFC-0010 as of 2026-07-06) |
| Merged PR count drifts | `git log origin/main --oneline \| grep -c "Merge pull request"` (72 as of 2026-07-06) |
| Accepted-warnings path | `grep -n "accepted_warnings" tools/pr_guardian.py` (.archetype/guardian/accepted_warnings.json) |
| Sibling tier tables | `grep -rn "Task tier" .claude/skills/*/SKILL.md` (every sibling carries one) |
| In-authoring skills landed | `ls .claude/skills/` (check aos-research-methodology, aos-evidence-loop-campaign, aos-proof-and-analysis-toolkit) |
| Haiku adoption status | Operator check-in; update section 1 and all "candidate" labels when Haiku routing is validated in practice |
