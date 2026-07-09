# Repo Research: kepano/obsidian-skills

**Analyzed:** 2026-07-09
**Stack:** Markdown (SKILL.md), YAML (Bases, plugin manifests), JSON (Canvas)
**Author:** Steph Ango (kepano), CEO of Obsidian
**License:** MIT (confirmed: `LICENSE` file, copyright 2026 Steph Ango)
**Activity:** Repo created in 2026; most recent commit 2026-06-08 (PR merge for Bases embed examples). Active but not high-velocity. Community PRs accepted (e.g., SDGLBL contributing).
**Stars:** ~40,544

---

## Executive Summary

**Fit verdict:** Partial-borrow (2 of 5 skills; specifically `json-canvas` and `obsidian-markdown`).

**Obsidian CLI/app dependency bottom line:** The `obsidian-cli` skill requires the Obsidian desktop application to be running on the same machine. Confirmed from `help.obsidian.md/cli`: "Obsidian app must be running. Obsidian CLI requires the Obsidian app to be running." This skill is **dead on arrival for AOS's headless server/CasaOS runtime**. `Obsidian Headless` (`obsidian-headless` npm package) is a separate tool that handles only Sync and Publish, not general vault operations. Neither resolves the headless gap for agent-driven vault authoring. Three of five skills (obsidian-cli, obsidian-bases in render context, defuddle) have conditional or full app dependency.

**JSON Canvas assessment:** Genuinely useful and genuinely open. JSON Canvas 1.0 is a stable, published open spec (`jsoncanvas.org/spec/1.0/`). The format is pure JSON with two arrays (`nodes`, `edges`). It has no runtime dependency on Obsidian or any app. AOS agents could emit `.canvas` files as portable visual artifacts of the Architecture Spine Graph today, with no app coupling whatsoever. Obsidian renders them, but so do other editors. This is the strongest single borrow candidate.

**Top-2 integration options:** (1) Adopt `json-canvas` skill + the JSON Canvas format as AOS Architecture Studio output, app-independent; (2) Adopt `obsidian-markdown` skill to sharpen agent authoring of `knowledge/wiki/` vault notes (additive to existing Obsidian MCP, not redundant).

**Top-3 risks:** (1) `obsidian-cli` skill is completely unusable headless; (2) Obsidian Bases `.base` files require the Obsidian app to render and have no headless query path for AOS agents; (3) overlap with existing Obsidian MCP for vault-authoring work already covered.

---

## Verdict

kepano/obsidian-skills is an official-tier Agent Skills pack authored by the Obsidian CEO, teaching Claude Code (and other skills-compatible agents) how to author the three Obsidian-native formats (Markdown, Bases, Canvas) and interact with the Obsidian CLI and the Defuddle web-scraping CLI. It is a pure-documentation collection of five SKILL.md instruction files (plus reference docs). There is zero runnable code. It is mature for what it is (a reference pack), not a library or framework. Its intended audience is developers using Claude Code with an Obsidian vault open on a desktop. AOS can borrow two skills directly (JSON Canvas and Obsidian Markdown) without any app dependency; the other three either require the desktop app (obsidian-cli), require the app to render (obsidian-bases), or are already covered by other means (defuddle).

---

## What It Is and Full Inventory

### Repository Layout

```
kepano/obsidian-skills/
├── LICENSE                              MIT, copyright 2026 Steph Ango
├── README.md                            Install instructions + skills table
├── .claude-plugin/
│   ├── plugin.json                      Claude Code plugin manifest (name: "obsidian", v1.0.1)
│   └── marketplace.json                 Marketplace listing for /plugin marketplace add
└── skills/
    ├── obsidian-markdown/
    │   ├── SKILL.md                     5,367 bytes; Obsidian Flavored Markdown authoring
    │   └── references/
    │       ├── CALLOUTS.md              Full callout type reference (13 types + aliases)
    │       ├── EMBEDS.md                All embed types (notes, images, PDF, audio, Bases, search)
    │       └── PROPERTIES.md            Frontmatter property types and tag syntax
    ├── obsidian-bases/
    │   ├── SKILL.md                     13,027 bytes; .base file format, syntax, formulas, views
    │   └── references/
    │       └── FUNCTIONS_REFERENCE.md   7,538 bytes; complete Bases function API
    ├── json-canvas/
    │   ├── SKILL.md                     7,624 bytes; JSON Canvas 1.0 spec + layout guidance
    │   └── references/
    │       └── EXAMPLES.md              6,476 bytes; four complete canvas examples
    ├── obsidian-cli/
    │   └── SKILL.md                     3,183 bytes; obsidian CLI command reference
    └── defuddle/
        └── SKILL.md                     1,123 bytes; defuddle CLI for web-to-markdown extraction
```

### Skill-by-Skill Inventory

| Skill | File | Size | What it teaches | Format targeted | App required? |
|-------|------|------|-----------------|-----------------|---------------|
| obsidian-markdown | `skills/obsidian-markdown/SKILL.md` | 5.3 KB | Wikilinks, embeds, callouts, properties, tags, comments, LaTeX, Mermaid, footnotes in Obsidian Flavored Markdown | `.md` | No; format is plain text |
| obsidian-bases | `skills/obsidian-bases/SKILL.md` | 13 KB | `.base` file YAML schema; views (table/cards/list/map), filters, formulas, summaries, all function types | `.base` | Authoring no; rendering yes |
| json-canvas | `skills/json-canvas/SKILL.md` | 7.6 KB | JSON Canvas 1.0 spec; nodes (text/file/link/group), edges, colors, layout, validation | `.canvas` | No; pure JSON spec |
| obsidian-cli | `skills/obsidian-cli/SKILL.md` | 3.2 KB | `obsidian` CLI commands for vault CRUD, search, properties, plugin dev, screenshots, eval | `obsidian` CLI | **Yes -- desktop app must be running** |
| defuddle | `skills/defuddle/SKILL.md` | 1.1 KB | `defuddle parse <url> --md` for web-to-markdown extraction | `defuddle` CLI (npm) | No |

### Plugin Manifest (`.claude-plugin/plugin.json`)

The Claude Code plugin manifest declares:
- `name`: `"obsidian"`, version `1.0.1`
- Trigger description: "Create and edit Obsidian vault files including Markdown, Bases, and Canvas. Use when working with `.md`, `.base`, or `.canvas` files in an Obsidian vault."
- Keywords: obsidian, markdown, bases, canvas, pkm, notes

Installation methods: Claude Code marketplace (`/plugin marketplace add kepano/obsidian-skills`), `npx skills add`, or manual copy of `skills/` into `.claude/skills/`. The marketplace.json wraps the plugin.json in a marketplace listing structure.

This follows the Agent Skills specification at `agentskills.io/specification` (confirmed via scrape). The spec is: SKILL.md with YAML frontmatter (`name`, `description`, optional fields), followed by Markdown body. Progressive disclosure: agent loads only name+description at startup, then full SKILL.md body when activating the skill, then `references/` files on demand. AOS already uses this exact pattern for its own skills in `.claude/skills/`.

---

## The Obsidian CLI Dependency: Critical Finding

**Source:** `skills/obsidian-cli/SKILL.md` (lead line): "Use the `obsidian` CLI to interact with a running Obsidian instance. Requires Obsidian to be open."

**Source:** `help.obsidian.md/cli` (scraped, confirmed): "Obsidian app must be running. Obsidian CLI requires the Obsidian app to be running. If Obsidian is not running, the first command you run launches Obsidian."

**What the Obsidian CLI is:** Not a standalone vault-manipulation tool. It is a thin shim bundled into the Obsidian 1.12+ desktop installer that communicates with the running Obsidian Electron app process. Installation: Settings > General > Enable Command line interface > register. Requires Obsidian 1.12 installer. It exposes the full command palette, plugin lifecycle, dev tools, screenshots, JavaScript eval, and vault CRUD -- all via the running app process.

**Obsidian Headless:** A separate npm package (`obsidian-headless`, open beta) that provides only Sync and Publish operations without the desktop app. It does NOT expose vault CRUD, search, property manipulation, or any of the commands in the obsidian-cli skill. It requires an Obsidian Sync subscription (paid) to authenticate and is not a general vault-operations tool.

**Headless verdict for AOS:** The `obsidian-cli` skill is fully blocked on AOS's CasaOS/headless server runtime. No workaround exists short of running a display-less Obsidian process (Electron + Xvfb), which is not reasonable for a server. AOS already has an Obsidian MCP for vault operations; that is the correct path. The obsidian-cli skill should not be adopted.

---

## Formats Analysis: Bases and JSON Canvas

### Obsidian Bases (`.base` files)

**What it is:** A Obsidian-native database-view format (`.base` extension) released alongside Obsidian 1.x. Files contain YAML with `filters`, `formulas`, `properties`, `summaries`, and `views` sections. Views can be table, cards, list, or map. Filters use an expression syntax (string comparisons, file metadata predicates like `file.hasTag()`, `file.inFolder()`). Formulas compute derived values from frontmatter properties.

**Is it app-independent?** Authoring (writing the YAML to disk) is app-independent. Rendering (executing filters, evaluating formulas, displaying views) requires the Obsidian app. The `base:query` CLI command that would let an agent execute a query also requires the Obsidian CLI (and thus the app). There is no standalone parser or interpreter for `.base` files outside of Obsidian.

**AOS register/keep-pile relevance:** AOS's register uses markdown tables in `index.md`. Bases would offer computed views, filter-by-tag, multi-view display. However, the query/render path is app-locked, which means AOS agents cannot read results back from a `.base` file without the Obsidian app running. The existing Obsidian MCP could write `.base` files but not query them. This is a write-only proposition for headless agents. Markdown tables remain superior for headless tooling.

**Assessment:** Bases is not a useful substrate for AOS's register. The format is not open-standard in the way JSON Canvas is. It is Obsidian-proprietary YAML with no published spec, no external parser, no CLI without the app. Reject for core AOS tooling; acceptable to document as an optional Obsidian-side view layer if Tim runs Obsidian on a client machine over the same vault.

### JSON Canvas (`.canvas` files)

**What it is:** An open specification (`jsoncanvas.org/spec/1.0/`, published 2024-03-11, hosted in the Obsidian GitHub org at `obsidianmd/jsoncanvas`) for node-graph canvases. The format is pure JSON with two top-level arrays: `nodes` and `edges`.

Node types: `text` (markdown content), `file` (path reference with optional subpath), `link` (URL), `group` (visual container with optional background image). Every node has `id` (16-char hex), `type`, `x`, `y`, `width`, `height`, optional `color`. Edges have `id`, `fromNode`, `toNode`, optional `fromSide`/`toSide` (top/right/bottom/left), `fromEnd`/`toEnd` (none/arrow), `color`, `label`.

**Is it app-independent?** Yes, definitively. The spec is a simple JSON schema. No runtime, no parser, no app required to produce valid files. Any program that can write JSON can produce a JSON Canvas. Obsidian renders them, but the spec notes that applications may define their own rendering for preset colors ("intentionally not defined so that applications can tailor the presets to their own brand colors"). Other editors (Capacitor, etc.) implement it. AOS agents can produce and consume `.canvas` files using only the JSON Canvas SKILL.md as a reference.

**AOS Architecture Spine Graph / Architecture Studio relevance:** This is a genuine additive opportunity. The Architecture Spine Graph is a conceptual node-graph of AOS components, dependencies, data flows, and risks. JSON Canvas is a stable open format for node-graph canvases. An AOS agent equipped with the json-canvas skill could:
- Emit a `.canvas` file representing the Architecture Spine Graph as a portable, Obsidian-renderable visual artifact
- Represent components as text nodes, connections as labeled directed edges, layer boundaries as group nodes
- Store `.canvas` files in the knowledge vault alongside the markdown notes they relate to
- Enable Tim to open them in Obsidian (connected via the existing Obsidian MCP vault) for visual review
- Produce architecture diagrams for PR descriptions, design reviews, or system snapshots

The json-canvas SKILL.md covers the full spec including: node creation with ID generation, layout guidelines (50-100px spacing, grid alignment, group padding), edge direction anchors, validation checklist (unique IDs, dangling edge detection), and four complete working examples (mind map, project board with groups, research canvas with file+link nodes, flowchart). The EXAMPLES.md reference is immediately usable.

**Assessment:** Adopt. Zero coupling to the Obsidian app. Additive to Architecture Studio. Low effort to implement.

---

## Integration Fit with ArchetypeOS Subsystems

### Knowledge Vault (`knowledge/wiki/`)

AOS's knowledge vault is Obsidian-format Markdown with wikilinks, section-heading pages, and frontmatter. The existing Obsidian MCP is already connected.

The `obsidian-markdown` skill covers everything AOS agents need to author correct Obsidian Flavored Markdown: wikilinks (`[[Note Name#Section]]`), embeds (`![[Note]]`), callouts (`> [!note]`), properties (YAML frontmatter with typed fields), inline tags, block IDs, Mermaid diagrams, and LaTeX. The reference files (CALLOUTS.md, EMBEDS.md, PROPERTIES.md) are compact and loadable on demand.

**vs. existing Obsidian MCP:** The MCP provides tools for vault operations (read, write, search). The skill provides authoring syntax knowledge -- what to write, not how to write to the vault. They are complementary, not competing. The skill makes the agent smarter about format correctness; the MCP executes the write. There is no overlap.

**vs. claude-obsidian (already evaluated):** The already-evaluated `claude-obsidian` (AgriciDaniel) was a self-organizing second-brain system implementing the Karpathy LLM-Wiki pattern with automated indexing. kepano/obsidian-skills is categorically different: it is syntax-level agent instruction for authoring Obsidian's specific Markdown dialect and formats. No overlap with the already-evaluated repo.

**Assessment:** Additive. Low coupling. Recommend adopting `obsidian-markdown` skill.

### Architecture Spine Graph / Architecture Studio

AOS has no current portable graph export format. The Architecture Spine Graph is a modeling concept; JSON Canvas would make it a storable, versionable, Obsidian-renderable artifact.

Specific capabilities the json-canvas skill enables for Architecture Studio:
- Component nodes as text nodes with component description in Markdown body
- Dependency edges with labeled arrows (`label: "calls"`, `label: "reads from"`)
- Data flow edges with directional anchors
- Risk zones as color-coded group nodes (color 1 = red for risk, color 4 = green for healthy)
- The graph can reference vault notes via `file` nodes (e.g., `file: "knowledge/wiki/components/RunExecutor.md"`)

The json-canvas SKILL.md includes a validation checklist that aligns with AOS's evidence-over-opinion principle: all IDs must be unique, all edge references must resolve, JSON must parse cleanly.

**Assessment:** High-value additive. Adopt json-canvas skill + emit `.canvas` files as Architecture Studio output artifacts.

### Register/Keep-Pile

As analyzed in the Bases section: Bases requires the app to render and query. AOS's headless agents cannot close the read loop. Markdown tables remain the correct choice.

**Assessment:** Do not adopt Bases for the register.

### Skill-Authoring Reference

AOS already authors SKILL.md files (confirmed: `.claude/skills/` in the worktree contains aos-build-run-and-operate, aos-architecture-contract, aos-debugging-playbook, aos-failure-archaeology, aos-diagnostics-and-tooling, aos-config-and-flags, aos-change-control, aos-docs-and-lessons, aos-knowledge-transfer-reference, aos-evidence-loop-campaign).

kepano/obsidian-skills exemplifies several patterns worth studying:

1. **Progressive disclosure via `references/` directory:** The SKILL.md body stays under 500 lines; detailed reference material lives in `references/FUNCTIONS_REFERENCE.md`, `references/EXAMPLES.md`, etc. The agent loads these only when needed. AOS's current skills do not consistently use this pattern. The FUNCTIONS_REFERENCE.md for Bases (7.5 KB) and EXAMPLES.md for Canvas (6.5 KB) are separated from the main SKILL.md (13 KB and 7.6 KB respectively) to keep context loading manageable.

2. **Trigger-oriented description field:** Every skill's frontmatter `description` includes both what the skill does and explicit "use when" triggers. Example from obsidian-bases: "Use when working with .base files, creating database-like views of notes, or when the user mentions Bases, table views, card views, filters, or formulas in Obsidian." AOS skills should adopt this pattern to help the agent select the right skill at the right time.

3. **Validation checklist as the final step in every workflow:** Each SKILL.md includes a validate step at the end of its "Workflow" section, specifying exactly what to check (json-canvas lists 8 validation items; obsidian-bases lists common YAML quoting errors with correct/incorrect examples). This is worth borrowing in AOS's own skill authoring.

4. **Workflow section as ordered numbered steps:** Rather than prose description, each skill opens with a numbered "Workflow" section that tells the agent exactly what to do in sequence. Effective for reducing hallucinated steps.

**Assessment:** Borrow the skill-authoring patterns described above. No need to adopt the obsidian-skills pack wholesale for this purpose.

---

## Notable Patterns Worth Borrowing

| Pattern | Where (file:line reference) | Why it's useful |
|---------|---------------------------|-----------------|
| Progressive reference loading | `skills/obsidian-bases/SKILL.md` body links to `references/FUNCTIONS_REFERENCE.md` (7.5 KB) on demand | Keeps the main SKILL.md fast-loading; heavy reference is only fetched when needed |
| Trigger-cued description field | `skills/obsidian-markdown/SKILL.md` frontmatter: `description: "...Use when working with .md files in Obsidian, or when the user mentions wikilinks, callouts, frontmatter..."` | Explicit "use when" keywords improve skill-selection accuracy |
| Ordered validate step in every workflow | `skills/json-canvas/SKILL.md`: "Validation Checklist" section enumerates 8 specific post-edit checks | Aligns with AOS's evidence-over-opinion principle; prevents format drift |
| CORRECT/WRONG example pairs | `skills/obsidian-bases/SKILL.md` Troubleshooting section; pairs labeled `# WRONG` and `# CORRECT` for every common error | Directly teachable to agents without prose explanation |
| 16-char hex node ID convention | `skills/json-canvas/SKILL.md`: "Generate 16-character lowercase hexadecimal strings (64-bit random value)" | Deterministic, collision-resistant, copy-paste safe for graph node IDs |
| Group nodes as visual domain boundaries | `skills/json-canvas/references/EXAMPLES.md`: Project Board example uses colored group nodes for To Do/In Progress/Done | Maps directly to AOS Architecture Studio: use groups for subsystem boundaries |

---

## Integration Options

### Option A: Adopt json-canvas skill + JSON Canvas format for Architecture Studio output
**What:** Add `skills/json-canvas/SKILL.md` (and its `references/EXAMPLES.md`) to AOS's `.claude/skills/`. Instruct the Architecture Studio agent to emit `.canvas` files alongside markdown notes. Store canvas artifacts in `knowledge/wiki/` or a dedicated `architecture/` directory in the vault.

**Effort:** Low. One file copy + update to Architecture Studio agent prompt to reference the skill. No new dependencies.

**Risk:** Low. JSON Canvas is app-independent; the format will parse and persist as plain JSON whether or not Obsidian is connected. Zero coupling to the Obsidian CLI or app.

**Coupling:** None beyond the JSON format itself.

**Headless:** Fully compatible. AOS agents produce files; Obsidian (when connected) renders them.

**What AOS gains:** Portable, versionable, Obsidian-renderable architecture diagrams. Component graphs, dependency maps, risk views can be authored by agents and reviewed visually by Tim in Obsidian.

**Dependency on Obsidian app:** Optional for authoring (none); required only for visual rendering.

### Option B: Adopt obsidian-markdown skill for knowledge vault authoring
**What:** Add `skills/obsidian-markdown/SKILL.md` + its three reference files to AOS's `.claude/skills/`. AOS agents that write to `knowledge/wiki/` would activate this skill to produce syntactically correct Obsidian Markdown.

**Effort:** Low. File copy only.

**Risk:** Very low. Skills are purely instructional; no code executes.

**Coupling:** None. The skill works alongside the existing Obsidian MCP without replacing it.

**Headless:** Fully compatible. Plain file authoring.

**What AOS gains:** Consistent callout usage, correct wikilink syntax (including block ID links and heading anchors), correctly typed frontmatter properties, proper embed syntax (including `![[BaseFile.base#View Name]]` for embedded Bases). Eliminates formatting errors that cause Obsidian to display notes incorrectly.

**Dependency on Obsidian app:** None for authoring.

### Option C: Adopt the full skills pack as a Claude Code plugin
**What:** Install via `/plugin marketplace add kepano/obsidian-skills` or `npx skills add`. All five skills activate based on context.

**Effort:** Trivial to install; cost is context contamination and wasted tokens from obsidian-cli and defuddle activating in inappropriate contexts.

**Risk:** Moderate. `obsidian-cli` skill will activate when Tim asks to "interact with the vault" and then fail because the desktop app is not running on CasaOS. This creates confusing failures. `defuddle` is redundant with AOS's existing web-fetch tooling and Firecrawl MCP.

**Coupling:** Low technically, but skill activation is automatic and context-driven. Hard to suppress individual skills in a full plugin install.

**Recommendation:** Do not adopt as a full plugin. Cherry-pick Options A and B instead.

### Option D: Reject all skills; use existing Obsidian MCP only
**What:** Continue using the existing Obsidian MCP for vault operations. Do not adopt any skills.

**Effort:** Zero.

**Risk:** Low, but misses the JSON Canvas opportunity (the MCP does not teach the agent to produce canvas files) and continues to risk Markdown authoring errors in the knowledge vault.

**Recommendation:** Reject as a standalone option. The json-canvas opportunity (Option A) is too concrete and low-cost to skip.

---

## Risks and Rough Edges

1. **obsidian-cli headless incompatibility (blocking for 1 of 5 skills):** Confirmed by both the SKILL.md text and Obsidian's official help docs. The skill will produce CLI commands that fail silently or with unhelpful errors on a headless server. If the full plugin is installed (Option C), this skill may activate and waste agent cycles. Mitigation: cherry-pick only the app-independent skills.

2. **Bases format is Obsidian-proprietary, render-locked:** The `.base` format has no published spec, no external parser, no headless query path. The `base:query` CLI command requires the running app. AOS agents cannot read computed results from Bases files without the desktop app. The SKILL.md itself notes "Test in Obsidian: Open the .base file in Obsidian to confirm the view renders correctly" -- this is a write-then-manually-inspect workflow, not a programmatic one. Not suitable for AOS's automated tooling.

3. **Overlap with existing Obsidian MCP (low severity):** The obsidian-markdown skill teaches the agent what to write; the MCP teaches it how to write it. These are complementary. However, if AOS's Obsidian MCP already activates reliably and the agent already produces correct Markdown, the skill is additive-but-minor. Risk is wasted context, not functional failure.

4. **defuddle redundancy:** AOS has Firecrawl MCP for web content extraction. The defuddle skill (`defuddle parse <url> --md`) is redundant. `defuddle` is a separate npm package (kepano's own; open source). There is no reason to add it to AOS's toolchain when Firecrawl is already present and more capable.

5. **Single-author dependency (low severity, high trust):** The repo is maintained by one person (the Obsidian CEO). However, as CEO, kepano directly controls the Obsidian format specifications. His skills will stay current with Obsidian's actual capabilities. Format drift is unlikely. The MIT license means AOS can fork if needed.

6. **JSON Canvas spec is v1.0 with no stated update cadence:** The spec was published 2024-03-11 and has not been revised. The Obsidian GitHub org owns it (`obsidianmd/jsoncanvas`). This is a risk only if Obsidian adds canvas node types without updating the spec. For AOS's purposes (component + edge graphs), the existing node types (text, group, edge) are sufficient and stable.

7. **Bases map view requires community plugin:** The `map` view type in Bases requires the Maps community plugin plus latitude/longitude properties. Not relevant to AOS.

---

## Architecture

The repo has no runtime architecture. It is a flat collection of SKILL.md files following the Agent Skills specification. The relevant "architecture" is the skill-loading flow:

```
Claude Code startup
  -> loads all SKILL.md frontmatter (name + description) from .claude/skills/
  -> when task matches trigger keywords in description -> loads full SKILL.md body
  -> when body references a file in references/ -> loads that file on demand
  -> agent executes using embedded instructions
```

The plugin manifest (`.claude-plugin/plugin.json`) is used by Claude Code's `/plugin` marketplace system. The marketplace.json wraps it for the marketplace listing. Neither file contains executable code.

---

## Distinction from claude-obsidian (AgriciDaniel)

The previously evaluated `claude-obsidian` by AgriciDaniel implemented a self-organizing second-brain system (Karpathy LLM-Wiki pattern): automated indexing, cross-document synthesis, memory extraction, wiki-style progressive summarization. It was about building and maintaining a knowledge base as a living system, with ~80% overlap with AOS's existing Obsidian MCP + knowledge vault implementation.

kepano/obsidian-skills is entirely different: it is syntax-level agent instruction for writing Obsidian's native formats correctly. It makes no claims about knowledge architecture, memory, or self-organization. It teaches format grammar (wikilink syntax, canvas JSON structure, bases YAML schema), not knowledge engineering patterns. There is no overlap between the two evaluations.

---

## Recommendations

### Summary
- **Adopt (Option A):** Cherry-pick `skills/json-canvas/SKILL.md` and `skills/json-canvas/references/EXAMPLES.md` into AOS's `.claude/skills/`. Direct the Architecture Studio agent to emit `.canvas` files as portable visual artifacts of the Architecture Spine Graph.
- **Adopt (Option B):** Cherry-pick `skills/obsidian-markdown/SKILL.md` and its three reference files into AOS's `.claude/skills/`. No new dependencies; tightens Markdown authoring quality in `knowledge/wiki/`.
- **Reject:** `skills/obsidian-cli/SKILL.md` -- desktop app required, incompatible with headless AOS runtime.
- **Reject:** `skills/obsidian-bases/SKILL.md` -- render-locked to Obsidian app; headless query path does not exist; Bases is not useful as a headless data substrate.
- **Reject:** `skills/defuddle/SKILL.md` -- redundant with Firecrawl MCP; not additive.
- **Reject:** Full plugin install (Option C) -- risk of obsidian-cli confusion in headless context.

### Evidence
- obsidian-cli SKILL.md (`skills/obsidian-cli/SKILL.md`, line 1): "Requires Obsidian to be open."
- Obsidian help docs (scraped, `help.obsidian.md/cli`): "Obsidian app must be running."
- JSON Canvas spec (scraped, `jsoncanvas.org/spec/1.0/`): Pure JSON, no runtime, no app.
- obsidian-bases SKILL.md (`skills/obsidian-bases/SKILL.md`, Workflow step 6): "Test in Obsidian: Open the .base file in Obsidian to confirm the view renders correctly."
- Obsidian Headless docs (scraped, `obsidian.md/help/headless`): headless covers Sync and Publish only, not vault CRUD or base:query.
- AOS `.claude/skills/` (confirmed in worktree): AOS already authors SKILL.md files; skill patterns from this repo are directly applicable.

### Alternatives Considered
- Adopting Bases as a query layer for the register: blocked by headless render requirement.
- Using defuddle as the web-scraping CLI: redundant with Firecrawl MCP already in place.
- Running Obsidian in headless Electron with Xvfb to enable obsidian-cli: excessive operational complexity for a server context; not aligned with local-first simplicity principle.

### Pros (of recommended partial-borrow)
- Zero new dependencies for Options A and B
- JSON Canvas is a stable, open, published spec (not proprietary)
- Both adopted skills complement the existing Obsidian MCP rather than overlapping
- MIT license; AOS can modify and fork without restriction
- Skills are purely instructional; drop at any time with no migration cost
- Architecture Spine Graph gains a portable visual output format

### Cons
- json-canvas skill is only useful if AOS actually builds the Architecture Studio canvas export feature; the skill alone adds context overhead if the feature is not built
- obsidian-markdown skill is minor additive value if the agent already writes correct Markdown via Obsidian MCP

### Risk
Low. Skills are non-executable, MIT licensed, from the Obsidian CEO. Worst case: they consume context tokens unnecessarily and get removed.

### Effort
Minimal. Both options are file copies into `.claude/skills/`. Total: 5 files, ~30 KB of text. No configuration changes, no new dependencies, no code.

### Dependencies
- Option A (json-canvas): None beyond the existing AOS architecture modeling work to produce canvas output. Knowledge of Architecture Studio's current data model needed to implement the emitter.
- Option B (obsidian-markdown): None. Drop-in skill.

### Acceptance Criteria
- `skills/json-canvas/SKILL.md` copied to `.claude/skills/json-canvas/SKILL.md` in AOS
- `skills/json-canvas/references/EXAMPLES.md` copied to `.claude/skills/json-canvas/references/EXAMPLES.md`
- Architecture Studio agent can be prompted to produce a `.canvas` file representing the Architecture Spine Graph with at least: component nodes (text type), dependency edges (labeled arrows), subsystem groups (group type), and the file validates against the 8-point checklist in the SKILL.md
- `skills/obsidian-markdown/` + its three reference files copied to `.claude/skills/obsidian-markdown/`
- Next knowledge vault authoring session uses callout syntax, wikilink heading anchors, and typed properties consistently

### Next Steps
1. Copy `json-canvas` skill files into AOS `.claude/skills/`. Low-friction starting point.
2. Copy `obsidian-markdown` skill files into AOS `.claude/skills/`.
3. When Architecture Studio is next developed, design the canvas emitter: map AOS Architecture Spine Graph nodes to json-canvas node types (components = text nodes, data stores = text nodes with color 5 cyan, risk areas = group nodes with color 1 red, edges = labeled directed edges).
4. Store generated `.canvas` files under `knowledge/wiki/architecture/` so the Obsidian MCP can access and render them.
5. Monitor `obsidian-bases` specification: if Obsidian releases a headless bases-query API or standalone parser, re-evaluate for the register use case.
