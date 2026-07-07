---
name: aos-research-methodology
description: Use when an ArchetypeOS session has a hunch, improvement idea, or proposed mechanism and needs to know how to turn it into an accepted result; when unsure whether an idea needs a reality test, lesson (LES-*), RFC, or work package (AOS-*); when tempted to ship on eyeball validation or tune thresholds to force a verdict; when deciding if evidence meets the bar (Constitution Articles III, VIII, XII); or when retiring a rejected approach like the raw-Jaccard score in LES-023.
---

# AOS Research Methodology: Hunch to Accepted Result

## 1. Overview

ArchetypeOS treats its own development as a research program. An idea is not "done" when the code runs; it is done when one mechanism explains every observation (including the negative ones), the mechanism survived an attempted refutation, and the result is recorded in an artifact a future session can consume (a lesson, an RFC, a work package, a closed index row).

This skill is the discipline that moves an idea through that pipeline. It defines:

- The evidence bar (what "accepted" means here).
- The rule that a hypothesis must predict numbers before the experiment runs.
- The idea lifecycle, stage by stage, with each stage's artifact.
- Where good ideas historically came from, verified against the lessons vault.
- The adversarial-refutation norm.
- The anti-patterns, each with the lesson that documents its cost.

Jargon used once and defined here:

- **Lesson (LES-*)**: a durable learning-event page under `knowledge/wiki/lessons/`, registered in `knowledge/wiki/lessons/index.md`, per RFC-0004 (`docs/rfc/RFC-0004-Learning-Feedback-Loop.md`). On conflict between a lesson page and the index table, the index wins.
- **Reality test**: running the real service pipeline over real external inputs (for example the 6-repo cloned portfolio) instead of synthetic fixtures, to surface honest defects.
- **Deterministic floor**: the hermetic, CI-safe, LLM-free tier of an evidence pipeline (per `docs/ORCHESTRATOR_PLAYBOOK.md`, "Design to the mature-state target"). Experiments plug in behind an existing floor seam; they never add throwaway scaffolding.
- **PR Guardian**: the deterministic gate `tools/pr_guardian.py` with verdicts PASS, PASS_WITH_WARNINGS, BLOCK. Local wrapper: `scripts/pre_pr_guardian.sh`.
- **Work package (AOS-*)**: a spec in `.archetype/work/AOS-*.md` (template: `.archetype/work/TEMPLATE.md`).

## 2. When to use / When NOT to use

Use this skill when:

- You have a hunch about a defect, a better mechanism, or a missing capability and need the path from hunch to merged result.
- You are about to claim a root cause or a fix and need to check whether the evidence actually clears the bar.
- You need to decide whether something deserves a lesson, an RFC, a work package, or nothing.
- You are retiring an approach and must document it so it is not re-proposed.

Do NOT use this skill for:

- The math and measurement recipes themselves (coverage vs Jaccard derivations, calibration checks, worked analyses): see **aos-proof-and-analysis-toolkit**.
- The change gates, Guardian rules, and merge mechanics: see **aos-change-control**.
- Live debugging of a known failure symptom: see **aos-debugging-playbook** (its symptom table has the discriminating checks this skill's refutation norm relies on).
- The catalog of already-settled battles and rejected approaches: see **aos-failure-archaeology**.
- Picking WHICH research direction to pursue (portfolio reuse intelligence, self-improving governance, evidence-governed agents): see **aos-research-frontier**.
- Authoring mechanics for lessons, RFCs, and state docs (house style, templates): see **aos-docs-and-lessons**.

## 3. The evidence bar

An idea is accepted only when all four hold:

1. **One mechanism explains ALL observations, including the negatives.** A hypothesis that explains why kubernetes ranked #1 but not why its confidence was 0.0147 is incomplete. LES-023 is the model: "union dominated by the candidate's own tokens" explained both the correct rankings AND the near-zero magnitudes AND why verbose candidates scored worst. If any observation is left over, the mechanism is wrong or partial.
2. **The mechanism survived an attempted refutation.** Before accepting it, design a cheap experiment whose outcome would differ if the mechanism were false, and run it (Section 7).
3. **Verification over inference.** Constitution Article VIII: "When deterministic verification exists, it should be preferred over inference." Read the source, run the command, reproduce the failure. Lessons in the vault say "Root cause (verified against source)" for exactly this reason (LES-022, LES-023 both do).
4. **Unknowns stay unknown.** Constitution Article XII: "Unknowns must remain unknown until evidence exists. Metrics and confidence scores must not be manipulated to support predetermined conclusions." Article III adds: when evidence is missing, incomplete, conflicting, or stale, say so clearly. "Open" and "candidate" are valid, permanent-until-consumed states here; forcing them closed is the violation.

The negative observations are the discriminating ones. `claude-agent-sdk-python` reading correctly at 77% Python is what proved the LES-013 language-mix misread was repo-dependent (config/docs-heavy repos), not universal. Always ask: what did NOT fail, and does my mechanism predict that too?

## 4. Hypothesis predicts numbers BEFORE running

A hypothesis in this repo is stated with the numbers it predicts, written into the spec's acceptance criteria before the verifying run. Real examples, all verifiable in `.archetype/work/`:

| Spec | Predicted before the run | Outcome |
| --- | --- | --- |
| `AOS-TRANSFER-002.md` (acceptance criteria) | Need-coverage scoring will yield kubernetes #1 on "container orchestration" at conf 0.333 and gin #1 on "HTTP routing" at conf 0.800, rankings unchanged | Held; the agent-framework ranking additionally improved (pydantic-ai over the SDK wrapper), recorded in LES-023 |
| `AOS-DISTILL-003.md` (harness contract) | `scripts/reality_test_distillation.py` must carry a module docstring stating the expected post-fix rankings: k8s #1 on container orchestration, gin #1 on HTTP routing | Held; harness committed as the manual regression gate |
| `AOS-ARCH-SEMANTICS-001` (via LES-013 close) | Source-classified weighting makes a docs/config-heavy fixture assert `primary_language == "Python"` | Held; test shipped in the same change set |

Why this matters: a prediction written after the run cannot be refuted by the run. If you cannot state what number the mechanism implies, you do not yet have a mechanism, you have a preference. Compute the expected values by hand from the design first (aos-proof-and-analysis-toolkit has the recipes), then run.

## 5. The idea lifecycle

Every stage has a named artifact. Skipping a stage is allowed only downward (a hunch that dies in the reality test produces just a lesson, or nothing if it taught nothing new).

| Stage | What happens | Artifact | Ground rules |
| --- | --- | --- | --- |
| 1. Hunch | A suspicion from a run, a review, an operator remark | None required; a note in `docs/ACTIVE_WORK.md` if it will wait | Check `knowledge/wiki/lessons/index.md` first: if a lesson already covers it, cite that instead of re-deriving |
| 2. Reality test / experiment | Run the real pipeline over real inputs, behind an EXISTING deterministic-floor seam | A repeatable harness (pattern: `scripts/reality_test_distillation.py`) or a recorded manual run with exact commands | Mature-state rule (`docs/ORCHESTRATOR_PLAYBOOK.md`): every experiment must be a strict subset of the mature-state target. Test: "will this design be extended or torn out by the mature system?" If torn out, do not build it. No scaffolding, ever |
| 3. Lesson | Record what was learned, positive or negative | `knowledge/wiki/lessons/LES-*.md` + index row, in the SAME change set as the work that surfaced it (RFC-0004; also a repo CLAUDE.md operating rule) | Categories: guardian-catch, guardian-gap, ci-failure, review-remediation, self-found-defect, process (plus design-insight in practice, e.g. LES-019, LES-023). Status open until a loop consumes it |
| 4. RFC (conditional) | Required if the idea changes an engine, agent, runtime service, provider integration, governance, security model, data model, major UI/UX, autonomous action capabilities, or external system integrations (full list: `docs/RFC_PROCESS.md`) | `docs/rfc/RFC-NNNN-title.md` per `docs/RFC_PROCESS.md` | Lifecycle: Draft, Council Review, Final Judge, Accepted/Rejected/Deferred, Implementation, Validation, Knowledge. "Important architectural change should be argued before it is coded" |
| 5. Work package | Scope the implementation as a subset of the mature-state target | `.archetype/work/AOS-*.md` with verified baseline, in-scope files, out-of-scope, acceptance criteria WITH PREDICTED NUMBERS (Section 4) | Precedent chain: LES-005 became AOS-RUNTIME-004, the loop's reference demonstration |
| 6. Guardian-gated PR | Implement, run the local gate, open the PR (with explicit operator approval), merge under the head-SHA-pinned manual merge gate | The PR + its evidence-bearing body | `bash scripts/pre_pr_guardian.sh` from the repo root (defaults: base `origin/main`, head `HEAD`). Never bypass Guardian, the manual merge gate, or the RFC process; no substantive code BLOCK has ever been overridden (verified record: aos-change-control section 8), BLOCKs are fixed in code |
| 7. Adopted OR documented retirement | Close the lesson citing what consumed it, or record the rejection so it stays dead | Closed index row with "Consumed by", or a rejection recorded in the lesson/spec | Both endings are results. An undocumented retirement is a future duplicate experiment |

### Worked retirement example: raw Jaccard (LES-023)

The Knowledge Transfer Engine's original `score_relevance` was `|need AND cand| / |need OR cand|` (Jaccard over the candidate's whole vocabulary). The end-to-end reality test showed correct #1 rankings with useless magnitudes (0.01 to 0.13; kubernetes #1 at conf 0.0147). The mechanism (union dominated by the candidate's own tokens, so magnitude measured candidate verbosity, not match quality) explained every observation. The retirement was documented, not silent:

- LES-023 records the mechanism, the evidence, and the standing rule: a retrieval confidence should measure coverage of the QUERY (`|covered| / |need|`), never overlap against the candidate's full vocabulary.
- AOS-TRANSFER-002 shipped the replacement with predicted numbers (0.333, 0.800) that held.
- The lesson's status line tells future sessions when to cite it: "if a retrieval/relevance score is defined as overlap against a candidate's full vocabulary", including for the embeddings tier (keep reported confidence coverage-like, not a raw similarity).

A sibling micro-retirement in LES-013: LoC-based language weighting was considered and rejected (the scanner does not read source bodies; classification fixed the misread without new I/O). One sentence in the lesson is all a retirement costs; re-running the dead experiment costs a session.

## 6. Where good ideas historically came from

Verified against `knowledge/wiki/lessons/` (as of 2026-07-06, branch `laptop/aos-selfheal-doc-loop`). Four generators account for the vault's highest-yield lessons:

| Generator | What it is | Lessons produced |
| --- | --- | --- |
| Portfolio reality test, single repo then diverse batch (AOS-21 / AOS-PORTFOLIO-001) | Scan real external repos the system did not write (pydantic-ai first, then the 6-repo diverse batch) | LES-013 (language mix), LES-014 (missing dependency edges), LES-015 (Playwright one-shot counts), LES-016 (ecosystem breadth), LES-017 (test-fixture secret false positives) |
| Full end-to-end reality test (2026-07-06) | Run the whole intelligence loop (`run_scan`, `distill_repository`, `recommend_reuse`) over the real cloned portfolio | LES-022 (distillation floor noise, frameworks never stamped), LES-023 (Jaccard retirement) |
| Alpha self-review (PR #37) | The system evaluating itself against its own Phase 10 questions | LES-005 (health endpoint crashed exactly when degraded), LES-007 (doc staleness invisible to the machine) |
| Operator correction (2026-07-06) | The operator naming a gap the sessions had normalized | LES-L01 (a detector without a remediation trigger is not self-learning; consumed by AOS-SELFHEAL-001, merged as PR #80) |

The pattern: the cheapest honest confrontation with reality (real repos, real end-to-end runs, the system's own health) out-produces speculation. AOS-PORTFOLIO-001 predicted this in writing before the run: "the cheapest reality test of every engine ... will generate the next round of honest lessons."

## 7. The adversarial-refutation norm

Before accepting a mechanism, attempt to refute it. Design a **discriminating experiment**: a cheap check whose outcome differs depending on whether your mechanism or a rival is true. The symptom table in **aos-debugging-playbook** has a dedicated "Discriminating check" column; reuse those checks verbatim where the symptom matches, and imitate their shape where it does not.

Refutation checklist:

- [ ] State the mechanism in one sentence with its predicted numbers.
- [ ] List at least one rival explanation (workflow-enforcement house rule: 3 hypotheses before investigating any is the debugging standard; for accepting a research result, one serious rival minimum).
- [ ] Name an observation that would differ between them. If none exists, your mechanism is unfalsifiable as stated; sharpen it.
- [ ] Run the check. LES-013's refutation was scanning a second repo: if "file-count mix is just noisy everywhere" were true, the lean SDK repo would also misread; it read 77% Python correctly, so the mechanism was pinned to config/docs-heavy repos.
- [ ] If the check contradicts the mechanism, the mechanism loses, not the check. Update or retire it (Section 5, stage 7).

The Council's abstention in LES-019 is this norm operating at system level: given only a structural scan for an adoption question, it refused to manufacture a verdict, cited the Constitution ("Research before implementation; Evidence over opinion"), and named the missing evidence classes. That abstention is documented as the Constitution working as intended, not as a failure. Imitate it: when your evidence cannot discriminate, say "insufficient evidence" and name what would.

## 8. Anti-patterns

| Anti-pattern | What it looks like | Why it fails | Documented cost |
| --- | --- | --- | --- |
| Eyeball validation | "The output looks right" without a pinned expectation or independent comparison | Correct-looking output hid uncalibrated confidences (rankings looked right for a full test cycle while magnitudes were artifacts) and badge markdown shipped as `DNA.purpose` until a reality test read it | LES-022, LES-023: both defects survived until a real end-to-end run compared output against stated expectations |
| Detector without remediation | Shipping a signal (WARN, flag, score) with no corrective path, then deferring every firing | The alarm becomes ambient noise; state docs sat 5 PRs behind while the staleness WARN fired repeatedly | LES-L01 (operator correction): "when a signal keeps firing, encode the correction, not just the detection, without gaming the metric (Article XII)"; consumed by AOS-SELFHEAL-001, `tools/doc_staleness.py --fix` (merged as PR #80) |
| Evidence-class mismatch | Feeding an experiment or agent evidence that answers a different question class (a structural scan of a target repo for an adoption decision) | The evidence cannot discriminate between the answers; a rigorous consumer abstains, a sloppy one hallucinates a verdict | LES-019 (open as of 2026-07-06): first real Council run, verdict "Insufficient evidence", confidence 0.0375; the fix is upstream (assemble the right corpus first). See aos-evidence-loop-campaign for the executable campaign |
| Forcing verdicts by threshold tuning | Nudging a threshold, boost, or weight until the desired output appears, without a mechanism | Article XII violation: "Metrics and confidence scores must not be manipulated to support predetermined conclusions." The tuned number is a memorized answer, not a model; it breaks on the next input | Contrast the compliant version: AOS-TRANSFER-002 replaced the scoring MECHANISM (Jaccard to need-coverage) with hand-predicted values, rather than scaling Jaccard up. `_TECH_BOOST` was removed, not tuned |

Two more house norms that guard the same territory:

- **Never override Guardian on substance.** Eight documented override tokens exist; no substantive BLOCK (tests, secrets, verification metadata, acceptance evidence) has ever been overridden on a code PR, and tokens appear in merged PR bodies only as warn acknowledgments and no-op audit markers (verified record: aos-change-control section 8). A BLOCK is data: fix the code, record the lesson.
- **Never build scaffolding to "just test the idea".** The mature-state rule applies to experiments too: run behind an existing seam (`score_relevance`, the distillation summary floor, the scanner) or write a standalone read-only harness under `scripts/`.

## 9. Task tier guide

Routing home is **aos-model-routing**; tier labels are operator guidance, candidate status.

| Task in this skill's scope | Tier |
| --- | --- |
| Check the lessons index for prior art before starting; re-run a committed reality harness verbatim; run the local Guardian gate | Haiku |
| Draft a lesson page for a clear-cut event; write a work package from an already-analyzed defect; design and run a discriminating check from an existing playbook row | Sonnet |
| Frame a new hypothesis with predicted numbers; judge whether one mechanism truly explains all observations including negatives; decide adopt vs retire; author or review an RFC | Opus |

## 10. Common mistakes

1. **Recording the lesson in a later PR.** RFC-0004 and the repo CLAUDE.md require the lesson in the SAME change set as the work that surfaced it (post-merge events go in the next reconciliation PR).
2. **Duplicating a lesson.** Check `knowledge/wiki/lessons/index.md` first; if the event repeats an existing lesson, cite it there instead of adding a row.
3. **Pinning an open lesson ID in tests or docs as if permanently open.** Open lessons are a queue, not anchors; closing LES-007 broke tests that assumed it (LES-025). Derive open sets live. Open as of 2026-07-06 on this branch: LES-019 and LES-029.
4. **Predicting numbers after the run.** Acceptance criteria written post-hoc cannot fail. Write them into the spec before the verifying run (Section 4).
5. **Treating an abstention or a negative result as a failure to hide.** Both are results; LES-019 (abstention) and the LES-013 LoC-weighting rejection are permanent artifacts.
6. **Claiming a root cause without source verification.** The vault standard is "Root cause (verified against source)". If you did not read the code or reproduce the failure, label the claim a hypothesis.
7. **Skipping the RFC because the change "is small".** The trigger is WHAT it changes (engine, agent, governance, data model, and six more classes including autonomous action capabilities and external system integrations, per `docs/RFC_PROCESS.md`), not how many lines.
8. **Grabbing the next sequential ID under concurrency.** Concurrent sessions racing `LES-NNN` caused add/add collisions twice; the laptop session uses the `LES-L##` band (LES-L02). Check the index's ID-allocation section before numbering.

## 11. Provenance and maintenance

Authored 2026-07-06 on branch `laptop/aos-selfheal-doc-loop` (HEAD = AOS-SELFHEAL-001, since merged as PR #80; AOS-EMBED-002 / PR #73 confirmed merged to origin/main). Derived from:

- `docs/ENGINEERING_CONSTITUTION.md` (Articles III, VIII, XII, XVIII, XX)
- `docs/rfc/RFC-0004-Learning-Feedback-Loop.md`, `docs/RFC_PROCESS.md`
- `knowledge/wiki/lessons/index.md` and pages LES-005, LES-007, LES-013 to LES-017, LES-019, LES-022, LES-023, LES-025, LES-029, LES-L01, LES-L02
- `.archetype/work/AOS-TRANSFER-002.md`, `AOS-DISTILL-003.md`, `AOS-PORTFOLIO-001.md`, `AOS-SELFHEAL-001.md`, `TEMPLATE.md`
- `docs/ORCHESTRATOR_PLAYBOOK.md` (mature-state rule), `tools/pr_guardian.py`, `scripts/pre_pr_guardian.sh`, `tools/doc_staleness.py`, `scripts/reality_test_distillation.py`

Facts that may drift, with a re-verification command each (run from the repo root):

| Fact | Re-verify with |
| --- | --- |
| Open lesson set (LES-019, LES-029 as of 2026-07-06) | `grep -n "| open |" knowledge/wiki/lessons/index.md` |
| LES-L01 consumed by AOS-SELFHEAL-001 (merged as PR #80) | `git log origin/main --oneline --grep "AOS-SELFHEAL-001"` (fetch origin first; a stale local ref shows nothing) |
| Guardian verdict strings PASS / PASS_WITH_WARNINGS / BLOCK | `grep -n "Verdict:" tools/pr_guardian.py` |
| Local gate defaults (base origin/main, head HEAD) | `head -8 scripts/pre_pr_guardian.sh` |
| Predicted-numbers example (0.333 / 0.800) | `grep -n "0.333" .archetype/work/AOS-TRANSFER-002.md` |
| Reality harness exists with expected-rankings docstring | `head -30 scripts/reality_test_distillation.py` |
| `doc_staleness.py --fix` draft-only contract | `python3 tools/doc_staleness.py --help` |
| Lesson categories and same-change-set rule | `grep -n "same change set" docs/rfc/RFC-0004-Learning-Feedback-Loop.md` |
| RFC-required change types | `sed -n "/## When An RFC Is Required/,/## RFC Lifecycle/p" docs/RFC_PROCESS.md` |
| No-substantive-override record | audited in aos-change-control section 8; re-run `gh pr list --state merged --limit 200 --json number,body --jq '[.[] \| select(.body \| contains("PR_GUARDIAN_OVERRIDE")) \| .number]'` (expect a nonzero list, none suppressing a substantive code BLOCK) |
| Laptop LES-L## ID band | `grep -n "ID allocation" knowledge/wiki/lessons/index.md` |
