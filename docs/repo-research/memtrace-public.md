# Repo Research: syncable-dev/memtrace-public

**Analyzed:** 2026-07-09  
**Stack:** Rust (core engine/binary), TypeScript (installer/skills), Python (benchmarks)  
**Activity:** Multiple commits per week; public repo synced from private main via `memtrace-sync-script`; latest push 2026-07-09

---

## Executive Summary (tight verdict)

**Fit verdict: partial-borrow / monitor — do NOT adopt as a dependency.**

**License bottom line:** Proprietary EULA. AOS may run the binary (personal/internal use only), may NOT modify source, redistribute, reverse-engineer, or build derivative works from it, and may NOT use it to build a competing product. This repo is a *-public* documentation and skills shell — the real engine (MemDB, Rust binary) is closed source and not in this repo.

**Local-first / telemetry reality:** Truly local in the most important sense (source code never leaves machine). But telemetry is opt-out, not opt-in: four streams ship to `memtrace.io` servers on every run. License validation and a heartbeat call hit Syncable servers on startup and every 15 minutes. Telemetry can be disabled via `MEMTRACE_TELEMETRY=off`; the heartbeat and license validation cannot be disabled (they are mandatory to use the software at all). This is an important privacy caveat for AOS's local-first posture.

**Bi-temporal structural memory — is it genuinely additive to AOS?** Yes, materially. The bi-temporal dimension (valid_from / valid_to per symbol, with episode replay and six temporal scoring modes) is something AOS's current scanner and Knowledge Graph do not have. AOS has churn metrics and a temporal model at the commit level, but not per-symbol version history queryable over time with multiple scoring algorithms. The cross-service HTTP topology detection (mapping which service calls which endpoint across repos) is also additive. However, the base structural graph (functions/classes/call edges/imports) significantly overlaps with AOS's existing architecture scanner and Neo4j graph.

**Top-2 integration options:**
1. Run as an MCP server alongside AOS agents (lowest friction, EULA-compliant, no code coupling). AOS agents gain temporal evolution queries and blast-radius analysis without AOS owning the indexer. Telemetry must be disabled for privacy posture.
2. Borrow the bi-temporal schema design and temporal scoring algorithm catalog as an architectural pattern for AOS's own scanner and Neo4j — no binary dependency, no license restriction on the *idea*.

**Top-3 risks:**
1. Proprietary EULA with no source access: zero ability to audit, modify, or self-host the engine. Vendor lock-in risk is high for a single commercial developer in private beta.
2. Mandatory network calls: license validation + heartbeat to syncable.dev servers on every startup. The software literally cannot run offline or without Syncable's servers being available. This is incompatible with a strict local-first / air-gapped deployment posture.
3. Bus factor / rug-pull: single vendor, private beta, v0.x. If Syncable pivots, shuts down, or changes license terms, AOS loses access to the feature and has no recourse.

---

## 1. License Analysis (LEAD)

**Full license text:** `LICENSE` file — "MEMTRACE END USER LICENSE AGREEMENT (EULA) — Version 1.0, Effective April 13, 2026. Copyright (c) 2026 Syncable Dev. All rights reserved."

This is a **proprietary end-user license** (not OSI-approved, not source-available, not BUSL/SSPL). It is bespoke, drafted by Syncable.

**Key grant clauses (Section 1):**
- Use in binary form only, for personal or internal business purposes.
- Use to index, analyze, and query codebases you own or have authorization to access.
- Use the bundled AI agent skills with compatible AI tools.

**Key restriction clauses (Section 2) — all prohibited:**
- Reverse engineering, decompiling, disassembling, or deriving source code.
- Modifying, adapting, translating, or creating derivative works.
- Redistributing, sublicensing, renting, leasing, lending, selling, or transferring the software or any rights.
- Removing proprietary notices.
- Using the software to build a competing product or service.
- Using the software in any manner that violates applicable laws.

**Section 3:** "The Software is licensed, not sold. Licensor retains all right, title, and interest."

**Section 4:** The AI agent skills (installed to `~/.claude/skills/`) are part of the Software and subject to the same terms. You may NOT extract, redistribute, or repurpose them independently.

**Section 5 (Data/Privacy):** Source code is processed locally and not transmitted unless you configure an external service connection. Telemetry may be collected (anonymous usage). The knowledge graph stays on your local machine.

**Section 8 (Liability cap):** Total aggregate liability capped at "the amount you paid for the Software (if any) in the preceding 12 months." During the free private beta, this is effectively $0.

**Section 9 (Termination):** Agreement terminates automatically if you breach any term. On termination, you must cease all use and destroy all copies.

**AOS legal matrix:**

| Action | Permitted? |
|---|---|
| (a) Run the binary for internal use | YES — Section 1(a) |
| (b) Self-host the binary on AOS infrastructure | YES for internal use; NO for redistributing to others |
| (c) Vendor/modify its source code | NO — Sections 2(a) and 2(b); source is not provided |
| (d) Use it commercially within AOS as an internal tool | YES, likely covered under "internal business purposes" |
| (e) Build a product that competes with memtrace | NO — Section 2(e) |
| (f) Use its architecture design/schema ideas in AOS | YES — ideas are not copyright-protected; only the specific expression/code is |
| (g) Redistribute it to AOS users | NO — Section 2(c) |

**Bottom line:** AOS can legally run memtrace as an internal tooling aid. AOS CANNOT vendor it into a product, ship it to users, modify its code, or build competing structural-memory features that "use" the software (rather than being independently implemented). This bounds integration to "run the binary as an MCP server that AOS agents query." Borrowing the *design ideas* (bi-temporal schema, scoring algorithm catalog, cochange detection, Louvain community detection) for a purpose-built AOS implementation is not restricted.

---

## 2. What It Actually Is and Architecture

### Is This Repo the Engine or a Client Shell?

This is a **documentation and skills shell, not the engine source**. Confirmed by:

1. README states: "Indexer + database (MemDB) are closed-source." (`README.md`, License & ownership section)
2. The repo contains no Rust source code — only documentation, benchmark Python scripts, and plugin/skill markdown files.
3. Installation is `npm install -g memtrace`, which downloads a pre-built platform-specific binary (`@memtrace/darwin-arm64`, `@memtrace/linux-x64`, `@memtrace/win32-x64`). The source of this binary is not in this repo.
4. The commit log is almost entirely `docs(skills): sync from memtrace main repo` — this repo is a one-way sync target from a private internal repo.
5. TELEMETRY.md references `crates/memtrace-mcp/src/telemetry.rs` as the pipeline source, but that path does not exist in this public repo.

**This repo contains:**
- README + docs/ (architecture, CLI reference, MCP tools, telemetry)
- BENCHMARKS-*.md and RELEASE-NOTES-*.md (public changelog/results)
- `plugins/memtrace-skills/skills/` — 30+ skill markdown files (SKILL.md prompt templates that teach agents how to use the MCP tools)
- `benchmarks/` — Python benchmark harness (MIT-licensed subset, publicly runnable)
- `.claude-plugin/marketplace.json` — Claude plugin marketplace metadata

**The real engine** is a proprietary Rust binary distributed via npm. The public repo is the integration surface (skills, docs, benchmarks) and a marketing presence.

### Architecture (from docs/architecture.md)

```
  AI Tool (Claude Code, Cursor, Codex...)
       |
       | MCP JSON-RPC (stdio or streamable-HTTP)
       v
  memtrace mcp process
  (attaches to owner, or becomes owner)
       |
       v
  WORKSPACE OWNER (one per .memdb directory)
  - MemDB: embedded graph engine (Rust, proprietary, no external service)
  - Tree-sitter AST parser (20+ languages)
  - ONNX Runtime: local embedding model (jina-code-v2, bge-small, etc.)
  - Tantivy: BM25 full-text index
  - HNSW: vector nearest-neighbor index
  - Cross-encoder reranker (bge-reranker-base)
  - libgit2: git history analysis for bi-temporal layer
  - Louvain community detection
  - PageRank / betweenness centrality
       |
       v
  ON-DISK STATE (.memdb/ in project root)
  - WAL + paged records (nodes, edges, episodes, vector blobs)
  - HNSW index (persisted since v0.4.0)
  - BM25 Tantivy segments
  - Bi-temporal episode log (valid_from/valid_to per commit)
```

Three entry points into the same local graph:
- `memtrace index <path>` — one-shot, no UI
- `memtrace start` — full owner: UI dashboard at localhost:3030, file watcher, live incremental indexing
- `memtrace mcp` — agent-only: starts or attaches to an owner, serves MCP tools

**MemDB** is the custom embedded graph engine (Rust). It is not Neo4j, not SQLite, not PostgreSQL — it is a proprietary embedded store with a WAL, property indexes, HNSW vector index, and BM25 Tantivy for full-text. Storage is 100% local (`.memdb/` in the project root). No external database service required.

### Is Storage Truly Local?

**Yes, for code and graph data.** Confirmed via PRIVACY.md and docs/architecture.md:
- AST parsing: local (Tree-sitter compiled into the binary)
- Graph construction: local (MemDB embedded)
- Vector embeddings: local by default (ONNX Runtime via fastembed — CoreML on Apple Silicon, CPU elsewhere)
- Full-text search: local (Tantivy BM25 on disk)
- Git history analysis: local (libgit2 vendored)
- MCP queries: local graph traversal

**What does go to Syncable's servers:**
1. License validation: `POST https://www.memtrace.io/api/device/auth` — sends license key + machine hostname. Required on startup; cannot be disabled.
2. Usage heartbeat: `POST https://www.memtrace.io/api/device/heartbeat` — sends aggregate integer counts (total nodes, edges, episodes, repos). Every 15 minutes while running; cannot be disabled without violating license (it is not gated by `MEMTRACE_TELEMETRY=off`).
3. Embedding model download: one-time download from HuggingFace Hub (~340 MB ONNX model).
4. Product telemetry: `POST https://memtrace.io/api/telemetry/ingest` — app-start events, indexing durations, crash reports, WARN/ERROR log lines, Rail routing-quality buckets. Opt-out: `MEMTRACE_TELEMETRY=off`.

**The optional "Weekly Memtrace Receipt" feature** (off by default, requires account-level opt-in) does include symbol name surface in the heartbeat. This is the one exception to "no symbol names leave the machine."

**With `MEMTRACE_TELEMETRY=off`:** telemetry is stopped. License validation and heartbeat still run. This is the minimum network footprint for a privacy-conscious deployment. The source code, symbol names, embeddings, file paths, and graph data itself never leave the machine under any configuration (per PRIVACY.md Section 5).

### Zero-LLM Claim: Confirmed

Indexing and querying make no LLM calls. Confirmed by:
- docs/architecture.md: "It doesn't talk to LLM APIs. Memtrace's pipeline uses only local ONNX models."
- README comparison with Mem0/Graphiti: "it indexes 1,500 files in 1.2–1.8 seconds for $0.00 — no LLM calls, no API costs, no rate limits. Native Tree-sitter AST parsers resolve deterministic symbol references (CALLS, IMPLEMENTS, IMPORTS) locally."
- Embedding is done via ONNX Runtime with local model weights, not via API calls to an LLM provider.

The embedding step (fastembed / jina-embeddings-v2-base-code) is NOT an LLM inference step — it is a sentence embedding model (~340 MB ONNX) running locally. This is deterministic and produces no interpretive output.

---

## 3. Capabilities

### Structural Queries an Agent Can Make

**Search and Discovery:**
- `find_symbol` — exact/fuzzy symbol lookup by name (sub-millisecond latency)
- `find_code` — hybrid BM25 + vector + graph + cross-encoder rerank ("find where authentication happens")
- `get_symbol_context` — 360-degree view: callers, callees, community, processes, recent changes

**Relationship / Impact:**
- `analyze_relationships` — bulk caller/callee/neighbor analysis
- `get_impact` — blast radius with transitive callers and risk rating
- `find_dependency_path` — path between two symbols in the call graph
- `find_bridge_symbols` — betweenness-centrality chokepoints
- `find_central_symbols` — PageRank-ranked important symbols

**Temporal / Bi-temporal:**
- `get_evolution` — symbol history with six scoring modes (compound, impact, novelty, recent, directional, overview)
- `get_timeline` — full bi-temporal version history per symbol (valid_from/valid_to per commit)
- `get_changes_since` — what changed between two dates
- `detect_changes` — given a git diff, classify affected symbols
- `get_cochange_context` — files/symbols that historically change together (hidden coupling)
- `get_episode_replay` — exact graph state at a past commit
- `record_external_episode` — inject non-file events (CI run, deploy) into the temporal history

**Architecture / Quality:**
- `list_communities` — Louvain-detected module clusters
- `get_codebase_briefing` — prose summary of the codebase
- `get_repository_stats` — counts, language distribution
- `find_dead_code` — zero-caller symbols
- `calculate_cyclomatic_complexity`, `find_most_complex_functions`

**API Topology (cross-repo):**
- `find_api_endpoints` — HTTP endpoints detected across 15+ frameworks
- `find_api_calls` — where an endpoint is called from (including cross-repo)
- `get_api_topology` — directed graph of which services call which endpoints
- `get_service_diagram` — Mermaid diagram output

**Index Management:**
- `index_directory` — parse, resolve, embed (async with `check_job_status`)
- `watch_directory` — live incremental re-index on file save (~30-50 ms p95)
- `execute_cypher` — direct graph queries (Cypher-like syntax against MemDB)

**Code Review (v0.4.62+):**
- `review_github_pr` — local-first PR review using the graph; posts comments via GitHub App

### Languages Supported

Programming: Rust, Go, TypeScript, JavaScript, Python, Java, C, C++, C#, Swift, Kotlin, Ruby, PHP, Dart, Scala, Perl, Lua (17 full AST languages).

Infrastructure: YAML, HCL/Terraform, JSON, TOML, SQL (PostgreSQL RLS, Drizzle/Prisma schema edges).

Framework-aware scanners for HTTP routing (Express, FastAPI, Flask, Django, Gin, Actix, Rails, NestJS, Vapor, Encore, and ~10 more), frontend HTTP clients (RTK Query, TanStack Query, SWR, URLSession, axios, fetch), CI (GitHub Actions with `needs:` edges), Terraform modules, Helm, K8s manifests, package.json scripts, Cargo.toml, pyproject.toml.

### Benchmark Claims (BENCHMARKS-v0.3.22.md — verified, methodology explained)

Against Python AST ground truth (never Memtrace's own index), isolated per-adapter processes:

| Axis | Memtrace | GitNexus | ChromaDB |
|---|---|---|---|
| RSS (mempalace) | 26.2 MB | 31.0 MB | 1,060 MB |
| avg query latency | 0.07 ms | 8.95 ms | 54.6 ms |
| HEAD index time (django 3.3k files) | 13.6 s | 48.4 s | 268.7 s |
| acc@1 (mempalace) | 96.6% | 97.0% | 62.4% |
| precision@10 | 0.967 | 0.702 | 0.188 |

Memtrace trails GitNexus by ~0.4-1.7 pp on acc@1 — a deliberate trade for structural (canonical-first) ranking. On latency, RSS, and index speed it wins decisively.

---

## 4. Privacy / Telemetry

### Data Flows (confirmed from PRIVACY.md and TELEMETRY.md)

**Stays local (never transmitted):**
- Source code, file contents
- Symbol names, embeddings, file paths, AST data
- Repository names, paths, remote URLs
- Branch names, commit messages, git history
- Search query text
- Which files/symbols matched a search
- GitHub PR URLs, review bodies, reviewer identities

**Goes to Syncable servers:**

| Stream | Endpoint | Can opt out? |
|---|---|---|
| License validation | `POST https://www.memtrace.io/api/device/auth` | NO — software won't run without it |
| Usage heartbeat | `POST https://www.memtrace.io/api/device/heartbeat` | NO — aggregate counts (no symbol names by default) |
| Product telemetry | `POST https://memtrace.io/api/telemetry/ingest` | YES — `MEMTRACE_TELEMETRY=off` |
| Rail shadow (routing quality buckets) | Same telemetry endpoint | YES — `MEMTRACE_RAIL_SHADOW=off` |

**Telemetry when enabled includes:** app-start events, indexing/embedding durations, panic reports, WARN/ERROR log lines (sanitized), Rail routing quality buckets (no search text, just pattern shape/hit/miss/bucketed score/yes-no relevance).

**Telemetry storage:** Postgres tables on memtrace.io infrastructure. Retention policy TBD (not yet published). Access restricted to @syncable.dev accounts.

**Crash reports:** Stored locally in `~/.memtrace/telemetry/queue.jsonl` first, flushed on next run. If `MEMTRACE_TELEMETRY=off`, file is still written (for local debugging) but never shipped.

**Privacy posture for AOS:** With `MEMTRACE_TELEMETRY=off`, AOS gets: no crash/error/usage telemetry, no Rail buckets. It still gets: mandatory license validation (license key + hostname) and heartbeat (aggregate integer counts only). This is acceptable for a developer tool, but is not fully air-gappable. AOS's local-first principle is _substantially_ honored but not absolutely. The mandatory heartbeat is the sticking point for strict privacy requirements.

**Inspectability:** Users can read the pending queue at `~/.memtrace/telemetry/queue.jsonl` before it ships. This is a meaningful transparency feature.

---

## 5. File Inventory

```
memtrace-public/
├── LICENSE                     # Proprietary EULA — read before anything else
├── README.md                   # Full product overview, benchmarks, install guide
├── PRIVACY.md                  # Data flow summary (3 types of network calls)
├── TELEMETRY.md                # Detailed telemetry spec with 4 streams
├── CONTRIBUTING.md             # Bug reports, feature requests, skills PRs welcome
├── BENCHMARKS-v0.3.22.md       # 1000-query symbol benchmark vs GitNexus/ChromaDB/CGC
├── BENCHMARKS-v0.3.29.md       # Hybrid retrieval benchmark (3K queries, Django)
├── RELEASE-NOTES-v0.3.85.md    # Historical
├── RELEASE-NOTES-v0.3.89.md    # Session ledger, watches.json, LeanCTX context compression
├── RELEASE-NOTES-v0.4.0.md     # Boot architecture rewrite, embedder flexibility
├── RELEASE-NOTES-v0.4.62.md    # Code review workflow, GitHub App, multi-language rules
├── docs/
│   ├── architecture.md         # MOST IMPORTANT: full system architecture diagram and internals
│   ├── tools.md                # Complete MCP tool catalogue with args/types
│   ├── data-directories.md     # Every path memtrace creates + what to delete
│   ├── mcp-and-transports.md   # stdio vs streamable-HTTP, multi-agent topology
│   ├── embedding-providers.md  # Local ONNX, remote OpenAI/Voyage/Ollama, Matryoshka
│   ├── environment-variables.md # Full env var reference
│   ├── cli-reference.md        # All CLI subcommands
│   ├── getting-started.md      # Quick setup
│   ├── code-reviewer.md        # PR review feature
│   ├── leanctx-native.md       # Context compression modes
│   ├── workflows.md            # Agent workflow patterns
│   ├── workspaces.md           # Multi-repo workspace setup
│   ├── indexing-and-ignore-rules.md
│   ├── performance-tuning.md
│   ├── telemetry-compliance-datasheet.md  # Full compliance/audit reference
│   └── troubleshooting.md
├── benchmarks/
│   ├── README.md               # Benchmark methodology (MIT-licensed subset)
│   ├── benchmark_full.py       # Full comparison harness (Python, MIT)
│   ├── bench_memtrace_only.py  # Memtrace-only runner
│   ├── benchmark_results.json  # Raw results
│   ├── datasets/, fair/, runners/, suite/ — test corpora and harness scripts
│   └── swebench-retrieval/     # SWE-Bench retrieval integration
├── plugins/
│   └── memtrace-skills/
│       ├── skills/             # 30+ SKILL.md prompt templates
│       │   ├── memtrace-search/, memtrace-evolution/, memtrace-impact/...
│       │   ├── memtrace-fleet-coordination/   # multi-agent intent/conflict resolution
│       │   ├── memtrace-decision-memory/      # Cortex decision memory
│       │   ├── memtrace-cochange/             # hidden coupling detection
│       │   ├── memtrace-code-review/          # PR review workflow skill
│       │   └── ... (30 total skill directories)
│       └── references/         # Reference docs for skills
└── .claude-plugin/
    └── marketplace.json        # Claude plugin marketplace metadata
```

---

## 6. Integration Fit with ArchetypeOS

### AOS Subsystem Mapping

**AOS Repository Scanner / Repository Intelligence**

AOS scans repos and builds an architecture graph: `contains` edges, manifest/dependency edges, compose/service edges, stamps RepositoryDNA, computes churn/temporal metrics.

Memtrace overlap: Both build a structural graph from source code. AOS extracts file/directory/dependency relationships at the architectural level. Memtrace extracts symbol-level relationships (function, class, method, CALLS/IMPLEMENTS/IMPORTS edges). These are different granularity levels — AOS is architecture-scale, memtrace is symbol-scale.

**Additive:** Memtrace's symbol-level call graph, blast-radius analysis, and cross-service HTTP topology detection go substantially deeper than AOS's file-level scanner. AOS's scanner does not do live watch, incremental re-index, or cyclomatic complexity at the symbol level.

**Genuinely additive (not duplicated in AOS):**
- Bi-temporal per-symbol version history with episode replay
- Six temporal scoring modes (impact, novelty, recency, directional, compound, overview)
- Cochange detection (files that historically move together)
- Louvain community detection at symbol level
- PageRank / betweenness centrality at symbol level
- Cross-repo HTTP API topology (which service calls which endpoint)
- Dead code detection (zero-caller symbols)
- Cyclomatic complexity per symbol

**AOS Knowledge Graph (Neo4j)**

AOS stores relationships between projects, technologies, decisions, repos, patterns, risks. Neo4j stores architecture-level entities.

Memtrace overlap: Memtrace's graph is code-structure-specific (symbols, edges, episodes). This is a DIFFERENT graph than AOS's Engineering Intelligence Graph. The AOS KG tracks engineering decisions and patterns; Memtrace tracks code structure and evolution.

**Assessment:** Additive, not overlapping. Memtrace does not model the things AOS's KG models (decisions, risks, patterns, tech choices). They operate at orthogonal granularities. The bi-temporal symbol graph Memtrace builds could potentially FEED the AOS KG as a data source.

**AOS Architecture Studio / Architecture Spine Graph**

The Architecture Spine Graph models high-level components, services, and their relationships as an editable model. Memtrace's API topology (`get_api_topology`, `get_service_diagram`) detects cross-service HTTP call relationships and produces Mermaid diagrams.

**Additive:** Memtrace could feed the Architecture Spine Graph with detected service dependencies. This is currently a manual/agent-driven process in AOS; memtrace automates it from code analysis.

**AOS Agent Memory / Knowledge Read Path**

AOS has KnowledgePage projections and a lessons system. Memtrace is described as "structural memory for AI coding agents" but its memory is different: it is code-structure memory (symbols, call graphs, temporal history), not semantic/episodic agent memory.

**Complementary (not competing):** AOS's lessons/KnowledgePage track engineering decisions and learnings. Memtrace tracks code structure evolution. An AOS agent that has both can answer "what did we decide about X" (AOS KG) AND "what has happened to the code implementing X over time" (Memtrace). They are complementary, not redundant.

**AOS Stack: Neo4j / Qdrant / tree-sitter**

- Neo4j: AOS uses this for the KG. Memtrace uses MemDB (custom embedded). Memtrace does NOT require or use Neo4j — it is a separate embedded store. No overlap on the database side.
- Qdrant: AOS uses this for vector search. Memtrace uses HNSW embedded in MemDB. No conflict — they are separate vector stores for different content.
- Tree-sitter: AOS already uses tree-sitter-style scanning. Memtrace also uses Tree-sitter. This is a partial overlap on the parsing layer. Both would parse the same code, separately.

**Summary of additive vs overlapping:**

| Capability | AOS has it? | Memtrace | Assessment |
|---|---|---|---|
| File/directory architecture graph | Yes (scanner) | No | AOS retains |
| Symbol-level call graph | No | Yes (CALLS/IMPLEMENTS edges) | ADDITIVE |
| Bi-temporal per-symbol history | No | Yes (valid_from/valid_to per commit) | ADDITIVE |
| Episode replay (graph at past commit) | No | Yes | ADDITIVE |
| Temporal scoring modes | No | Yes (6 modes) | ADDITIVE |
| Cochange detection | No | Yes | ADDITIVE |
| Cross-service HTTP topology | No (or partial) | Yes (framework-aware) | ADDITIVE |
| Dead code detection | No | Yes (zero-caller) | ADDITIVE |
| Cyclomatic complexity | No | Yes | ADDITIVE |
| Louvain community detection | No | Yes | ADDITIVE |
| PageRank / betweenness | No | Yes | ADDITIVE |
| Hybrid BM25 + vector code search | Partial (Qdrant) | Yes (local embedded) | OVERLAPPING |
| Knowledge graph (decisions, patterns) | Yes (Neo4j) | No | AOS retains |
| Semantic/episodic agent memory | Yes (Recall) | No | AOS retains |
| Architecture model (editable) | Yes (Spine) | No (read-only analysis) | AOS retains |

---

## 7. Integration Options

### Option A: Run as MCP Server — AOS Agents Query Memtrace

**What:** AOS agents (especially the Repository Intelligence and Architecture Studio agents) add memtrace as an MCP server. Agents call memtrace tools for temporal evolution queries, blast-radius analysis, cochange detection, and API topology detection.

**Setup:**
```json
{
  "mcpServers": {
    "memtrace": {
      "command": "memtrace",
      "args": ["mcp"],
      "env": { "MEMTRACE_TELEMETRY": "off" }
    }
  }
}
```

Requires: npm install, license key (private beta — waitlist at memtrace.io), `memtrace index <project>` per repo.

**What AOS gains:** Symbol-level structural memory, bi-temporal evolution queries, blast-radius analysis (what breaks if I change X), cochange patterns, cross-service HTTP topology, dead code detection, community detection, and the full 25+ MCP tool surface — all without AOS owning the indexer or its tech debt.

**Effort:** Low (1-2 days to wire in and validate). No code coupling to memtrace internals.

**Risk:** High vendor dependency. Private beta — access not guaranteed. If Syncable changes license or goes out of business, AOS loses this capability entirely. License prohibits using it to build a competing product, which could be interpreted broadly given AOS is an Engineering Intelligence Platform.

**EULA compatibility:** Yes, assuming AOS is using it for "internal business purposes" to analyze codebases AOS has authorization to access. AOS is NOT redistibuting the binary to end users.

**Local-first / privacy:** Substantially honored with `MEMTRACE_TELEMETRY=off`. Mandatory heartbeat (aggregate counts) cannot be disabled. Source code never leaves the machine.

**Coupling:** Zero code coupling. JSON-RPC via MCP. Decoupled by protocol.

### Option B: Borrow Bi-Temporal Schema and Temporal Scoring Design

**What:** Use memtrace's documented architecture — bi-temporal valid_from/valid_to per symbol, six scoring algorithm catalog (impact/novelty/recency/directional/compound/overview), Structural Significance Budgeting, cochange pattern detection, episode-based version history — as a blueprint for extending AOS's own tree-sitter-based scanner and Neo4j graph.

**What AOS gains:** The *capability* without the vendor dependency. AOS builds its own bi-temporal layer on top of its existing scanner and Neo4j, borrowing the conceptual model from memtrace's docs. The schema ideas are not copyrightable.

**Effort:** High (2-4 weeks engineering). Requires extending the AOS scanner to stamp valid_from/valid_to on every symbol change and store this in Neo4j, then implementing temporal scoring algorithms.

**Risk:** Low for dependency, high for implementation correctness. Building a bi-temporal graph engine is non-trivial.

**EULA compatibility:** Yes — this is independently implementing a design concept, not using the software. Legal.

**What to borrow specifically:**
- The bi-temporal edge model: every symbol gets `valid_from` / `valid_to` tied to a git commit episode
- Six scoring modes applied to symbol evolution (documented in README's Temporal Engine section)
- Structural Significance Budgeting: surface the minimum set of changes covering >=80% of total significance
- Cochange detection: git log analysis for file coupling
- Cross-service HTTP topology: framework-aware endpoint detection mapped to call sites

### Option C: Hybrid — MCP Short Term, Own Implementation Long Term

**What:** Use memtrace via MCP now to validate that bi-temporal structural memory is genuinely useful to AOS agents. If it proves out, implement independently in AOS (Option B). This avoids premature investment while building evidence.

**Effort:** Low now + High later. Risk-managed.

**Recommended approach:** Start with Option C.

### Option D: Reject — Monitor Only

**What:** Given the proprietary EULA, mandatory network calls to Syncable, private-beta access requirement, and the conceptual overlap with AOS's existing scanner investment, choose not to integrate at all. Monitor the project for open-source re-release or license change.

**When appropriate:** If AOS has strict local-first requirements (no network calls to third-party servers), if the private beta waitlist is a blocker, or if legal review of the EULA is unfavorable.

---

## 8. Risks and Rough Edges

### Risk 1: Proprietary EULA with Closed-Source Engine (CRITICAL)

The binary is closed-source, the EULA is proprietary, and Section 2(e) prohibits using it to build a competing product. AOS is an Engineering Intelligence Platform that could be construed as competing with memtrace's "structural memory for AI coding agents" positioning. This is a legal risk that warrants review before deeper integration. If Syncable asserts that AOS + memtrace = competing product, Section 9 allows automatic termination of the license.

### Risk 2: Mandatory Network Calls to Syncable Servers (HIGH)

License validation (`POST /api/device/auth`) and heartbeat (`POST /api/device/heartbeat`) are mandatory and cannot be disabled. The software requires access to memtrace.io servers to start and to stay running. This is incompatible with:
- Air-gapped deployment environments
- Strict zero-egress network policies
- Any scenario where memtrace.io is unavailable (server outage, company shutdown, internet connectivity loss)

AOS's local-first principle is "local-first preferred when practical" — this dependency on Syncable's servers means memtrace is not truly local-first in the hosting/network sense, only in the code-data-processing sense.

### Risk 3: Private Beta / Single Vendor Bus Factor (HIGH)

Memtrace is in private beta (v0.3-v0.4). Access requires joining a waitlist. A single commercial vendor (Syncable Dev, Copenhagen) is the sole developer. The public repo is a docs/skills shell — the real engine is fully internal. Risks:
- Waitlist may not grant access on AOS's timeline
- Vendor pivot, funding issues, or shutdown ends the integration
- License terms can change at any time (no OSI license protection)
- No fork/self-host path exists (source not available)

### Risk 4: Tree-Sitter Double-Parsing (MEDIUM)

AOS already uses tree-sitter (or similar) for repo scanning. If both AOS's scanner and memtrace independently parse the same repos, there is redundant work and potential for conflicting results. This is manageable but adds operational complexity.

### Risk 5: Large Store Startup Costs (MEDIUM)

Full pipeline (parse + embed + replay) for Django-class repos takes ~500 seconds per docs. Full replay of git history is expensive. The v0.4.0 boot rewrite improves incremental startup but cold-start on large repos remains heavy. AOS agents that depend on memtrace being available immediately may face startup latency.

### Risk 6: Private Beta Maturity (MEDIUM)

At v0.4.x, memtrace is not yet stable. Release notes document active issues: large-store vector attach stalls, semantic cache startup hardening still in progress, relation rendering incomplete in the UI, multi-repo startup clarity gaps. The benchmark methodology is still being refined (BENCHMARKS-v0.3.22.md explicitly describes bugs in earlier runs that were fixed).

### Rough Edges Found in Docs

- `memtrace service install` / `memtrace daemon` removed in v0.6.10 — some external tutorials may be outdated.
- `weekly Memtrace Receipt` feature requires account-level opt-in and does send symbol names to the heartbeat — must be confirmed off.
- Large `.memdb` stores (Django-class: 700 MB to 1 GB) require 10-20 GB free disk per the requirements table.
- Pre-AVX2 CPUs have a separate binary path (docs/pre-avx2-cpus.md) — relevant for older CI machines.
- Remote embedding providers (OpenAI, Voyage) do transmit symbol bodies (~1500 chars per symbol) over HTTPS to the provider. Default local provider avoids this.

---

## 9. Recommendation

### Summary

Memtrace is a technically impressive, well-documented proprietary tool that offers genuine capabilities AOS does not currently have: bi-temporal per-symbol version history, episode replay, temporal scoring algorithms, cross-service HTTP topology detection, and deep symbol-level blast-radius analysis. The zero-LLM-call, deterministic, local indexing approach strongly aligns with AOS's "verification preferred over inference" principle.

However, the proprietary EULA with closed-source engine, mandatory network calls to Syncable servers, private-beta access requirement, and single-vendor lock-in make deep integration high-risk. The right short-term move is conservative validation; the right long-term move is independent implementation of the genuinely valuable bi-temporal design.

### Evidence

- LICENSE: Proprietary EULA, no source access, no competing-product use (Section 2(e)).
- PRIVACY.md: License validation and heartbeat are mandatory network calls, confirmed not disableable.
- docs/architecture.md: Confirms truly local code processing; engine is embedded (no Neo4j/Postgres).
- README.md: "Indexer + database (MemDB) are closed-source" — confirms public repo is a shell.
- Commit log: All recent commits are `docs(skills): sync from memtrace main repo` — confirms this is a sync target, not the engine source.
- BENCHMARKS-v0.3.22.md: Benchmark methodology is honest and well-documented; claims are plausible but self-reported.
- TELEMETRY.md: Four telemetry streams, only one (telemetry events) is opt-out; two (license, heartbeat) cannot be disabled.

### Recommendation: partial-borrow / monitor

**Immediate actions (1-2 weeks):**
1. Join the waitlist at memtrace.io to assess access feasibility and beta timeline.
2. If access is granted, run a private-beta pilot on the AOS codebase itself with `MEMTRACE_TELEMETRY=off`. Test specifically: `get_evolution`, `get_impact`, `get_cochange_context`, and `get_api_topology`. Document whether the bi-temporal tools surface genuinely new insights versus what AOS's scanner already provides.
3. Have legal review Section 2(e) against AOS's product positioning. This is the key legal ambiguity.

**Medium-term (1-3 months):**
4. If pilot is positive and legal clears: adopt Option A (MCP server for AOS agents) with `MEMTRACE_TELEMETRY=off` and treat it as an optional enhancement, not a core dependency. Do not couple AOS architecture to memtrace APIs.
5. Begin designing AOS's own bi-temporal extension to the existing scanner: add `valid_from`/`valid_to` to the scanner output model and Neo4j schema. This de-risks the vendor dependency over time.

**Long-term:**
6. If memtrace releases source or adopts an OSI license, re-evaluate for deeper integration or contribution.
7. If memtrace remains proprietary and AOS's scanner bi-temporal work progresses, deprecate the MCP dependency.

### Alternatives Considered

- **Graphiti (AGPL):** Already evaluated; AGPL license was decisive against it. Memtrace is not better on license (proprietary) but is better on local-first (no LLM calls, truly embedded, not cloud-first).
- **GitNexus:** Used as a benchmark comparison in memtrace's own benchmarks. Lower latency/precision than memtrace per benchmarks; not evaluated independently.
- **Build from scratch on Neo4j:** High effort but gives AOS full control. The bi-temporal schema design is borrowable from memtrace's docs.

### Pros and Cons

**Pros:**
- Genuine bi-temporal capability AOS currently lacks
- Zero LLM calls aligns with AOS's determinism preference
- MCP-native: minimal integration friction with Claude Code
- Extremely fast at scale (26 MB RSS, sub-ms symbol lookup)
- Comprehensive language and framework coverage (20+ languages, framework-aware HTTP detection)
- 25+ MCP tools covering temporal, impact, quality, topology domains
- Honest benchmarking methodology (open harness, external ground truth)

**Cons:**
- Proprietary EULA, closed source — no audit, no fork, no modification rights
- Mandatory network calls to Syncable servers (license + heartbeat) cannot be disabled
- Private beta, single vendor, v0.x maturity
- Section 2(e) prohibition on competing products creates legal ambiguity for AOS
- Access via waitlist — not guaranteed or predictable
- Duplicates some parsing work AOS already does with tree-sitter

### Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| EULA restricts AOS's use | Medium | High | Legal review; treat as optional tool |
| Syncable servers unavailable | Low-Medium | High | `MEMTRACE_TELEMETRY=off`; accept heartbeat dependency |
| Private beta access denied | Medium | Medium | Evaluate Option B (implement internally) |
| Vendor shutdown / license change | Low-Medium | High | No code coupling; pilot only, plan independent impl |
| Competing-product clause triggered | Low | Very High | Legal review required before adoption |

### Effort

- Option A (MCP integration, pilot): 1-2 days setup + 1 week validation
- Option B (AOS-native bi-temporal): 3-6 weeks implementation + 2 weeks validation
- Option C (hybrid): Option A now + Option B over 2-3 months

### Dependencies

- Private beta access (memtrace.io waitlist)
- Legal review of Section 2(e) vis-a-vis AOS product positioning
- Linux x64 binary availability (confirmed in npm: `@memtrace/linux-x64`)
- Node.js >= 18 on AOS infrastructure

### Acceptance Criteria

For Option A pilot to proceed to adoption:
1. Legal review clears Section 2(e) ambiguity.
2. Private beta access granted.
3. Pilot on AOS codebase demonstrates at least one agent workflow measurably improved by memtrace tools (specifically: temporal evolution or cross-service topology).
4. Heartbeat-only network profile is acceptable to AOS's privacy requirements.
5. Memtrace version is >= 0.5.x (indicating post-beta stability).

### Next Steps

1. Legal: review LICENSE Section 2(e) re: competing-product prohibition.
2. Access: join memtrace.io waitlist; assess timeline.
3. Design: begin AOS bi-temporal schema RFC for the existing scanner + Neo4j (Option B pre-work, independent of memtrace access).
4. Monitor: watch for source release, license change, or v1.0 maturity signal.
5. If access granted: pilot with `MEMTRACE_TELEMETRY=off`, document findings.
