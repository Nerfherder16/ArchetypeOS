---
name: aos-knowledge-transfer-reference
description: "Use when working on ArchetypeOS distillation, transfer scoring, embeddings, or council evidence semantics. Symptoms: DNA.purpose is badge markdown or analogy noise, recommend_reuse ranks wrong or confidence looks tiny, score_relevance or need-coverage questions, pgvector or fastembed or EMBEDDING_PROVIDER setup, embedding column stays NULL, council abstains with Insufficient evidence, decision approve returns 409 needs_evidence, validation_state derived vs reasoned."
---

# AOS Knowledge Transfer Reference

## 1. Overview

Domain reference for the ArchetypeOS knowledge pipeline: how repository content becomes distilled knowledge (RFC-0008), how a target need is scored against the portfolio (RFC-0009), how the embedding tier upgrades that scoring (RFC-0010), and how the Agent Council consumes knowledge as evidence (RFC-0005). Every formula, constant, and status value below was verified against source at the paths in section 8, as of 2026-07-06.

Definitions used throughout (each defined once):

| Term | Definition |
|------|-----------|
| DNA | A `RepositoryDNA` row: the structural fingerprint of a scanned repo (`language_mix`, `package_managers`, `frameworks`, `runtime_services`, `risk_flags`, `maturity`, `scan_summary`) plus the distilled one-line `purpose`. Model: `packages/aos_core/aos_core/models.py`. |
| Distillation | Extracting durable knowledge from a repo's actual content (README + bounded source files) into a vault page and a `KnowledgePage` row, stamping `DNA.purpose`. Service: `packages/aos_core/aos_core/services/distillation.py`. |
| Need | The free-text description of what a target project requires, sent as `{"need": "..."}` to `POST /projects/{project_id}/transfer`. |
| Coverage | The transfer relevance score: the fraction of the need's meaningful tokens that a candidate covers via its text or its technologies (LES-023). |
| Evidence class | The category of evidence fed to a council persona (research note, decision, repo distillation, architecture node, DNA facts, risk flags). LES-019: the class must match the question class. |
| Abstention | The Final Judge verdict `Insufficient evidence`, emitted when total evidence or aggregate confidence falls below documented floors. Abstention is constitutional behavior, not a failure. |

## 2. When to use / When NOT to use

Use this skill when you need the exact semantics of distillation tiers, transfer scoring, the embedding seam, council evidence, or knowledge page types.

Do NOT use it for:

- Scanner heuristics, secret signals, language classification, or how DNA fields get populated by `run_scan`: see `aos-scanner-dna-reference`.
- Executing the LES-019 evidence-gathering campaign end to end: see `aos-evidence-loop-campaign`.
- Full config axis list and drift checks (EMBEDDING_PROVIDER is one axis of many): see `aos-config-and-flags`.
- Starting services, the full endpoint map, artifact conventions: see `aos-build-run-and-operate`.
- Test recipes and the evidence bar for changes in this area: see `aos-validation-and-qa`.
- The history of how these designs were settled (LES-013, LES-022, LES-023 narratives): see `aos-failure-archaeology`.
- Load-bearing invariants that must not be broken when editing these services: see `aos-architecture-contract`.

## 3. Distillation: tiers and validation states

`distill_repository` (in `packages/aos_core/aos_core/services/distillation.py`) runs three capability layers per repo. They produce exactly two `validation_state` values on the resulting repository `KnowledgePage`:

| Layer | What it does | Provider needed | Effect on validation_state |
|-------|-------------|-----------------|---------------------------|
| Summary floor (README-only, deterministic) | `extract_repo_knowledge`: title from the first `# ` heading, cleaned summary, key points from `##`/`###` headings, technologies from DNA + fenced-code languages, `useful_for` keyword heuristics. Pure Python, no LLM, hermetic. | None (always runs) | `"derived"` |
| Code-aware (deterministic, RFC-0008 Phase 2) | `select_source_files` (entry points, largest source files, primary manifest; caps: 10 files, 40,000 bytes) + `summarize_sources` (Python via `ast`, other languages via a top-level symbol regex). Renders a "Components (from source)" section. Always runs, hermetic. | None (always runs) | still `"derived"` (this layer never changes the state) |
| Reasoned purpose (AOS-DISTILL-004) | `reason_purpose`: a real LLM provider reasons ONE declarative purpose sentence from README + bounded source. A non-empty result replaces the floor summary and stamps `DNA.purpose`. `reason_over_source` adds the "How it works / Built for" narrative. | Real (non-`deterministic`) provider | `"reasoned"` |

Key rules, all verified in source:

- The `deterministic` provider (CI default) NEVER produces a narrative or reasoned purpose. Empty or garbled reasoned output falls back to the floor and `"derived"`. No fabrication, ever.
- Vault write path: `<knowledge_root>/wiki/repositories/<slug>.md`. A read-only vault (the compose stack mounts it `:ro`) raises HTTP 409, never 500, and mutates nothing.
- The `KnowledgePage` is upserted keyed on `vault_path`, `page_type="repository"`, sha256 checksum. `DNA.purpose` is stamped with the page summary when a DNA row exists.
- Endpoint: `POST /repositories/{repository_id}/distill` (route: `apps/api/app/routes/repositories.py`).

### Summary-floor cleaning rules (LES-022, closed)

The floor once emitted raw badge markdown as `DNA.purpose` (kubernetes) and grabbed the "FastAPI revolutionized web development" analogy as pydantic-ai's purpose, starving the Transfer Engine. The fixed `_clean_summary` rules:

1. Drop noise before choosing: fenced code, HTML comments, badge/image-link-only lines, bare links, bullets, blockquotes, tables, numbered lists, and headings are never a summary.
2. Prefer the first declarative description sentence: subject begins with the distilled title or repo name followed by a copula/verb (`is`, `are`, `provides`, `enables`, and the rest of the `_COPULAS` set). "Gin is a high-performance ... framework" matches; "Gindalf is ..." for repo "gin" does not.
3. Prose declaratives beat heading declaratives (a release-announcement heading like "Gin 1.12.0 is now available!" structurally matches; only when no prose sentence declares is a heading accepted, which is how PydanticAI's `<h3>` description gets picked up).
4. A prose-anchored summary is extended with following prose blocks up to a 500-char budget, capped at 1200 chars total.
5. No clean prose at all yields the honest fallback string "README present but no prose summary could be extracted." An honest empty is strictly better than noise, because noise mis-ranks the retrieval that consumes it.

## 4. Transfer scoring: need coverage (LES-023, closed)

Service: `packages/aos_core/aos_core/services/transfer.py`. Endpoint: `POST /projects/{project_id}/transfer` with body `{"need": "<text>"}`; the target project's own repos are excluded. Advisory, compute-and-return, no persistence.

### Tokenization

`_tokenize`: ASCII-lowercase, split on runs of non-alphanumeric characters, drop tokens shorter than 3 characters and a small English stopword set (the, a, and, for, with, ...).

### The exact formula (`score_relevance`)

```
covered = (need & cand) | (need & tech)      # set intersections and union, from source line 134
score   = len(covered) / len(need)           # rounded to 4 decimals
```

where `need` is the tokenized need, `cand` is the tokenized candidate text (`KnowledgePage.title + " " + DNA.purpose`), and `tech` is the tokenized technology terms (`language_mix` keys + `package_managers` + `frameworks`). A tech match counts the same as a text match in the score. Empty need yields `(0.0, [])`. Matched terms are returned sorted as provenance.

This replaced a Jaccard over the candidate's whole vocabulary, which collapsed a correct #1 match to confidence 0.01 to 0.13 because the union denominator was dominated by the candidate's own verbosity (LES-023). Coverage answers "how much of what you asked for does this repo cover?" and is bounded 0 to 1.

### Tie-breaking (`_finalize`)

Sort key: confidence descending, then technology-hit count descending (`tech_hits = len(need_tokens & tech_terms)`), then repository name ascending (stable). Zero-score candidates are dropped. Results are capped at `limit` (default 5; the API route uses the default).

### Worked numeric example (real reality-test outcomes, LES-023 / LES-022)

From the fixed-needs regression gate (`scripts/reality_test_distillation.py`, deterministic provider, lexical path):

Need: `"container orchestration and scheduling"`
- Tokens: `{container, orchestration, scheduling}` ("and" is a stopword). `len(need) = 3`.
- kubernetes covered exactly one term, `container` (via "container-packaged" in its cleaned purpose, per LES-022).
- Score: 1/3 = 0.3333, reported as **0.333**. kubernetes ranks #1 (previously: no match at all, because its purpose was raw badge markdown).

Need: `"HTTP routing and middleware for a web API"`
- Tokens: `{http, routing, middleware, web, api}` ("and", "for" are stopwords; "a" is under 3 chars). `len(need) = 5`.
- gin covered `{http, routing, web, api}`; `middleware` was not covered.
- Score: 4/5 = **0.800**. gin ranks #1 (previously 3rd behind repos matching generic api/web noise).

Run the gate yourself (needs the cloned portfolio under `settings.repository_root`, default `./repositories`; run from the repo root):

```bash
cd /home/nerfherder/Dev/ArchetypeOS
PYTHONPATH=packages/aos_core python scripts/reality_test_distillation.py
```

It is a manual harness, not collected by pytest. Opt-in real-provider mode: `--provider claude_code` or `AOS_REALITY_PROVIDER=claude_code` (Orchestrator-only; invokes the local `claude` CLI).

## 5. Embedding tier (RFC-0010, AOS-EMBED-001/002)

AOS-EMBED-002 is merged to main via PR #73 as of 2026-07-06 (`git log origin/main` shows merge commit `ddb04cc`). One historical footnote: RFC-0010 as written specifies sentence-transformers (torch); the shipped implementation was revised to fastembed (ONNX) in the AOS-EMBED-002 plan revision (commit `05606e9`). The code is ground truth: fastembed.

| Fact | Value | Source |
|------|-------|--------|
| Model | `sentence-transformers/all-MiniLM-L6-v2` via fastembed (ONNX runtime), no torch | `packages/aos_core/aos_core/embeddings/_fastembed.py` |
| Dimensions | `EMBEDDING_DIM = 384` (single source of truth) | `packages/aos_core/aos_core/config.py` |
| Column | nullable `embedding vector(384)` on `knowledge_pages`; sqlite variant degrades to a JSON column | `models.py` (`EmbeddingColumn`), migration `0005` |
| Index | `ix_knowledge_pages_embedding_cosine`, ivfflat, `vector_cosine_ops`, `lists = 100` (Postgres only) | `apps/api/alembic/versions/0005_repository_embedding.py` |
| Config seam | `EMBEDDING_PROVIDER` env var / `settings.embedding_provider`, default `"deterministic"`; compose passes it to api AND worker | `config.py`, `docker-compose.yml` |
| Deterministic fallback | `DeterministicEmbedder.embed()` returns `None`; callers read `None` as "use the lexical path"; the column stays NULL. This is a real shippable backend, not a test double | `embeddings/__init__.py` |
| Real tier install | `fastembed==0.5.1` in `apps/api/requirements-embeddings.txt` (and `apps/worker/requirements-embeddings.txt`), NOT in the base requirements | those files |
| Vector properties | L2-normalized unit vector (clean cosine, matches `vector_cosine_ops`); empty/whitespace input returns `None`; a per-call embed failure returns `None`; a model load/import failure raises `RuntimeError` | `_fastembed.py` |
| Lazy import invariant | `get_embedder` imports `._fastembed` only when the provider is `"fastembed"`; nothing heavy loads on the default path. Do NOT add an eager fastembed/onnxruntime import to `embeddings/__init__.py` | `embeddings/__init__.py` docstring and code |
| Unknown provider | `get_embedder` raises `ValueError` (explicit misconfiguration, no silent fallback) | `embeddings/__init__.py` |

### How the semantic path activates in `recommend_reuse`

Both conditions must hold, otherwise the deterministic lexical Layer-0 path runs unchanged:

1. The embedder returns a non-`None` vector for the need (so never the deterministic embedder).
2. The DB dialect is `postgresql` (sqlite has no `<=>` operator).

Semantic confidence is calibrated, never a raw cosine (LES-023):

```
sem        = clamp(1 - cosine_distance, 0, 1)
confidence = round(max(coverage, 0.6 * sem + 0.4 * coverage), 4)   # _W_SEM = 0.6, _W_COV = 0.4
```

The `max(coverage, ...)` floor means a strong keyword match is never dragged below its honest lexical coverage. Candidates without an embedding fall back to their lexical coverage inside the semantic path. Any DB error degrades to the lexical path; `recommend_reuse` never raises. Lexical `matched_terms` remain the provenance in both paths, and the return schema is identical.

During distillation the embedded text is `title + " " + summary` (the same content the lexical path scores). On re-distill, the deterministic tier (embedding `None`) leaves any existing stored vector untouched; only a real embedder overwrites it.

Test gates: `apps/api/tests/test_embeddings.py` (hermetic, mocks fastembed), `test_fastembed_real.py` (`@pytest.mark.embedder`, skipped unless fastembed is installed), `test_pgvector_store.py` (`@pytest.mark.pgvector`, skipped unless `AOS_TEST_DATABASE_URL` points at Postgres with the `vector` extension; uses synthetic vectors and a fake embedder).

## 6. Council evidence classes and abstention semantics

Service: `packages/aos_core/aos_core/services/council.py`. Four personas (research_librarian, architecture_cartographer, technology_fitness_judge, security_agent), each with an evidence selector reading durable DB rows. Evidence item kinds by persona:

| Persona | Evidence kinds |
|---------|---------------|
| research_librarian | `research_note`, `decision`, `repo_distillation` (repository `KnowledgePage` rows, so distillation feeds the council) |
| architecture_cartographer | `architecture_node`, `framework`, `runtime_service` |
| technology_fitness_judge | `language`, `framework`, `package_manager`, `maturity` |
| security_agent | `risk_flag`, `security_decision` |

The rule-based Final Judge (`synthesize_verdict`) abstains to verdict `Insufficient evidence` when `total_evidence < MIN_EVIDENCE` (1) or aggregate confidence `< ABSTAIN_CONFIDENCE` (0.35). The verdict vocabulary has 8 entries (Accept, Accept with warnings, Reject, Defer, Research further, Simulate first, Escalate to human, Insufficient evidence).

### LES-019 (open as of 2026-07-06): evidence class must match question class

The first real council run (`.archetype/council/pydantic-ai-review.json`, narrated in `docs/COUNCIL_REALRUN_PYDANTIC_AI.md`) asked an adoption question about pydantic-ai but was fed only a structural scan of pydantic-ai's own repo. The council correctly abstained: verdict `Insufficient evidence`, confidence 0.0375, and its `follow_up` named exactly which evidence classes were missing (fitness comparison, production-readiness research, security review). A structural scan answers "how is this system built?"; an adoption question needs a research/decision corpus. Nothing yet gathers the named evidence and re-runs automatically; that loop is the campaign in `aos-evidence-loop-campaign`.

### Abstention blocks decision approval (verified HTTP statuses)

Service: `packages/aos_core/aos_core/services/decisions.py`; routes: `apps/api/app/routes/decisions.py`.

- `POST /council-reviews/{review_id}/draft-decision` drafts a `Decision` from a review (idempotent, one draft per review). An abstained review (verdict `Insufficient evidence` OR confidence below 0.35) yields status `needs_evidence`; otherwise `draft`.
- `POST /decisions/{decision_id}/approve` on a `needs_evidence` decision returns **HTTP 409** with a detail message telling you to gather primary evidence, re-run the council, and re-draft from a cleared-floor review. Only `draft` is approvable; any other status also 409s.
- `POST /decisions/{decision_id}/reject` is allowed from `draft` or `needs_evidence`; already approved/rejected 409s.
- Approval writes `approved_by`/`approved_at` and an `ApprovalRecord` (a named human, always).
- Council runs are async: `POST /projects/{project_id}/council-reviews` returns a job, results via `GET /council-reviews/{review_id}`.

## 7. Knowledge page types and vault layout

The repo vault is the source of truth; `sync_knowledge` (`packages/aos_core/aos_core/services/knowledge.py`, `POST /knowledge/sync`) re-derives `KnowledgePage` rows from it, so a DB reset loses nothing. `knowledge_root` defaults to `./knowledge`.

| page_type | Vault path pattern | validation_state values | Derived from |
|-----------|-------------------|------------------------|--------------|
| `repository` | `wiki/repositories/<slug>.md` | `derived` or `reasoned` (via distillation); sync from vault sets `derived` | `distill_repository`, or sync re-reading the vault file |
| `decision` | `wiki/decisions/<name>.md` | `approved` (Status block reads Accepted/Approved) else `raw` | ADR export (`POST /decisions/{id}/adr`) + sync |
| `lesson` | `wiki/lessons/LES-<n>.md` | the lesson's index status (e.g. `open`, `closed`) | `knowledge/wiki/lessons/index.md` table rows |

Notes:

- The model default for `validation_state` is `"raw"`.
- As of 2026-07-06 the committed tree has `knowledge/wiki/lessons/` and `knowledge/wiki/decisions/` but no committed `knowledge/wiki/repositories/` directory: distillation pages are runtime artifacts written into a writable local vault checkout. The compose stack mounts the vault read-only, so distillation there 409s by design.

## 8. Task tier guide (candidate)

Routing home is `aos-model-routing`; these labels are operator guidance with candidate status, scoped to this skill's domain.

| Task in this scope | Tier |
|--------------------|------|
| Look up a constant, formula, status value, endpoint, or page type from this reference | Haiku |
| Run the reality-test harness or the gated embedder/pgvector suites and interpret rankings | Sonnet |
| Wire or debug the fastembed tier on a node (env, extras install, model fetch) | Sonnet |
| Change summary-floor cleaning rules or anything touching `score_relevance` / confidence calibration | Opus |
| Redesign council evidence selectors, abstention floors, or the evidence-assembly loop (LES-019) | Opus |

## 9. Common mistakes

1. Reporting a raw cosine (or any raw similarity) as confidence. LES-023: confidence must stay coverage-like and bounded 0 to 1. The blend already enforces this; do not "simplify" it away.
2. Scoring with Jaccard over the candidate's full vocabulary. That penalizes descriptive distillations and collapses magnitudes; coverage of the need is the settled design.
3. Expecting the semantic path on sqlite or with the deterministic embedder. Both gates must pass (real vector AND postgresql dialect); otherwise you are on Layer-0 lexical, which is correct behavior, not a bug.
4. Setting `EMBEDDING_PROVIDER=fastembed` without installing `requirements-embeddings.txt`. The first embed raises a RuntimeError naming the fix; this is intentional (misconfiguration must surface, not silently degrade).
5. Adding an eager fastembed/onnxruntime/torch import to `aos_core/embeddings/__init__.py`. That breaks the hermetic CI invariant; the lazy-import structure is load-bearing.
6. Feeding a target-repo structural scan to the council for an adoption question and treating the abstention as a defect. The abstention is the Constitution working (LES-019); gather the named evidence classes instead.
7. Trying to approve a `needs_evidence` decision or treating its 409 as an API bug. The 409 is the governance gate.
8. Letting a summary floor emit badge/link markup or analogy prose "because something is better than nothing". LES-022 proved noise actively mis-ranks retrieval; the honest fallback string is the correct empty.
9. Running distillation against the compose stack's read-only vault mount and expecting a write. Use a writable local vault checkout; the 409 is by design.
10. Assuming a re-distill under the deterministic embedder wipes a stored vector. It does not: `None` embeddings leave the existing column value untouched.

## 10. Provenance and maintenance

Authored 2026-07-06 against branch `laptop/aos-selfheal-doc-loop` (HEAD = AOS-SELFHEAL-001, since merged as PR #80; nothing in this skill depends on that change). AOS-EMBED-002 verified merged to origin/main (PR #73).

Derived from: `packages/aos_core/aos_core/services/transfer.py`, `services/distillation.py`, `services/council.py`, `services/decisions.py`, `services/knowledge.py`, `packages/aos_core/aos_core/embeddings/__init__.py` and `_fastembed.py`, `packages/aos_core/aos_core/config.py`, `packages/aos_core/aos_core/models.py`, `apps/api/app/routes/{transfer,decisions,council,repositories,knowledge}.py`, `apps/api/alembic/versions/0005_repository_embedding.py`, `apps/api/tests/{test_transfer,test_distillation,test_embeddings,test_fastembed_real,test_pgvector_store}.py`, `scripts/reality_test_distillation.py`, `docs/rfc/RFC-0008*`, `RFC-0009*`, `RFC-0010*`, `docs/COUNCIL_REALRUN_PYDANTIC_AI.md`, `.archetype/council/pydantic-ai-review.json`, `knowledge/wiki/lessons/LES-019.md`, `LES-022.md`, `LES-023.md`.

Re-verification commands (run from the repo root; if any output disagrees with this file, the repo wins):

| Fact | Command |
|------|---------|
| Coverage formula and rounding | `grep -n "covered = " packages/aos_core/aos_core/services/transfer.py` |
| Blend weights 0.6 / 0.4 and max-floor | `grep -n "_W_SEM\|_W_COV\|max(coverage" packages/aos_core/aos_core/services/transfer.py` |
| Semantic-path gates (vector + postgresql) | `grep -n "dialect == \"postgresql\"" packages/aos_core/aos_core/services/transfer.py` |
| Tie-break order | `grep -n "results.sort" packages/aos_core/aos_core/services/transfer.py` |
| validation_state derived/reasoned | `grep -n "validation_state = " packages/aos_core/aos_core/services/distillation.py` |
| Summary floor budget/cap/fallback | `grep -n "_SUMMARY_BUDGET\|_SUMMARY_MAX\|_SUMMARY_FALLBACK" packages/aos_core/aos_core/services/distillation.py` |
| Reality-test gate numbers 0.333 / 0.800 | `grep -n "0.333\|0.800" knowledge/wiki/lessons/LES-023.md` |
| EMBEDDING_DIM 384 and default provider | `grep -n "EMBEDDING_DIM = \|embedding_provider" packages/aos_core/aos_core/config.py` |
| ivfflat cosine index | `grep -n "ivfflat\|vector_cosine_ops" apps/api/alembic/versions/0005_repository_embedding.py` |
| fastembed pin | `cat apps/api/requirements-embeddings.txt` |
| AOS-EMBED-002 merge status | `git log --oneline origin/main \| grep -i "AOS-EMBED-002\|pull request #73"` |
| Abstention floors 0.35 / 1 | `grep -n "ABSTAIN_CONFIDENCE = \|MIN_EVIDENCE = " packages/aos_core/aos_core/services/council.py` |
| needs_evidence approve 409 | `grep -n "status_code=409" packages/aos_core/aos_core/services/decisions.py` |
| LES-019 open/closed status | `sed -n "/## Status/,+2p" knowledge/wiki/lessons/LES-019.md` |
| Page types synced from vault | `grep -n "page_type=" packages/aos_core/aos_core/services/knowledge.py` |
