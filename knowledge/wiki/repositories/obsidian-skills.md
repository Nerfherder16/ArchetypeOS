# obsidian-skills

## Aliases

- kepano/obsidian-skills
- Obsidian agent skills (Steph Ango / Obsidian CEO)
- JSON Canvas / Obsidian format skills

## Status

evaluated

## Verdict

partial-borrow — cheap, clean, genuinely additive. MIT, authored by the Obsidian CEO, pure agent-instruction SKILL.md files (no code). Adopt **json-canvas** (the standout — a portable visual-output format AOS's Architecture Spine Graph lacks today) and **obsidian-markdown**; reject the three that need the Obsidian desktop app or duplicate existing AOS tools.

## Repo facts

- URL: https://github.com/kepano/obsidian-skills
- Language: none (SKILL.md instruction files) · License: MIT · Stars: ~40,544 · Last push: 2026-06-08
- Shape: a Claude Code plugin (`.claude-plugin/plugin.json`, name `obsidian` v1.0.1) wrapping 5 Agent Skills, following the agentskills.io spec AOS already uses. Zero executable code.

## AOS engines touched

- Architecture Spine Graph / Architecture Studio (additive — JSON Canvas as portable visual output)
- Knowledge Vault (additive — obsidian-markdown authoring, complements the Obsidian MCP)
- Skill authoring (reference — patterns worth propagating to AOS's own `.claude/skills/`)

## Per-skill verdict

| Skill | Verdict | Reason |
|-------|---------|--------|
| **json-canvas** | **adopt** | Open, app-independent JSON spec (jsoncanvas.org). AOS can emit `.canvas` without Obsidian installed; Obsidian renders them if connected. Fills a real gap — the Spine Graph has no portable output format. |
| **obsidian-markdown** | **adopt** | Callouts/embeds/properties grammar; complements the Obsidian MCP, no app dependency. |
| obsidian-cli | reject | `skills/obsidian-cli/SKILL.md`: "Requires Obsidian to be open." The CLI is a shim into the running desktop Electron app — no headless path. DOA for AOS's CasaOS/server runtime. |
| obsidian-bases | reject | `.base` is render-locked to the Obsidian app; the `base:query` read path also needs the app. Write-then-manually-inspect, not programmatic. Register stays on markdown tables. |
| defuddle | reject | Web-scraping CLI redundant with the Firecrawl MCP already in AOS. |

## Overlap vs additive

- Additive: JSON Canvas gives Architecture Studio a versionable, portable, Obsidian-renderable visual artifact (components = text nodes, dependencies = labeled edges, subsystem boundaries = colored group nodes, risks = red groups). obsidian-markdown tightens vault authoring.
- Reject: anything depending on the running Obsidian desktop app (cli, bases) — incompatible with headless local-first AOS.
- Orthogonal to [[claude-obsidian]] (that was a self-organizing second-brain; this is format grammar). No overlap.

## Integration options

1. **Cherry-pick `skills/json-canvas/` into AOS `.claude/skills/`** (recommended) + direct Architecture Studio to emit `.canvas` files into `knowledge/wiki/architecture/`. Zero new dependencies; effort ≈ file copy + an emitter task. **Strongest borrow.**
2. **Cherry-pick `skills/obsidian-markdown/` + its references** into AOS `.claude/skills/`. Complements the Obsidian MCP. Zero dependencies; effort ≈ file copy.
3. Do NOT install the full plugin — the obsidian-cli skill will activate in headless contexts and produce confusing failures.

## Risks

- **obsidian-cli headless-incompatible (high if full pack installed):** needs the desktop app; must not ship as a whole-plugin install.
- **Bases render-locked (medium):** not usable for the register or any automated query.
- Low overall commitment: skills are prompts — trivial to vendor two files and drop the rest; MIT, high-trust author.

## Evidence

- [[../../../docs/repo-research/obsidian-skills|Full teardown]] — per-skill inventory, CLI-dependency confirmation, JSON Canvas + Bases analysis, skill-authoring patterns
- `skills/obsidian-cli/SKILL.md` ("Requires Obsidian to be open") + official docs (`help.obsidian.md/cli`); `jsoncanvas.org/spec/1.0/` (open format); `.claude-plugin/plugin.json`

## Linked Decisions / Projects

- Plane AOS-68 — "Evaluate: obsidian-skills" (Done)
- Plane AOS-69 — "JSON Canvas emitter for Architecture Studio" (Todo, RFC-first) — greenlit 2026-07-09
- Plane AOS-70 — "Vendor obsidian-markdown skill into AOS .claude/skills" (Todo) — greenlit 2026-07-09
- Plane AOS-71 — "Propagate obsidian-skills skill-authoring patterns to AOS skills" (Todo) — greenlit 2026-07-09
- obsidian-cli / obsidian-bases / defuddle remain rejected (headless-incompatible / redundant)
