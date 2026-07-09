# impeccable

## Aliases

- pbakaus/impeccable
- impeccable design language
- anti-AI-slop design skill

## Status

evaluated

## Verdict

partial-borrow — genuinely additive, not redundant. Apache-2.0, ~45k stars, core is 100% local. AOS's Design Intelligence *chooses* a visual direction; impeccable is the deterministic *execution / anti-"AI-slop"* layer AOS lacks. Borrow the rules/rubric into AOS-native tooling, and/or install the skill for design work.

## Repo facts

- URL: https://github.com/pbakaus/impeccable
- Language: JavaScript (Node scripts) + markdown skill · License: Apache-2.0 (patent grant; `NOTICE.md` attribution if vendored) · Stars: ~45,037 · Last push: 2026-07-09
- Shape: three separable layers — (a) the portable design skill (`skill/SKILL.src.md` + 30+ `skill/reference/*.md`), (b) local Node scripts (`skill/scripts/`: `hook-lib.mjs` 46-rule detector, `palette.mjs` OKLCH generator, `context.mjs`), (c) a Cloudflare Pages site that only serves initial-install ZIP bundles. Installs into ~14 agent harnesses (`.claude/`, `.codex/`, `.cursor/`, `.gemini/`, `.pi/`, …).

## AOS engines touched

- Design Intelligence (additive — execution layer beneath direction-choosing)
- Control Tower dashboard `apps/web` (additive — better design for the agents that build/audit it)
- design-system / ui-design-system skills (complement — adds a deterministic anti-slop rubric)

## Self-contained vs hosted

- **Fully local after install.** The only network call is an opt-outable 24h version check (`IMPECCABLE_NO_UPDATE_CHECK=1` or `.impeccable/config.json {"updateCheck": false}`). Cloudflare serves install ZIPs only — no auth, no telemetry, no gating (source-verified `functions/api/download/...`). Fits local-first.

## What the design language teaches (deterministic, CI-safe)

- 46 anti-pattern rules, no LLM: "AI slop tells" (purple gradients, ghost-card borders, over-rounded corners, bounce easing, side-stripe borders) + real quality (contrast < 4.5:1, touch targets < 44px, flat type hierarchy)
- "Anti-cream" rule — bans the warm-neutral OKLCH band (L 0.84-0.97, C < 0.06, hue 40-100) as the 2026 AI default
- Reflex-reject font ban list (Inter, Fraunces, Playfair, Cormorant, DM Sans, Instrument Sans, …)
- Color-strategy commitment axis (Restrained / Committed / Full-palette / Drenched)
- Product-register rules matching AOS's Control Tower: 7 states per interactive component, skeleton loading, consistent affordances, no display fonts in UI labels
- 5-dimension audit rubric (0-4 per dimension, P0-P3 severity). Framework-agnostic; plain CSS (AOS uses plain CSS too).

## Overlap vs additive

- Additive: AOS has Design Intelligence (a 74-line framework for *choosing* a direction) but **no design-quality/execution skill installed** (`.claude/skills/` has 18 engineering skills, zero design-quality). impeccable fills the execution layer.
- Alignment: the 46-rule detector is deterministic/CI-safe → fits "verification over inference" (a design *linter*, not LLM taste).
- Complements Tim's dark-first token standards + `ui-design-system`/`design-system` skills rather than replacing them.

## Integration options

1. **Install as a global Claude Code plugin (Option A)** — `/plugin marketplace add pbakaus/impeccable`; adds ~23 design commands to Tim's Claude Code sessions. ~5 min, no AOS repo change, local-first with the env var. Best for interactive design work.
2. **Vendor the rules/rubric into AOS's own design-system skill (Option B, AOS-native)** — lift `skill/reference/audit.md`, `critique.md`, `product.md` rules into AOS's design-system skill so the rubric is AOS-owned, zero external dependency. Best for repeatable dashboard audits / a design linter.
3. **Wire the deterministic 46-rule detector as a design lint** — the CI-safe `hook-lib.mjs` rules could back a design check for `apps/web`. Higher effort; strongest "verification" fit.

## Risks

- **Redundancy is low** but the skill is opinionated — confirm its defaults don't fight Tim's established dark-first token aesthetic (the "anti-cream"/font bans align well; verify case by case).
- **Do NOT run `/impeccable init` on the Control Tower** without first writing AOS's own PRODUCT.md — init generates one from scratch and could conflict with the established ops-deck aesthetic.
- Apache-2.0 — clean; `NOTICE.md` attribution required if code/rules are vendored.
- Version-check network call — opt out for strict local-first.

## Evidence

- [[../../../docs/repo-research/impeccable|Full teardown]] — three-layer breakdown, rule inventory, hosted-vs-local analysis, options
- `skill/SKILL.src.md` + `skill/reference/*.md` (design laws); `skill/scripts/hook-lib.mjs` (46 deterministic rules); `functions/api/download/...` (install-only, no telemetry); `LICENSE` (Apache-2.0)

## Linked Decisions / Projects

- Plane AOS-72 — "Evaluate: impeccable" (Done) — in the External Repo Evaluation & Adoption Pipeline module
- No borrow item created yet — Option B (vendor rules into AOS design-system skill) is the strongest AOS-native candidate; Option A (plugin install) is a Tim-environment action. Pending operator greenlight.
