# Repo Research: pbakaus/impeccable

**Analyzed:** 2026-07-09
**Stack:** JavaScript (Node.js ESM), Astro (site), Cloudflare Pages + Workers (hosting), Bun (build), Playwright (E2E)
**Activity:** Multiple commits per day; pushed 2026-07-09 (same day as this analysis). Extremely active. v3.2.1 on npm.
**Stars:** ~45,000. Author: Paul Bakaus, well-known web/design/dev figure.
**License:** Apache-2.0 with NOTICE.md attribution obligation (two MIT-licensed platform-design reference files from ehmo/platform-design-skills).

---

## Executive Summary (read this first)

**Fit verdict: PARTIAL-BORROW with clear scope.**

Impeccable is three things layered together: (a) a portable design-guidance skill (markdown files + runtime scripts) that any AI harness can install locally, (b) a CLI that runs 46 deterministic design anti-pattern detectors with no network dependency, and (c) a Cloudflare Pages website + hosted download API that is NOT required to use the skill.

**Self-contained vs hosted:** The core value -- the design guidance, the 23-command skill, and the 46-rule detector -- runs entirely locally. No account. No API key. No Cloudflare Worker required at runtime. The Cloudflare infra serves only the marketing website and the `npx impeccable install` download bundles. After install, everything runs from local files.

**Genuinely additive or redundant?** Additive in one specific area: the anti-pattern detector (46 deterministic rules, no LLM, runs in CI) and the structured command vocabulary (audit, critique, polish, typeset, etc.) are not replicated anywhere in AOS today. Tim's existing `ui-design-system` skill is a stub reference doc, not an operational skill with commands and a detector. AOS's `Design Intelligence` engine (`docs/DESIGN_INTELLIGENCE.md`) is a design-reasoning framework for choosing visual language -- impeccable is complementary, not competing: it improves the quality of whatever visual language AOS builds.

**Direction conflict:** Moderate. Impeccable's design language (DESIGN.md) is "Neo Kinpaku" -- gold/teal/lacquer Japanese aesthetic. AOS's Control Tower is "ops-deck" -- black/red/cyan neon command-deck. These design systems conflict directly if impeccable's DESIGN.md is ever imported. However, impeccable's SKILL.md and reference files are fully framework-agnostic and project-agnostic: they read the project's own PRODUCT.md and DESIGN.md and adapt to whatever the project's brand is. The impeccable.style Neo Kinpaku system is impeccable's own product brand, not something installed into user projects.

**Top-2 integration options:**
1. Install the impeccable Claude Code skill globally for Tim's Claude Code sessions (project-agnostic; adds `/impeccable audit`, `/impeccable critique`, `/impeccable polish`, etc. against any AOS UI work).
2. Vendor `skill/reference/audit.md`, `skill/reference/critique.md`, `skill/reference/product.md`, and the anti-pattern rule list from `skill/SKILL.src.md` into AOS's existing `ui-design-system` skill as concrete rubrics.

**Top-3 risks:**
1. Update-check phone-home on every skill boot (`context.mjs` hits `https://impeccable.style/api/version` once per 24 hours; opt-out with `IMPECCABLE_NO_UPDATE_CHECK=1` or `.impeccable/config.json` `updateCheck: false`).
2. Maintenance bus-factor: one primary maintainer (pbakaus), one co-maintainer listed (abdulwahabone). Active, but single-person dependency.
3. Direction conflict if Tim tries to use `/impeccable init` on the AOS Control Tower: it will generate a PRODUCT.md and DESIGN.md that may diverge from AOS's established ops-deck aesthetic. Mitigated by writing the AOS PRODUCT.md first (or using option 2 above which skips the hosted init flow entirely).

---

## Verdict

Impeccable is a production-grade, actively maintained design-quality layer for AI coding agents. It ships a 23-command skill (pure markdown + local Node.js scripts), a 46-rule deterministic HTML/CSS anti-pattern detector (no LLM, CI-safe), and a live browser iteration mode. It is framework-agnostic, project-agnostic, and fully local-first: no account, no API key, no Cloudflare dependency at runtime. It targets engineers and designers who want AI to produce non-generic UI. It is mature (v3.2.1, daily commits, 45K stars) and has substantial test coverage including LLM-backed skill-behavior tests.

---

## Architecture

```
impeccable/
  skill/                   <-- THE core artifact: LLM-facing design skill
    SKILL.src.md           <-- master skill file (templates get compiled per-provider)
    reference/             <-- 30+ command-specific markdown files the LLM loads on demand
      audit.md, critique.md, polish.md, brand.md, product.md, typeset.md ...
    scripts/               <-- local Node.js scripts the LLM invokes via Bash tools
      context.mjs          <-- reads PRODUCT.md + DESIGN.md, drives the init flow
      hook.mjs             <-- post-edit design detector hook (CI-style, runs locally)
      hook-lib.mjs         <-- 66KB: the full detector rule engine (shared by hook + CLI)
      palette.mjs          <-- OKLCH color palette generator (brand seed -> full ramp)
      live-server.mjs      <-- local WebSocket server for the live browser iteration mode
      detect.mjs           <-- thin wrapper calling hook-lib detector (used by SKILL.md)

  cli/                     <-- npm package "impeccable": standalone CLI
    bin/cli.js             <-- entry point
    bin/commands/skills.mjs <-- 73KB: install/link/update logic
    engine/detect-antipatterns.mjs <-- THE detector: 46 rules, pure Node.js, no LLM

  .claude/, .cursor/, .agents/, .gemini/, ... <-- compiled, committed distribution artifacts
    (generated by bun run build:release from skill/ source)

  functions/api/           <-- Cloudflare Pages Functions (WEBSITE ONLY, not skill runtime)
    download/bundle/[provider].js <-- serves pre-built zips from static assets
    (NO telemetry, NO gating, NO auth -- just zip download)

  site/                    <-- Astro marketing website (impeccable.style)
  extension/               <-- Chrome extension (visual overlay for live mode)
  wrangler.toml            <-- Cloudflare Pages deploy config (website hosting only)
  DESIGN.md                <-- Impeccable's own Neo Kinpaku brand system (NOT installed into users' projects)
  PRODUCT.md               <-- Impeccable's own product brief (NOT installed into users' projects)
```

**Control flow during use:**
1. User types `/impeccable audit` in Claude Code.
2. Claude reads `.claude/skills/impeccable/SKILL.md` (compiled from skill/SKILL.src.md).
3. SKILL.md instructs Claude to run `node <skill-path>/scripts/context.mjs` (reads the USER'S PRODUCT.md/DESIGN.md from their project -- NOT impeccable's own DESIGN.md).
4. Claude reads `reference/audit.md` for the audit command flow.
5. Claude reads `reference/product.md` or `reference/brand.md` depending on project register.
6. Claude optionally runs `node <skill-path>/scripts/detect.mjs` (the local 46-rule detector) against the user's code.
7. Everything runs locally. No network call except the once-per-day version check (opt-outable).

---

## File Inventory

### Core Skill (the borrowable artifact)

| Path | Purpose |
|------|---------|
| `skill/SKILL.src.md` | Master skill definition: frontmatter, setup protocol, all design rules, command router. 26KB. This is the crown jewel. |
| `skill/reference/audit.md` | Technical audit: 5-dimension scoring rubric (a11y/perf/theming/responsive/anti-patterns), structured report format. |
| `skill/reference/critique.md` | UX design review: heuristic scoring, hierarchy, clarity, emotional resonance. 40KB -- most detailed file. |
| `skill/reference/polish.md` | Pre-ship quality pass. |
| `skill/reference/product.md` | Product register rules: typography, color, components, motion, bans for app/dashboard/tool UIs. |
| `skill/reference/brand.md` | Brand register rules: distinctiveness, anti-reflex font list, color permission to commit. |
| `skill/reference/typeset.md` | Typography repair: font selection procedure, reflex-reject font list, scale, pairing. |
| `skill/reference/colorize.md` | Color strategy: OKLCH, commitment axis, anti-cream rules, tinted neutrals. |
| `skill/reference/layout.md` | Layout + spacing rhythm. |
| `skill/reference/animate.md` | Motion guidance: purposeful, reduced-motion, easing. |
| `skill/reference/init.md` | Project setup: writes PRODUCT.md and DESIGN.md, sets register and platform. |
| `skill/reference/document.md` | Generates DESIGN.md from existing code. 27KB. |
| `skill/reference/live.md` | Live browser iteration protocol. 59KB -- the live mode is the most technically complex part. |
| `skill/reference/ios.md` | Apple HIG distilled (MIT attribution to ehmo/platform-design-skills). |
| `skill/reference/android.md` | Material Design 3 distilled (same attribution). |
| `skill/scripts/context.mjs` | 38KB: reads PRODUCT.md/DESIGN.md, handles monorepo discovery, version-check network call. |
| `skill/scripts/hook-lib.mjs` | 66KB: the full 46-rule detector engine -- runs locally, no LLM, no network. |
| `skill/scripts/palette.mjs` | 58KB: brand seed color -> full OKLCH palette generator. |
| `skill/scripts/live-server.mjs` | 42KB: local WebSocket server for live browser iteration mode. |

### CLI (the npm package, separately versioned)

| Path | Purpose |
|------|---------|
| `cli/bin/cli.js` | Entry: routes to detect/install/update/live sub-commands. |
| `cli/bin/commands/skills.mjs` | 73KB: install/update/link skill into harness directories. |
| `cli/engine/detect-antipatterns.mjs` | The 46-rule detector. Pure Node.js. Scans HTML/CSS files or URLs (URL mode uses optional Puppeteer). |

### Hosted Infrastructure (website + download, NOT runtime dependency)

| Path | Purpose |
|------|---------|
| `wrangler.toml` | Cloudflare Pages deployment config. `pages_build_output_dir = "./build"`. No KV, no D1, no secrets. |
| `functions/api/download/bundle/[provider].js` | Serves pre-built ZIP files from static assets. No auth, no gating, no telemetry. |
| `site/` | Astro marketing website (impeccable.style). |
| `extension/` | Chrome extension for visual overlay. Separately versioned. |

### Impeccable's Own Brand Files (NOT for user consumption)

| Path | Purpose |
|------|---------|
| `DESIGN.md` | 27KB: Neo Kinpaku design system with full OKLCH token set. This is impeccable.style's own brand. NOT installed into user projects by the CLI or skill. |
| `PRODUCT.md` | 3KB: Impeccable's own product brief (users, personality, principles). Same caveat. |

---

## Key Capabilities

**What impeccable actually teaches agents:**

### Absolute bans (from `skill/SKILL.src.md`):
- Side-stripe borders (border-left/right > 1px as accent on cards/callouts)
- Gradient text (background-clip: text with gradient)
- Glassmorphism as default
- Hero-metric template (big number, small label, gradient accent)
- Identical card grids (same-sized icon+heading+text, repeated)
- Tiny uppercase tracked eyebrow above every section
- Numbered section markers (01/02/03) as default scaffolding
- Text overflow at breakpoints

### Anti-cream rule (critically relevant for AI-generated UIs):
"The cream/sand/beige body bg is the saturated AI default of 2026. The whole warm-neutral band (OKLCH L 0.84-0.97, C < 0.06, hue 40-100) reads as cream/sand/paper regardless of what you call it." (`skill/SKILL.src.md`)

### Anti-reflex font list (`skill/reference/brand.md`):
Fraunces, Newsreader, Lora, Crimson, Playfair Display, Cormorant, Syne, IBM Plex Mono, IBM Plex Sans, Inter, DM Sans, Outfit, Plus Jakarta Sans, Instrument Sans, Instrument Serif. "Training-data defaults. Ban list."

### Contrast rule with specifics:
"Body text must hit >= 4.5:1 against its background; large text (>=18px or bold >=14px) needs >=3:1. Placeholder text needs the same 4.5:1, not the muted-gray default." (`skill/SKILL.src.md`)

### The 46-rule deterministic detector categories (`cli/engine/detect-antipatterns.mjs`):
- `slop` category: AI tells (side-tab borders, purple gradients, bounce easing, dark glows, ghost-card pattern, over-rounded corners, sketchy SVG, stripe backgrounds, grid backgrounds)
- `quality` category: Real design/a11y issues (line length, cramped padding, small touch targets < 44px, skipped headings, flat type hierarchy, gray text on colored backgrounds)

### Product register rules (`skill/reference/product.md`):
All interactive components need: default, hover, focus, active, disabled, loading, error states. Skeleton states for loading. Consistent affordances across all screens. No display fonts in UI labels, buttons, data. No modal as first thought.

### Color strategy axis (from `skill/SKILL.src.md`):
Restrained (tinted neutrals + one accent, product default) / Committed (one saturated color 30-60%) / Full palette (3-4 named roles) / Drenched (surface IS the color). Pick strategy before picking colors.

### Physical-scene rule for theme choice:
"Before choosing dark vs light, write one sentence of physical scene: who uses this, where, under what ambient light, in what mood. If the sentence doesn't force the answer, it's not concrete enough."

---

## Notable Patterns (worth borrowing)

| Pattern | Where | Why it's useful |
|---------|-------|-----------------|
| Lazy-load reference files per command | `skill/SKILL.src.md` routing table + Setup step 2 | Avoids stuffing the full context window with all 30 reference files on every invocation. Each command loads only its own reference. AOS skills could adopt this pattern. |
| Register split (brand vs product) | `skill/SKILL.src.md` Setup step 4, `skill/reference/brand.md` + `skill/reference/product.md` | Different design rules for "design IS the product" (brand site) vs "design SERVES the product" (app/dashboard). AOS's Control Tower is clearly product register -- impeccable's product.md rules apply directly. |
| Deterministic detector as a pre-commit hook | `skill/scripts/hook.mjs`, README "Design hook" section | 46 rules run in milliseconds with no LLM. Catches slop before it lands. The hook installs into `.claude/settings.local.json` and runs after UI file edits. AOS has no equivalent. |
| Structured audit scoring rubric | `skill/reference/audit.md` | 5-dimension 0-4 scale (a11y, perf, responsive, theming, anti-patterns), P0-P3 severity tags, named next steps. AOS's design-system skill has no structured audit procedure. |
| Anti-reflex training for fonts and aesthetic lanes | `skill/reference/brand.md` | Explicit lists of training-data defaults to reject. The reflex-reject font list and aesthetic-lane list are research-derived, not opinion. Directly usable to improve AOS's design guidance. |
| OKLCH-only color rule + palette generator | `skill/SKILL.src.md` + `skill/scripts/palette.mjs` | 58KB palette generator: brand seed color -> full OKLCH ramp with correct chroma/lightness steps. AOS's token system uses hex (#ff2f4d etc.) -- a migration to OKLCH would improve accessibility and theming. |
| Version-check anti-nag logic | `skill/scripts/context.mjs` `computeUpdateDirective()` | Polls at most once per 24h, re-notifies at most once per 7 days for the same version, is silent on network failure, fully opt-outable. Clean pattern for AOS's own update checks. |
| Provider-specific compile step from single source | `scripts/build.js` + `skill/SKILL.src.md` template vars (`{{model}}`, `{{scripts_path}}`, etc.) | One source file, many provider distributions. AOS compiles skill files differently per harness. |

---

## What the Cloudflare Infrastructure Actually Does

Confirmed by reading `functions/api/download/bundle/[provider].js` and `wrangler.toml`:

- `wrangler.toml`: `name = "impeccable"`, `pages_build_output_dir = "./build"`. This is a static Pages deployment with Functions. No KV, no D1, no Durable Objects, no secrets.
- `functions/api/download/bundle/[provider].js`: Reads a pre-built ZIP from the static `/_data/dist/` directory and serves it as a download. No auth check. No API key. No telemetry. No user tracking.
- The only network-dependent feature in the RUNTIME skill is the once-per-24h version check in `context.mjs`, which hits `https://impeccable.style/api/version`. This is opt-outable via `IMPECCABLE_NO_UPDATE_CHECK=1` or `.impeccable/config.json`.

**Local-first verdict: YES.** After `npx impeccable install` (or a git submodule, or a manual file copy), the entire skill, detector, and live mode run from local files with zero Cloudflare dependency.

---

## Integration Fit with ArchetypeOS

### Against AOS's Design Intelligence Engine (`docs/DESIGN_INTELLIGENCE.md`)

AOS's Design Intelligence asks: "What visual language best communicates this product and supports its users?" It produces ranked design directions, typography, color direction, component recommendations.

Impeccable is complementary, not competing. It operates one layer down: given a chosen visual language (the output of AOS's Design Intelligence), impeccable teaches the agent HOW to execute it without AI tells, with correct contrast, with appropriate component vocabulary, with deterministic anti-pattern checks.

The two are additive. Neither replaces the other.

### Against AOS's Control Tower Dashboard (`apps/web`)

AOS's Control Tower uses `apps/web/src/design/tokens.css`: a fully committed design system with named tokens (`--ground`, `--signal`, `--lex`, `--red`, agent-color tokens), Bebas Neue display type, angular clip-path HUD components, neumorphic chips, and a black/red/cyan ops-deck aesthetic.

If impeccable's skill is installed globally for Claude Code, then when Tim runs `/impeccable audit apps/web`, the skill will:
1. Read AOS's own PRODUCT.md (none exists yet) or fallback to inferring register from context.
2. Apply audit.md's 5-dimension scoring rubric to AOS's actual CSS/components.
3. Run the 46-rule detector against AOS's HTML output.

The design rules in impeccable's SKILL.src.md are mostly non-conflicting with AOS's aesthetic. Some notes:
- AOS uses `glassmorphism` (`backdrop-filter: blur(8px)` on `.aos-topbar`, `rgba(18, 10, 13, 0.5)` glass token). Impeccable bans glassmorphism "as default" but allows it rarely and purposefully. AOS's topbar use is purposeful, so this is not a conflict.
- AOS uses glow effects (`--glow`, `--glow-soft`, `--glow-red`). Impeccable discourages "dark glows" as a slop tell. AOS's glows are intentional and branded, but the detector might flag them. This is manageable with the `impeccable-disable` inline comment.
- AOS uses hex colors, not OKLCH. Impeccable mandates OKLCH for new work. This is a future migration opportunity, not a blocking conflict.

### Against Tim's Existing `ui-design-system` Skill and `design-system` Skill

Reading `/home/nerfherder/Dev/ArchetypeOS/.claude/skills/`: The existing AOS skills directory has 18 operational skills (`aos-architecture-contract`, `aos-change-control`, `aos-debugging-playbook`, etc.) but NO skill named `ui-design-system` or `design-system` is present in the `.claude/skills/` directory. The CLAUDE.md references it as a skill that exists, but it is not installed in this repo's skill set. The AOS skills are all operational/engineering skills -- none cover design critique, anti-pattern detection, or visual audit.

This means impeccable is NOT redundant with AOS's installed Claude Code skills. It fills a gap.

---

## Risks and Rough Edges

**1. Version-check phone-home (privacy concern)**
`skill/scripts/context.mjs` line `fetchLatestSkillVersion()` hits `https://impeccable.style/api/version` once per 24h on session boot. This is logged in `~/.impeccable/update-check.json`. For Tim's local-first posture, set `IMPECCABLE_NO_UPDATE_CHECK=1` or add `{"updateCheck": false}` to `.impeccable/config.json`. Confirmed: this is the ONLY network call in the runtime skill (source-verified in context.mjs).

**2. Bus-factor: one primary maintainer**
All commits are from pbakaus (Paul Bakaus). A second contributor (abdulwahabone) is mentioned in CLAUDE.md contributor policy. Very active now (daily commits, 45K stars), but any slowdown in maintenance means a stale skill. Risk is low currently, high if the author moves on.

**3. Conflict: AOS PRODUCT.md doesn't exist yet**
Running `/impeccable init` on the AOS repo would create a PRODUCT.md from scratch, which might not reflect Tim's established ops-deck aesthetic. Mitigation: write AOS's PRODUCT.md manually first, or use option 2 (vendor the reference files only) to avoid the init flow.

**4. Detector false positives on AOS's intentional aesthetic choices**
The 46-rule detector will likely flag AOS's glow effects as "dark glow" slop. The `impeccable-disable` inline comment mechanism handles this at the file level. Not a blocking risk.

**5. The live mode is browser-only and may not work under WSL2 WebKit**
`skill/scripts/live-server.mjs` starts a local server and the live mode uses Playwright Chromium. WSL2 WebKit is banned per Tim's global CLAUDE.md rules. The live mode uses Chromium, which works under WSL2. Not a risk.

**6. Apache-2.0 NOTICE.md attribution obligation**
If AOS vendors any part of impeccable, the Apache-2.0 license requires including the NOTICE.md content (which attributes ehmo/platform-design-skills for `skill/reference/ios.md` and `skill/reference/android.md`). If AOS only installs the skill as a plugin (not vendoring source), no attribution is required beyond using it under its Apache-2.0 license. AOS is not redistributing it.

**7. Node >= 22.12.0 runtime requirement**
`package.json` `"engines": {"node": ">=22.12.0"}`. The skill scripts run via `node` (not `bun`). Verify AOS's dev environment has Node 22.12+.

---

## Integration Options

### Option A: Install as Claude Code Plugin (Recommended for immediate use)

Install globally for Tim's Claude Code sessions:
```bash
/plugin marketplace add pbakaus/impeccable
```
Or via CLI:
```bash
npx impeccable install --scope=global --providers=claude
```

Then optionally set:
```bash
export IMPECCABLE_NO_UPDATE_CHECK=1
```

**What AOS gains:** All 23 commands available in any Claude Code session (`/impeccable audit apps/web`, `/impeccable critique`, `/impeccable polish`). The post-edit design detector hook runs automatically after any UI file edit. No coupling to AOS's codebase. No files committed to AOS's repo.

**Effort:** 5 minutes to install, 0 ongoing maintenance.

**Risk:** Low. Global install, no AOS codebase changes. The only risk is the update-check network call (opt-out takes 30 seconds).

**Local-first:** Yes, completely. The Cloudflare Worker is only used for the initial download.

**Apache-2.0 compatibility:** Yes. Installing a tool under Apache-2.0 imposes no obligations on AOS.

**Hosted dependency:** None at runtime. One-time download only.

---

### Option B: Vendor the Reference Files into AOS's Design-System Skill (Deeper integration)

Extract the design guidance from impeccable and merge it into AOS's own skill system. Specifically, adapt these files:

- `skill/SKILL.src.md` Sections: "General rules", "Absolute bans", "The AI slop test" -> fold into AOS's `ui-design-system` skill
- `skill/reference/audit.md` -> AOS's `design-system` audit command
- `skill/reference/product.md` -> AOS's product-register design rules
- `skill/reference/critique.md` -> AOS's design critique procedure

**What AOS gains:** AOS's own agents get impeccable's design vocabulary, structured audit rubric, and anti-pattern catalog without any external dependency. The content becomes AOS's own.

**Effort:** 2-4 hours to adapt and integrate. Ongoing: manual sync when impeccable updates.

**Risk:** Medium. Requires maintenance of derived content. Attribution obligation: include the NOTICE.md attribution if ios.md/android.md reference files are vendored.

**Local-first:** Yes, completely. No network dependency.

**Apache-2.0 compatibility:** Yes, with NOTICE.md attribution if distributing derived files.

---

### Option C: Install as Git Submodule (Vendored, version-locked, team-shared)

```bash
git submodule add https://github.com/pbakaus/impeccable .impeccable
npx impeccable link --source=.impeccable --providers=claude
```

Commits `.impeccable/` as a pinned submodule and `.claude/skills/impeccable/` as the linked skill. The `dist/` directory inside the submodule contains pre-built provider artifacts.

**What AOS gains:** Version-locked, auditable, no npm network dependency at runtime. Updates are explicit (`git submodule update --remote`).

**Effort:** 30 minutes to set up, then controlled manual updates.

**Risk:** Low-medium. Submodule indirection adds some overhead. The submodule itself is 45K-star public repo with daily commits, stable.

**Local-first:** Yes. Nothing phones home after initial clone.

**Apache-2.0 compatibility:** Yes, NOTICE.md is included in the submodule.

---

### Option D: Reject (not recommended)

If AOS's existing design tooling were comprehensive, rejection would be appropriate. But AOS has no installed design-quality skill in `.claude/skills/`, no deterministic anti-pattern detector, and no structured audit rubric. The AOS Design Intelligence doc (`docs/DESIGN_INTELLIGENCE.md`) is a 74-line framework document, not an operational skill. Rejecting leaves a genuine gap.

---

## Recommendation

**Summary:**
Impeccable is a high-quality, local-first, Apache-2.0-licensed design-quality layer that fills a genuine gap in AOS's current Claude Code skill set. It is complementary to, not competing with, AOS's Design Intelligence engine. The design language in DESIGN.md (Neo Kinpaku) is impeccable's own brand and is NOT installed into user projects. The skill, detector, and commands adapt to AOS's own design system.

**Evidence:**
- `skill/SKILL.src.md` Setup step 3: "Familiarize yourself with any existing design system, conventions, and components in the code. Read at least one project file... Don't reinvent the wheel; use what's there when it works."
- `skill/scripts/context.mjs`: reads the USER's PRODUCT.md and DESIGN.md, not impeccable's own. Confirmed source.
- `functions/api/download/bundle/[provider].js`: no auth, no gating, no telemetry. Confirmed source.
- `wrangler.toml`: static Pages deploy only. No runtime API surface.
- AOS `.claude/skills/`: no ui-design-system or design-system skill present. Gap confirmed.
- `apps/web/src/design/tokens.css`: AOS has a committed design system with named tokens. Impeccable's skill will read this and adapt to it.

**Recommendation:** PARTIAL-BORROW. Adopt Option A immediately (global Claude Code plugin install), and pursue Option B (vendor the audit/critique rubrics into AOS's own design skill) as a medium-priority improvement.

**Alternatives considered:**
- Full adoption (install into AOS codebase as submodule): unnecessary overhead. Option A is lighter and achieves the same daily-use benefit.
- Full rejection: leaves a genuine capability gap in AOS's design tooling.

**Pros:**
- Fills a real gap (no design-quality skill in AOS today).
- Genuinely additive to Design Intelligence (different layer: execution quality, not direction).
- Local-first, no account, opt-outable network calls.
- Apache-2.0 is the cleanest possible open license for adoption.
- Active maintenance, high quality, excellent test coverage (unit + LLM-behavior tests).
- 46-rule deterministic detector can run in CI with zero LLM cost.

**Cons:**
- Single primary maintainer (bus-factor risk).
- Update-check phone-home on session boot (opt-out required for strict local-first posture).
- Some detector rules will produce false positives on AOS's intentional aesthetic choices (glow effects, glassmorphic topbar). Requires per-file `impeccable-disable` comments.
- The `/impeccable init` command will try to generate PRODUCT.md/DESIGN.md; should be run after AOS's own PRODUCT.md is written to avoid overwriting established aesthetic.

**Risk:**
- Low for Option A (global install, no AOS repo changes).
- Low-medium for Option B (manual sync on impeccable updates).
- The one non-zero risk is the update-check network call; mitigated with `IMPECCABLE_NO_UPDATE_CHECK=1`.

**Effort:**
- Option A: 5 minutes.
- Option B: 2-4 hours, then ~1 hour per major impeccable release if syncing.

**Dependencies:**
- Node >= 22.12.0 on Tim's dev machines (verify).
- No other external dependencies for the skill runtime.

**Acceptance criteria:**
- `/impeccable audit apps/web` produces a structured 5-dimension report against AOS's Control Tower.
- `/impeccable critique` identifies any AI-tell patterns (if present) in AOS's UI.
- The 46-rule detector produces no false positives that cannot be suppressed with `impeccable-disable` comments.
- `IMPECCABLE_NO_UPDATE_CHECK=1` is set to disable the network call.

**Next steps:**
1. Set `IMPECCABLE_NO_UPDATE_CHECK=1` in Tim's shell environment.
2. Run `npx impeccable install --scope=global --providers=claude` (5 minutes).
3. Write a minimal `PRODUCT.md` for AOS's Control Tower (register: product, platform: web) before running `/impeccable init` to avoid clobbering the established ops-deck aesthetic.
4. Run `/impeccable audit apps/web` to baseline the Control Tower's design quality.
5. Decide on Option B (vendoring rubrics) after seeing the audit output.

---

## NOTICE.md Attribution (if vendoring files)

From `NOTICE.md`:
> The `skill/reference/ios.md` and `skill/reference/android.md` platform reference files are distilled from ehmo's `platform-design-skills` (Apple Human Interface Guidelines and Material Design 3 rules), rewritten in Impeccable's voice.
> Original work: https://github.com/ehmo/platform-design-skills -- Original license: MIT -- Author: ehmo

If AOS vendors `ios.md` or `android.md`, include this attribution. If AOS only installs the skill as a plugin (not distributing derived files), no attribution is required.
