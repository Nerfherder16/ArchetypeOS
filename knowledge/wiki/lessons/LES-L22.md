# LES-L22 — An unmerged nightly conflict-learn PR orphans its lesson and lets covered hashes recur in the digest indefinitely

## Aliases

- nightly lesson PR not merged within 24 h
- lesson ID collision between nightly run and regular session
- 07508cfb worker import recurs 6 days with no lesson on main
- 133417e7 LES-L16 rerere replay from orphaned nightly branch
- stale-nightly-pr pattern

## Status

open

## Owner

Chief Architect / Orchestrator (laptop session)

## Evidence

- `07508cfb` appears in **all 5** conflict digests spanning 2026-07-08 to 2026-07-13 (6
  consecutive days). The nightly conflict-learn run on 2026-07-10
  (`laptop/nightly-conflict-learn-20260710`, commit `af7fa12`) wrote a lesson about this
  hash as `LES-L21 — worker import block is a tandem-treadmill hot-spot`. The PR was never
  merged. Main's `LES-L21` was simultaneously claimed by a concurrent laptop session for a
  different lesson (the Recall shakedown silent-fallback, 2026-07-10). The nightly lesson
  was orphaned. As of 2026-07-13, `07508cfb` has **no covering lesson on main**.
- `133417e7` appears in digests 2026-07-10 to 2026-07-13 (4 consecutive days). Its content
  is the `knowledge/wiki/lessons/LES-L16.md` file itself — two sessions both wrote it with
  different content: `52f296c` ("override tokens require explicit lesson citation") and
  `683567a` ("GITHUB_TOKEN-pushed rebases skip CI"). The session that lost the race never
  cleaned up its branch; the auto-rebase runner rebases it daily and rerere replays the same
  LES-L16 conflict resolution every time.
- Both hashes trace to the same root cause: **nightly conflict-learn PRs not merged within
  one nightly cycle.** LES-L02 partitioned cloud vs laptop namespaces; it does not protect
  against a nightly run and a concurrent regular laptop session allocating the same
  `LES-L##` ID in the same day.

## Linked Decisions / Projects

- [[LES-L02]] — the LES-L## / LES-NNN namespace partition (laptop vs cloud). Covers
  cross-session-type collisions; does not cover intra-laptop nightly-vs-regular collisions.
- `laptop/nightly-conflict-learn-20260710` — the orphaned nightly PR (`af7fa12`).
- `683567a` — the losing branch whose LES-L16 version is still alive on a stale remote
  branch, replaying `133417e7` every day via the auto-rebase runner.
- AOS-CI-AUTOREBASE-001 / AOS-CI-AUTOREBASE-002 — the auto-rebase runner; keeps stale
  branches alive and rerere-resolved indefinitely.

## Content

- **Event**: The nightly self-learn routine writes a lesson, allocates the next `LES-L##`
  ID by inspecting the highest ID on main, and opens a PR. When a concurrent laptop session
  merges a lesson with the same ID before the nightly PR is reviewed, the nightly lesson is
  orphaned: it can no longer be merged as-is (ID collision), and its hash coverage never
  reaches main. The hash then appears in the next night's digest again. If the nightly PR
  also has a lesson FILE collision (the losing session wrote the same `LES-L<N>.md`), the
  auto-rebase runner replays the rerere conflict for that file every day until the branch is
  closed or rebased.

- **Rules**:
  1. **Merge or close every `laptop/nightly-conflict-learn-*` PR within 24 hours** — before
     the next nightly run fires. A PR open across two nightly cycles will produce a duplicate
     lesson attempt (the following run sees the hash as uncovered on main) and may have a
     stale ID.
  2. **Before allocating a new `LES-L##` ID, the nightly routine must check open PRs** with
     `gh pr list --json headRefName,title`. If a branch named `laptop/nightly-conflict-learn-*`
     is already open and cites the same hash, skip and exit rather than duplicating.
  3. **When a lesson ID collision is detected** (another session claimed the same ID before
     this PR merged), rename the lesson file to the next free ID in the PR and push — do
     not close and re-open. The index row must be updated in the same commit.
  4. **Clean up the losing branch of any lesson-file collision.** If two sessions wrote
     `LES-L<N>.md` with different content and one version reached main first, the other
     branch must be rebased with `LES-L<N>.md` renamed to the next free ID, then re-pushed.
     Leaving the branch open means the auto-rebase runner generates a daily rerere replay of
     that lesson file indefinitely.

- **Fix (mechanical follow-ups — not implemented in this lessons-only PR)**:
  1. Add a `gh pr list` check at the top of the conflict-learn distiller to skip any hash
     already cited in an open nightly PR (`tools/conflict_digest.py` or the distiller skill).
  2. Add a `stale-nightly-pr` check to the nightly audit heartbeat: if any
     `laptop/nightly-conflict-learn-*` branch is older than 24 h and still open, include it
     in the heartbeat findings.
  3. Rebase `laptop/nightly-conflict-learn-20260710` — rename its `LES-L21.md` to `LES-L22.md`
     (or the next free ID at that time), update the index row, re-push, and merge it to
     permanently cover `07508cfb`.
  4. Identify and close or rebase the stale branch carrying the losing `LES-L16.md` version
     (commit `683567a`) to eliminate the `133417e7` rerere replay.
