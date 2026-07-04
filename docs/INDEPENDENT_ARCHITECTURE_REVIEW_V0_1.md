# Independent Architecture Review — ArchetypeOS v0.1

Status: Delivered
Reviewer: Independent engineering consulting review (commissioned)
Date: 2026-07-04
Scope: Entire repository at commit `fb30b80` — all 76 docs, 3 RFCs, all application code, CI, scripts, registries, knowledge vault
Method: First-hand source inspection of every implementation file; systematic critical reading of every design document; cross-checks against `git` history. Evidence is cited as `file:line`. No claim below is made without repository evidence.

---

## 1. Executive Summary

ArchetypeOS is an ambitious, internally coherent **vision** wrapped around a very small **system**. The repository contains roughly 76 design documents describing ~30 engines, a 10-agent council, a communication bus, an authority engine, a distributed runtime, and a self-learning loop — and approximately **1,100 lines of application code** that implement a project/repository CRUD API, a file-extension counter labeled "repository scan," a worker whose only job handler returns a hard-coded `"test job completed"` message (`apps/worker/app/worker.py:41`), and a 71-line health-check web page. The design-to-implementation ratio is approximately 20:1.

That ratio, by itself, is not the problem — early projects are allowed to be mostly design. The problems this review found are structural:

1. **The documentation is written in confident present tense about systems that do not exist**, and in an agent-driven repository the documentation *is* the agents' world model. This is not a cosmetic issue; it is an active correctness hazard.
2. **The governance layer — the project's stated differentiator — is ~95% prose.** Exactly one gate is machine-enforced (the deterministic PR Guardian), its most important input (verification status) is self-attested and gameable, and the repo's own docs admit that branch protection is not technically enforceable on the current GitHub plan (`docs/BRANCH_PROTECTION.md:91`).
3. **The coordination substrate — six hand-edited markdown state files — has already failed at N=1.** All four state trackers (`CURRENT_STATE.md`, `ACTIVE_WORK.md`, `HANDOFF.md`, `RECENT_CHANGES.md`) currently contradict `git`: they describe the already-merged PR #8 as "in review / verification pending." The anti-context-rot machinery has itself rotted, with a single author, before a single autonomous agent has touched it.
4. **The architecture as specified cannot scale past a handful of agents.** A single orchestrator, a single Final Judge, a single human approver on the hot path of every write, and markdown files as shared mutable state produce hard serialization points and O(N²) merge conflicts. The design would strain at 5 agents, fail at 20, and is not in the design space of 100+.
5. **Nothing has ever been verified running locally.** Every verification record in the repo is "Level 1/Level 3 via GitHub CI; local Level 2 execution unavailable" (`docs/ACTIVE_WORK.md:33,64,92`). For a self-described local-first platform, `docker compose up` on the target machine has never been demonstrated.

The strategy "governance before automation" is correct. The finding of this review is that ArchetypeOS currently has neither: the automation is a stub, and the governance is a constitution without an enforcement branch. The path forward is not more design — it is a documentation freeze, a reconciliation pass, machine enforcement of the three governance rules that matter, and **one intelligence loop proven end-to-end**.

The vision is worth building. The current trajectory — accreting engine specifications faster than code — will not build it.

---

## 2. Architectural Strengths

These are real, verified in source, and worth protecting:

1. **The deterministic PR Guardian is genuinely good engineering.** `tools/pr_guardian.py` (355 lines) enforces required files, secret patterns on added diff lines, test-changes-with-code-changes, docs-with-code, capability-map updates for new docs, runtime-junk blocking, and structured verification metadata — deterministically, without an LLM, with explicit override tokens that leave an audit string in the PR body. Most "AI governance" projects have nothing this concrete.
2. **CI is real and layered.** `.github/workflows/ci.yml` runs Guardian, ruff, compileall, pytest for API and worker, a web build, and a Docker Compose smoke test that polls `/health` and dumps logs on failure (`ci.yml:108-118`). This is a credible pipeline for the code that exists.
3. **Read-only-by-default is actually enforced in code** — the single place where a safety principle has teeth: `safe_repo_path` rejects path traversal (`apps/api/app/repository_scanner.py:32-39`), repository mounts are `:ro` (`docker-compose.yml:52,71`), and `Repository.is_read_only` defaults true (`apps/api/app/models.py:68`).
4. **"Durable artifacts over chat memory" is the right core principle.** Treating conversations as disposable and the repository as the source of truth (`docs/ORCHESTRATION_ENGINE.md:12`) gives auditability and session recovery that chat-memory systems lack. The principle is sound even though its current implementation (hand-edited markdown) is not.
5. **The relational schema shows real design maturity.** The `AuditMixin` (id/status/version/timestamps/actor/metadata on every table, `models.py:38-46`), and evidence/confidence fields on `Decision`, `ResearchNote`, `Recommendation`, `ArchitectureNode` encode the "evidence over opinion" constitution directly into the data model. It is over-built relative to the API (see Weaknesses), but the shape is right.
6. **Honest self-knowledge exists in places.** `docs/V0_1_SCOPE_LOCK.md` correctly defers voice, marketplace, simulation, GPU nodes; `docs/SELF_REVIEW_ARCHETYPEOS_REPOSITORY.md` correctly predicted scope creep and documentation fragmentation; `docs/BRANCH_PROTECTION.md:89-105` openly admits the merge gate is not technically enforced. The project can tell itself the truth — it just doesn't act on it consistently.
7. **Several design instincts are better than industry norm:** architecture stored as editable data rather than diagrams (`docs/ARCHITECTURE_STUDIO.md:41-42`); "do not hide disagreement" in the council dashboard (`docs/AGENT_COUNCIL_DASHBOARD.md:57`); verification statuses that include "Verification unavailable/blocked" as first-class, merge-blocking states; the voice safety ladder that treats spoken commands as draft intent.
8. **The scope-lock instinct.** The idea of a signed v0.1 scope with explicit out-of-scope lists and RFC-gated expansion is exactly what an autonomous-agent platform needs. (Its enforcement gap is covered below.)

---

## 3. Architectural Weaknesses

Organized by the review areas requested.

### 3.1 System architecture

- **The architecture document is not an architecture.** `docs/SYSTEM_ARCHITECTURE.md` is 55 lines of layer names and bullets. There are no interfaces, no data flows, no contracts between the Control Plane / Intelligence / Council / Execution layers, no failure-mode analysis, no capacity model. For a system intended to survive a decade, this is a table of contents, not a design.
- **Layering exists in prose only.** In code there is one FastAPI app, one stub worker, one React page. There is no module boundary corresponding to any documented layer; the "Intelligence Layer" has no code at all.
- **Dead schema:** 13 of 20 tables (`Decision`, `ResearchNote`, `Recommendation`, `KnowledgePage`, `Evaluation`, `Risk`, `Benchmark`, `Experiment`, `NightlyDigest`, `AuthorityGrant`, `ApprovalRecord`, `Agent`, `Engine`) have no endpoint, no writer, no reader. `main.py:12` imports 7 of 22 model classes. Schema shipped ~65% ahead of any feature, with **no migration tooling** (`create_all` only, admitted at `docs/V0_1_RUNTIME_FOUNDATION.md:94`) — guaranteeing painful schema churn.
- **The one intelligence output cannot be read back.** The scanner writes `ArchitectureNode`/`ArchitectureEdge` rows (`main.py:124-172`) but there is no GET endpoint for the graph and the web UI does not display it. The core loop is open-circuit.
- **The scan endpoint has a correctness bug:** every re-scan creates a new root node and a full new set of nodes/edges with no dedup or upsert — the "architecture graph" grows without bound on every scan. Scans also run synchronously (`rglob` over the whole repo) inside the request handler, which will block the API on any large repository.

### 3.2 Agent architecture

- **There is no agent runtime.** The 10 agents in `.archetype/agent_registry.json` are `{id, name, mission}` triples never loaded by code. The three agent `CLAUDE.md` files are prompt personas for a human to paste into sessions (`docs/SESSION_BOOTSTRAP.md:32-82` is literally a copy-paste prompt template). The `Agent` and `Engine` tables are dead.
- **The communication bus does not exist and has no chosen design.** `docs/AGENT_COMMUNICATION_BUS.md:71-73` concedes the current "bus" is GitHub issues and PR comments; lines 85-95 list six candidate transports without choosing one. The 20-field message schema is an unenforced bullet list; delivery semantics (ordering, acks, retries, at-least-once) are never mentioned.
- **The real queue loses jobs.** `worker.py:49` uses `brpop` (removes the id immediately); a crash before completion strands the job in `running` forever. No visibility timeout, no retry (the `attempts` counter is written and never read), no dead-letter queue, no idempotency keys, no hang detection. The `priority` column is ignored by the FIFO list.
- **Scaling analysis (5 / 20 / 100 / 1000 agents):**
  - **5 agents:** workable only because the human operator is the actual orchestrator. State-file merge conflicts already appear (the git log's "Reconcile … after rebase" commits at `94cbd40`, `a46af71` with one author).
  - **20 agents:** fails. Six shared markdown files under concurrent edit (`docs/HANDOFF.md:37` calls them "high-conflict"), a single human approving every write (`agents/UNIVERSAL_AGENT_CONTRACT.md:26-37` gates file writes, commits, pushes, and paid API calls on human approval), and a single orchestrator sequencing everything (`docs/ORCHESTRATION_ENGINE.md:66-79`).
  - **100–1000 agents:** not in the design space. Requires a broker with real delivery semantics, sharded orchestration, policy-based (not human-per-action) approvals, per-agent identity/budgets, and DB-backed state — none of which is designed, let alone built.
- **No failure model.** Nothing specifies what happens when an agent hangs, produces garbage, or exceeds authority. Garbage output is caught only if a human notices at PR review; runtime output validation does not exist.
- **No agent memory system.** Memory = re-reading ~10 prescribed markdown files each session. There is no retrieval, no relevance ranking, no per-agent state. The cold-start context tax grows with the repo forever.

### 3.3 Governance

- **The Constitution's canon is corrupted.** `docs/CONSTITUTION_AMENDMENTS.md` redefines Articles XVI–XIX to different topics than `docs/ENGINEERING_CONSTITUTION.md:99-121` already assigns those numbers — and the amendment topics duplicate existing Articles XIII–XVI. The promised "consolidation pass" would produce two Article XVIs. For a document positioned as supreme law, this is a severity-one defect.
- **The RFC process is violated by all three of its own RFCs.** Each omits ~6 of the 14 required sections (evidence, security impact, compliance, migration plan) and each carries a bare, undated, unattributed `Final Judge Verdict: Accepted` written by the same author as the proposal. The "Council" that reviews RFCs is referenced in 10 docs and defined in none.
- **The Authority & Approval Engine is 0% implemented.** Six action levels, grants, expiry, emergency stop, audit trail (`docs/AUTHORITY_APPROVAL_ENGINE.md`) — no code path reads or writes `AuthorityGrant`/`ApprovalRecord`. Meanwhile the scanner and worker act with zero authority mediation. The doc's own closing principle ("capability only as authority becomes trustworthy," line 159) is inverted in practice.
- **Verification is self-attested.** Guardian checks only that `Verification Status: <allowed value>` lines exist (`pr_guardian.py:132-136, 237-297`). Nothing cross-checks a claimed "Verified / Level 4" against actual CI conclusions or reviewer state. An author can type `Verified` with fabricated evidence and pass. Worse, editing a PR body does **not** re-trigger `pull_request` CI, so metadata can be honestly filled, checked, then edited afterward.
- **The merge gate is honor-system.** Branch protection cannot be enforced on a private free-plan repo (`docs/BRANCH_PROTECTION.md:91,104-105`); Guardian is PR-only (`ci.yml:17`), so direct pushes to `main` bypass it entirely; and a PR that weakens `pr_guardian.py` is reviewed only by the base version of itself with no CODEOWNERS to require a second set of eyes.
- **Decision memory (Constitution Article VI) is unimplemented in the Constitution's own repo:** no `docs/adr/` directory exists; `templates/adr.md` is unused; the `Decision` table is dead; nothing links PRs to decisions.

### 3.4 Knowledge system

- On disk, the knowledge vault is **four stub files totaling ~1.2 KB** (`knowledge/wiki/{hot,index,log,overview}.md`) and a manifest whose checksum is the literal string `"initial"` and whose graph-node list is empty. The ten domain subdirectories in `docs/KNOWLEDGE_VAULT_STRUCTURE.md:11-38` do not exist; `index.md`'s "catalog" entries are plain text, not links.
- **No retrieval exists.** The documented cascade (hot → index → graph search → embeddings) has no lexical index, no embeddings, no vector store, no `pgvector` dependency, no graph query API. Retrieval is "an agent opens files a human points at" — and even the cheap `hot.md`-first protocol recommended by the project's own review (`docs/KARPATHY_OBSIDIAN_REVIEW.md:149`) was never added to `CLAUDE.md`'s reading order.
- **No freshness mechanism.** `KnowledgePage` has no `last_verified` or freshness field; `ResearchNote.freshness` is free text; the code↔doc linkage that would make staleness detectable does not exist. A page written today is "valid" forever.
- **Single-file conflict magnets.** `hot.md`, `index.md`, and append-only `log.md` are global files every agent must read and update — guaranteed merge conflicts under any concurrency, unbounded growth over time.
- **Self-learning without evals.** The Nightly Self-Learning Loop calls itself "the eval, learning, and healing cycle" while no eval set, no metric, no groundedness check, and no scheduler exist. A learning loop with no measurement cannot learn.
- **System-of-record contradiction.** `docs/OBSIDIAN_GRAPHIFY_INTEGRATION.md:24-32` declares Postgres canonical, but `KnowledgePage` stores only a path and checksum — the truth lives in ungoverned markdown, the exact anti-pattern the project's own Karpathy review warns against (`KARPATHY_OBSIDIAN_REVIEW.md:256-262`).

### 3.5 Repository intelligence

- The Repository Intelligence Engine doc specifies 7 phases and an 18-point rubric; the implementation counts file extensions, matches 8 manifest filenames, flags committed `.env` files, and emits `repository —contains→ top-level-directory` edges with hard-coded `confidence: 0.65` (`repository_scanner.py:77-78`). This is `ls` with a Counter presented as an architecture graph.
- What elite organizations actually do here — and what is missing entirely: dependency-graph extraction from real import/call analysis (tree-sitter / language servers), ownership and hotspot analysis from git history, API-surface extraction, build/test topology, security posture (lockfile audit, SAST), and incremental re-scan with content hashing. None is designed to buildable depth.
- Repository DNA confidence (0.65) and evidence ("read-only repository scanner") are hard-coded, which quietly violates Constitution Article XII (metrics must not be manipulated) — the number conveys no information.

### 3.6 Verification

- Strengths acknowledged above (deterministic Guardian, layered CI, honest verification-status vocabulary). The failures: self-attestation (3.3), no re-check on body edit, PR-only scope, no required checks, and **the Verification Protocol's decision tree never consults the Authority model that claims to govern it** (`docs/VERIFICATION_PROTOCOL.md:150-186` vs `AUTHORITY_APPROVAL_ENGINE.md:113`) — the two core governance docs are not integrated with each other.
- **Can verification fail safely? No.** The failure mode of every gate is "prose was ignored": Guardian's BLOCK exit code does not prevent merge; post-merge validation is advisory and `|| true`s its own CI check (`scripts/post_merge_validation.sh:35`); the Branch Isolation Protocol's "Connector Fallback" institutionalizes force-resetting branches and accepts "Temporary PR Closure Risk" (`docs/BRANCH_ISOLATION_WORKTREE_PROTOCOL.md:197-215`) — i.e., the recovery procedure plans to lose PR state.

### 3.7 Research engine

- Design (source-priority ladder, conflicting-evidence capture, confidence fields) is sensible on paper. Implementation: none. No fetcher, no scheduler, no citation verification, no URL liveness checking, no populated research note anywhere in the repo. Quality control is a 27-line prompt telling an LLM to prefer official docs.
- **Should research become a first-class product? Yes — it is the highest-leverage near-term output.** Research reports (technology fitness comparisons with verified citations) are valuable even with zero orchestration runtime, exercise the whole thesis (evidence, confidence, decision memory), and produce artifacts a human will actually consume. The Research Engine should be the **first** engine implemented end-to-end, not a background capability.

### 3.8 Roadmap

Covered in §11 (Roadmap Adjustments). Headline defects: state docs contradict git; `ACTIVE_WORK.md:95-108` proposes as new an epic (scanner MVP) that is already merged; the Master Roadmap has no estimates, no cut lines, and phases (multi-agent council, GPU inference node, distributed workers) that represent multiple engineering-years for a team, presented as a flat checklist for a solo builder; there is no UI epic, no migration epic, no "wire the dead schema" epic, and no graph-read epic — the four pieces of work the current code most obviously needs.

### 3.9 Plane integration

- Nothing in the repo integrates Plane; it appears only as a design intention. **Recommendation: do not self-host Plane now.** At current scale (one repo, one human), a self-hosted PMO adds an ops burden, a second source of truth to drift, and a sync engine that must be written and maintained. GitHub Issues + Projects already integrates with the PR-based governance and requires zero new infrastructure. Adopt a dedicated PMO only when the portfolio exceeds ~3 active projects or a second human joins; at that point Plane (open-source, self-hostable, API-first) is a reasonable choice consistent with local-first values, with Linear the better choice if operational simplicity outweighs self-hosting. Defer the decision — it is not on the critical path, and the Work Package Protocol should be transport-agnostic so the PMO can be swapped.

### 3.10 UI / UX

- The shipped UI is a health page with a placeholder list (`apps/web/src/main.tsx:57-63`). The dashboard docs are menus of screen names; only the Voice Inbox has interaction detail, and the Agent Council dashboard (the best UI spec, with a real status state machine) describes agents that don't exist.
- Missing entirely: information architecture, navigation model, the three operator workflows that matter (triage a Guardian block; review/correct an architecture graph; approve a decision), empty/loading/error states, and any screen for the approval queue — the one UI an approval-gated system cannot function without.
- Choosing among six visual styles (`docs/DASHBOARD_INTERFACE.md:76-83`) before any screen exists is design-system procrastination.

### 3.11 Multi-LLM architecture

- **There is no provider abstraction — zero LLM code of any kind exists in the repository** (no `anthropic`, `openai`, `ollama`, or provider module anywhere in `*.py`). The "abstraction" is a list of interface *names* with prose responsibilities (`docs/VOICE_PROVIDER_ADAPTERS.md:11-18`); routing is two sentences (`docs/LOCAL_LLM_GPU_NODE.md:27-38`). No method signatures, no streaming contract, no timeout/retry/fallback, no cost accounting, no capability negotiation, no caching, no request/response logging for evals.
- Sufficient? **No — it is unstarted.** This is acceptable for v0.1 only if the roadmap stops claiming multi-LLM routing as a near-term phase.

### 3.12 Security

- **The largest single gap in the project: no sandboxing or agent-isolation design exists at all.** The stated purpose is to run agents, Claude Code, and test runners against arbitrary repositories — and no document specifies process isolation, container-per-job, resource limits, network egress control, or how untrusted repo content (a malicious `setup.py`, a prompt-injection README) is kept from the agent's credentials. For an autonomous engineering platform this is the load-bearing safety question, and it is unasked.
- Concrete present-day issues: no authentication on any API route; `allow_credentials=True` with wildcard methods/headers; weak default Postgres credential baked into compose fallbacks (`docker-compose.yml:7,35,60`); Postgres and Redis published to the host with no Redis auth (`docker-compose.yml:15-16,20,28-29`); no SECURITY.md; no CODEOWNERS; no dependency pinning policy or lockfile audit; no commit signing or provenance — notable for a system whose thesis is trustworthy AI actions.
- Positive: path-traversal guard, `:ro` mounts, secret regexes in Guardian, and the voice safety ladder's thinking are real. But the security *vocabulary* is far ahead of the security *engineering*.

### 3.13 Infrastructure

- Compose stands up five services; the distributed runtime (GPU node, WSL node, runner node) is a text diagram. The web "production" container runs the Vite dev server on 5173. No backup/restore for the Postgres volume, no resource limits, no restart policies, no log rotation, no monitoring. CasaOS/Portainer/Proxmox appear in docs only. **The infrastructure documentation should be one page until the single-node deployment is verified working — which it has not been (§1, point 5).**

---

## 4. Critical Risks

Ranked. Each of these can independently prevent ArchetypeOS from reaching its goal.

| # | Risk | Evidence | Consequence |
|---|------|----------|-------------|
| CR-1 | **Documentation-reality inversion.** Present-tense specs for nonexistent systems, in a repo where docs are the agents' ground truth and `CLAUDE.md` mandates reading them before acting. | Engine docs vs. `worker.py:41`; stale state docs vs. `git log` | Agents (and the human) plan against a fictional system; compounding wrong decisions; the exact "context rot" the project exists to prevent |
| CR-2 | **Governance is unenforceable.** Self-attested verification, honor-system merge gate, PR-only Guardian, no required checks, Guardian can be weakened by a PR it reviews. | `pr_guardian.py:132-136`; `BRANCH_PROTECTION.md:91`; `ci.yml:17` | The project's core differentiator is currently theater; when agents arrive, nothing actually constrains them |
| CR-3 | **Coordination substrate cannot scale and has already failed.** Six hand-edited "high-conflict" markdown files as shared mutable state; all four state docs currently contradict git. | `HANDOFF.md:37`; `CURRENT_STATE.md:29-48` vs merged `fb30b80` | Multi-agent operation produces conflict storms; single-agent operation produces stale state — both observed already |
| CR-4 | **Human-approval serialization.** Every file write, commit, push, and paid API call routes through one human; no delegation mechanism is implemented. | `UNIVERSAL_AGENT_CONTRACT.md:26-37`; dead `AuthorityGrant` table | Fleet throughput = one person's review bandwidth; autonomy is structurally impossible without redesign |
| CR-5 | **No sandboxing design.** Agents are to execute tools against arbitrary repos with no isolation model, while the API itself has no auth and weak default credentials. | §3.12 | First real autonomous write-capable agent is a security incident waiting to happen; blocks any responsible move past read-only |
| CR-6 | **Never verified locally.** All verification is CI-only; `docker compose up` unproven on the target machine; compose smoke test in CI is the only runtime evidence. | `ACTIVE_WORK.md:33,64,92`; `V0_1_RUNTIME_FOUNDATION.md:71,90` | The local-first product may not run on its own target platform; every "Implemented" claim carries hidden risk |
| CR-7 | **Solo-builder sustainability.** 126 commits, one author, self-approved RFCs, self-merged PRs, an 8-phase roadmap of engineering-years, and governance ceremony sized for a multi-team org. | `git shortlog`; RFC verdicts | Burnout or abandonment is the single most probable failure mode; the process overhead accelerates it |

---

## 5. Hidden Risks

Less obvious; found only by cross-referencing code against docs.

1. **Unbounded graph duplication:** every `/repositories/{id}/scan` call appends a complete new node/edge set with no dedup (`main.py:124-172`). The architecture graph silently becomes garbage after the second scan — and the nightly loop, if built as designed, would scan on schedule, corrupting it nightly.
2. **Job-loss window:** `brpop` + crash = job stranded in `running` forever, invisible (no hang detection, `attempts` never read). The queue also silently drops jobs if Redis LPUSH fails after DB commit (`main.py:220-224`).
3. **PR-body TOCTOU:** verification metadata is read from a mutable field whose edit does not re-trigger CI. Claimed status is uncorrelated with the SHA it "verifies."
4. **Constitution canon corruption** (duplicate/conflicting article numbers) will propagate: agents told to comply with "Article XVII" will find two of them.
5. **Registry drift as a pattern:** the engine catalog lists 12 engines; 23 engine docs exist; the JSON registry lists 14 and omits 6 documented ones. The same drift already visible in state docs affects every parallel-maintained list in the repo. Any hand-maintained duplicate index will diverge — this is a systemic property, not an isolated mistake.
6. **`create_all` schema debt:** 20 tables shipped with no Alembic. First breaking model change forces manual DB surgery or data loss, and the dead tables maximize the surface for it.
7. **Hard-coded confidence values** (0.65, 0.9 in scanner/API) train downstream consumers to ignore confidence — poisoning the one field the whole evidence model depends on, in violation of Constitution Article XII.
8. **No cost containment anywhere:** no token budgets, rate limits, or spend telemetry exist even in design. The Autonomous App Creation Loop, pointed at a real provider account, has an unbounded bill.
9. **Prompt-injection surface unconsidered:** scanned repositories, fetched research pages, and PR comments are all untrusted input to future LLM agents; no doc mentions it.
10. **Ceremony fatigue:** the verification-metadata block, capability-map rule, and multi-file state updates required on every PR are already generating override tokens and reconciliation commits with one author. Under load, overrides become the norm and the governance signal dies quietly.
11. **`.archetype/` vs `docs/` split-brain:** two parallel context/roadmap systems (`.archetype/roadmap.md` still says "Current phase: Foundation," pre-dating the merged runtime) with no stated precedence.

---

## 6. Missing Systems

What a CTO would require that has no design or implementation today:

**Trust & safety tier (blocking any autonomy):**
1. **Identity & access:** user/service/agent identities, API authentication, RBAC; per-agent credentials so `created_by="system"` becomes a real audit trail.
2. **Policy-as-code authority engine:** the Levels 0–5 matrix evaluated in code (CI + runtime middleware), writing `ApprovalRecord` rows; an emergency stop that actually stops something.
3. **Append-only audit log** with a query surface.
4. **Sandboxed execution:** container-per-job, no-egress default, resource quotas, credential scoping, untrusted-content handling.
5. **Secret management:** at minimum SOPS/age or a vault container; rotation story; per-node scoping for the distributed future.

**Engineering platform tier:**
6. **Real task queue semantics:** acks/visibility timeout (Redis Streams consumer groups or Postgres `SELECT … FOR UPDATE SKIP LOCKED`), retries with backoff, DLQ, idempotency keys, job timeouts, priority.
7. **Schema migrations** (Alembic) — before the next model change, not after.
8. **Observability:** structured logs with correlation IDs, metrics, job/agent traces, cost telemetry; without this the Meta Agent and Observatory are unbuildable.
9. **LLM provider gateway:** one typed interface, routing, fallback, budget enforcement, response caching, full request/response logging (which becomes the eval dataset for free).
10. **Evaluation harness:** golden tasks for agents, retrieval-precision and citation-accuracy checks for knowledge, regression gates. *The single most important missing system for the long-term vision — autonomy without evals is faith.*
11. **Knowledge retrieval:** lexical index first (SQLite FTS / `rg` service), embeddings later; freshness computed from code-diff signals; conflict entities.
12. **Backup/restore + disaster recovery** for Postgres and artifacts.

**Organizational tier (not software):**
13. **Supply chain hygiene:** CODEOWNERS, SECURITY.md, dependency pinning + audit, commit signing/provenance.
14. **Sustainability plan:** bus-factor mitigation, an explicit weekly time budget, and governance right-sized to one person (see §9).
15. **A decision on hosting/plan** so branch protection and required checks become technically enforceable (public repo, paid plan, or self-hosted forge).
16. **Legal/licensing posture** for scanning and learning from third-party repositories.

---

## 7. Immediate Improvements (next ~4 weeks, roughly ordered)

1. **Documentation freeze + reconciliation (2–3 days).** No new engine/vision docs. Reconcile the four state docs with `git`; collapse six trackers into one `STATE.md` (or generate it — see §9.3); fix the Constitution amendment numbering; add a `Status: Implemented | Partial | Aspirational` header to every doc (a ~20-line linter can enforce the header's presence in CI). This single step removes CR-1 and CR-3's active harm at near-zero cost.
2. **Security defaults (half a day).** Remove `:-archetypeos` password fallbacks from compose; stop publishing 5432/6379 by default; add Redis `requirepass`; add SECURITY.md and CODEOWNERS.
3. **Prove local runtime (half a day).** Run `docker compose up` on the target machine; record real Level 2 evidence; fix what breaks. A local-first platform with no local verification is a contradiction.
4. **Adopt Alembic (1 day)** and generate the initial migration before any further schema change. Drop or explicitly quarantine the 13 dead tables into a clearly-marked "reserved, unwired" section.
5. **Close the v0.1 loop (3–5 days).** Add `GET /repositories/{id}/architecture` ; fix scan dedup (upsert by repository, replace prior draft nodes); move the scan into the worker as the first real `job_type` (proving dispatch, retry, and status transitions); render the graph and scan results in the web UI. This converts the skeleton into a demonstrable product.
6. **Harden the queue minimally (1–2 days).** Switch to Redis Streams with a consumer group (or Postgres SKIP LOCKED); implement retry-with-backoff using the existing `attempts` column; add a stuck-job reaper honoring a timeout.
7. **Make verification less gameable (1–2 days).** Trigger Guardian on `pull_request: types: [opened, synchronize, edited]`; have Guardian fail if claimed Level ≥3 while required CI checks on the head SHA are not green (queryable via the GitHub API); require an approver name on any `PR_GUARDIAN_OVERRIDE_*` token.
8. **Enable required status checks** by making the repo public or moving to a plan that supports it — this is the difference between governance and decoration.

---

## 8. Long-Term Improvements

1. **Replace markdown coordination with the database you already run.** Work packages, agent status, handoffs, and the message bus belong in Postgres (with Redis Streams for notification). Markdown becomes a *generated view* of that state, never hand-edited. This one change removes the top scaling bottleneck and the drift class of bugs simultaneously.
2. **Implement the authority engine as middleware**, not documentation: every state-changing tool call passes a policy check (agent identity × action level × target scope), writes an `ApprovalRecord`, and human approval becomes an asynchronous queue with a UI — one human approving *policies and exceptions*, not every write.
3. **Design and build the sandbox before the first write-capable agent:** container-per-work-package, read-only base, explicit egress allowlist, scoped short-lived credentials, artifact-only output channel.
4. **Build the provider gateway + eval harness as one system:** every LLM call logged with inputs/outputs/cost; golden-task suites replayed against changes to prompts, models, and agent definitions; promotion of any agent to higher autonomy gated on measured false-positive/negative rates (this is what makes the Meta Agent real).
5. **Tiered autonomy rollout with objective gates:** L0 read-only analysis → L1 suggestions in PRs → L2 gated writes in sandboxed worktrees → L3 auto-merge for low-risk classes — each promotion requiring N consecutive weeks above a measured quality threshold, per agent, recorded in the audit log.
6. **Knowledge system, Postgres-first:** pages as rows (content, not just paths), lexical search endpoint, freshness computed from linked code paths' git activity, conflict records as first-class entities; Obsidian as an optional read/annotate client, never the substrate; embeddings only when lexical search measurably fails.
7. **Repository intelligence worth the name:** tree-sitter-based import/dependency extraction, git-history hotspot and ownership analysis, incremental scans keyed on content hashes — each phase shipping a visible graph improvement.
8. **Scale-out only after single-node excellence:** the GPU node and distributed workers become worthwhile only when there is a queue with real semantics, observability, and a workload that saturates one machine. Today none of the three exists.

---

## 9. Alternative Designs Worth Considering

1. **The "Thin OS" alternative (strongly recommended for evaluation).** ArchetypeOS's genuine differentiators are governance, decision memory, and verification culture — not runtime plumbing. Alternative: don't build an orchestrator, bus, or session manager at all. Use GitHub as the substrate (Issues = work packages, PRs = the bus, Actions = execution, branch protection = authority), use Claude Code / existing agent harnesses as the execution layer, and build only what nobody sells: the decision/evidence store, the fitness engine, PR Guardian's intelligence, and the knowledge system. This halves the roadmap and eliminates the least-differentiated 50% of the design. The cost is platform lock-in and less control — a fair trade at current team size, and reversible later.
2. **Event-sourced control plane.** Instead of separate bus + audit log + state files, one append-only `events` table (actor, type, payload, refs) from which current state, audit trail, and notifications are all derived. One primitive replaces three subsystems and makes the audit log structurally impossible to skip.
3. **Off-the-shelf workflow engine.** If the orchestrator is to be built, Temporal (or even the already-benchmarked n8n for lighter flows) provides retries, timeouts, versioned workflows, and observability that would take person-months to replicate. The Work Package Protocol maps naturally onto workflow definitions.
4. **Generated state docs.** `CURRENT_STATE.md` / `RECENT_CHANGES.md` should be build artifacts produced from `git log` + the DB by a script or nightly job — never hand-edited. Drift becomes structurally impossible rather than procedurally discouraged.
5. **Postgres-only start.** Redis currently adds an operational dependency to deliver a worse queue than Postgres SKIP LOCKED would provide at this scale. Dropping Redis until pub/sub throughput actually demands it simplifies the runtime.

---

## 10. Prioritized Recommendations

| P | Recommendation | Effort | Risk if skipped | Acceptance criteria |
|---|----------------|--------|-----------------|---------------------|
| P0 | Doc freeze; reconcile state docs with git; collapse to one tracker; status headers on all docs; fix Constitution numbering | 2–3 d | CR-1, CR-3 persist and compound | Zero contradictions between state doc and `git log`; every doc carries a status header enforced by CI |
| P0 | Compose/security defaults; SECURITY.md; CODEOWNERS | 0.5 d | CR-5 grows | No default credentials in compose; DB/Redis unpublished; Redis auth on |
| P0 | Local `docker compose up` verified with recorded evidence | 0.5 d | CR-6 | Level 2 verification record with command output on the target machine |
| P0 | Alembic baseline; quarantine dead tables | 1 d | Hidden risk 6 | `alembic upgrade head` from empty DB reproduces schema |
| P1 | Close the loop: graph GET + scan dedup + scan-as-worker-job + UI rendering | 3–5 d | Product remains undemonstrable | Register → scan → view graph works in the browser; re-scan does not duplicate nodes |
| P1 | Queue semantics: streams/SKIP LOCKED, retry, reaper, idempotency | 1–2 d | Hidden risks 2 | Kill -9 the worker mid-job; job is retried and completes; stuck jobs surface |
| P1 | Guardian hardening: `edited` trigger, CI cross-check for claimed levels, named override approvers; required status checks enabled | 1–2 d | CR-2 | A PR claiming "Verified Level 3" with red CI is blocked; body edits re-run Guardian |
| P1 | First real intelligence vertical: Research Engine end-to-end (question → sourced, citation-checked note → `research_notes` row → visible in UI) | 1–2 wk | Thesis remains unproven | One real research note with live-checked citations produced and displayed |
| P2 | Decide Thin-OS vs full-runtime (write it as RFC-0003, following the full RFC template, with an external reviewer or genuinely independent judge) | 3 d | Roadmap stays 2× too large | Accepted RFC with evidence, security impact, migration plan — the first compliant RFC |
| P2 | Authority middleware MVP + audit events; approval queue UI | 1–2 wk | CR-4 blocks all autonomy | Every state-changing API call writes an ApprovalRecord with a real actor |
| P2 | Sandbox design doc + container-per-job implementation | 1–2 wk | CR-5 blocks write-capable agents | A work-package job runs in an isolated container with no egress and scoped mounts |
| P3 | Provider gateway + eval logging; then first LLM-backed engine pass | 2–3 wk | Multi-LLM claims stay fictional | One engine callable through a typed provider interface with cost + budget recorded |
| P3 | Knowledge Postgres-first + lexical search + freshness signals | 2–3 wk | Vault stays 4 stub files | An agent query returns ranked pages; stale pages are flagged from code-diff signals |

---

## 11. Roadmap Adjustments

**Remove or explicitly park (move to a `docs/vision/` folder with `Status: Aspirational`):** Digital Twin, Simulation Lab, Evolution forecasting/Score, Portfolio Marketplace, Organizational Intelligence, Mentor, Voice (all three docs), Workspace Layout, GPU node, Distributed Runtime, CasaOS/Portainer/Proxmox material. None is load-bearing for the next two quarters; together they roughly double the conceptual surface and dilute every conversation.

**Replace the 8-phase Master Roadmap with four gated phases:**

- **Phase A — Truth (weeks 1–2):** P0 items. *Gate: state docs match git; compose runs locally; migrations exist; security defaults fixed.*
- **Phase B — Loop (weeks 3–6):** P1 items. *Gate: register → scan → graph → view works; queue survives a worker kill; Guardian cross-checks CI; one compliant research note shipped.*
- **Phase C — Trust (quarter 2):** authority middleware, audit events, sandbox, provider gateway + eval seed, Thin-OS RFC decision. *Gate: an LLM-backed job runs sandboxed, budgeted, logged, and audit-recorded.*
- **Phase D — Agents (quarter 3+):** DB-backed work state and bus, 2–3 agents at L1 autonomy, Meta-Agent metrics from real telemetry, tiered promotion. *Gate: two agents complete work packages concurrently with zero state-file conflicts — because there are no state files.*

Voice, distributed runtime, marketplace, and the remaining council re-enter the roadmap only after Phase D's gate, each via a compliant RFC.

**Hidden dependencies to make explicit:** UI depends on graph-read API; nightly loop depends on scan dedup + scheduler + queue semantics; Meta Agent depends on observability; *all* autonomy depends on sandbox + authority middleware + evals; multi-agent depends on retiring markdown state. The current roadmap encodes none of these edges.

---

## 12. Comparative Position (long-term vision check)

- **vs. Claude Code / Cursor / Devin / Codex / OpenHands:** ArchetypeOS is *stronger* in governance design, decision-memory ambition, and verification vocabulary — none of those products has a constitution, evidence-graded decisions, or verification levels. It is *weaker* in everything executable: all of them ship working agents, sandboxes (Devin, OpenHands), real editor/runtime integration, and eval-driven iteration. Strategy implication: do not compete on execution runtime; integrate it (§9.1) and win on the governance/memory layer they all lack.
- **vs. Plane / Linear / GitHub:** ArchetypeOS currently re-implements issue tracking as hand-edited markdown — strictly worse than any of the three. Its genuinely novel additions (work packages with verification metadata, authority levels, evidence links) should be a layer *on* such a system, not a replacement.
- **vs. n8n:** n8n has a real workflow runtime with retries and observability; the Orchestration Engine doc describes less than n8n ships. Either use such an engine or consciously accept rebuilding one.
- **vs. Obsidian:** the knowledge design borrows Obsidian's vocabulary without its tooling; four stub files vs. a mature graph/index/plugin ecosystem. The project's own Karpathy review pointed the right direction (structured store as truth, markdown as view) — it was designed and then not followed.
- **Does it have the characteristics to become a true Engineering OS?** The *values* (evidence, verification, memory, governed autonomy) are exactly right and rare. The *mechanisms* do not yet exist, and several documented mechanisms (markdown coordination, human-per-action approval, single orchestrator) are anti-scalable and must be replaced, not incrementally hardened. The honest comparison today: a well-argued PhD thesis proposal standing next to shipping products.

---

## 13. Final Verdict

**Conditional GO — with a mandatory course correction.**

ArchetypeOS is not currently being engineered according to the practices of elite software organizations. Elite organizations write less speculative documentation and enforce more of what they write; they verify on the target platform before claiming "implemented"; they never let their source of truth drift from reality; and they make their governance machine-checked or admit they have none. On each of those axes, this repository currently fails — while *documenting, eloquently, that it intends the opposite*.

The redeeming facts are substantial: the values are correct and rare; the one enforced gate (PR Guardian + CI) is genuinely well-built; the read-only safety boundary is real code; the scope-lock and self-review show the project can self-diagnose; and every defect found by this review is fixable with weeks, not years, of focused work — because there is so little system yet, nothing is load-bearing enough to be hard to change. That is the advantage of reviewing at v0.1, and it will not last.

The decisive test of this project is not any engine on the roadmap. It is whether, in the next month, the project can: stop designing, reconcile its documents with reality, make three governance rules technically enforceable, run itself on its own target machine, and ship one intelligence loop a user can see. If it can do that, the constitution acquires a country, and the ten-year ambition is credible. If instead the next month produces more engine specifications, this review's prediction is that ArchetypeOS becomes the best-documented system never built.

Probability-weighted assessment: with the course correction above, this is a viable long-horizon project with a defensible differentiator (governed, memory-bearing engineering intelligence). Without it, the most probable outcome is solo-builder exhaustion under self-imposed process, with the artifact surviving as an excellent reading list.

---

*Cross-reference appendix: findings trace to first-hand inspection of `apps/api/app/main.py`, `models.py`, `repository_scanner.py`, `apps/worker/app/worker.py`, `apps/web/src/main.tsx`, `tools/pr_guardian.py`, `.github/workflows/ci.yml`, `docker-compose.yml`, `.env.example`, `scripts/*.sh`, both `.archetype/` registries, the knowledge vault, and all 76 documents under `docs/` including the three RFCs and all templates.*
