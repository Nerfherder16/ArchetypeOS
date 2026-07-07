---
name: aos-research-frontier
description: Use when planning research direction for ArchetypeOS, deciding what could be state of the art, evaluating whether a result is publishable or claimable externally, benchmarking the Knowledge Transfer Engine against baselines, framing the lessons-to-Guardian-rules loop or Council abstention as a methodology, or when someone asks "is this novel", "can we claim this", "what should AOS research next", or wants precision-at-k / ranked-retrieval evaluation of recommend_reuse.
---

# AOS Research Frontier

## Overview

ArchetypeOS (AOS) is an Engineering Intelligence Platform: it scans repositories, distills knowledge, recommends reuse, and governs its own changes with a deterministic PR Guardian and an evidence-gated Agent Council. This skill maps the three operator-confirmed (2026-07-06) directions where AOS could plausibly advance the state of the art, and the positioning discipline that governs what may be claimed externally.

Core stance, from docs/ENGINEERING_CONSTITUTION.md: Evidence over opinion (Article III), Engineering Integrity (Article XII), Decisions Are Hypotheses Until Validated (Article XVIII). Every "SOTA" statement below is an internal assessment until the proof bar in the Positioning section is met. No external literature review is recorded in this repo, so all novelty claims are candidate status.

Jargon used once and defined here:

| Term | Meaning |
| --- | --- |
| Transfer Engine | `recommend_reuse` in `packages/aos_core/aos_core/services/transfer.py`: given a free-text need, ranks distilled portfolio repos (RFC-0009) |
| Need coverage | The calibrated lexical score: fraction of the query's tokens satisfied by a candidate (LES-023), not Jaccard, never raw cosine |
| PR Guardian | Deterministic, stdlib-only gate in `tools/pr_guardian.py`; verdicts PASS / PASS_WITH_WARNINGS / BLOCK |
| Lessons vault | `knowledge/wiki/lessons/` (RFC-0004): one page per Guardian BLOCK, CI failure, remediation, or self-found defect, in the same change set |
| Agent Council | Multi-persona review service (`packages/aos_core/aos_core/services/council.py`) with a Final Judge that abstains on thin evidence |
| Golden portfolio | The 6 real repos used for reality testing: kubernetes, gin, pydantic-ai, example-voting-app, claude-agent-sdk-python, free-llm-api-resources; clones live under `./repositories/` (gitignored), frozen scan artifacts under `.archetype/portfolio/` |

## When to use / When NOT to use

Use this skill when:

- Choosing or prioritizing a research direction for AOS
- Designing a benchmark or evaluation for the Transfer Engine
- Drafting anything for an external audience (README claims, blog, paper, demo)
- Judging whether a result clears the bar for an external claim

Do NOT use this skill for:

- Executing the LES-019 evidence loop end to end: use `aos-evidence-loop-campaign`
- The evidence bar for internal PRs and the golden test inventory: use `aos-validation-and-qa`
- Distillation tiers, need-coverage math, embeddings internals: use `aos-knowledge-transfer-reference`
- The full lessons chronicle and dead ends: use `aos-failure-archaeology`
- Hypothesis-to-accepted-result process mechanics: use `aos-research-methodology`
- Change gating and Guardian non-negotiables: use `aos-change-control`

## Direction 1: Portfolio reuse intelligence

Goal: reuse recommendation that measurably beats naive baselines (grep-style lexical match, plain embedding search) on ranked-retrieval metrics.

### Why current practice falls short (assessment, no citations)

Common reuse discovery is grep or ad hoc embedding search over raw code or READMEs. Assessment: raw lexical search cannot bridge vocabulary gaps ("message queue" vs "Redis queue"), raw embedding search over undistilled text is noisy and its cosine scores are uninterpretable to a human deciding whether to reuse. AOS's bet is that retrieval over deliberately distilled, provenance-tagged repository knowledge, with a calibrated confidence, outperforms both. This is unproven: candidate.

### Repo-specific assets (verified as of 2026-07-06)

| Asset | Where | Status |
| --- | --- | --- |
| Calibrated need-coverage scorer | `score_relevance` in `packages/aos_core/aos_core/services/transfer.py` | shipped (AOS-TRANSFER-002, LES-023) |
| Semantic tier: fastembed (ONNX) `all-MiniLM-L6-v2`, 384-dim, pgvector storage | `packages/aos_core/aos_core/embeddings/` (`_fastembed.py`), `EMBEDDING_DIM` in `packages/aos_core/aos_core/config.py` | shipped (AOS-EMBED-001/002); note the built embedder is fastembed, not the sentence-transformers/torch named in RFC-0010's design text |
| Blend: `confidence = round(max(coverage, 0.6*sem + 0.4*coverage), 4)` | `_W_SEM` / `_W_COV` in `transfer.py` | shipped; blend weights are a candidate, not tuned against a labeled set |
| Distillation pipeline (deterministic floor + reasoned tier) | `packages/aos_core/aos_core/services/distillation.py`, RFC-0008 | shipped |
| Golden 6-repo portfolio + regression harness | `scripts/reality_test_distillation.py` | shipped; 4 fixed needs, gate: kubernetes #1 on "container orchestration and scheduling" (conf 0.333), gin #1 on "HTTP routing and middleware for a web API" (conf 0.800) |
| Measured semantic wins over the lexical floor | docs/RECENT_CHANGES.md (AOS-EMBED-002 entry) | "build AI agents that call tools" -> claude-agent-sdk-python: lexical 0.000, semantic 0.533; "deploy containers across machines" -> kubernetes: lexical 0.200, semantic 0.529 |

Run the existing harness (deterministic, hermetic; requires the portfolio cloned under `./repositories/`):

```bash
cd /home/nerfherder/Dev/ArchetypeOS
PYTHONPATH=packages/aos_core python scripts/reality_test_distillation.py
```

### First three steps in this repo

1. Freeze a labeled query-relevance set. Today the eval is 4 needs with a single expected #1 (the `NEEDS` list in `scripts/reality_test_distillation.py`). Expand to roughly 30 to 50 needs with graded relevance labels (relevant / partially relevant / irrelevant) for each of the 6 portfolio repos, stored as a committed JSON fixture (natural home: alongside the harness in `scripts/`, or under `.archetype/`), with the portfolio repo commit SHAs pinned in the same file. This is a normal work package: RFC or `.archetype/work/` spec first.
2. Implement baseline scorers behind the existing seam. `score_relevance` and `_semantic_recommendations` in `packages/aos_core/aos_core/services/transfer.py` already isolate scoring. Add a benchmark harness (a sibling of `reality_test_distillation.py`) that runs, over the same frozen set: (a) a grep-style baseline (raw substring/token match over the repos' README text, no distillation), (b) plain embedding search (raw cosine over undistilled README text, same fastembed model), (c) the shipped lexical floor, (d) the shipped blend. Do not change production defaults; baselines live in the harness only.
3. Report ranked-retrieval metrics. Precision-at-k (k = 1, 3), MRR (mean reciprocal rank), and, since labels are graded, nDCG, per scorer, in a committed report doc. Deterministic tiers, pinned SHAs, documented config (`embedding_provider`, `embedding_model`).

### You have a result when

The shipped pipeline (distillation + blend) beats BOTH baselines on the frozen labeled set on P@1 and MRR, with the gap larger than label noise (report per-query results, not just aggregates), reproducible by one command from a clean checkout plus the pinned portfolio. If it does not beat grep, that is also a result: record it as a lesson and do not claim reuse intelligence externally.

## Direction 2: Self-improving governance

Goal: the lessons-to-Guardian-rules loop as a publishable methodology: incidents become deterministic rules, rules cite their incident, and the loop enforces itself.

### Why current practice falls short (assessment)

Postmortems and lint rules usually live in separate worlds: incidents get written up, rules get added ad hoc, and nothing enforces the linkage or expires the exceptions. Assessment: the failure mode is silent repetition (the same warning firing forever, unactioned). AOS closed that with machine-checked traceability. Whether this generalizes beyond one repo is unproven: candidate.

### Repo-specific assets (verified as of 2026-07-06)

| Asset | Evidence |
| --- | --- |
| 33 lesson pages as of 2026-07-07: LES-001 to LES-031 plus the laptop band LES-L01/LES-L02 (id-collision fix, LES-L02), indexed with source PR and "Consumed by" per row; recount with ls knowledge/wiki/lessons/LES-*.md before citing | `knowledge/wiki/lessons/index.md` |
| Rule evolution commit: lessons become rules | `git log` commit d407905, AOS-PRG-003 "guardian evolution" (lessons become rules, RFC-0004 Phase 2); spec `.archetype/work/AOS-PRG-003.md` |
| Self-referential enforcement: `guardian-change-without-lesson` BLOCKs any `tools/pr_guardian.py` change that does not touch `knowledge/wiki/lessons/`; `override-without-lesson-citation` BLOCKs any override token without a `LES-<n>` citation | `tools/pr_guardian.py` (check functions; 13 `check_*` functions total as of 2026-07-06) |
| Expiring acceptances: WARN acceptances carry `review_by`; expiry escalates to BLOCK | `.archetype/guardian/accepted_warnings.json`; forcing function demonstrated by LES-009 (the 2026-08-01 expiry drove AOS-WEB-001 early) |
| No-substantive-override record | No `PR_GUARDIAN_OVERRIDE` token in any commit message (`git log --all --grep`; commit messages only). Across the merged PRs (numbers issued through about #81), no substantive code BLOCK (tests, secrets, metadata, acceptance) has ever been overridden; override tokens do appear in a minority of merged PR bodies as warn acknowledgments, prophylactic no-ops on docs-only PRs, and a few early suppressions. The PR-body audit is machine-verified via `gh`; its home is aos-change-control section 8 |
| Detect-to-correct extension | `tools/doc_staleness.py --fix` + post-merge hook (AOS-SELFHEAL-001, commit f197bda; merged via PR #80) |

### First three steps in this repo

1. Extract the traceability dataset. From `knowledge/wiki/lessons/index.md`, tabulate per lesson: category, source PR/run, status, and what consumed it (deterministic Guardian rule vs practice vs tooling). The "Consumed by" column is already the raw data.
2. Quantify recurrence before/after. For each lesson that became a rule, measure recurrence from repo history: e.g. `web-tests-not-enforced` fired unactioned on PRs #27/#34/#36 (LES-006) and then never silently repeated after the acceptance registry; secret-fixture trips (LES-001) vs later clean fixture practice (LES-017). Use `git log` and the CI run ids cited in the index; do not reconstruct ids from memory (LES-008).
3. Write the methodology case study as a doc (candidate RFC), including the no-substantive-override record (as audited in aos-change-control section 8, not a flat "zero overrides"), the expiry forcing function, and the self-referential rules, with every claim citing a repo artifact an external reader can re-derive.

### You have a result when

An external reader, given only the repository plus the merged PR bodies, can independently re-derive: every Guardian rule change cites a triggering lesson; at least three lessons show a measurable recurrence stop after rule adoption; and no substantive BLOCK override across the full PR history (re-derivable from the PR-body audit in aos-change-control section 8; a flat "zero overrides" claim would collapse, since tokens do appear in some merged bodies). Until a second, independent codebase runs the same loop, claim it as a single-repo case study, not a validated methodology.

## Direction 3: Evidence-governed agents

Goal: constitutional abstention and evidence-class discipline as a rigor standard for agent systems: an agent council that refuses to answer when fed the wrong class of evidence, and names exactly what is missing.

### Why current practice falls short (assessment)

Multi-agent review systems typically produce a confident-sounding verdict regardless of evidence quality; abstention, where it exists, is a raw confidence threshold with no account of evidence class. Assessment: the interesting standard is not "abstain when unsure" but "abstain because the evidence is the wrong kind for the question, and emit the missing-evidence spec." AOS has one real artifact of this behavior. One run is an existence proof, not a validated standard: candidate.

### Repo-specific assets (verified as of 2026-07-06)

| Asset | Evidence |
| --- | --- |
| A real abstention run with artifacts | `.archetype/council/pydantic-ai-review.json`: pydantic-ai adoption question, verdict "Insufficient evidence", confidence 0.0375, and a `follow_up` array naming the missing evidence classes (research notes, technology-fitness comparison, security/dependency review), citing the Constitution and RFC-0004 by name. Narrative: `docs/COUNCIL_REALRUN_PYDANTIC_AI.md` |
| Deterministic abstention floors | `ABSTAIN_CONFIDENCE = 0.35`, `MIN_EVIDENCE = 1` in `packages/aos_core/aos_core/services/council.py` (RFC-0005 Open Question 3; conservative, tunable) |
| The captured design insight | LES-019 (open as of 2026-07-06): a structural repo scan is the wrong evidence class for an adoption question; the abstention's `follow_up` is itself the spec for what to assemble |

The known gap, and the operator's hardest live problem: nothing yet gathers the requested evidence and re-runs the Council. That closure work is `aos-evidence-loop-campaign`; this direction is the research framing around it.

### First three steps in this repo

1. Make evidence classes first-class. Define a small taxonomy (structural scan, distillation, research note, fitness comparison, security review, decision record) mapped to question classes (how-is-it-built vs should-we-adopt vs is-it-safe), seeded directly from LES-019 and the `follow_up` array in `.archetype/council/pydantic-ai-review.json`. The evidence selectors in `packages/aos_core/aos_core/services/council.py` are the seam to annotate.
2. Build the assembly loop (via `aos-evidence-loop-campaign`): the Phase C decision loop gathers and records the named evidence (RFC-0004 capture), then re-runs the Council over a research/decision corpus instead of a target-repo scan.
3. Re-run the pydantic-ai adoption question with an assembled corpus and archive the run artifact next to the abstention one, plus a negative control: a deliberately starved re-run that must still abstain.

### You have a result when

The same adoption question that produced the 0.0375 abstention clears the floor with a cited-evidence verdict after assembly, the starved control still abstains, and both artifacts are committed under `.archetype/council/`. That pair (abstain-then-satisfy, with the abstention's own follow_up as the assembly spec) is the demonstrable unit. Generalizing to "a rigor standard" additionally requires the loop working on at least a handful of distinct questions without hand-tuning per question.

## Positioning discipline

Positioning is thin pre-publication by design. Nothing leaves this repo as a claim until it clears the bar below.

### Novel vs known (honest ledger, candidate assessments)

| Piece | Known components | Candidate-novel part |
| --- | --- | --- |
| Reuse retrieval | Lexical scoring, sentence embeddings, hybrid blending are all standard IR | Retrieval over deliberately distilled, provenance-tagged repo knowledge with a calibrated coverage-like confidence (never raw cosine, LES-023) as the human-facing number |
| Governance loop | Lint gates, CI policy, postmortems exist everywhere | Machine-enforced lesson-to-rule traceability (the Guardian blocks its own un-cited evolution) plus expiring acceptances, with a record of never overriding a substantive BLOCK (audit: aos-change-control section 8) |
| Evidence-governed Council | LLM abstention and confidence thresholds are known ideas | Evidence-CLASS mismatch as the abstention trigger, with the abstention output doubling as the evidence-assembly spec |

No external literature survey is recorded in this repo. Before publishing, run one and record it as research notes (Article II: Research Before Implementation applies to research output too). Do not invent citations; if a prior-art search finds the same idea, downgrade the claim and record a lesson.

### Proof bar before any external claim

All of the following, per claim:

- [ ] Benchmark exists: frozen labeled set, named baselines, ranked-retrieval metrics (Direction 1) or re-derivable repo artifacts (Directions 2 and 3)
- [ ] Reproducibility: pinned portfolio (repo commit SHAs recorded), deterministic tiers as the default path, documented config (`embedding_provider`, `embedding_model`, blend weights, abstention floors), one-command re-run
- [ ] The claim text distinguishes measured results from assessments; every number traces to a committed artifact
- [ ] Negative results and known limitations stated (e.g. the semantic tier's quality tracks the distilled text: the "message queue" -> example-voting-app match needs the reasoned `DNA.purpose`, per docs/RECENT_CHANGES.md)
- [ ] The change shipping the claim passed PR Guardian and the head-SHA-pinned manual merge gate like any other change; research work gets no governance shortcut, ever

The no-oversell rule: anything unproven or unvalidated at scale stays labeled candidate or open, in the repo and in any external text. A single-repo result is stated as a single-repo result.

## Task tier guide

Routing home is `aos-model-routing`; tier labels here are operator guidance, candidate status.

| Task in this skill's scope | Tier |
| --- | --- |
| Run the reality/benchmark harness, collect metric tables, re-verify provenance commands | Haiku |
| Extract the lesson-to-rule traceability dataset from the index | Haiku |
| Implement baseline scorers and the labeled-set benchmark harness | Sonnet |
| Label the query-relevance set (graded judgments over the portfolio) | Sonnet, operator-reviewed |
| Evidence-class taxonomy design; Council selector seam changes | Opus |
| Novelty assessment, prior-art survey, any externally facing claim text | Opus, operator sign-off required |

## Common mistakes

- Claiming SOTA from the 4-need reality gate. It is a regression gate with single expected winners, not a labeled benchmark. Build the frozen set first.
- Reporting raw cosine anywhere a human reads it. LES-023: confidence must be coverage-like and bounded.
- Citing RFC-0010's design text as ground truth for the embedder. The shipped tier is fastembed (ONNX), not sentence-transformers/torch; the build revision was operator-approved (AOS-EMBED-002).
- Claiming flat "zero overrides". Commit history is clean of override tokens, but the machine-verified PR-body audit (aos-change-control section 8) found tokens in a minority of merged PR bodies; the defensible claim is "no substantive code BLOCK ever overridden". Keep the `git log --grep` check only as a commit-message check.
- Hardcoding the lesson count. It moves with every session (33 pages as of 2026-07-07: 31 numbered plus LES-L01/LES-L02); recount from the index before citing. The L band exists because of a real id-collision lesson (LES-L02).
- Generalizing one abstention run into "a rigor standard". One artifact is an existence proof.
- Skipping governance for research code. Benchmark harnesses, labeled sets, and claim docs go through RFC or work-package specs, PR Guardian, and the manual merge gate like everything else. Never suggest bypassing them.
- Reconstructing PR numbers, run ids, or SHAs from memory (LES-008): copy them from tool output.

## Provenance and maintenance

Authored 2026-07-06 on branch `laptop/aos-selfheal-doc-loop` (HEAD f197bda, AOS-SELFHEAL-001, since merged as PR #80). Derived from: `docs/rfc/RFC-0009-Knowledge-Transfer-Engine-Portfolio-Reuse.md`, `docs/rfc/RFC-0010-Embedding-Relevance-Tier-Transfer-Engine.md`, `packages/aos_core/aos_core/services/transfer.py`, `packages/aos_core/aos_core/services/council.py`, `packages/aos_core/aos_core/embeddings/__init__.py` and `_fastembed.py`, `packages/aos_core/aos_core/config.py`, `scripts/reality_test_distillation.py`, `tools/pr_guardian.py`, `.archetype/work/AOS-PRG-003.md`, `.archetype/guardian/accepted_warnings.json`, `.archetype/council/pydantic-ai-review.json`, `knowledge/wiki/lessons/index.md` (and LES-019), `.archetype/roadmap.md`, `docs/MASTER_ROADMAP.md`, `docs/ARCHETYPEOS_CONTEXT.md`, `docs/ORCHESTRATOR_PLAYBOOK.md`, `docs/RECENT_CHANGES.md`, `docs/ENGINEERING_CONSTITUTION.md`.

Re-verification commands (run from the repo root):

| Fact | Re-verify with |
| --- | --- |
| Reality-gate rankings (k8s 0.333 / gin 0.800) | `PYTHONPATH=packages/aos_core python scripts/reality_test_distillation.py` |
| Blend weights 0.6 / 0.4 and coverage scorer | `grep -n "_W_SEM\|_W_COV\|def score_relevance" packages/aos_core/aos_core/services/transfer.py` |
| Embedder is fastembed, 384-dim, deterministic default | `grep -n "fastembed\|embedding_provider\|EMBEDDING_DIM" packages/aos_core/aos_core/config.py packages/aos_core/aos_core/embeddings/__init__.py` |
| Abstention floors 0.35 / 1 | `grep -n "ABSTAIN_CONFIDENCE\|MIN_EVIDENCE" packages/aos_core/aos_core/services/council.py` |
| Abstention artifact (verdict, 0.0375) | `python3 -c "import json;d=json.load(open('.archetype/council/pydantic-ai-review.json'));print(d['verdict'],d['confidence'])"` |
| Lesson count and open set | `ls knowledge/wiki/lessons/LES-*.md | wc -l` and `grep -n "| open |" knowledge/wiki/lessons/index.md` |
| Guardian self-referential rules | `grep -n "guardian-change-without-lesson\|override-without-lesson-citation" tools/pr_guardian.py` |
| No override token in history | `git log --all --grep="PR_GUARDIAN_OVERRIDE" --oneline` (expect empty) |
| Merge-commit count (an approximate upper bound, NOT the merged-PR count; the authoritative PR count lives in aos-change-control section 16) | `git log origin/main --oneline --merges | wc -l` |
| AOS-EMBED-002 merged (PR #73); AOS-SELFHEAL-001 merged (PR #80) | `git log origin/main --oneline | grep -i "EMBED-002\|SELFHEAL"` (fetch origin first; a stale local ref hides PR #80) |
| LES-019 still open / LES-014 closed | `grep -n "LES-019\|LES-014" knowledge/wiki/lessons/index.md` |
