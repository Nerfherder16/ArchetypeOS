# Repo Research: AgriciDaniel/claude-obsidian

**Analyzed:** 2026-07-09 · **Stack:** Python 3.10+, Bash, JSON Canvas · **Activity:** Last push 2026-05-28, ~9K stars, single maintainer (AgriciDaniel / Daniel Agrici)

---

## Verdict

claude-obsidian is a Claude Code plugin (15 Agent Skills + 3 sub-agents + a hook set) that implements Karpathy's LLM Wiki pattern over an Obsidian vault. It is marketed as a "self-organizing AI second brain" but the underlying mechanism is structured prompt-driven LLM reasoning, not deterministic code — the LLM decides what to file and how to cross-reference. The project is genuinely well-engineered at the automation layer (per-file advisory locking, hybrid BM25+cosine retrieval, multi-agent concurrency, web egress hygiene) and sits at ~9K stars with active maintenance through May 2026.

**For ArchetypeOS: the pattern was already adopted.** AOS implemented the Karpathy LLM Wiki pattern natively (hot.md, index.md, log.md, manifest tracking, retrieval order) before this analysis. The gap between what claude-obsidian provides and what AOS already has is smaller than it appears from the outside. The additive value lives in three specific places: the BM25+cosine hybrid retrieval pipeline, the web-egress-safe autoresearch loop, and the `/think` 10-principle framework. The Obsidian app dependency and single-maintainer bus factor are the primary risks.

---

## Architecture

The repo is structured as a Claude Code plugin with three entry-point layers:

```
claude-obsidian/
├── .claude-plugin/plugin.json    # Claude Code plugin manifest (slug, version, metadata)
├── commands/                      # slash-command entry points (/wiki, /autoresearch, etc.)
├── skills/                        # 15 Agent Skills (SKILL.md files, not Python classes)
│   ├── wiki/                      # orchestrator — routes to sub-skills
│   ├── wiki-ingest/               # source ingestion loop
│   ├── wiki-query/                # answer questions from vault
│   ├── wiki-lint/                 # vault health check
│   ├── wiki-retrieve/             # hybrid retrieval (BM25+cosine, opt-in)
│   ├── wiki-mode/                 # methodology mode router (LYT/PARA/Zettelkasten/Generic)
│   ├── wiki-cli/                  # Obsidian CLI transport adapter
│   ├── wiki-fold/                 # log rollup (DragonScale opt-in)
│   ├── autoresearch/              # autonomous 3-round web research loop
│   ├── save/                      # /save — file conversations to wiki
│   ├── canvas/                    # JSON Canvas 1.0 visual layer
│   ├── think/                     # 10-principle reasoning framework
│   ├── defuddle/                  # web extraction wrapper
│   ├── obsidian-bases/            # Obsidian Bases schema reference
│   └── obsidian-markdown/         # Obsidian Flavored Markdown reference
├── agents/
│   ├── wiki-ingest.md             # parallel batch ingestion sub-agent
│   ├── wiki-lint.md               # health check sub-agent
│   └── verifier.md                # pre-commit audit agent (v1.7.1+)
├── hooks/hooks.json               # SessionStart / PostCompact / PostToolUse / Stop hooks
├── scripts/                       # 12 Python/Bash helpers
│   ├── wiki-lock.sh               # per-file advisory locking (flock-based)
│   ├── bm25-index.py              # BM25 inverted index builder
│   ├── retrieve.py                # hybrid retrieval orchestrator
│   ├── rerank.py                  # cosine rerank via ollama
│   ├── contextual-prefix.py       # Anthropic-contextual prefix generator (consent-gated)
│   ├── wiki-mode.py               # methodology mode path router
│   └── boundary-score.py          # DragonScale frontier scoring
├── tests/                         # 9 hermetic test suites (~1240 assertions, make test)
├── bin/                           # 5 setup scripts
├── WIKI.md                        # master schema reference (26KB — the authoritative spec)
└── wiki/                          # seeded vault content (demo)
```

**Control flow for a typical ingest:**

```
User: "ingest this source"
  -> skills/wiki/SKILL.md (orchestrator)
  -> routes to skills/wiki-ingest/SKILL.md
  -> scripts/wiki-mode.py route <type> <name>  (get vault-relative path)
  -> scripts/wiki-lock.sh acquire <path>        (per-file advisory lock)
  -> Write/Edit via selected transport           (CLI / MCP / filesystem)
  -> scripts/wiki-lock.sh release <path>
  -> update index.md, log.md, hot.md
  -> PostToolUse hook: git add wiki/ .raw/ .vault-meta/ && git commit
```

**All skill logic is in SKILL.md prompt documents.** There is no Python class hierarchy for ingestion or query reasoning. The "self-organizing" is Claude reasoning from structured SKILL.md instructions. The only deterministic code is in the scripts (locking, BM25 indexing, path routing) and hooks (shell one-liners).

---

## File Inventory

| Path | Purpose |
|------|---------|
| `WIKI.md` | Full schema reference: frontmatter, folder conventions, 6 wiki modes, all operations. The authoritative spec. |
| `skills/wiki/SKILL.md` | Orchestrator skill. Routes /wiki command to sub-skills. Contains cross-project referencing pattern. |
| `skills/wiki-ingest/SKILL.md` | Ingest loop: read source, extract 8-15 pages, lock, write, update index/log/hot. 18KB. |
| `skills/wiki-retrieve/SKILL.md` | Hybrid retrieval (BM25+cosine). Feature-gated. Contains cost ceiling notes ($12/1K docs with Haiku). |
| `skills/autoresearch/SKILL.md` | 3-round autonomous web research loop with URL validation and content sanitization. |
| `skills/think/SKILL.md` | OBSERVE-OBSERVE-LISTEN-THINK-CONNECT-CONNECT-FEEL-ACCEPT-CREATE-GROW framework. 13KB. |
| `skills/wiki-mode/` | Methodology mode router (LYT, PARA, Zettelkasten, Generic). |
| `agents/wiki-ingest.md` | Sub-agent spec for parallel batch ingestion. Enforces lock discipline; bans address allocation in sub-agents. |
| `hooks/hooks.json` | SessionStart: read hot.md; PostCompact: re-read hot.md; PostToolUse (Write|Edit): auto-commit wiki/; Stop: prompt hot cache update. |
| `scripts/wiki-lock.sh` | flock-based per-file advisory locking. sha1(path) as lock key. 60s stale timeout, cross-process release allowed. |
| `scripts/bm25-index.py` | Pure-Python BM25 inverted index over vault chunks. No runtime dependency other than stdlib. |
| `scripts/contextual-prefix.py` | Three-tier prefix generation: Anthropic API / claude CLI subprocess / synthetic. Requires --allow-egress consent. |
| `scripts/retrieve.py` | Hybrid retrieval: BM25 candidates (top 20) -> cosine rerank (ollama) -> top-N results. |
| `scripts/wiki-mode.py` | Path router: reads .vault-meta/mode.json, returns vault-relative path for given type and name. |
| `.claude-plugin/plugin.json` | Plugin manifest: name, version (1.9.2), description, license, keywords. |
| `tests/` | 9 test suites covering wiki-lock, concurrent writes, BM25 index, retrieval, wiki-mode routing, tiling, contextual prefix, boundary scoring, address allocation. |

---

## Key Capabilities

**What the plugin does well:**

1. **Hot cache pattern.** `wiki/hot.md` (~500 words) is updated after every ingest and read first on every session. Confirmed in `hooks/hooks.json` SessionStart hook. Reduces token cost for repeat queries without needing embeddings.

2. **Per-file advisory locking.** `scripts/wiki-lock.sh` uses `flock` keyed on `sha1(path)`. Stale locks self-clear after 60s. PostToolUse hook defers `git add` while locks are held to avoid torn commits. This solves a real problem for parallel Claude agents.

3. **Hybrid retrieval (opt-in).** `scripts/retrieve.py` chains BM25 (always-on) + cosine rerank via local ollama. A consent-gated Anthropic API tier adds contextual prefix generation. README claims +32pp top-1 accuracy and +41% error reduction vs v1.6 baseline (50-query benchmark, not independently verified).

4. **Methodology modes.** `scripts/wiki-mode.py` reads `.vault-meta/mode.json` and returns the correct vault-relative path for LYT / PARA / Zettelkasten / Generic. Backward-compatible: absent mode.json falls back to generic paths.

5. **Autonomous research loop.** `skills/autoresearch/SKILL.md` defines a 3-round loop: broad search, gap fill, synthesis check. URL validation rejects `file://`, `javascript:`, RFC1918 hosts. Content sanitization strips `<script>` tags and escapes `[[` to prevent wikilink injection. 50KB fetch body cap.

6. **10-principle thinking framework.** `skills/think/SKILL.md` formalizes OBSERVE-OBSERVE-LISTEN-THINK-CONNECT-CONNECT-FEEL-ACCEPT-CREATE-GROW as an invocable reasoning discipline with anti-pattern documentation. Each other skill has a "How to think" appendix mapping the framework to its specific work.

7. **Vault as cross-project knowledge base.** `skills/wiki/SKILL.md` §Cross-Project Referencing defines the `CLAUDE.md` snippet pattern that lets any project read the vault with a cost-optimal retrieval order (hot -> index -> domain sub-index -> pages).

---

## The Karpathy LLM Wiki Pattern

Andrej Karpathy's gist (https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) describes a dead-simple idea: instead of repeatedly feeding raw documents to an LLM, continuously distill them into a structured Markdown wiki that grows richer over time. Key properties: persistent artifact (not ephemeral RAG context), bidirectional wikilinks, a hot cache for fast session start, an append-only log, and a master index.

**How faithfully claude-obsidian implements it:**

The implementation is faithful and substantially extended. The core three-layer architecture (`.raw/` sources, `wiki/` output, CLAUDE.md instructions) matches the gist directly. The extensions that go beyond the gist include: per-file locking for parallel safety, optional BM25+cosine hybrid retrieval, methodology modes (LYT/PARA/Zettelkasten), a configurable autonomous research loop, web egress hygiene, and an optional DragonScale address system. The seeded vault shipped in the repo includes `wiki/concepts/LLM Wiki Pattern.md` and `wiki/entities/Andrej Karpathy.md`, confirming the attribution is first-class, not cosmetic.

---

## Dependencies and Runtime Requirements

**Required:**
- Claude Code (latest) — the only execution environment for skills
- Bash 4.0+ — for locking, setup, hook scripts
- Git — PostToolUse auto-commit hook
- Obsidian v1.9.10+ (for Bases dashboard) or v1.6+ (with Dataview fallback)

**Optional but meaningful:**
- Python 3.10+ — for BM25 indexing, retrieval pipeline, mode routing, all tests
- ollama with `nomic-embed-text` model — for cosine rerank in `/wiki-retrieve`
- Anthropic API key — for tier-1 contextual prefix generation (consent-gated, off by default)
- Obsidian Local REST API plugin (port 27124) OR `@bitbonsai/mcpvault` npm package — for MCP transport. **Filesystem transport (Claude's Write/Edit tools) works as a fallback without either.**
- defuddle-cli — optional web extraction wrapper

**Does it need the Obsidian app?** For full use, yes. The Obsidian app renders the vault, provides the graph view, runs community plugins (Obsidian Git auto-commit, Templater, Calendar), and optionally serves the Local REST API. The skills themselves write plain Markdown to disk and function without the Obsidian app running. The vault is readable and useful without Obsidian open, but the visual graph, dashboard, and community plugin ecosystem require it.

**External network calls:** WebFetch and WebSearch in the autoresearch skill. Anthropic API call in contextual-prefix.py (opt-in, consent-gated). The BM25 index and cosine rerank are fully local (Python stdlib + ollama). The repo explicitly states: "Does this send my notes to Anthropic? No by default."

**Python packages (for scripts/tests):** Not listed in a requirements.txt or pyproject.toml in the repository root (this is a rough edge — the Python dependencies must be inferred from imports in the scripts). The BM25 index appears to use only stdlib; the retrieval and rerank scripts use ollama API calls via HTTP.

---

## Integration Fit with ArchetypeOS

### What AOS already has (confirmed by inspection)

AOS already implements the Karpathy LLM Wiki pattern. Evidence from the repo:

- `knowledge/wiki/hot.md` — hot cache, exact same 500-word format
- `knowledge/wiki/index.md` — master catalog with retrieval order documented
- `knowledge/wiki/log.md` — append-only operation log
- `knowledge/wiki/overview.md` — executive summary
- `knowledge/wiki/lessons/LES-001.md` through `LES-L13.md` — lessons wiki per RFC-0004, more structured than claude-obsidian's equivalent
- `knowledge/.manifest.json` — delta tracking (referenced in index.md)
- `docs/KARPATHY_OBSIDIAN_REVIEW.md` — a thorough prior internal review that recommended adopting the pattern, which was then implemented
- `docs/KNOWLEDGE_VAULT_STRUCTURE.md` — AOS's own vault structure spec
- `docs/OBSIDIAN_GRAPHIFY_INTEGRATION.md` — Obsidian integration planning doc
- `docs/KNOWLEDGE_GRAPH.md` — graph layer (the structured relationship layer above the Markdown wiki)
- Obsidian MCP is already connected in the environment (per task brief)

**AOS's knowledge retrieval order** (from `knowledge/wiki/index.md`):
```
hot.md -> index.md -> domain index -> specific pages -> graph search -> embeddings -> LLM synthesis
```
This matches claude-obsidian's retrieval order but extends it with graph search and embeddings as higher tiers — which AOS's Knowledge Graph engine and future embedding work would provide.

### Overlap Map

| claude-obsidian capability | AOS equivalent | Assessment |
|---------------------------|----------------|------------|
| `wiki/hot.md` hot cache | `knowledge/wiki/hot.md` | **FULL OVERLAP — already implemented** |
| `wiki/index.md` master catalog | `knowledge/wiki/index.md` | **FULL OVERLAP — already implemented** |
| `wiki/log.md` append-only log | `knowledge/wiki/log.md` | **FULL OVERLAP — already implemented** |
| `.raw/.manifest.json` delta tracking | `knowledge/.manifest.json` | **FULL OVERLAP — already implemented** |
| Per-file advisory locking (`wiki-lock.sh`) | Not implemented | **ADDITIVE — relevant if parallel agent writes to knowledge/wiki/** |
| BM25+cosine hybrid retrieval (`retrieve.py`) | Not implemented | **ADDITIVE — addresses RFC-0010 Embedding Relevance Tier** |
| Autonomous web research loop (`autoresearch`) | Research Engine (planned) | **PARTIAL OVERLAP — AOS Research Engine is more structured; autoresearch is simpler and immediately usable** |
| Methodology modes (LYT/PARA/Zettelkasten) | AOS uses domain-based structure | **LOW VALUE — AOS's engineering domains already define the structure** |
| Wiki lint (`wiki-lint/`) | `knowledge/meta/lint-report.md` (manual) | **PARTIALLY ADDITIVE — AOS has lint placeholder but no automation** |
| 10-principle thinking framework | AOS CLAUDE.md reasoning principles | **ADDITIVE — structured reasoning discipline not explicitly formalized in AOS** |
| `/save` conversation filing | Not implemented | **ADDITIVE — low priority but useful for filing research sessions** |
| Contradiction flagging `[!contradiction]` callouts | Not implemented | **ADDITIVE — relevant for Decision Intelligence / ADR conflict detection** |
| Obsidian canvas (`/canvas`) | Not implemented | **LOW VALUE for AOS — AOS is an engineering platform, not a visual note system** |
| Cross-project CLAUDE.md referencing pattern | AOS CLAUDE.md approach | **FULL OVERLAP — AOS already does this** |
| SessionStart hook (read hot.md) | Not explicitly hooked | **ADDITIVE — AOS could adopt this hook pattern** |
| Frontmatter schema (type/status/created/updated/tags/related) | AOS has `templates/page-template.md` | **SUBSTANTIAL OVERLAP — AOS templates may need schema alignment** |
| `knowledge/wiki/lessons/` registry (RFC-0004) | `wiki/questions/` filing | **AOS lessons is MORE structured** — not a gap |

### Additive Value Summary

The net new value from claude-obsidian for AOS, after accounting for what AOS already has:

1. **BM25+cosine hybrid retrieval pipeline** (`scripts/bm25-index.py`, `scripts/retrieve.py`, `scripts/rerank.py`, `scripts/contextual-prefix.py`). This is the most technically substantive additive piece. AOS RFC-0010 (Embedding Relevance Tier) calls for something like this. The claude-obsidian scripts are self-contained pure-Python implementations that could be vendored or adapted. The contextual-prefix tier integrates cleanly with local ollama (AOS already has ollama in the stack).

2. **Per-file advisory locking** (`scripts/wiki-lock.sh`). AOS has parallel agents (Research Librarian, Architecture Cartographer, etc.) that could write to `knowledge/wiki/` concurrently. The 60-second stale timeout and PostToolUse hook integration are clean patterns.

3. **`/think` 10-principle framework** (`skills/think/SKILL.md`). AOS has reasoning principles in CLAUDE.md but no formalized decision reasoning loop. The 10-principle framework is a well-structured approach to architectural decisions and audits that maps well to AOS's Decision Intelligence engine.

4. **Web egress hygiene in autoresearch** (`skills/autoresearch/SKILL.md` §Web egress hygiene). AOS Research Engine and RFC-0012 (Web Tier Network Policy) would benefit from the explicit URL validation and content sanitization patterns documented here.

5. **PostToolUse auto-commit hook with lock awareness** (`hooks/hooks.json`). AOS could adopt this specific hook pattern for `knowledge/wiki/` auto-commits.

---

## Notable Patterns Worth Borrowing

| Pattern | Location | Why useful |
|---------|----------|------------|
| Lock-aware PostToolUse auto-commit | `hooks/hooks.json` (PostToolUse) | Prevents torn commits during parallel agent writes; defers git add if any locks are held |
| BM25 inverted index over markdown chunks | `scripts/bm25-index.py` | Pure-Python, no vector DB needed for lexical search; pairs with local ollama for semantic rerank |
| Three-tier contextual prefix generation | `scripts/contextual-prefix.py` | Degrades gracefully: Anthropic API / claude subprocess / synthetic; explicit egress consent gate matches AOS local-first policy |
| Content sanitization before vault write | `skills/autoresearch/SKILL.md` §Web egress hygiene | Strips script tags, escapes [[wikilinks]], rejects `---` YAML delimiters in fetched content; prevents prompt injection into the knowledge graph |
| Address allocation with flock guard | `scripts/allocate-address.sh` | Monotonic counter for stable page addresses; prevents race conditions in parallel ingest; sub-agents banned from calling allocator (orchestrator backfills) |
| Methodology mode path router | `scripts/wiki-mode.py` | Config-file-driven path routing; backward-compatible default (absent config = generic); AOS could use this for routing to different knowledge domain folders |
| Sub-agent ban on allocator calls | `agents/wiki-ingest.md` (Do NOT section) | Clear invariant: sub-agents write pages without addresses, orchestrator backfills in post-pass; prevents counter corruption without serializing everything |
| 10-principle per-skill "How to think" appendix | Every SKILL.md | Maps abstract reasoning stages to concrete skill work; reduces LLM reasoning drift during complex operations |
| Retrieval order documentation in CLAUDE.md | `skills/wiki/SKILL.md` §Cross-Project Referencing | Makes the retrieval cost model explicit for any consuming project; AOS already does this in `knowledge/wiki/index.md` |

---

## Risks and Rough Edges

1. **Bus factor of 1.** AgriciDaniel is the sole maintainer and committer. The AI Marketing Hub Pro "Pro features" create a split-maintenance surface that could diverge. The last commit (2026-05-28) is cosmetic (social preview card). No secondary maintainers are visible in CODEOWNERS (which just lists `@AgriciDaniel`).

2. **All skill logic is non-deterministic LLM reasoning.** The "self-organizing" filing decision, entity extraction, concept page creation, and cross-reference generation are entirely driven by Claude's understanding of SKILL.md instructions. There is no deterministic code path for these operations. For AOS, which values "verification preferred over inference," this is a structural mismatch for any knowledge that needs to be authoritative.

3. **Prompt injection attack surface.** The autoresearch loop fetches arbitrary URLs and writes content to the vault. Despite the web egress hygiene section in `skills/autoresearch/SKILL.md`, the sanitization is applied by the same LLM Claude that is being attacked. An adversarial page that looks like a SKILL.md instruction could potentially redirect behavior. The `[[` escaping and script-tag stripping are documented as defenses but implemented as Claude reasoning, not deterministic code.

4. **No requirements.txt / pyproject.toml.** The Python scripts have no dependency manifest. The retrieval pipeline imports are not listed anywhere in the repo. Setting up the optional retrieval tier requires detective work or reading the scripts directly.

5. **BM25 index is not auto-refreshed on wiki writes.** Per `skills/wiki-retrieve/SKILL.md` §Index maintenance: "Re-run after substantive ingest sessions." A stale BM25 index returns degraded results. The PostToolUse hook does not trigger index refresh. For AOS with a nightly learning loop this would need to be scheduled explicitly.

6. **Obsidian app dependency for full value.** The Obsidian app is required for the graph view, community plugins (auto-commit, Templater), and the Bases dashboard. In AOS's Docker/CasaOS runtime, Obsidian is a desktop GUI app that cannot run in a container. The filesystem transport works headlessly, but the value proposition degrades substantially without the Obsidian visual layer.

7. **Marketing community coupling in the skill code.** `skills/wiki/SKILL.md` §Community Footer instructs Claude to append the AI Marketing Hub promotional footer after scaffold, lint, and autoresearch operations. This is wired into the skill's behavioral spec and would appear in AOS's output if the skill is used as-is. It is trivially removable by forking, but it indicates the skill is designed for community acquisition alongside knowledge management.

8. **Benchmark claims are self-reported.** The "+32pp top-1 accuracy, +41% error reduction" retrieval claims in README and `skills/wiki-retrieve/SKILL.md` reference an internal 50-query benchmark. The benchmark runner (`scripts/benchmark-runner.py`) is in the repo, but no third-party verification or methodology description exists. AOS should not rely on these figures without running its own benchmark on AOS-specific content.

9. **Lock stale timeout is implicit, not configurable per-vault.** `scripts/wiki-lock.sh` uses `STALE_AFTER_SEC=60` as a default with no config file override. For AOS agents that might have longer write times (deep research sessions, large batch ingests), 60 seconds could be too short.

---

## Integration Options

### Option A: Vendor the hybrid retrieval scripts only (Recommended, Low Risk)

Copy `scripts/bm25-index.py`, `scripts/retrieve.py`, `scripts/rerank.py`, and `scripts/contextual-prefix.py` into AOS's knowledge layer. Adapt the input paths to AOS's `knowledge/wiki/` structure. Wire into AOS's Research Engine and nightly loop.

- **Effort:** Low (4 scripts, no framework coupling)
- **Risk:** Low (pure Python, no lock-in to Obsidian or Claude Code plugin format)
- **Coupling:** Minimal — scripts are self-contained CLI tools
- **AOS gains:** The BM25+cosine retrieval pipeline that RFC-0010 calls for, without importing the plugin's Obsidian dependency or LLM-driven logic
- **What to adapt:** Path conventions (AOS uses `knowledge/wiki/` not `wiki/`), integration with AOS's scheduled jobs for index refresh

### Option B: Borrow the SKILL.md patterns (prompt templates) for AOS agent skills (Recommended, Low Risk)

AOS already has a Claude Code skill approach (CLAUDE.md per-project). The SKILL.md frontmatter format (name, description, trigger phrases, allowed-tools) and the "How to think" per-skill appendix pattern are worth importing as a standard for AOS's own Research Librarian, Architecture Cartographer, and other council agents.

- **Effort:** Low (documentation and template work, no code)
- **Risk:** Negligible (pure prompt structure borrowing)
- **Coupling:** None
- **AOS gains:** Structured skill authoring convention for AOS's agent council; the OBSERVE-OBSERVE-LISTEN-THINK-CONNECT-CONNECT-FEEL-ACCEPT-CREATE-GROW framework as an explicit reasoning discipline for council agents working on ADRs and architectural reviews

### Option C: Fork and adapt the autoresearch loop for AOS Research Engine (Medium Effort, Medium Risk)

Fork `skills/autoresearch/SKILL.md` and the web egress hygiene policy. Adapt the filing destinations to AOS's knowledge structure. Strip the Obsidian-specific transport layer (use AOS's knowledge write path instead). Wire the research output into the `knowledge/wiki/research/` domain.

- **Effort:** Medium (requires adapting transport, frontmatter schema, filing paths)
- **Risk:** Medium (LLM-driven loop; non-deterministic output; prompt injection surface from web content)
- **Coupling:** Moderate — AOS needs to maintain a fork or accept semantic drift from upstream
- **AOS gains:** A working autonomous research loop immediately rather than building from scratch per RFC-0011/RFC-0012; web egress hygiene policy that matches AOS's local-first, security-first principles

### Option D: Install the plugin as-is for the Obsidian vault layer (Not Recommended)

Install claude-obsidian into the Obsidian vault that sits beside AOS. Use it for human-readable research notes and decision drafts, as AOS's knowledge strategy anticipates ("Obsidian can store human-readable research and decision notes").

- **Effort:** Very low (2-minute install per README)
- **Risk:** High for AOS-as-platform — the community footer, non-deterministic LLM filing, and Obsidian-app dependency are all load-bearing in this option; AOS would have no control over what gets filed or how
- **Coupling:** High — the plugin's frontmatter schema, folder conventions, and terminology become the AOS vault format
- **AOS gains:** Immediate working Obsidian vault with research ingestion, but with no alignment to AOS's own frontmatter schemas, lesson registry format (RFC-0004), or decision card format

---

## Recommendation

### Summary

Adopt selectively from claude-obsidian. Do not install the plugin as-is. The pattern AOS needed from this project was already internalized and implemented before this analysis. The actionable residual value is in three specific components: the BM25+cosine retrieval scripts, the autoresearch web egress hygiene policy, and the `/think` 10-principle reasoning framework as a formalized discipline for council agents.

### Evidence

- AOS `knowledge/wiki/` already implements hot.md, index.md, log.md, manifest delta tracking, and the retrieval order. This was confirmed by direct inspection (paths listed above).
- `docs/KARPATHY_OBSIDIAN_REVIEW.md` contains a thorough prior analysis that recommended exactly the pattern that was subsequently implemented.
- The claude-obsidian plugin's unique technical contributions beyond the base pattern are: (a) the retrieval pipeline scripts, which map directly to RFC-0010; (b) the web egress hygiene policy, which maps to RFC-0012; and (c) the `/think` framework.
- The plugin's non-unique elements (hot cache, index, log, manifest) are already implemented in AOS.

### Recommendation

**Adopt Options A and B. Consider Option C for the autoresearch egress policy only.**

- **Immediate action (Option A):** Evaluate `scripts/bm25-index.py`, `scripts/retrieve.py`, and `scripts/rerank.py` for integration into AOS's knowledge retrieval path as part of RFC-0010 work. These are self-contained and can be adopted without importing the plugin's Obsidian dependency.
- **Immediate action (Option B):** Adopt the SKILL.md frontmatter convention and the "How to think" per-skill appendix pattern for AOS's council agent skill authoring. Formally document the OBSERVE-OBSERVE-LISTEN-THINK-CONNECT-CONNECT-FEEL-ACCEPT-CREATE-GROW framework in an AOS-internal reference (adapted from `skills/think/SKILL.md`).
- **Deferred action (Option C):** When RFC-0011 (Research Engine) and RFC-0012 (Web Tier Network Policy) are active, review `skills/autoresearch/SKILL.md` §Web egress hygiene as a reference implementation. Adapt the URL validation policy and content sanitization approach. Do not import the LLM-driven filing loop as-is.
- **Reject Option D** for AOS-platform use. The community footer coupling, non-deterministic filing, and Obsidian-app dependency are incompatible with AOS's verification-over-inference principle and Docker runtime.

### Alternatives Considered

- **Build the retrieval pipeline from scratch:** More control, more effort. The claude-obsidian scripts are clean enough to serve as reference implementations without being used verbatim.
- **Use a dedicated vector DB (Qdrant) instead of BM25:** AOS already has Qdrant in the stack. However, the BM25 tier in claude-obsidian fills a complementary lexical search role that Qdrant's cosine similarity doesn't replace — they are additive, not competing.
- **Adopt the plugin fully for the human-Obsidian use case:** Viable for Tim's personal research vault but risky for AOS-platform integration due to the reasons noted in Option D.

### Pros / Cons

**Pros of the recommended approach:**
- Acquires the retrieval pipeline (the most technically unique contribution) with minimal coupling
- The SKILL.md convention is non-binding and can be adopted incrementally
- Avoids the Obsidian-app dependency, bus-factor risk, and community-footer coupling in AOS's core platform
- Aligns with AOS's local-first, verification-over-inference, determinism-preferred principles

**Cons:**
- Does not get the full Obsidian visual layer (graph view, canvas) for free — AOS would need separate work for visual knowledge mapping
- Requires AOS to maintain its own adaptation of the retrieval scripts rather than pulling upstream fixes
- The `/think` framework provides no automated enforcement — it is a reasoning discipline, not a verification mechanism

### Risk

- **Low** for Options A and B: no runtime dependency, no Obsidian dependency, no LLM-driven control flow imported
- **Medium** for Option C (autoresearch): the web egress hygiene policy is sound but the filing loop is LLM-driven and carries prompt injection risk from fetched content
- **High** for Option D: full plugin install creates dependency on a single-maintainer project with marketing community coupling

### Effort

- Option A (retrieval scripts): 2-4 days to adapt and test against `knowledge/wiki/` content
- Option B (SKILL.md convention): 1-2 days to document AOS's skill authoring standard
- Option C (autoresearch egress policy): 1 day to extract and adapt the URL validation / sanitization policy; additional work to build the research loop around it

### Dependencies

- Option A requires RFC-0010 (Embedding Relevance Tier) to be active or co-authored
- Option B is a documentation-only change with no code dependencies
- Option C requires RFC-0011 and RFC-0012 to be scoped

### Acceptance Criteria

- Option A: `scripts/retrieve.py` equivalent returns ranked pages from `knowledge/wiki/` given a freeform query; BM25 index rebuilds correctly on schedule; cosine rerank works with AOS's existing ollama instance
- Option B: AOS agent skill CLAUDE.md files (for Research Librarian, Architecture Cartographer, etc.) adopt the SKILL.md frontmatter convention and include "How to think" appendices for their key operations
- Option C: AOS Research Engine network policy document references the URL validation rules (no file://, javascript:, RFC1918 targets) adapted from `skills/autoresearch/SKILL.md`

### Next Steps

1. Open a tracking work item for RFC-0010 that references `scripts/bm25-index.py` and `scripts/retrieve.py` as reference implementations.
2. Add the `OBSERVE-OBSERVE-LISTEN-THINK-CONNECT-CONNECT-FEEL-ACCEPT-CREATE-GROW` framework to AOS CLAUDE.md or a dedicated AOS reasoning reference document, attributed to `skills/think/SKILL.md`.
3. When RFC-0012 is scoped, cite `skills/autoresearch/SKILL.md` §Web egress hygiene as a prior art reference for the URL policy.
4. Note for any future Obsidian MCP work: the vault filesystem transport (Claude's native Write/Edit tools) is the most reliable path; the Local REST API MCP is optional and adds complexity without proportional value given that AOS's Obsidian MCP is already connected.
