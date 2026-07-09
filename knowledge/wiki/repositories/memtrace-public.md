# memtrace-public

## Aliases

- syncable-dev/memtrace-public
- Memtrace — structural memory for coding agents
- MemDB bi-temporal graph

## Status

evaluated

## Verdict

partial-borrow / monitor — genuinely additive capability, but **do not adopt as a core dependency**. The engine is closed-source under a proprietary EULA with a "no competing product" clause, and it requires a mandatory heartbeat to the vendor's servers. The license-safe, principle-aligned path is to **clean-room borrow the bi-temporal symbol-graph design** into AOS's own scanner + Neo4j.

> This repo is a docs/skills shell, not the engine. The real engine (MemDB, Rust) ships as a closed binary via npm; README states plainly "Indexer + database (MemDB) are closed-source."

## Repo facts

- URL: https://github.com/syncable-dev/memtrace-public
- Language: Rust engine (closed binary) + TS installer/skills + Python benchmarks · License: **proprietary EULA v1.0 (Syncable Dev, all rights reserved)** · Stars: ~395 · Last push: 2026-07-09 (auto-synced from a private repo)
- Shape: MCP server (25+ tools) backed by MemDB — an embedded Rust graph store (HNSW vectors + Tantivy BM25 + WAL), stored locally in `.memdb/`. Streamable-HTTP transport serves many agent sessions. Zero-LLM (deterministic tree-sitter indexing).

## AOS engines touched

- Repository scanner / Repository Intelligence (overlap: partial at base graph; additive at symbol level)
- Knowledge Graph (overlap: low — MemDB is embedded, not Neo4j; no conflict)
- Architecture Spine Graph (additive — cross-service API topology could feed it)
- Agent memory / Knowledge read path (additive — structural memory substrate for agents)

## Overlap vs additive

- Overlap: base structural graph (CALLS/IMPLEMENTS/IMPORTS) partially duplicates AOS's scanner, but at symbol/function granularity vs AOS's file/architecture granularity — complementary, different levels.
- Genuinely additive (not in AOS today): per-symbol `valid_from`/`valid_to` tied to git commits (bi-temporal), six temporal scoring modes (impact/novelty/recency/directional/compound/overview), episode replay (graph state at a past commit), cochange detection, symbol-level Louvain/PageRank/betweenness, cross-service HTTP API topology, zero-caller dead-code, per-symbol cyclomatic complexity.
- Alignment: zero-LLM determinism fits "verification over inference"; local code storage fits local-first — but see the heartbeat caveat.

## Integration options

1. **Run as MCP server (Option A)** — wire memtrace as an MCP server for AOS agents; `MEMTRACE_TELEMETRY=off`. ~1-2 days, zero code coupling. **Gated on:** private-beta access + **legal review of the EULA Section 2(e) competing-product clause** (AOS's positioning is close to memtrace's) + acceptance of the mandatory memtrace.io heartbeat.
2. **Borrow the bi-temporal schema design (Option B, recommended)** — clean-room implement `valid_from`/`valid_to` per symbol + temporal scoring + cochange in AOS's own scanner + Neo4j, using memtrace's documented architecture as a blueprint. ~3-6 weeks. No license restriction on design ideas; no vendor dependency; fully local; aligns with AOS principles.
3. **Monitor** — track maturity/license; revisit if it open-sources or drops the competing-product clause.

## Decision (2026-07-09): defer Option B, capture as Evolution Engine blueprint

Operator decision: **do not build Option B now; keep it as a captured blueprint, memtrace stays `monitor`.** Rationale (evidence over YAGNI):

- AOS + jcodemunch already cover the symbol-level **static** half memtrace advertises (blast radius, call hierarchy, churn, dead code, coupling, symbol importance). Re-building that is redundant.
- The only genuinely novel delta is the **bi-temporal history layer** — point-in-time graph replay, cochange detection, temporal scoring. Its natural consumer is the **Evolution Engine** ("evolve systems over time"), which is roadmap, not built. With no live driver, a 3-6 week build now is YAGNI.
- This page + the full teardown (`docs/repo-research/memtrace-public.md`) ARE the blueprint. When the Evolution Engine is scheduled, promote **Plane AOS-67** to an RFC and build the bi-temporal layer clean-room in AOS's scanner + Neo4j then.
- The one slice with a live driver today (cochange → PR Guardian blast-radius) was explicitly NOT started as part of this decision; it can be picked up separately if that becomes a priority.

## Risks

- **Proprietary EULA + closed engine (critical):** binary-only; no audit/modify/fork/redistribute; Section 2(e) prohibits building a competing product — **mandatory legal review** before any adoption of the binary. No source path to self-host the core.
- **Mandatory heartbeat (high):** cannot run without license-auth + a 15-min heartbeat to memtrace.io; not air-gappable. Telemetry is opt-out (`MEMTRACE_TELEMETRY=off`), but auth/heartbeat are not.
- **Single vendor, v0.x, private beta (high):** rug-pull / shutdown / license-change risk with no fork path. The `-public` repo is a sync target, not a community repo.
- Overlap-redundancy: some base graph capability duplicates AOS's existing scanner investment.

## Evidence

- [[../../../docs/repo-research/memtrace-public|Full teardown]] — EULA analysis, engine-vs-shell, MemDB architecture, telemetry streams, capability list, integration options
- `LICENSE` (proprietary EULA v1.0, Syncable Dev; Section 2(e) competing-product prohibition; binary-only grant)
- `README.md` ("Indexer + database (MemDB) are closed-source"); `TELEMETRY.md` / `PRIVACY.md` (4 streams; heartbeat `POST memtrace.io/api/device/heartbeat` every 15 min, non-disableable); benchmarks/ (MIT, publicly runnable)

## Linked Decisions / Projects

- Plane AOS-66 — "Evaluate: memtrace-public" (Done)
- Plane AOS-67 — "Bi-temporal symbol memory (memtrace Option B) — deferred blueprint, build with Evolution Engine" (Backlog) — the parked anchor; this page is its blueprint
- Option A (run as MCP) remains gated on legal review + heartbeat acceptance — not pursued
