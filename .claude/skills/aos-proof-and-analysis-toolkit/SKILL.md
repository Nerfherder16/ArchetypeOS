---
name: aos-proof-and-analysis-toolkit
description: 'Use when an ArchetypeOS score or confidence looks wrong (near-zero confidence for a correct top match, Jaccard collapse, raw cosine surfaced to users), when a real model tier must be proven without breaking CI hermeticity (fastembed, torch-free jobs, pytest markers), when designing a reality test or regression gate, when a work package needs predicted numbers before running, or when the Council abstains with "Insufficient evidence" and you must classify what evidence the question needs.'
---

# AOS Proof and Analysis Toolkit

## 1. Overview

Five first-principles analysis recipes, each grounded in a real incident or shipped validation from this repo's history. These are the reusable "how do I prove it" patterns behind ArchetypeOS results: score calibration diagnosis, hermetic-vs-real tier validation, reality-test protocol design, prediction-before-execution, and evidence-class analysis.

Each recipe gives: when to use it, numbered steps, a worked example with numbers verified against the repo, and failure modes. The lifecycle these recipes live inside (hunch, spec, evidence bar, accepted result) is owned by the sibling skill aos-research-methodology; this skill is the toolbox, that one is the process.

Definitions used throughout:

| Term | Meaning |
|------|---------|
| Reality test | Running the real service code over the real cloned 6-repo portfolio (not fixtures) and inspecting output by hand |
| Hermetic | Runs with no network, no real model, no cloned repos; deterministic and CI-safe |
| Need coverage | The Transfer Engine confidence: fraction of the query's meaningful terms the candidate covers (LES-023) |
| Evidence class | The kind of evidence a question requires (structural scan vs research corpus vs decision record), per LES-019 |
| Work package | A spec file in `.archetype/work/AOS-*.md` with Verified Baseline, In-Scope Files, Acceptance Criteria, Verification sections |

## 2. When to use / When NOT to use

Use this skill when:

- A ranking is correct but its confidence magnitude reads as wrong (too small, too large, or uninterpretable in a UI).
- You are adding a component that needs a real dependency (model, service) proven in CI without polluting the hermetic unit jobs.
- You need a repeatable gate for behavior that only shows up on real data.
- You are writing a work package Verification section and want it falsifiable.
- An agent or Council run abstained or returned garbage and you suspect the input evidence was the wrong kind.

Do NOT use this skill for:

- The overall research lifecycle and evidence bar: see aos-research-methodology.
- Test-suite mechanics, golden inventory, and how to add tests: see aos-validation-and-qa.
- Transfer Engine internals (tokenization, blend weights, embeddings seam) as reference material: see aos-knowledge-transfer-reference.
- Actually executing the LES-019 evidence loop end to end: see aos-evidence-loop-campaign.
- Triage of a live failure with unknown cause: see aos-debugging-playbook.
- Running the measurement tools themselves: see aos-diagnostics-and-tooling.

## 3. Recipe 1: Confidence calibration analysis

Use when a retrieval or scoring system ranks correctly but the reported magnitudes are not believable, or before surfacing any score in a UI.

### The incident (LES-023, fixed in AOS-TRANSFER-002, PR #66, merged 2026-07-06)

The Transfer Engine's first full reality test returned the correct repo #1 on every query, with honest matched-term provenance, but every confidence sat between 0.01 and 0.13. Examples recorded in `knowledge/wiki/lessons/LES-023.md`:

- `kubernetes` #1 for "container orchestration" at conf 0.0147
- `gin` #1 for "HTTP routing" at conf 0.108

Root cause: `score_relevance` was `jaccard = |need INTERSECT cand| / |need UNION cand|` plus a 0.15-per-hit tech boost (baseline recorded in `.archetype/work/AOS-TRANSFER-002.md`). The union is dominated by the candidate's own vocabulary: a distilled `purpose` tokenizes to many terms, so a correct match still scores near zero. The magnitude measured candidate verbosity, not match quality.

### Walk the actual math

Tokenization (verified in `packages/aos_core/aos_core/services/transfer.py`): lowercase, split on non-alphanumeric, drop stopwords and tokens shorter than 3 characters.

| Query | Need tokens | Count |
|-------|-------------|-------|
| "container orchestration and scheduling" | container, orchestration, scheduling | 3 |
| "HTTP routing and middleware for a web API" | http, routing, middleware, web, api | 5 |
| "agent framework with tool calling" | agent, framework, tool, calling | 4 |

Old Jaccard, back-derived from the recorded confidences (derivation, not a direct measurement; the matched counts are from LES-022/LES-023):

- kubernetes matched 1 term (container), conf 0.0147, so `|union|` was about 1 / 0.0147, roughly 68 tokens. One correct hit divided by 68 mostly-candidate tokens.
- gin matched 4 terms, conf 0.108, so `|union|` was roughly 4 / 0.108, about 37 tokens.

The denominator artifact: `|need UNION cand|` grows linearly with candidate vocabulary, so a richer (better) distillation is punished with a lower score. Jaccard penalizes a descriptive candidate exactly for being descriptive.

The bounded alternative, need coverage (shipped, verify in `transfer.py` `score_relevance`):

```
covered = (need INTERSECT cand) UNION (need INTERSECT tech)
score   = |covered| / |need|
```

Re-run results on the same portfolio (LES-023, AOS-TRANSFER-002 acceptance criteria):

| Query | Repo | Old conf | New conf | Reading |
|-------|------|----------|----------|---------|
| container orchestration and scheduling | kubernetes | 0.0147 | 0.333 | 1 of 3 need terms |
| HTTP routing and middleware for a web API | gin | 0.108 | 0.800 | 4 of 5 need terms |
| agent framework with tool calling | pydantic-ai | (ranked below SDK wrapper) | 0.5 | 2 of 4; now correctly outranks claude-agent-sdk at 1 of 4 (0.25) |

Rankings were preserved and one improved: the denominator fix sharpened, not just rescaled.

### The generalized recipe

1. Define the population: the set of (query, known-good candidate) pairs. Here: the 4 fixed reality-test needs against the 6-repo portfolio.
2. Compute the score distribution for known-good pairs. If correct #1 matches cluster near the bottom of the scale (here 0.01 to 0.13 on a 0..1 scale), you have a calibration defect even if rankings are right.
3. Identify the denominator (or normalizer) artifact: write the formula out and ask which inputs the denominator scales with. If it scales with something unrelated to match quality (candidate verbosity), that is the artifact.
4. Propose a bounded alternative whose denominator is under the asker's control (here `|need|`), so the score answers a plain-language question ("how much of what you asked for is covered?").
5. Re-run the same population and compare both magnitude (are correct matches now mid-to-high?) and ranking (order must be preserved or explainably improved).
6. Record the lesson (RFC-0004) and cite it in the code: `transfer.py` cites LES-023 at every point where a raw similarity might leak out.

The same rule now governs the semantic tier: `_W_SEM = 0.6`, `_W_COV = 0.4`, blended as `max(coverage, 0.6*sem + 0.4*coverage)`, and a raw cosine is never emitted (verify in `transfer.py`, `_recommend_semantic`).

### Failure modes

- Fixing magnitude while silently breaking rank order. Always diff rankings, not just scores.
- Reporting a raw cosine because "it is already 0..1". Bounded is not the same as calibrated; cosine 0.6 means nothing to a user.
- Sampling only good pairs. Also check that bad pairs stay low, otherwise you rescaled noise upward.

## 4. Recipe 2: Hermetic-vs-real tier validation

Use when adding a component with a heavy or nondeterministic dependency (an embedding model, a live LLM) that must be proven for real, while the default CI path stays dependency-free and deterministic.

### The incident-free example (AOS-EMBED-001 PR #70, AOS-EMBED-002 PR #73, both merged 2026-07-06)

The embedding tier (RFC-0010, `docs/rfc/RFC-0010-Embedding-Relevance-Tier-Transfer-Engine.md`) shipped a real fastembed (ONNX) embedder without ever letting fastembed, onnxruntime, or torch touch the hermetic unit jobs. The pattern, all paths verified in the repo:

1. A seam with a hermetic default. `packages/aos_core/aos_core/embeddings/__init__.py` defines the `EmbeddingProvider` Protocol, a `DeterministicEmbedder` default, and `get_embedder(settings)`. The real import is lazy: only `get_embedder("fastembed")` plus the first `embed` call load fastembed.
2. Separate requirements. `apps/api/requirements-embeddings.txt` pins `fastembed==0.5.1` (about 50 MB via onnxruntime, no torch) and is NOT in `requirements.txt`, so unit jobs stay minimal.
3. Hermetic tests that mock the heavy dep. `apps/api/tests/test_embeddings.py` installs a fake `fastembed` module (canned 384-vector, load counter) and asserts the seam invariant directly: after `import aos_core.embeddings`, none of `fastembed`, `onnxruntime`, `torch` appear in `sys.modules`.
4. Real tests behind a registered marker. `apps/api/tests/test_fastembed_real.py` is gated by `pytest.mark.embedder` plus `pytest.importorskip("fastembed")`; the marker is registered in the root `pyproject.toml`. It loads the actual all-MiniLM-L6-v2 ONNX model and asserts semantics: a 384-length L2-normalized unit vector, and paraphrases ("deploy containers across a cluster" vs "scheduling and orchestrating containers over many servers") scoring a higher cosine than an unrelated text (a cookie recipe).
5. A dedicated CI job with model caching. `.github/workflows/ci.yml` job `embedder-tests`: installs `requirements.txt` plus `requirements-embeddings.txt`, caches `~/.cache/fastembed` and `~/.cache/huggingface` keyed on the requirements file hash (the model is about 90 MB), asserts torch is NOT installed (a `sys.exit` if `importlib.util.find_spec('torch')` hits), then runs `PYTHONPATH=apps/api pytest apps/api/tests -m embedder`.

Run the real tests locally (cwd: repo root, fastembed installed in the venv):

```bash
pip install -e ./packages/aos_core   # CI does this too (ci.yml); without it collection fails with ModuleNotFoundError: aos_core
pip install -r apps/api/requirements-embeddings.txt
PYTHONPATH=apps/api pytest apps/api/tests -m embedder
```

### The generalized recipe

1. Put the heavy dependency behind a provider seam with a deterministic default; keep the import lazy.
2. Prove the hermetic contract with a mocked provider AND an explicit "importing the seam loads nothing heavy" assertion (`sys.modules` check). Absence of pollution is a testable claim; test it.
3. Prove the real behavior with marker-gated tests that skip cleanly when the dep is absent, asserting semantic properties (relative distances), not exact floats.
4. Give the real tier its own CI job with dependency and artifact caching; add a negative assertion that the forbidden heavy dep (torch) did not sneak in transitively.
5. Keep runtime opt-in via config (`EMBEDDING_PROVIDER=fastembed`; compose default stays `deterministic`).

### Failure modes

- LES-027 (`knowledge/wiki/lessons/LES-027.md`): the first AOS-EMBED-002 CI run failed with 0 jobs and 0 check-runs because an unquoted `run:` scalar contained `ok: no torch`, a YAML parse error. None of the local gates (ruff, compileall, compose config, pytest) parse workflow YAML. After editing `ci.yml`, verify the workflow parses and inspect the actual run, not just the PR checks list.
- Asserting exact vector values in the real test. Model or runtime bumps will flake it; assert dimensionality, normalization, and relative order.
- Letting the "temporary" mock become the only test. The marker-gated real job is the point; keep it green, do not delete it when it is slow.

## 5. Recipe 3: Reality-test protocol design

Use when a behavior only manifests on real data (real READMEs, real manifests) and you need a repeatable regression gate rather than a one-off manual poke.

### The worked example: `scripts/reality_test_distillation.py` (AOS-DISTILL-003)

This harness was promoted from the Orchestrator's scratch reality test (2026-07-06, the run that produced LES-022) into a committed, documented gate. Design elements, all verifiable in the script:

| Principle | How the harness does it |
|-----------|-------------------------|
| Pinned inputs | The cloned 6-repo portfolio under `settings.repository_root` (free-llm-api-resources, example-voting-app, gin, claude-agent-sdk-python, pydantic-ai, kubernetes) |
| Fixed queries | A module-level `NEEDS` list of 4 needs; the first two are the ranking gate |
| Known-answer expectations | The module docstring states the expected post-fix rankings: kubernetes #1 on "container orchestration and scheduling", gin #1 on "HTTP routing and middleware for a web API", and pydantic-ai's purpose being the "Pydantic AI is a Python agent framework" sentence, not the FastAPI analogy |
| Hermetic by default | `DeterministicProvider` distillation, scratch sqlite DB in a tempdir; no model, no network |
| Real mode opt-in | `--provider claude_code` or `AOS_REALITY_PROVIDER=claude_code` for the live quality check (flag wins; Orchestrator-only) |
| Tolerant ingest | A bad repo prints a warning and never aborts the whole harness |
| Idempotent | A repo whose `rt-<slug>` project already exists is skipped |
| Manual, not CI | It needs multi-GB cloned repos on disk, so it is not collected by pytest; it is a documented operator gate |

Run it (cwd: repo root, so `./repositories` and `./knowledge` resolve):

```bash
PYTHONPATH=packages/aos_core python scripts/reality_test_distillation.py
PYTHONPATH=packages/aos_core python scripts/reality_test_distillation.py gin kubernetes
```

Tolerance principle: the gate asserts rank ("kubernetes is #1"), not exact confidence values. AOS-TRANSFER-002 changed every magnitude and the gate still held, because behavioral tests assert which repo ranks, not floats (noted explicitly in that work package's test plan).

### The generalized recipe

1. Start from a manual reality test that actually found something (this one found LES-022's badge-markdown purposes and the never-stamped `frameworks` field).
2. Freeze the inputs: a fixed corpus and a fixed query list. Committing the queries is what turns exploration into a gate.
3. Write the expected outcomes into the harness itself (docstring or asserts), stated as ranks and properties, with tolerance for magnitudes.
4. Default to the hermetic path; make any real-model mode explicit opt-in so the gate stays reproducible.
5. Make ingest idempotent and per-item fault tolerant, so a partial portfolio still yields a usable report.
6. Document exactly how to run it, including cwd and env, in the file header.

### Failure modes

- Gate rot: expectations live only in a chat transcript or someone's head. If the expected rankings are not committed next to the harness, the next regression is invisible.
- Over-tight expectations: asserting `conf == 0.333` would have made the calibrated-blend work (RFC-0010) a false failure. Assert order and bounds.
- Silent portfolio drift: if the cloned repos change (new READMEs), rankings can shift for honest reasons. Record which portfolio snapshot the expectations were set against (here: the 2026-07-06 clones).

## 6. Recipe 4: Predict numbers before running

Use whenever writing the Verification or Acceptance Criteria section of a work package. Writing the expected observation down BEFORE executing makes the run falsifiable and makes "it worked" mean something.

### Real examples from `.archetype/work/` (verbatim spirit, paths verifiable)

1. `AOS-TRANSFER-002.md`, Acceptance Criteria, written before verification ran: "Reality-test gate holds with meaningful confidence: kubernetes #1 on 'container orchestration' (conf 0.333), gin #1 on 'HTTP routing' (conf 0.800); the correct repo is #1 on every gated need." The predicted 0.333 and 0.800 come straight from the coverage formula (1/3 and 4/5) computed on paper first; the Verification section then reports the run confirming 0.2 to 0.8 magnitudes versus the old 0.01 to 0.13.
2. `AOS-EMBED-002.md`, Verification section, predicted before the embedder existed in the repo: the semantic tier must surface a match the lexical floor misses, with named predictions: "message queue" / "background job runner" resolving to `example-voting-app` (its purpose names a Redis queue), and "deploy containers across machines" resolving to `kubernetes`.
3. `AOS-EMBED-002.md`, Acceptance Criteria: `embed` returns a 384-length unit vector and paraphrases score closer than unrelated text; these became the literal asserts in `test_fastembed_real.py`.
4. `AOS-DISTILL-003.md`, In-Scope Files: the spec required the new harness to "include a module docstring stating the expected post-fix rankings (k8s #1 on container orchestration, gin #1 on HTTP routing)", baking prediction into the deliverable itself.

### The generalized recipe

1. Before running anything, derive the expected number or rank from the design on paper (coverage 1/3 means predicted conf 0.333, not "confidence should improve").
2. Write it into the work package Acceptance Criteria or Verification section, with the query and the expected winner named.
3. Distinguish gate predictions (exact rank, must hold) from directional predictions (magnitude band, "misses become hits").
4. Run, then report the observed numbers next to the predicted ones in the Verification section. A mismatch is a finding, not an embarrassment; it either reveals a defect or a wrong model of the system, and either one is a lesson candidate (RFC-0004).
5. Where possible, promote the prediction into a committed assert (Recipe 3) so it keeps being checked.

### Failure modes

- Vague predictions ("scores should be more reasonable") that any outcome satisfies. If you cannot compute the number in advance, at least predict the order and the band.
- Predicting after peeking: running once "to see", then writing the observed value as the "prediction". This destroys the falsifiability the recipe exists for.
- Predicting exact floats for stochastic paths (real embedder cosines). Predict inequalities there (paraphrase > unrelated).

## 7. Recipe 5: Evidence-class analysis

Use before running the Council or any evidence-consuming agent on a question, and when diagnosing an abstention or a low-confidence verdict.

### The incident (LES-019, open as of 2026-07-06)

The first real Agent Council run (`docs/COUNCIL_REALRUN_PYDANTIC_AI.md`, captured output in `.archetype/council/pydantic-ai-review.json`) asked an adoption question: should ArchetypeOS adopt pydantic-ai as its LLM provider abstraction. The only evidence the selectors supplied was a structural scan of pydantic-ai's own repository; the security agent's evidence array was literally `[]`. The Council correctly abstained: verdict `Insufficient evidence`, confidence 0.0375, below the `ABSTAIN_CONFIDENCE` floor of 0.35, with `research_librarian` citing the Engineering Constitution ("Research before implementation; Evidence over opinion") and RFC-0004. Its `follow_up` named exactly what was missing: research notes on pydantic-ai, a technology-fitness comparison against alternatives, and a security/dependency-risk review.

The category error: a structural scan answers "how is this system built?"; an adoption question needs a research/decision corpus (fitness comparison, production-readiness notes, security review, prior decisions). This is a design insight, not a defect: constitutional abstention worked as intended. What is still missing, and why LES-019 stays open, is the loop that gathers the named evidence and re-runs; that campaign is aos-evidence-loop-campaign.

### The generalized recipe

1. Classify the question before selecting evidence. Minimum taxonomy in use here:
   - Structural ("how is X built?", "what languages/services?"): a scan/DNA answers it.
   - Adoption/decision ("should we use X?"): needs research notes, fitness comparison, security review, prior decisions.
   - Calibration ("is this score honest?"): needs a known-good population and score distributions (Recipe 1).
   - Behavioral regression ("did we break ranking?"): needs a pinned-input known-answer harness (Recipe 3).
2. Check what the evidence selectors will actually deliver for that question, before the run. An empty evidence array for one agent is a pre-run red flag, not a post-run surprise.
3. If the classes mismatch, stop and gather upstream first. Feeding the wrong class does not produce a weaker answer; it produces either an abstention (best case) or a manufactured verdict (worst case).
4. Treat an abstention's `follow_up` as a specification: the pydantic-ai run's follow_up list is literally the input spec for the evidence-gathering loop.
5. Never lower the abstention floor to force a verdict. The floor is the Constitution enforcing "Evidence over opinion"; the fix is always more or better-classed evidence.

### Failure modes

- Reading abstention as failure and retrying with the same evidence. Same class in, same abstention out.
- Fixing the parser and thinking you fixed the evidence: the same run also surfaced LES-018 (fenced-JSON parse defect, 3 of 4 agents degraded to a prose fallback at confidence 0.05). Re-parsing recovered real content but the aggregate still abstained (about 0.16), because the evidence-class problem is independent of the parse problem. Separate the two diagnoses.
- Skipping classification because the question "seems structural". Adoption questions frequently masquerade as structural ones ("scan pydantic-ai so we can decide").

## 8. Task tier guide

Routing home is aos-model-routing; these labels are operator guidance, candidate status as of 2026-07-06 (Haiku is being introduced, not yet standard).

| Task in this skill's scope | Tier |
|----------------------------|------|
| Run the reality harness and diff output against the documented expected rankings | Haiku |
| Run `pytest -m embedder` locally and report pass/fail with output | Haiku |
| Back-derive a score formula's behavior from recorded confidences (Recipe 1 steps 1 to 3) | Sonnet |
| Write marker-gated hermetic/real test pairs for a new heavy dependency | Sonnet |
| Draft predicted numbers for a work package Verification section | Sonnet |
| Design a new calibration formula or scoring blend (bounded alternative, Recipe 1 step 4) | Opus |
| Classify a novel question's evidence class and decide whether to gate a Council run | Opus |
| Promote a scratch reality test into a committed regression gate with tolerances | Opus |

## 9. Common mistakes

- Rescaling instead of recalibrating: multiplying Jaccard by 10 would have made the numbers bigger and still meaningless. Fix the denominator, not the scale.
- Surfacing a raw cosine anywhere user-visible. LES-023's closing rule: keep reported confidence coverage-like and calibrated, even in the embeddings tier (enforced in `transfer.py`).
- Trusting local gates for workflow YAML. ruff, compileall, compose config, and pytest all pass on a broken `ci.yml` (LES-027). Check the actual CI run for the head SHA.
- Writing a reality test without committed expectations, or with float-exact expectations. Both kill it as a gate.
- Running the Council on an adoption question with only a target-repo scan, then "fixing" the abstention by rerunning. Gather the named evidence classes first.
- Bypassing governance to land a "proven" result faster. Nothing in this skill ever justifies skipping PR Guardian, the head-SHA-pinned manual merge gate, or the RFC process; a BLOCK is fixed in code (the audited record: no substantive code BLOCK has ever been overridden; see aos-change-control section 8 for the exact override-token history).

## 10. Provenance and maintenance

Authored 2026-07-06 on branch laptop/aos-selfheal-doc-loop (HEAD AOS-SELFHEAL-001, since merged as PR #80; nothing in this skill depends on it). AOS-EMBED-002 (PR #73) and AOS-TRANSFER-002 (PR #66) verified merged to origin/main as of 2026-07-06.

Derived from:

- `knowledge/wiki/lessons/LES-019.md`, `LES-022.md`, `LES-023.md`, `LES-027.md`
- `packages/aos_core/aos_core/services/transfer.py`
- `packages/aos_core/aos_core/embeddings/__init__.py`
- `scripts/reality_test_distillation.py`
- `apps/api/tests/test_embeddings.py`, `apps/api/tests/test_fastembed_real.py`
- `apps/api/requirements-embeddings.txt`, `.github/workflows/ci.yml` (job `embedder-tests`)
- `.archetype/work/AOS-TRANSFER-002.md`, `AOS-EMBED-002.md`, `AOS-DISTILL-003.md`
- `docs/rfc/RFC-0010-Embedding-Relevance-Tier-Transfer-Engine.md`
- `docs/COUNCIL_REALRUN_PYDANTIC_AI.md`, `.archetype/council/pydantic-ai-review.json`

Re-verification commands (run from repo root):

| Fact | Re-verify with |
|------|----------------|
| Coverage formula and no-raw-cosine rule | `grep -n "covered\|_W_SEM\|LES-023" packages/aos_core/aos_core/services/transfer.py` |
| Blend weights 0.6/0.4 | `grep -n "_W_SEM\|_W_COV" packages/aos_core/aos_core/services/transfer.py` |
| LES-023 numbers (0.0147, 0.108, 0.333, 0.800) | `grep -n "0.0147\|0.108\|0.333\|0.800" knowledge/wiki/lessons/LES-023.md .archetype/work/AOS-TRANSFER-002.md` |
| Reality-harness expected rankings and usage | `sed -n '1,46p' scripts/reality_test_distillation.py` |
| Embedder marker registration | `grep -n "embedder" pyproject.toml` |
| Embedder CI job, model cache, no-torch assert | `grep -n -A 30 "embedder-tests:" .github/workflows/ci.yml` |
| fastembed pin | `cat apps/api/requirements-embeddings.txt` |
| Seam imports nothing heavy | `PYTHONPATH=apps/api:packages/aos_core pytest apps/api/tests/test_embeddings.py -q` (or `pip install -e ./packages/aos_core` first, as CI does; with bare `PYTHONPATH=apps/api` collection fails on ModuleNotFoundError: aos_core) |
| Council abstention numbers (0.0375, floor 0.35) | `grep -n "0.0375\|0.35" docs/COUNCIL_REALRUN_PYDANTIC_AI.md` |
| LES-019 still open | `grep -n -A 2 "## Status" knowledge/wiki/lessons/LES-019.md` |
| PR #73 / #66 merge state | `gh pr view 73 --json state,mergedAt; gh pr view 66 --json state,mergedAt` |
