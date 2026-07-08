# LES-L07 — CAPABILITY_MAP.md is a Guardian-mandated shared doc that was never given the union treatment, so it is the last tandem-treadmill file still genuinely conflicting

## Aliases

- capability map conflicts on every merge
- the un-union-marked shared doc
- last tandem-treadmill file
- capability-map-not-updated forces the collision

## Status

validated

## Owner

Chief Architect / Orchestrator (laptop session)

## Evidence

- Conflict digest `2026-07-08` (`.archetype/conflicts/2026-07-08.md`): 2 recorded rerere conflicts, one of which (`d9d1177e`) is `docs/CAPABILITY_MAP.md` (preview: "# Capability Map / ## Purpose / The Capability Map defines how ArchetypeOS capabilities fit together. …"). The rerere preimage under `.git/rr-cache/d9d1177e…/preimage` is the layered capability list — an additive-append region, not a semantic edit.
- Recurrence in `git log`, not a one-off: **6** explicit `Merge remote-tracking branch 'origin/main' into laptop/*` merge commits touch `docs/CAPABILITY_MAP.md` (`96be86b`, `398b2f1`, `793a899`, `5ef490f`, `581566a`, `6711382`), plus multiple "reconcile" / "post-merge reconciliation" commits (`5eef648`, `9bda8dc`, `2c53f0d`, `062f78f`). 54 commits touch the file in total. It is the most conflict-prone doc in the repo.
- Root cause is a Guardian mandate: `tools/pr_guardian.py:225` `check_capability_map` raises `capability-map-not-updated` ("New docs were added without updating docs/CAPABILITY_MAP.md") whenever a branch adds docs. So every doc-adding feature branch is *forced* to append artifacts/capabilities to the same per-layer sections — the identical additive-concurrency pressure LES-026 identified for the coordination logs.
- The remedy gap: `.gitattributes` grants `merge=union` to exactly three files (`docs/ACTIVE_WORK.md`, `docs/RECENT_CHANGES.md`, `knowledge/wiki/lessons/index.md`) — `docs/CAPABILITY_MAP.md` is **not** on the list. The auto-rebase runner from LES-L03 (`.github/workflows/auto-rebase-prs.yml`) states it plainly: "Union-file conflicts self-heal within ~30s; genuine (non-union) conflicts can't be auto-resolved, so it leaves a comment for manual resolution." Because CAPABILITY_MAP is un-marked, its conflicts fall into the manual-comment bucket on every concurrent merge.

## Linked Decisions / Projects

- [[LES-026]] — the union merge driver for the three coordination logs (the fix that deliberately left CAPABILITY_MAP out; its same-line caveat applies here too)
- [[LES-L03]] — GitHub doesn't run merge drivers → the auto-rebase runner (AOS-CI-AUTOREBASE-001); it named CAPABILITY_MAP as "not union … genuinely conflicts on top" but only papered the remote side
- [[LES-003]] — the "new docs must update the capability map" rule this lesson traces the friction back to
- `tools/pr_guardian.py` — `check_capability_map` (`capability-map-not-updated`)
- `.gitattributes` — where the follow-up union line belongs
- `.github/workflows/auto-rebase-prs.yml` — the runner that would then auto-heal these conflicts

## Content

- Event: `docs/CAPABILITY_MAP.md` conflicts on nearly every concurrent laptop merge (6 merge commits + repeated reconciliation commits; resurfaced in the 2026-07-08 rerere digest). The conflict is on the per-layer capability/artifact bullet lists — additive edits, not semantic disagreements.
- Source: conflict self-learn digest 2026-07-08 + `git log` recurrence.
- Category: process.
- Why it recurs: it is structurally identical to the tandem-treadmill LES-026 fixed for the logs — a shared file that PR Guardian *forces* every branch to append to (`capability-map-not-updated`) — but it was the one such file never given the union treatment. LES-L03's CI auto-rebase runner resolves union files automatically and drops everything else to a human PR comment, so an un-marked CAPABILITY_MAP is guaranteed to keep generating manual-resolution work.
- Lesson: **when a mandate forces every branch to append to a shared file, that file must be made merge-safe by construction — apply the LES-026 remedy to it, don't leave it as the exception.** A per-file union mark or fragment split, not case-by-case manual reconciliation, is what stops the recurrence. The auto-rebase runner (LES-L03) is what makes union viable here despite GitHub not running drivers: union self-heals in the runner, which then pushes a clean branch — the exact reason union "wasn't enough" for CAPABILITY_MAP no longer holds once the runner is in place.
- Fix (mechanical follow-up — NOT implemented in this lessons-only PR): add `docs/CAPABILITY_MAP.md merge=union` to `.gitattributes`. Its layer sections are additive bullet lists (same shape as the coordination logs), so union keeps both concurrent sides and the auto-rebase runner self-heals within ~30s instead of leaving a manual-resolution comment. The LES-026 same-line caveat carries over: union does NOT resolve two sides *editing the same existing line* (e.g. renaming a layer or re-ordering bullets) — those stay single-writer by reconciliation-owner discipline. If append-conflicts persist after union (e.g. two branches inserting under the same heading in different orders), the stronger fix is to split each layer into an included fragment file so concurrent branches touch different files. Track as a separate one-line change-control ticket; do not bundle it into a lesson PR.
- Status: open — the lesson is recorded; the `.gitattributes` union line (or fragment split) is the un-done remediation this lesson exists to trigger.
