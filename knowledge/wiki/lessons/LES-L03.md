# LES-L03 — git's union merge driver is local-only; GitHub never applies it, so serialized PRs re-conflict

## Aliases

- union driver does nothing on GitHub
- "second PR goes red every time I merge the first"
- custom merge drivers are not server-side
- the tandem treadmill, part 2

## Status

validated

## Owner

Chief Architect / Orchestrator (laptop session)

## Evidence

- Operator observation (2026-07-07): "as soon as I merged 88, 89 went red. what are we doing wrong? I can't have this happen every time." PRs #88 and #89 both touched `docs/ACTIVE_WORK.md`, `docs/RECENT_CHANGES.md` (union-marked) and `docs/CAPABILITY_MAP.md` (not union). Merging #88 flipped #89 to CONFLICTING/DIRTY on GitHub every time.
- Root cause: `.gitattributes merge=union` (LES-026) is honored ONLY by local git. **GitHub.com's merge machinery does not run custom merge drivers** (union included), so its mergeability probe uses the default merge, sees two appends in the same region of the union files, and flags the second PR CONFLICTING — even though a local rebase resolves it in one no-touch pass. The union driver reduced *local* rebase pain but never prevented the *GitHub-side* red flag. Separately, `CAPABILITY_MAP.md` is not union and every self-heal PR edited the same Layer 8 bullet → a genuine conflict on top of the spurious ones.
- Confirming detail: the failed rebase recorded an rr-cache preimage for `docs/CAPABILITY_MAP.md` — i.e. AOS-SELFHEAL-003's own conflict harvester captured this exact event.

## Linked Decisions / Projects

- [[LES-026]] — the union merge driver (necessary but insufficient: local-only)
- [[LES-L02]] — the id-partition fix for a different tandem-conflict class
- `.github/workflows/auto-rebase-prs.yml` — AOS-CI-AUTOREBASE-001, the fix
- `docs/ORCHESTRATOR_PLAYBOOK.md` — Tandem sessions section

## Content

- Event: every feature PR is required (by the Guardian) to update the same three shared docs, so any two serialized PRs collide there by construction. The union driver made me *believe* those collisions were handled, but GitHub kept re-flagging the second PR because it never runs the driver. The manual fix (local rebase, union auto-resolves, force-push) worked but had to be repeated after every single merge — treating the symptom.
- Fix (mechanism, not discipline): a `push: main` GitHub Action (`auto-rebase-prs.yml`) that, in a real runner where `.gitattributes` union DOES apply, merges the new main into each open same-repo non-draft PR branch and pushes (a normal fast-forwarding push, not a force-push). Union-file conflicts self-heal within ~30s with no human action; a genuine non-union conflict (e.g. `CAPABILITY_MAP.md`) can't be auto-resolved, so the bot comments on the PR and moves on.
- Generalization: a custom merge driver only helps where *your* git runs. If the merge that matters happens on a server you don't control (GitHub's mergeability probe, its merge button, a merge queue), the driver is absent — automate the resolution in a runner instead of assuming the driver covers you. Also: minimize the shared-file surface every PR must touch (append-only, non-adjacent edits) so genuine conflicts stay rare.
