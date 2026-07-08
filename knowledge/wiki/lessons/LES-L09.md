# LES-L09 — the doc-staleness check reported FRESH while CURRENT_STATE was ~45 PRs stale: it unioned the state docs and missed squash merges

## Aliases

- doc_staleness says FRESH but CURRENT_STATE is frozen
- state drift not detected
- RECENT_CHANGES masks CURRENT_STATE staleness
- squash-merge PRs invisible to the lag check
- how do we assuredly stop doc drift

## Status

validated

## Owner

Chief Architect / Orchestrator (laptop session)

## Evidence

- AOS-REVIEW-001 (the ChatGPT system evaluation, PR #117) flagged `CURRENT_STATE.md` as internally contradictory and ~45 PRs stale (its "Current sprint" / "Current Objective" / "Active Branch" were frozen around PR #79 while the repo had merged through #121). Meanwhile `tools/doc_staleness.py` reported `Verdict: FRESH`.
- Two compounding root causes in the harvester:
  1. **Union masking**: `check_state_pr_lag` computed `newest_ref = max(PRs in CURRENT_STATE ∪ PRs in RECENT_CHANGES)`. Because RECENT_CHANGES is updated in every PR, `newest_ref` was current (#121), so CURRENT_STATE's own staleness never produced a lag.
  2. **Squash blindness**: `_MERGED_PR = r"Merge pull request #(\d+)"` only matches traditional merge-commit subjects. This repo squash-merges (`Title (#123)`), so the "newest merged PR" was under-counted, further suppressing any lag signal.
- The reconcile nightly deliberately only refreshes the watermark and "NEVER the Current sprint line", so nothing ever corrected CURRENT_STATE's narrative or derived fields, and nothing detected that it hadn't been.

## Linked Decisions / Projects

- `tools/doc_staleness.py` — `check_canonical_state`, `extract_merged_prs` (squash-aware), `derive_canonical` / `refresh_canonical_block`
- `docs/CURRENT_STATE.md` — the new delimited `AOS-CANONICAL` block
- `.github/workflows/state-canonical-refresh.yml` — the push:main auto-derive assurance layer
- AOS-REVIEW-001 (`knowledge/wiki/reviews/2026-07-08-...`) Finding 1 — the source of this
- [[LES-031]] — a sibling "the gate reads X literally" behavior gotcha

## Content

- Event: a staleness alarm that could not fire for the very file it was meant to protect. A check that aggregates across documents hides a single document's rot; a regex tuned for one merge style is blind to the other.
- Root cause: (1) scope error — the freshness of one file was inferred from the union of many; (2) coverage error — the PR extractor matched only non-squash merges.
- Fix (assurance, not policing): make the mechanical fields **impossible** to drift rather than merely detected —
  - `CURRENT_STATE.md` now has a small delimited `AOS-CANONICAL` block; the giant saga moved to `RECENT_CHANGES.md` (minimize the drift surface).
  - `state-canonical-refresh.yml` (push:main) auto-derives `Watermark PR` + `Active Branch` on every merge, commits with `[skip ci]` (no loop). A human never owns those fields, so they cannot go stale.
  - `check_canonical_state` scopes the watermark/branch check to CURRENT_STATE's OWN block (not the union), and `extract_merged_prs` now catches squash `(#N)` and traditional merges — a backstop detector for the nightly.
- Generalization: **the assurance against drift is auto-derivation of the derivable, not stricter alarms.** Compute machine-owned fields from ground truth on every state change; keep the human-authored surface tiny; scope each freshness check to the exact artifact it guards, and make sure it recognizes every way the ground truth actually changes (here: squash merges).
- Portability: the mechanism is now a reusable composite action (`.github/actions/state-hygiene`, self-contained `state_hygiene.py`) so any ArchetypeOS-managed repo inherits the same assurance from one central, versioned source (a vendored copy would itself drift). ArchetypeOS is its first consumer (dogfood).
- Addendum (regex): the block-refresh `re.sub` first used `^\s*-\s*...`; because `\s` matches newlines and `(?m)^` also matches at string position 0, `\s*` swallowed the line's leading newline and fused it onto the marker. Fix: use `[ \t]*` (horizontal whitespace only) for leading/inner indent in any line-rewriting regex. Applied in both `state_hygiene.py` and `tools/doc_staleness.py`.
