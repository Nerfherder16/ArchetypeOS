# RFC-0008 — Knowledge Distillation Engine: Repository Content Extraction (MVP)

## Status

**MVP landed (AOS-DISTILL-001).** The deterministic content-extraction MVP described below is implemented: `distill_repository` (`packages/aos_core/aos_core/services/distillation.py`) reads a scanned repo's real README, runs the LLM-free `extract_repo_knowledge` (provenance-tagged `title`/`summary`/`key_points`/`technologies`/`useful_for`), writes `knowledge/wiki/repositories/<slug>.md`, projects a re-syncable `KnowledgePage` (`page_type="repository"`), stamps `RepositoryDNA.purpose`, and is surfaced to the council via a research-evidence selector; `POST /repositories/{id}/distill` exposes it. Still deferred (see Non-goals): the Knowledge Transfer Engine, web tools, and the rich isolated `claude_code` extraction path.

Proposed (operator-directed 2026-07-06: "id say 2 [the content-extraction MVP] but … write as an rfc first"). Queued behind the current roadmap (Phase B — architecture semantics) per operator direction to "continue on with what we were doing prior … to keep in line with the roadmap." This RFC captures the design so it is not lost; it is **not** authorized for implementation yet.

## Summary

ArchetypeOS today ingests a repository as a **structural fingerprint** — the scanner (`repository_scanner.py`) reads file *extensions*, manifests, and the directory *tree*, never file **content**. The Agent Council (RFC-0005) then reasons over that fingerprint. This RFC introduces the missing upstream stage the operator's own docs already specify — the **Knowledge Distillation Engine** (`docs/KNOWLEDGE_DISTILLATION_ENGINE.md`): a stage that reads a repository's actual **content** (README, docs, source) and distills it into **durable, provenance-tagged knowledge** in the vault (`knowledge/wiki/repositories/`, `wiki/technologies/`, `wiki/patterns/`). This is the first concrete step toward the operator's founding intent: *"feed ArchetypeOS a repo → it outputs what is useful → the consumed knowledge lives in Obsidian for reuse on any repo."*

## Problem — the reality test that motivated this

Operator direction (2026-07-06): "make sure ingestion actually works and not just abstain every time," run on `cheahjs/free-llm-api-resources`. The pipeline was run end to end in-session (the `pydantic-ai` counterpart is committed at `.archetype/council/pydantic-ai-review.json`; the `free-llm` real-provider run is non-deterministic so its finding is recorded verbatim in LES-021 rather than as a committed artifact). Findings:

1. **Ingestion + scan + DNA work.** Real evidence was produced — `language_mix {Markdown, YAML, Python}`, `pip`, 3 architecture nodes, and an accurate risk flag ("code present, no tests"). The **deterministic** council over that evidence cleared the abstention floor (confidence **0.475**, "Escalate to human"). So the council is **not** "always abstain."
2. **The abstention is "right judge, wrong evidence."** `free-llm-api-resources` is a **curated catalog** whose entire value is the prose in its README (which providers, which rate limits). A structural fingerprint (`{Markdown, YAML, Python, pip}`) cannot recover value that was **never extracted**. The council is a *judge*; it was handed a fingerprint instead of the document.
3. **The extract-what-is-useful capability is unbuilt.** The operator's question — "is the point to break down whatever is fed in and pull out what is useful, stored in Obsidian for reuse?" — describes the **Knowledge Distillation Engine** + **Knowledge Transfer Engine**, both of which are *specs, not code*. The council (RFC-0005) is the **Decision/Judgment** layer (Layer 4), not the **extraction** layer (Layer 1–2).

### Corollary defect — provider context contamination (LES-021)

The real-provider (`claude_code`) run over `free-llm` **abstained** (confidence 0.2875) — and *why* exposed a defect: the `technology_fitness_judge`, whose evidence array was only `{Markdown, YAML, Python, pip}`, returned a summary describing **ArchetypeOS itself** ("FastAPI 0.115, SQLAlchemy 2.0, psycopg3, apps/worker, apps/scheduler … missed the JS/TS web app"). Those facts can only come from reading *this* repo's files. Root cause: `ClaudeCodeProvider` shells `claude -p …` in ArchetypeOS's own working directory, so the agent inherits `CLAUDE.md` + filesystem access and reasons about the wrong codebase — violating the council's "reason only from supplied evidence" contract. Recorded as **LES-021** (open). **This is a prerequisite for RFC-0008**: an extraction stage that also shells a model must run it **isolated** (empty cwd, no ambient project context, provenance-tagged inputs), or the contamination recurs at scale.

## The architectural decision this RFC settles — where tools live

The operator asked whether the system should be given tools (MCPs — firecrawl/exa — or "something better") and skills to help "digest." The decision:

- **Tools do NOT go inside the Council/judge agents.** We have live evidence (LES-021) that ambient tool/file access to a judge corrupts its reasoning and destroys **auditability** (you cannot reproduce what an agent chose to fetch) and **provenance** (evidence with no traceable source) — both non-negotiable per the Constitution.
- **Tools go in the upstream extraction/research stage**, which is deterministic-where-possible and **provenance-tagged**: every extracted claim cites the file (and line/section) it came from. The stage reads content, distills structured knowledge into the vault, and *then* the Council/Transfer engines reason over that durable, cited knowledge.
- **Choose the tool to the input class.** For a *repository*, the right tool is a **content-aware reader** (README/source → chunk → extract entities/APIs/patterns), not a web crawler. **firecrawl/exa are web-research tools** — they belong to the separate **Research Engine** (Layer 2, evaluating a technology against the outside world), a later RFC. "Something better" for the repo case is a local, code/doc-aware extractor plus (for the future Transfer Engine) a semantic index for relevance-to-a-target.

## Goals (MVP scope)

- A **`distill_repository(repository, knowledge_root, provider)`** service in `aos_core` that reads a bounded set of a scanned repo's **content** (README + top-level docs + a bounded sample of source/manifest files) and produces a **structured RepositoryDistillation**: `what_it_is` (one-paragraph purpose), `key_entities` (modules/APIs/commands), `notable_patterns`, `technologies` (grounded in real content, correcting the fingerprint's blind spots — cf. the fitness judge noting the scan "undercounted the stack"), `useful_for` (candidate reuse signals), and **provenance** (each item cites its source path).
- **Deterministic default + isolated real provider.** Same `Provider` seam as RFC-0005: a **deterministic** extractor (rule/heuristic-based over real file content — hermetic, CI-runnable) is the default; the `claude_code` adapter is used only on an authed node **and only after the LES-021 isolation fix** (empty cwd, no ambient context).
- **Durable, re-syncable vault output.** The distillation is written to `knowledge/wiki/repositories/<repo>.md` (Obsidian-compatible, the operator's "in Obsidian for reuse") and projected as a re-syncable `KnowledgePage` (`page_type="repository"`), reusing the RFC-0002/0004 read path (`sync_knowledge` already re-derives such pages — extend it, per the AOS-COUNCIL-PHASEC2A pattern).
- **Feeds the council.** A new evidence selector surfaces the distillation to the Council so a content-rich repo (like `free-llm`) yields a substantive review instead of a fingerprint abstention.
- **Provenance is mandatory.** No extracted claim without a `source` pointer. Verification over inference.

## Non-goals (explicitly deferred)

- **The Knowledge Transfer Engine** — "what is useful *for the target repo you are searching against*" — is a **relevance/retrieval** problem (represent a target need, match source-repo knowledge to it) and a **later RFC**. RFC-0008 builds the *extraction* that Transfer will later query; it does **not** add a target/need representation or semantic retrieval.
- **Web research tools (firecrawl/exa)** — the Research Engine, a separate RFC (Layer 2).
- **Embeddings / semantic index** — needed by Transfer; not by the extraction MVP. A local-first embedding store is a Transfer-phase concern.
- **The `ClaudeCodeProvider` isolation fix (LES-021)** is a **prerequisite**, tracked separately (small tactical fix); RFC-0008's real-provider path depends on it but the deterministic path does not.

## Connectors and the ingestion edge (n8n as a candidate)

The Distillation Engine's documented input list is not just repositories — it includes conversations, PRs, issues, Slack/ChatGPT/Claude exports, meeting transcripts, PDFs, and Obsidian notes. That is a **"connect to many messy external sources"** problem, not a reasoning problem, and it sits at the **edge** of the system. **n8n** (self-hostable, fits the CasaOS/Portainer runtime the vision already names) is a reasonable candidate there, under one firm boundary:

- **n8n captures and delivers; ArchetypeOS owns all reasoning, decisions, and provenance.** n8n watches external sources (Slack/Gmail/Drive/GitHub/RSS), normalizes events, and drops raw material into `knowledge/raw/` or an intake API — the deterministic ArchetypeOS pipeline takes over from there. It may also serve the **outbound/human-in-the-loop edge** (e.g., route "a decision needs approval" to Slack, whose approve action calls `POST /decisions/{id}/approve`).
- **n8n never holds judgment.** No council/distillation/decision logic goes into n8n's mutable visual flows — that would forfeit the auditability, determinism, provenance, and guardian discipline that define ArchetypeOS (LES-021 is the live evidence of what happens when reasoning loses provenance). The reasoning/governance core stays as versioned, tested code.
- **Do not adopt n8n for core orchestration.** The scheduler (RFC-0007) and worker + job queue (RFC-0006) already own scheduling and async execution deliberately; routing those through n8n would duplicate the control plane and risk split-brain over "what ran when."

**Not in RFC-0008's scope.** The extraction MVP operates on an already-cloned repo — pure internal code, no external connectors. n8n becomes relevant only when the broader input surface (Slack/transcripts/Drive) comes online; that is a **later connector RFC**, alongside the Research Engine. This section records the boundary decision (n8n at the edge, never the core) so it is not re-litigated.

## Alternatives considered

- **Give the council agents live tools (rejected).** Simplest to bolt on, but LES-021 shows it corrupts judgment and breaks auditability/provenance. Rejected on Constitution grounds.
- **LLM-summarize the whole repo in one shot (rejected for MVP).** No provenance, poor determinism, context-window bound on large repos. The chunked, cited extraction is auditable and scales.
- **Do nothing / richer structural scan only (insufficient).** Phase B (LES-013/014) improves the *fingerprint* but still never reads content — `free-llm` stays an abstention. Structural richness and content extraction are complementary, not substitutes.

## Risks

- **Provider contamination at scale (LES-021)** — mitigated by the isolation prerequisite + provenance requirement (a claim with no citable source is dropped).
- **Cost/latency of a real extractor** — mitigated by the deterministic default (CI + cheap path) and bounded file sampling.
- **Vault write discipline** — reuses the AOS-COUNCIL-PHASEC2A local-first pattern (writable checkout; `:ro` compose → graceful failure; re-syncable projection).

## Acceptance criteria (when implemented)

- Running distillation on a **content-rich, structurally-thin** repo (`free-llm-api-resources`) yields a structured vault page naming *what it is* ("a curated catalog of free LLM API providers …") with per-item provenance — not an abstention-grade fingerprint.
- The distillation is a re-syncable `KnowledgePage` and an Obsidian-readable `wiki/repositories/*.md`; a DB reset loses nothing.
- A council review that includes the distillation as evidence clears the abstention floor on `free-llm` where the fingerprint-only review did not.
- Hermetic (deterministic provider) in CI; the real-provider path runs only post-LES-021 on an authed node.

## Dependencies

- **LES-021** (ClaudeCodeProvider isolation) — prerequisite for the real-provider path.
- RFC-0002 (Knowledge System) / RFC-0004 (learning loop) — the vault + re-syncable `KnowledgePage` read path this extends.
- RFC-0005 (Council) — the consumer of the distilled evidence.
- `docs/KNOWLEDGE_DISTILLATION_ENGINE.md`, `docs/KNOWLEDGE_TRANSFER_ENGINE.md`, `docs/KNOWLEDGE_VAULT_STRUCTURE.md` — the pre-existing design this implements.

## Next steps

1. Land the current roadmap item (Phase B — architecture semantics) first, per operator direction.
2. Fix LES-021 (isolation) as a small tactical prerequisite.
3. Implement RFC-0008 MVP (deterministic extractor → vault page → council evidence selector), proven on `free-llm-api-resources`.
4. Future RFC: Knowledge Transfer Engine (target/need representation + relevance retrieval) — the "useful *for* the intended repo" half.
