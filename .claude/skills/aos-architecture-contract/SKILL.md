---
name: aos-architecture-contract
description: Use when an ArchetypeOS change touches structure or invariants, such as adding a service or layer, editing packages/aos_core, the ClaudeCodeProvider or llm_provider seam, EMBEDDING_PROVIDER tiers, ArchitectureNode or ArchitectureEdge semantics, the knowledge vault vs Postgres split, confidence and evidence fields, a missing-core-tests BLOCK, provider context contamination (LES-021), or a proposed shortcut around deterministic-floor-plus-real-tier or mature-state-only rules.
---

# ArchetypeOS Architecture Contract

## 1. Overview

This skill is the contract layer of ArchetypeOS: the design decisions that everything else leans on, why they hold, the numbered invariants, and the weak points stated without euphemism. Read it before any change that adds a service, moves code across a package boundary, adds a provider or tier, or touches how evidence and confidence flow through the system.

ArchetypeOS is an Engineering Intelligence Platform (v0.1 shipped 2026-07-05). It scans repositories into structured "DNA", runs an agent council over evidence, distills knowledge into a git vault, and gates every change through a deterministic PR Guardian plus a human merge gate. Facts below are verified against the repo as of 2026-07-06; volatile ones carry a re-verification command in section 9.

## 2. When to use / When NOT to use

Use this skill when:

- You are about to add, split, or rename a service, package, or layer.
- A change touches `packages/aos_core/` and you need to know what enforcement follows it.
- You are working on the LLM provider seam, the embedding seam, or distillation tiers.
- You need to know whether a proposed design violates an invariant before writing code.
- Someone proposes "just this once" scaffolding, an ambient-context provider call, or letting a builder agent self-verify.

Do NOT use this skill for:

- How changes are classified and gated end to end: see `aos-change-control`.
- Diagnosing a live failure: see `aos-debugging-playbook`.
- The full history of lessons and dead ends: see `aos-failure-archaeology`.
- Scanner heuristics and RepositoryDNA field semantics: see `aos-scanner-dna-reference`.
- Distillation tiers, embeddings, and council evidence classes in operational detail: see `aos-knowledge-transfer-reference`.
- Config axes and defaults: see `aos-config-and-flags`.
- Standing up the environment: see `aos-build-run-and-operate`.

## 3. The four layers

Source: `docs/SYSTEM_ARCHITECTURE.md`.

| Layer | Owns | Concrete form today |
|---|---|---|
| Control Plane | Dashboard, API, project registry, job routing, agent registry, reports, release gates, audit logs | `apps/api` (FastAPI), `apps/web` (React/Vite Control Tower), `apps/scheduler` |
| Intelligence | Engines that research, compare, evaluate, recommend, explain | `packages/aos_core/aos_core/services/` (scan, digest, distillation, transfer, council, decisions, knowledge, ...) |
| Council | Specialized agents: Research Librarian, Architecture Cartographer, Technology Fitness Judge, Security Agent, Compliance Agent, Design Intelligence Agent, External Repo Scout, PR Guardian, Builder, Final Judge | `aos_core/services/council.py` (MVP roster per RFC-0005); full roster in `docs/AGENT_CATALOG.md` |
| Execution | Tools and models: Claude Code, local LLMs, deterministic scanners, GitHub tools, test runners | `aos_core/llm/` providers, `aos_core/repository_scanner.py`, `tools/pr_guardian.py` |

Safety model baked into the layer split: read-only by default, explicit approval for writes, audit log for every job, path validation for repository access, human approval for destructive actions.

## 4. Service topology

Source: `docker-compose.yml` (verified 2026-07-06). Six services, three volumes.

| Service | Image / build | Port (default) | Depends on (healthy) | Notes |
|---|---|---|---|---|
| postgres | `pgvector/pgvector:pg16` | 5432 | none | RFC-0010: ships the `vector` extension; drop-in for `postgres:16-alpine` |
| redis | `redis:7-alpine` | 6379 | none | `--appendonly yes` |
| api | `apps/api/Dockerfile` | 8000 | postgres, redis | `EMBEDDING_PROVIDER` defaults to `deterministic`; repos and knowledge mounted read-only |
| worker | `apps/worker/Dockerfile` | none | api, redis | Same `EMBEDDING_PROVIDER` env; must match api's setting |
| scheduler | `apps/scheduler/Dockerfile` | none | postgres, redis | |
| web | `apps/web` build | 5173 | api | `VITE_API_BASE_URL` defaults to `http://localhost:8000` |

fastembed is installed in the api and worker images unconditionally, but the ~90 MB model is NOT pre-downloaded by default; an offline node builds with `PREDOWNLOAD_EMBEDDING_MODEL: "true"` (compose comments, AOS-EMBED-002).

## 5. THE house pattern: deterministic floor plus real tier

Every intelligence capability ships in two tiers behind one seam. The deterministic tier is the default, is hermetic (no network, no model download, no nondeterminism), and is what CI runs. The real tier is opt-in by config.

| Capability | Seam | Deterministic floor | Real tier |
|---|---|---|---|
| LLM reasoning | `aos_core/llm/get_provider`, setting `llm_provider` (default `deterministic`) | `DeterministicProvider`: rule-based JSON from the evidence array | `ClaudeCodeProvider`: shells the local `claude` CLI, "Never invoked in CI" (docstring) |
| Embeddings | `aos_core/embeddings/get_embedder`, setting `embedding_provider` (default `deterministic`) | `DeterministicEmbedder`: `embed()` returns `None`, callers fall back to the lexical Layer-0 path | `FastEmbedEmbedder`: all-MiniLM-L6-v2, 384-dim, via fastembed/ONNX (no torch), lazy import only |
| Distillation summary | `aos_core/services/distillation.py` | Deterministic summary floor (AOS-DISTILL-003): first declarative sentence after noise-line filtering | Reasoned `DNA.purpose` from a real provider (AOS-DISTILL-004); garbled output falls back to the floor |

Why this pattern holds (the load-bearing reasons):

1. Hermetic CI: the whole pipeline, including migrations and the vector-store path, tests green with zero heavy dependencies and zero network.
2. Local-first (Constitution preamble and `docs/SYSTEM_ARCHITECTURE.md`): a node with no API key and no GPU still runs the full loop at floor quality.
3. Offline nodes: the real tiers are chosen so offline works too (fastembed model pre-download build arg; `claude` via local subscription auth).
4. Degradation is explicit, never silent: `embed() -> None` means "use lexical", a garbled reasoned purpose falls back to the floor and is marked derived. No tier pretends to be the other.

Rule of thumb: if you add a capability with only a real tier, or only a mocked test of the real tier, you have broken the house pattern. Add the floor first, then the real tier behind the same seam (`EMBEDDING_DIM = 384` in `aos_core/config.py` is the model of this: one constant keeps the pgvector column and both embedder tiers dimension-compatible).

## 6. The packages/aos_core boundary

`packages/aos_core` is the shared domain core (RFC-0006): models, database, config, scanner, and all services, installed with `pip install -e` into api, worker, and scheduler. The boundary is also an enforcement boundary:

- LES-010: when the domain layer moved from `apps/api/app/` to `packages/aos_core/`, the Guardian's path-keyed test enforcement went blind to the moved code. Fix, shipped in the same change set: `check_tests_for_code_changes` in `tools/pr_guardian.py` sets `core_changed` for any `packages/aos_core/` path and BLOCKs with `missing-core-tests` unless a test changes under `packages/aos_core/tests/` or `apps/api/tests/`.
- LES-020: the rule is intentionally strict. ANY `aos_core` source change needs a unit test in the same change set, even a one-line infra tweak, and an e2e that happens to cover the code does not count (e2e paths are not in the Guardian's test globs). Extract the decision logic into a testable predicate and pin its branches.
- The override token `PR_GUARDIAN_OVERRIDE_TESTS` exists but the working rule is: never override, add the test. The verified record: zero overrides of any substantive code BLOCK (tests, secrets, metadata, acceptance evidence), ever; override tokens do appear in some merged PR bodies as warn acknowledgments and no-op markers. The authoritative override audit lives in aos-change-control section 8.

Corollary for any future extraction into `packages/`: move the code AND extend the Guardian paths plus a `missing-*-tests` rule in the same change set.

## 7. Provider isolation contract (LES-021)

A shelled model provider must be a pure function of `system` + `prompt`. History: a real-provider council agent (`technology_fitness_judge`) described ArchetypeOS itself instead of the target repo, because `claude -p` inherited the working directory's `CLAUDE.md` and filesystem.

The contract, as implemented in `packages/aos_core/aos_core/llm/__init__.py` (`ClaudeCodeProvider`), is two-part and both parts are mandatory:

1. Isolated cwd: the subprocess runs inside `tempfile.TemporaryDirectory(prefix="aos-llm-")`, a fresh empty directory with no project `CLAUDE.md` and no repo files.
2. Tool and MCP denial: argv includes `--disallowedTools` with the full `_ISOLATED_DISALLOWED_TOOLS` list (`Bash`, `BashOutput`, `KillShell`, `Read`, `Edit`, `Write`, `NotebookEdit`, `Glob`, `Grep`, `WebFetch`, `WebSearch`, `Task`) plus `--strict-mcp-config` to ignore ambient MCP servers.

The hermetic regression test `test_claude_code_provider_mocked` (`apps/api/tests/test_council.py`) pins the isolated cwd and the exact argv. Any new shelled provider (including the future RFC-0008 extraction path) must replicate both parts and pin them in a test. Cite LES-021 if a shelled provider regains ambient context.

## 8. Builder is not verifier

The council recommends; it never builds, merges, or acts (RFC-0005 non-goal, verbatim: "the council never builds, merges, or acts; it recommends"). The Builder Agent executes validated plans; verification belongs to different parties:

- Deterministic: PR Guardian (`tools/pr_guardian.py`, verdicts PASS / PASS_WITH_WARNINGS / BLOCK) and CI, run locally first via `scripts/pre_pr_guardian.sh`.
- Judgment: Final Judge reviews agent outputs, rejects unsupported claims, resolves conflicts.
- Authority: the human operator merges, via the Manual Merge Gate comment pinned to the head SHA (`docs/ORCHESTRATOR_PLAYBOOK.md`); a new push voids the gate.

Never let the entity that produced a change also issue its passing verdict, and never suggest bypassing the Guardian, the merge gate, or the RFC process.

## 9. Confidence and evidence on every entity

Source: `packages/aos_core/aos_core/models.py` (verified 2026-07-06).

- `AuditMixin`, inherited by every table: `id`, `status`, `version`, `created_at`, `updated_at`, `created_by`, `updated_by`, `meta` (JSON).
- `confidence: Float` and/or `evidence: JSON list` appear on the reasoning entities: RepositoryDNA, ArchitectureNode, ArchitectureEdge, Decision, ResearchNote, Recommendation (evidence), Evaluation, Risk, Benchmark, Experiment, CouncilReview (verdict default "Insufficient evidence", confidence default 0.0), CouncilAgentOutput.
- Defaults are honest zeros: `confidence` defaults to 0.0, `evidence` to `[]`. Nothing starts confident (Constitution Article XII: metrics and confidence must not be manipulated).
- The Final Judge abstains below `ABSTAIN_CONFIDENCE = 0.35` (`aos_core/services/council.py`, RFC-0005 Open Question 3). Abstention is correct behavior, not a bug; the open gap is that nothing gathers the named missing evidence and re-runs (LES-019, open; see `aos-evidence-loop-campaign`).

## 10. Knowledge vault in git, Postgres as index

The repo vault (`knowledge/`, lessons under `knowledge/wiki/lessons/` per RFC-0004) is the source of truth. Postgres `KnowledgePage` is a derived read projection (AOS-KNOW-002, `docs/KNOWLEDGE_VAULT_STRUCTURE.md`): a sync parses `wiki/lessons/index.md` and upserts one page per lesson. A DB reset loses nothing; re-run the sync from the repo tree. Never treat DB knowledge rows as authoritative over the vault files.

High-contention coordination docs (`docs/ACTIVE_WORK.md`, `docs/RECENT_CHANGES.md`, `knowledge/wiki/lessons/index.md`) use git's `merge=union` driver (`.gitattributes`) so parallel additive edits auto-merge; status flips on an existing line stay single-writer by protocol.

## 11. Mature-state-only (architectural rule)

Source: `docs/ORCHESTRATOR_PLAYBOOK.md`, "Design to the mature-state target (operator rule, 2026-07-06)". Define the mature-state architecture of a subsystem first, then make every work package a strict subset of that target: a permanent layer later work extends, never scaffolding you tear out. The test for every spec step: will this design be extended or torn out by the mature system? If torn out, do not build it, or reduce it to the honest minimum that survives. This is why the deterministic floors exist: they are permanent Layer-0 behavior, not throwaway stubs.

## 12. INVARIANTS

1. Every intelligence capability has a deterministic floor behind the same seam as its real tier. Violated: CI stops being hermetic, offline nodes lose the capability entirely, and degradation becomes silent.
2. CI never invokes a real provider (`llm_provider` and `embedding_provider` default to `deterministic`; `ClaudeCodeProvider` is "Never invoked in CI"). Violated: nondeterministic, network-dependent, cost-bearing CI; green stops meaning anything.
3. Any `packages/aos_core/` source change carries a test under `packages/aos_core/tests/` or `apps/api/tests/` in the same change set. Violated: Guardian BLOCK `missing-core-tests`; overriding it instead of adding the test erodes the record of never overriding a substantive code BLOCK (see aos-change-control section 8).
4. A shelled provider runs in an empty temp cwd with `--disallowedTools` (full deny list) and `--strict-mcp-config`. Violated: agents reason about the wrong repo (LES-021 recurrence) and council output stops being a function of the supplied evidence.
5. Council agents reason only from the supplied evidence array; the Final Judge abstains below confidence 0.35 rather than guessing. Violated: Constitution Articles III and XII (evidence over opinion, no manipulated confidence).
6. Builder never verifies its own output; merge requires deterministic Guardian PASS plus the head-SHA-pinned Manual Merge Gate plus human approval. Violated: the whole governance story (Article IX, Human Authority) collapses.
7. The git vault is the source of truth for knowledge; Postgres is a rebuildable projection. Violated: a DB reset or drift becomes data loss instead of a no-op resync.
8. Every entity carries audit fields and honest confidence/evidence defaults (0.0 and []). Violated: provenance is unreconstructable and confidence numbers become decoration.
9. Package moves carry their enforcement with them: extend Guardian path rules in the same change set as any relocation (LES-010). Violated: the gate goes blind exactly where code just churned.
10. Every work package is a strict subset of a written mature-state target; no scaffolding. Violated: you build things twice and tear-outs mask as progress.
11. Embedding dimensionality has one source of truth (`EMBEDDING_DIM = 384` in `aos_core/config.py`). Violated: pgvector column and embedder disagree and the vector path corrupts silently.
12. api and worker must run the same `EMBEDDING_PROVIDER` value (compose comments). Violated: distillation-time vectors and query-time behavior disagree.

## 13. KNOWN-WEAK POINTS (plainly)

- Architecture graph edges are `contains` (directory containment), compose-derived `depends_on` (AOS-ARCH-SEMANTICS-001), and manifest/local-path-derived `depends_on` at top-level-directory granularity, capped at `MAX_LOCAL_DEP_EDGES = 200` (AOS-ARCH-EDGES-001, merged to main, closes LES-014). Source import-graph edges are still absent: the graph cannot see which module imports which. That is a scoped follow-up, not shipped.
- The Postgres audit trail is mutable. `AuditMixin` rows can be edited by anyone with DB access; there is no append-only ledger. Git history (vault, docs, lessons) is the immutable fallback, which is exactly why invariant 7 matters.
- Validation is at 6-repo portfolio scale only: 5 external repos under `.archetype/portfolio/` (pydantic-ai, claude-agent-sdk-python, gin, example-voting-app, kubernetes) plus ArchetypeOS itself. Ranked-retrieval and scanner claims beyond that scale are unproven (see `aos-research-frontier` for the baseline-beating ambition, still open).
- Embeddings are untested on non-English corpora (candidate weak point, operator assessment as of 2026-07-06; no repo evidence either way). all-MiniLM-L6-v2 is an English-centric model and every portfolio repo is English-documented.
- Single-operator assumption: one human (the operator) approves every merge, owns state-doc status flips, and holds the only authority tier. Multi-operator concurrency is handled only for parallel agent sessions (union merge driver), not for humans disagreeing.
- The evidence assembly loop is missing: the council names missing evidence classes when it abstains, but nothing gathers that evidence and re-runs (LES-019, open). This is the hardest live problem; see `aos-evidence-loop-campaign`.
- Doc staleness self-healing (`tools/doc_staleness.py --fix`, AOS-SELFHEAL-001, closing lesson LES-L01) is merged via PR #80. Detection (`tools/doc_staleness.py` without `--fix`) was already merged earlier (AOS-20).

## 14. Task tier guide

Routing home is `aos-model-routing`; these labels are operator guidance, candidate status.

| Task in this skill's scope | Tier |
|---|---|
| Look up an invariant, port, flag, or edge kind before a change | Haiku |
| Verify a change against the invariants list; run the re-verification commands | Haiku |
| Add a floor-tier test or a `missing-*-tests` Guardian path for a package move | Sonnet |
| Implement a new capability behind the floor-plus-real-tier seam | Sonnet |
| Design a new layer, provider, or seam; write a mature-state target; amend an invariant | Opus |
| Adjudicate a proposed invariant violation or a Constitution conflict | Opus |

## 15. Common mistakes

- Shipping a real tier without a deterministic floor, or "temporarily" defaulting a provider to the real tier. The default is always `deterministic`.
- Treating an e2e test as satisfying `missing-core-tests`. It does not; only `packages/aos_core/tests/` or `apps/api/tests/` count.
- Reaching for `PR_GUARDIAN_OVERRIDE_TESTS` on a BLOCK. Substantive code BLOCKs have never been overridden (verified record in aos-change-control section 8); fix it in code.
- Adding a shelled provider (or subprocess LLM call) without the empty-cwd plus `--disallowedTools` plus `--strict-mcp-config` triple, or without pinning the argv in a test.
- Writing knowledge into Postgres directly instead of into the vault files and resyncing.
- Building scaffolding "to unblock" a package instead of writing the mature-state target and cutting a strict subset.
- Assuming the architecture graph shows imports. It shows containment, compose service dependencies, and manifest-declared local-path dependencies only.
- Reading confidence 0.0 or verdict "Insufficient evidence" as a failure. Honest abstention is the designed behavior; the gap is the missing re-run loop (LES-019).

## 16. Provenance and maintenance

Authored 2026-07-06 on branch `laptop/aos-selfheal-doc-loop` (HEAD includes origin/main through PR #79; AOS-SELFHEAL-001 since merged as PR #80).

Derived from: `docs/SYSTEM_ARCHITECTURE.md`, `docs/ENGINEERING_CONSTITUTION.md`, `docs/AGENT_CATALOG.md`, `docs/ORCHESTRATOR_PLAYBOOK.md`, `docs/KNOWLEDGE_VAULT_STRUCTURE.md`, `docs/CURRENT_STATE.md`, `docker-compose.yml`, `.gitattributes`, `packages/aos_core/aos_core/{config.py,models.py,repository_scanner.py}`, `packages/aos_core/aos_core/llm/__init__.py`, `packages/aos_core/aos_core/embeddings/__init__.py`, `packages/aos_core/aos_core/services/{council.py,distillation.py}`, `tools/pr_guardian.py`, `tools/doc_staleness.py`, `docs/rfc/RFC-0005-Intelligence-Layer-Agent-Council-Final-Judge.md`, RFC-0006, RFC-0010, `knowledge/wiki/lessons/{LES-010,LES-014,LES-020,LES-021}.md`, `knowledge/wiki/lessons/index.md`.

Re-verification commands (run from the repo root, `/home/nerfherder/Dev/ArchetypeOS` or your clone):

| Fact | Re-verify with |
|---|---|
| Service names, ports, images, depends_on | `grep -n "image:\|ports:\|Dockerfile" docker-compose.yml` |
| Provider defaults and names | `grep -n "llm_provider\|embedding_provider" packages/aos_core/aos_core/config.py` |
| EMBEDDING_DIM value | `grep -n "EMBEDDING_DIM" packages/aos_core/aos_core/config.py` |
| Isolation flags and deny list | `grep -n "_ISOLATED_DISALLOWED_TOOLS\|strict-mcp\|aos-llm-" packages/aos_core/aos_core/llm/__init__.py` |
| missing-core-tests rule paths | `grep -n "missing-core-tests\|packages/aos_core" tools/pr_guardian.py` |
| Guardian verdict strings | `grep -n "Verdict:" tools/pr_guardian.py` |
| Abstention floor value | `grep -n "ABSTAIN_CONFIDENCE" packages/aos_core/aos_core/services/council.py` |
| Edge kinds emitted by the scanner | `grep -n '"type": "contains"\|"type": "depends_on"\|MAX_LOCAL_DEP_EDGES' packages/aos_core/aos_core/repository_scanner.py` |
| AuditMixin and confidence/evidence fields | `grep -n "class AuditMixin\|confidence\|evidence" packages/aos_core/aos_core/models.py` |
| Union merge driver files | `cat .gitattributes` |
| LES-014 / LES-019 / LES-L01 status | `grep -n "LES-014\|LES-019\|LES-L01" knowledge/wiki/lessons/index.md` |
| AOS-SELFHEAL-001 merged to main yet (was merged, PR #80) | `if git merge-base --is-ancestor f197bda origin/main; then echo merged; else echo in-review; fi` (fetch origin first; a stale local ref reports in-review) |
| Portfolio repo count | `ls .archetype/portfolio/` |
| Mature-state rule text | `grep -n "mature-state" docs/ORCHESTRATOR_PLAYBOOK.md` |
