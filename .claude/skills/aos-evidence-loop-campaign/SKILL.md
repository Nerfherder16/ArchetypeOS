---
name: aos-evidence-loop-campaign
description: Use when the Agent Council returns verdict "Insufficient evidence", confidence near zero (0.0375 in the pydantic-ai run), or follow_up items naming missing evidence classes; when a drafted Decision is stuck in needs_evidence and approve returns 409; when working LES-019 (evidence class mismatch, "scan is not research"); or when asked to close the evidence assembly loop so the Council can answer adoption questions instead of abstaining.
---

# AOS Evidence Loop Campaign (LES-019)

## 1. Overview

This is a decision-gated, executable campaign for the hardest live problem in ArchetypeOS as of 2026-07-06: **the evidence assembly loop is open**.

Background, stated plainly:

- The Agent Council (four personas plus a rule-based Final Judge, RFC-0005) correctly **abstains** when the evidence it is fed is the wrong class for the question. In the first real run (question: "should we adopt pydantic-ai?", evidence: a structural scan of pydantic-ai's own repo) it returned verdict `Insufficient evidence` at confidence `0.0375`.
- The Council's `follow_up` output **names exactly which evidence classes are missing** (research notes, fitness comparison, security review, prior decisions).
- **Nothing yet gathers that evidence and re-runs the Council.** The `follow_up` list is produced by `synthesize_verdict` in `packages/aos_core/aos_core/services/council.py` and copied into the drafted Decision's `consequences` by `services/decisions.py`, and that is where the chain ends (verified by grep: no other consumer).

Closing that gap, manually first, then durably, is this campaign. Success is measured in **verdict, confidence, and corpus coverage numbers**, never judged by eye.

Key terms, defined once:

| Term | Meaning |
|------|---------|
| Agent Council | Four LLM personas (research_librarian, architecture_cartographer, technology_fitness_judge, security_agent) plus a deterministic Final Judge. Advisory only: it drafts, never approves. |
| Evidence class | The *kind* of durable record fed to an agent: research note, decision, DNA/scan signal, distillation page. LES-019: the class must match the question class. |
| Abstention floor | `ABSTAIN_CONFIDENCE = 0.35` and `MIN_EVIDENCE = 1` in `packages/aos_core/aos_core/services/council.py`. Below either, verdict is forced to `Insufficient evidence`. |
| Evidence selector | Per-persona function in `services/council.py` that reads DB rows and builds the evidence array for that agent's prompt. |
| needs_evidence | Decision status given to a draft made from an abstained review. Not approvable (HTTP 409). |

## 2. When to use / When NOT to use

**Use this skill when:**

- A council review came back `Insufficient evidence` and you need to get to a substantive verdict the governed way.
- `POST /decisions/{id}/approve` returned 409 with "drafted from an abstained council review".
- You are asked to design or build the durable evidence-gathering loop (Phase 4 below).
- You are closing lesson LES-019.

**Do NOT use this skill for:**

- Understanding evidence classes, distillation tiers, or council internals in general: see **aos-knowledge-transfer-reference**.
- A council run that errors, hangs, or returns garbage (as opposed to abstaining correctly): see **aos-debugging-playbook**.
- Standing up the stack from scratch or endpoint reference: see **aos-build-run-and-operate**.
- How lessons and RFCs are authored when you record results: see **aos-docs-and-lessons**.
- The change-gating rules (Guardian, merge gate, RFC triggers) that govern promotion: see **aos-change-control**.
- The general hunch-to-accepted-result method this campaign instantiates: see **aos-research-methodology**.
- The history of how LES-019 arose (LES-018 sibling parse defect, LES-021 prompt isolation): see **aos-failure-archaeology**.

## 3. Phase 0: Preflight

Environment: Docker Compose stack (Postgres pgvector, Redis, API :8000, worker, scheduler, web :5173). All commands run from the repo root.

```bash
cd /path/to/ArchetypeOS
docker compose up -d --build
curl -s http://localhost:8000/health
```

**EXPECTED:** `{"status":"ok","api":true,"database":true,"redis":true}`. Anything `degraded` means Postgres or Redis is not reachable; fix before proceeding (aos-build-run-and-operate).

Read the historical artifact (committed evidence of the first real run):

```bash
python3 -c "import json; d=json.load(open('.archetype/council/pydantic-ai-review.json')); print(d['verdict'], d['confidence'], d['provider'], d['wall_time_s']); [print('-', f) for f in d['follow_up']]"
```

**EXPECTED (exact values from the artifact, verified 2026-07-06):**

- `verdict`: `"Insufficient evidence"`
- `confidence`: `0.0375`
- `provider`: `"claude_code"`, `wall_time_s`: `132`
- `follow_up` (8 items). The first two are the generic floor instructions; the six `Verify:` items are the missing-evidence specification, including:
  - "Verify: The evidence array provided is empty (zero research notes or recorded decisions)."
  - "Verify: No prior research notes on pydantic-ai exist in the supplied corpus to assess production-readiness."
  - "Verify: No technology-fitness comparison (e.g., vs. LangChain, instructor, raw provider SDKs, or a custom abstraction) was supplied."
  - "Verify: No security review or vulnerability/dependency-risk data for pydantic-ai was supplied."

That `follow_up` list **is the specification** for the evidence corpus in Phase 2. Do not edit this artifact; it is captured evidence.

**GATE 0:** health OK and artifact readable with the values above. If the artifact values differ from the above, the file changed since 2026-07-06: re-read it and treat ITS contents as ground truth.

## 4. Phase 1: Reproduce the abstention

Two lanes. The deterministic lane is hermetic and always available; the real lane reproduces the actual LES-019 signature.

### Lane A: deterministic provider (compose stack as-is)

The compose stack runs `DeterministicProvider` (compose sets no `LLM_PROVIDER`; the `Settings.llm_provider` default is `"deterministic"`, verified in `packages/aos_core/aos_core/config.py` and `docker-compose.yml`).

```bash
# 1. Create a throwaway project
PROJECT_ID=$(curl -s -X POST http://localhost:8000/projects \
  -H 'Content-Type: application/json' \
  -d '{"name": "les019-campaign"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

# 2. Enqueue a council review (this is the real API: it returns a Job, not a review)
JOB_ID=$(curl -s -X POST "http://localhost:8000/projects/$PROJECT_ID/council-reviews" \
  -H 'Content-Type: application/json' \
  -d '{"question": "Should ArchetypeOS adopt pydantic-ai as the foundation for its Agent Council provider abstraction?"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

# 3. Poll the job until completed, then read the review
curl -s "http://localhost:8000/jobs/$JOB_ID"          # repeat until status == "completed"
REVIEW_ID=$(curl -s "http://localhost:8000/jobs/$JOB_ID" | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['review_id'])")
curl -s "http://localhost:8000/council-reviews/$REVIEW_ID" | python3 -m json.tool
```

**EXPECTED (fresh project, zero evidence):** `verdict = "Insufficient evidence"`, `confidence = 0.0`, all four `agent_outputs` have `status = "Needs Evidence"` and empty `evidence`, and `follow_up` starts with "Gather primary evidence for this project...". This is the evidence-less abstention branch, also covered by the API test suite.

**Executed simulation results (run 2026-07-06 against the source with `DeterministicProvider` piped through `_build_prompt` -> `_parse_agent_output` -> `synthesize_verdict`):**

| Corpus fed | Verdict | Confidence |
|------------|---------|-----------|
| Empty (all four agents) | Insufficient evidence | 0.0 |
| Thin scan-only (2 architecture + 3 fitness DNA items; librarian and security empty) | Insufficient evidence | 0.325 |
| Rich scan-only (4 architecture + 4 fitness DNA items; librarian and security empty) | **Accept** | 0.40 |
| Scan + research corpus (3 notes/decisions to librarian, 1 security decision) | Accept | 0.625 |

Note the third row: with a rich enough scan, the deterministic tier **clears the floor and says Accept on the wrong evidence class**, because it counts evidence and does not judge class. That is the deterministic analogue of the LES-019 category error and is one of the fenced-off wrong paths (Section 8).

### Lane B: real provider (claude_code) on an authed node

The real abstention signature (persona reasoning that names the missing classes, like the artifact) needs `ClaudeCodeProvider`, which shells to the local `claude` CLI with subscription auth. Two hard constraints, both verified in source:

1. `docker-compose.yml` does **not** plumb `LLM_PROVIDER` into any service (0 occurrences), and the worker image has no `claude` binary. The compose worker is always deterministic.
2. Therefore the real lane runs the worker **on the host** (the pattern `docs/LLM_PROVIDER_ABSTRACTION.md` describes: operator sets `LLM_PROVIDER=claude_code` on an authed node).

```bash
# Stop the containerized worker so it cannot race you for the queue
docker compose stop worker

# Host worker with the real provider (Python 3.12 venv)
python3 -m venv .venv && source .venv/bin/activate
pip install -e packages/aos_core -r apps/worker/requirements.txt
cd apps/worker
LLM_PROVIDER=claude_code \
DATABASE_URL='postgresql+psycopg://archetypeos:archetypeos@localhost:5432/archetypeos' \
REDIS_URL='redis://localhost:6379/0' \
python -m app.worker
```

Then enqueue exactly as in Lane A. Budget roughly 2 to 3 minutes wall time per review (the historical run took 132 s for 4 sequential live calls). Restart the compose worker afterward: `docker compose start worker`.

**EXPECTED (project whose only evidence is a structural scan of the target repo):** abstention, near-zero confidence, `follow_up` containing `Verify:` items naming research notes, a fitness comparison, and a security review, i.e. the artifact's signature. To supply that scan corpus first, onboard and scan the target repo via `scripts/onboard_repo.sh <git-url> <name>` and the register/scan API calls it prints.

### GATE 1

- **Abstains as expected:** proceed to Phase 2.
- **Does NOT abstain (Lane B, scan-only corpus, substantive verdict):** the provider or the evidence handling changed since 2026-07-06. STOP. Diff `packages/aos_core/aos_core/services/council.py` (selectors, `ABSTAIN_CONFIDENCE`, `synthesize_verdict`) and `packages/aos_core/aos_core/llm/__init__.py` against git history, and work it through **aos-debugging-playbook** before continuing. A Council that answers adoption questions from scans is a regression, not a win.
- **Job fails / errors:** worker-side failure (missing claude binary raises `RuntimeError: claude binary not found`; timeout raises after 120 s). Fix via aos-debugging-playbook; this is not the LES-019 phenomenon.

## 5. Phase 2: Assemble the evidence corpus

Map each class the Council asked for to its real ingestion mechanics. Critical selector facts (verified in `services/council.py`):

- `research_librarian` reads: research notes + decisions (latest 10 each) + repository distillation pages (`page_type="repository"`).
- `security_agent` reads: DNA `risk_flags` + decisions whose title/context contains one of `security, auth, secret, vuln, cve, encrypt`. **It does NOT read research notes.**
- `architecture_cartographer` and `technology_fitness_judge` read only architecture nodes and DNA fields. Research notes never reach them under current selectors. This asymmetry is exactly why Phase 4 exists.

| Evidence class asked for | Mechanism | Endpoint / path |
|--------------------------|-----------|-----------------|
| Research notes (production-readiness) | ResearchNote row | `POST /projects/{id}/research-notes` |
| Technology-fitness comparison | ResearchNote row (no dedicated model exists) | same endpoint |
| Security / dependency-risk review | Decision row with a security keyword in title or context (so the security_agent selector picks it up) plus optionally a ResearchNote for the librarian | `POST /projects/{id}/decisions` |
| Prior decisions | Decision row | `POST /projects/{id}/decisions` |
| Knowledge pages / distillations | **No create API.** Vault file in the repo checkout, then sync. Lessons: `knowledge/wiki/lessons/`, ADRs: `knowledge/wiki/decisions/`, repo distillations: `knowledge/wiki/repositories/` | file + `POST /knowledge/sync` |

Copy-paste corpus (edit content to be real research, not filler; the Council's product is only as good as this corpus):

```bash
# Research note: production-readiness
curl -s -X POST "http://localhost:8000/projects/$PROJECT_ID/research-notes" \
  -H 'Content-Type: application/json' -d '{
  "title": "pydantic-ai production-readiness research",
  "question": "Is pydantic-ai production-ready for the council provider abstraction?",
  "summary": "Findings from release history, API stability, maintainer profile.",
  "sources": ["https://github.com/pydantic/pydantic-ai/releases"],
  "findings": ["1.0 stable milestone reached 2025", "maintained by Pydantic Labs"],
  "freshness": "2026-07",
  "confidence": 0.6}'

# Research note: fitness comparison
curl -s -X POST "http://localhost:8000/projects/$PROJECT_ID/research-notes" \
  -H 'Content-Type: application/json' -d '{
  "title": "Fitness comparison: pydantic-ai vs LangChain vs instructor vs raw SDKs vs custom seam",
  "summary": "Tradeoff matrix against the existing aos_core.llm Provider protocol.",
  "findings": ["current custom seam is 2 backends behind a Protocol", "pydantic-ai overlaps the seam, does not extend it"],
  "confidence": 0.5}'

# Security review, recorded as a Decision so the security_agent selector sees it
curl -s -X POST "http://localhost:8000/projects/$PROJECT_ID/decisions" \
  -H 'Content-Type: application/json' -d '{
  "title": "Security review: pydantic-ai dependency and CVE posture",
  "context": "Supply-chain review: dependency tree, CVE history, secret handling of pydantic-ai.",
  "decision": "Record security findings as evidence for the adoption question.",
  "evidence": [{"type": "external", "ref": "CVE scan output"}],
  "confidence": 0.5}'
```

**Deterministic lane only: also supply scan/DNA evidence.** The GATE 2 minimum corpus (2 research notes + 1 security decision) alone cannot clear the floor under `DeterministicProvider`: architecture_cartographer and technology_fitness_judge read only ArchitectureNode rows and DNA fields, which a fresh project has none of, so those two agents stay at confidence 0.0 and the aggregate tops out at (0.7 + 0.5 + 0 + 0) / 4 = 0.30 < 0.35, still an abstention. Before the Phase 3 re-run, onboard and scan a repo into `$PROJECT_ID` (`scripts/onboard_repo.sh <git-url> <name>`, or `POST /repositories` then `POST /repositories/{id}/scan`) so the architecture and fitness selectors have evidence; the cleared-floor simulation row above ("Scan + research corpus", 0.625) included scan evidence for exactly this reason.

**Measure corpus coverage before re-running** (the coverage number is a first-class success metric):

```bash
curl -s "http://localhost:8000/projects/$PROJECT_ID/research-notes" | python3 -c "import sys,json; print('research_notes:', len(json.load(sys.stdin)))"
curl -s "http://localhost:8000/projects/$PROJECT_ID/decisions" | python3 -c "import sys,json; print('decisions:', len(json.load(sys.stdin)))"
```

**GATE 2:** at least one row per evidence class the `follow_up` named (research note count >= 2 covering readiness + fitness, decision count >= 1 with a security keyword). If a class has no ingestion path (e.g. you want a distillation page), say so explicitly in your campaign notes and use the vault-file route; do not fake it through the wrong model.

## 6. Phase 3: Re-run and measure (predictions FIRST)

Write predictions down before enqueueing. The threshold is justified from the scoring source, not chosen by feel:

- `ABSTAIN_CONFIDENCE = 0.35` and `MIN_EVIDENCE = 1` (`packages/aos_core/aos_core/services/council.py`, module constants near the top). Abstention fires when aggregate confidence < 0.35 OR total evidence items < 1. Therefore the minimum claim of success is: **verdict != "Insufficient evidence" and confidence >= 0.35.**

**Predictions (deterministic lane, derived and executed against source 2026-07-06):**

1. Verdict flips from `Insufficient evidence` to a substantive verdict (one of `Accept`, `Accept with warnings`, `Reject`, `Escalate to human`).
2. Confidence >= 0.35. Executed simulation with scan + 3 librarian items + 1 security decision gave `Accept` at `0.625`.
3. `research_librarian` and `security_agent` outputs change from `status="Needs Evidence"` / empty evidence to `status="Complete"` with nonzero evidence arrays.

**Predictions (real claude_code lane):** same direction (abstention lifts, confidence clears 0.35, follow_up items shift from "Verify: ... was supplied" gaps to "Address: ..." concerns), but the exact confidence is model-dependent. This lane's numbers are an **open, candidate result as of 2026-07-06**: no cleared-floor real run has been captured yet. Capture yours to `.archetype/council/` style evidence if it is campaign-significant.

Re-run and compare:

```bash
JOB_ID=$(curl -s -X POST "http://localhost:8000/projects/$PROJECT_ID/council-reviews" \
  -H 'Content-Type: application/json' \
  -d '{"question": "Should ArchetypeOS adopt pydantic-ai as the foundation for its Agent Council provider abstraction?"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
# poll GET /jobs/$JOB_ID until status == "completed", then extract the NEW review id
# (do not reuse the Phase 1 REVIEW_ID, or you will re-read the old abstained review):
REVIEW_ID=$(curl -s "http://localhost:8000/jobs/$JOB_ID" | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['review_id'])")
curl -s "http://localhost:8000/council-reviews/$REVIEW_ID" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('verdict:', d['verdict'], '| confidence:', d['confidence'])
for a in d['agent_outputs']:
    print(f\"  {a['agent_name']}: status={a['status']} evidence_items={len(a['evidence'])} confidence={a['confidence']}\")"
```

**GATE 3:** compare observed vs predicted, number by number.

- **All three predictions hold:** the manual loop is closed for this question. Continue: `POST /council-reviews/{review_id}/draft-decision` now yields a Decision with `status="draft"` (not `needs_evidence`), which a named human may approve via `POST /decisions/{id}/approve` with body `{"approver": "<name>", "rationale": "..."}`. Record the run per aos-docs-and-lessons; this is the closure evidence LES-019's status line asks for ("consumed when the decision loop feeds the Council a research/decision corpus").
- **Verdict flips but confidence < 0.35:** contradiction; abstention would still fire. Re-read the review JSON, something is off in your reading or the floor logic changed. Verify with `grep -n "ABSTAIN_CONFIDENCE" packages/aos_core/aos_core/services/council.py`.
- **Still abstains:** count evidence per agent in `agent_outputs`. If librarian/security evidence arrays are still empty, your corpus rows did not reach the selectors (wrong project_id, or security decision missing a keyword); fix the corpus. If librarian/security arrays are nonzero but the architecture/fitness arrays are empty, the project lacks scan/DNA evidence (the GATE 2 minimum corpus alone aggregates to 0.30, below the 0.35 floor); onboard and scan a repo into the project, not more corpus rows. Either way, do NOT touch the floor.

## 7. Phase 4: Durable-loop solution menu (ranked)

The campaign above is manual. The durable closure is a new engine capability and must go through the RFC process first (Section 9). Options, ranked by recommended order:

### (c) Documented manual protocol: the floor (do first, effectively done by running this skill)

Phases 2 and 3 above, executed by an operator or a session, with the run recorded.

- **Theory obligation:** none new; it instantiates the existing Phase C loop (Council -> gather/record research -> draft decision -> human approve).
- **Effort:** hours (documentation + one recorded cleared-floor real run).
- **Risk:** low. It does not scale and depends on operator discipline, but it cannot corrupt governance.

### (a) follow_up-driven evidence selector inside the council service

On re-run, a selector (or a pre-run step) parses the prior abstained review's `follow_up`, maps named classes to queries (research notes matching the question topic, keyword-matched decisions, distillation pages), and widens what each persona receives. Could also route research notes to fitness/architecture personas for adoption-class questions (today they only see DNA/nodes).

- **Theory obligations:** (1) a question-class taxonomy (adoption vs structural vs security) with a documented classifier, because "match evidence class to question class" needs the question class to be machine-readable; (2) proof that widened selectors cannot re-introduce the category error in reverse (structural questions drowning in research prose); (3) determinism preserved for the CI provider (equal inputs, equal outputs).
- **Effort:** days (selector code, taxonomy, tests mirroring the existing selector tests).
- **Risk:** medium. Touches the governed synthesis path; a bad mapping silently changes verdicts. Gate with golden tests over captured reviews.

### (b) A librarian agent wired to gather named classes

An agent (worker job or scheduled task) that consumes an abstained review, executes research to produce the missing ResearchNote/Decision rows, then re-enqueues the council review.

- **Theory obligations:** everything from (a), plus: (1) an autonomy boundary consistent with the Constitution (the agent writes evidence rows, it must never approve decisions or lower floors); (2) an evidence-provenance standard so gathered notes are auditable (sources, freshness, confidence fields are already in the model, they must be mandatory here); (3) a loop-termination rule (max re-runs, else you build an abstain/gather/abstain spinner).
- **Effort:** weeks (new job type, provider usage policy, provenance rules, e2e tests).
- **Risk:** high. Autonomous evidence generation feeding a governed verdict is the exact place self-persuasion bugs live. Do not attempt before (a) exists and (c) has produced at least one recorded cleared-floor real run to test against.

## 8. Wrong paths, fenced off

| Wrong path | Why it is wrong | Verified fact |
|------------|-----------------|---------------|
| Feeding structural scans to adoption questions and shipping the verdict | Category error, LES-019 itself. The deterministic tier will even say `Accept` at 0.40 on a rich scan-only corpus (executed simulation, Section 4) because it counts evidence, it does not judge class. | `knowledge/wiki/lessons/LES-019.md`; simulation vs `services/council.py` |
| Lowering `ABSTAIN_CONFIDENCE` or `MIN_EVIDENCE` to force a verdict | Constitutional abstention is the feature. Governance-parameter changes are RFC-class changes; forcing a verdict by tuning the floor is manufacturing evidence. | constants in `services/council.py`; `docs/RFC_PROCESS.md` lists governance changes as RFC-required |
| Bypassing the decision-approval block on abstention | `approve_decision` returns **HTTP 409** for a `needs_evidence` draft, with a message naming the gather/re-run/re-draft path. That block IS the LES-019 teeth. Route around it and the whole loop is theater. | `packages/aos_core/aos_core/services/decisions.py` (409 branch) |
| Skipping the RFC for the durable loop | Options (a)/(b) are new engine/agent capability: explicitly RFC-required categories ("new engines", "new agents", "autonomous action capabilities"). | `docs/RFC_PROCESS.md` |
| Editing `.archetype/council/pydantic-ai-review.json` | It is captured evidence of the first real run. Evidence is append-only; new runs get new artifacts. | `docs/COUNCIL_REALRUN_PYDANTIC_AI.md` |
| Bypassing PR Guardian or the manual merge gate to land any of this | Never. No substantive code BLOCK (tests, secrets, metadata, acceptance) has ever been overridden; BLOCKs are fixed in code. Override tokens in merged PR bodies were warn acknowledgments or no-op/early suppressions. | verified record: aos-change-control section 8 |

## 9. Promotion path (manual protocol -> engine capability)

1. **RFC** per `docs/RFC_PROCESS.md` (Draft -> Council Review -> Final Judge -> Accepted), with the required sections including Alternatives (this menu), Evidence (your Phase 1/3 numbers and the artifact), and Acceptance criteria in verdict/confidence/coverage numbers.
2. **Work package** in `.archetype/work/AOS-*.md` (strict subset of the mature-state target; no scaffolding).
3. **Tests first**, hermetic against `DeterministicProvider` (the existing council/decision test suites are the pattern).
4. **Local gate** `scripts/pre_pr_guardian.sh`, then PR Guardian, then the head-SHA-pinned manual merge gate. No shortcuts.
5. **Reality-test evidence**: one captured real (`claude_code`) run before/after, committed as an artifact plus an honest evaluation doc, mirroring `docs/COUNCIL_REALRUN_PYDANTIC_AI.md`.
6. **Close LES-019** in the same change set, citing the cleared-floor run (RFC-0004 discipline; see aos-docs-and-lessons).

## 10. Task tier guide

Routing home is **aos-model-routing**; these labels are operator guidance, candidate status as of 2026-07-06.

| Task in this campaign | Tier |
|-----------------------|------|
| Polling jobs, running the curl phases, quoting the artifact, coverage counts | Haiku |
| Writing the corpus content (research notes, security-review decision) with real sources | Sonnet |
| Executing the full campaign end to end and comparing predictions vs observed | Sonnet |
| Interpreting a GATE 1 failure (provider/selector regression triage) | Opus |
| Phase 4 design work: taxonomy, selector design, the RFC itself | Opus |

## 11. Common mistakes

- **Expecting `POST /projects/{id}/council-reviews` to return a review.** It returns a Job; the review id is in the completed job's `result.review_id`.
- **Running the real lane while the compose worker is up.** Both consume the same Redis queue; the containerized (deterministic) worker will steal your job. `docker compose stop worker` first.
- **Setting `LLM_PROVIDER=claude_code` on the compose worker.** The env var is not plumbed in `docker-compose.yml` and the image has no `claude` binary. Real lane = host worker.
- **Expecting the security_agent to see research notes.** It reads DNA risk flags and keyword-matched decisions only. Record the security review as a Decision with a security keyword in title/context.
- **Treating a deterministic-lane `Accept` as substantive validation.** It validates plumbing and floor math only; the deterministic provider does not judge evidence class or content.
- **Creating knowledge pages via API.** There is no create endpoint; pages come from vault files via `POST /knowledge/sync`.
- **Stating predictions after the run.** GATE 3 is meaningless unless predictions were written down before enqueueing.

## 12. Provenance and maintenance

Authored 2026-07-06 against branch `laptop/aos-selfheal-doc-loop` (HEAD = AOS-SELFHEAL-001, since merged as PR #80; nothing in this skill depends on that change set). All endpoints, constants, status codes, and artifact values were verified against source; the deterministic-lane verdict/confidence table was produced by executing the real provider + judge code paths.

Derived from: `.archetype/council/pydantic-ai-review.json`, `knowledge/wiki/lessons/LES-019.md`, `docs/COUNCIL_REALRUN_PYDANTIC_AI.md`, `packages/aos_core/aos_core/services/council.py`, `packages/aos_core/aos_core/services/decisions.py`, `packages/aos_core/aos_core/llm/__init__.py`, `packages/aos_core/aos_core/config.py`, `apps/api/app/routes/council.py`, `apps/api/app/routes/decisions.py`, `apps/api/app/routes/knowledge.py`, `apps/api/app/schemas.py`, `apps/worker/app/worker.py`, `docker-compose.yml`, `docs/DECISION_LIFECYCLE.md`, `docs/RFC_PROCESS.md`, `docs/LLM_PROVIDER_ABSTRACTION.md`, `.archetype/work/AOS-COUNCIL-PHASEA.md`, `.archetype/work/AOS-COUNCIL-PHASEC.md`.

Re-verification commands for every fact that may drift:

| Fact | Re-verify with |
|------|----------------|
| Artifact verdict / confidence 0.0375 / follow_up | `python3 -c "import json; d=json.load(open('.archetype/council/pydantic-ai-review.json')); print(d['verdict'], d['confidence'])"` |
| Abstention floor 0.35 / MIN_EVIDENCE 1 | `grep -n "ABSTAIN_CONFIDENCE\|MIN_EVIDENCE" packages/aos_core/aos_core/services/council.py` |
| 409 on approving a needs_evidence draft | `grep -n "409" packages/aos_core/aos_core/services/decisions.py` |
| Council endpoints and payload shape | `grep -n "council-reviews\|CouncilReviewCreate" apps/api/app/routes/council.py apps/api/app/schemas.py` |
| Decision-loop endpoints | `grep -n "draft-decision\|/approve\|/reject" apps/api/app/routes/decisions.py` |
| Security-agent keyword list | `grep -n "security\", \"auth" packages/aos_core/aos_core/services/council.py` |
| No LLM_PROVIDER in compose / deterministic default | `grep -c LLM_PROVIDER docker-compose.yml; grep -n llm_provider packages/aos_core/aos_core/config.py` |
| follow_up still has no automated consumer | `grep -rn "follow_up" packages/aos_core/aos_core/services/ apps/worker/app/ \| grep -v test` |
| LES-019 still open | `grep -n "^open" -A0 knowledge/wiki/lessons/LES-019.md; grep -n LES-019 knowledge/wiki/lessons/index.md` |
| Research-note / decision payload fields | `grep -n "class ResearchNoteCreate\|class DecisionCreate" -A 10 apps/api/app/schemas.py` |
