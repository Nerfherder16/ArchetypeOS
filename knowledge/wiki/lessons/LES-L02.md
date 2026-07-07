# LES-L02 — Concurrent sessions must not race a shared sequential ID; partition the namespace

## Aliases

- LES-ID add/add collision
- tandem sequential-counter race
- first-committer-wins, second-committer-collides

## Status

validated

## Owner

Chief Architect / Orchestrator (laptop session)

## Evidence

- Operator observation (2026-07-06): the laptop session's branches repeatedly hit merge conflicts while the cloud session's did not. Data: the recurring conflict was an add/add on `knowledge/wiki/lessons/LES-0NN.md` (LES-027 on PR #74, LES-029 on PR #80). Both sessions optimistically claimed the next sequential lesson number from the same base; the merge cadence showed the cloud session as the dominant/faster merger (it merged #64-67, #69-70, #73, #76-77 while the laptop PRs sat gated), so it was always the first-committer on the shared counter and never collided — the laptop session was always the second-committer and always collided.

## Linked Decisions / Projects

- [[index]] — lessons registry (see the ID-allocation convention in Update rule)
- [[LES-026]] — the union merge driver (fixed additive shared-log conflicts; this fixes the shared-counter conflict)
- [[LES-008]] — never reconstruct opaque IDs from memory
- `docs/ORCHESTRATOR_PLAYBOOK.md` — Tandem sessions section

## Content

- Event: with two concurrent sessions, a globally-sequential `LES-NNN` id is an optimistically-allocated shared counter. The first branch to merge claims the number; the second branch that claimed the same number gets an add/add file collision. Whichever session merges first never sees it; the slower/second-mover always does. Renumbering-on-collision (done manually twice) is a band-aid, not a fix.
- Source: operator observation, 2026-07-06.
- Category: process.
- Lesson: **when concurrent writers share a resource, don't race it — partition it or make it merge-safe by construction** (the same principle as the LES-026 union driver, applied to an id counter instead of an append log). Fix: **partition the lesson-id namespace by session.** The laptop session allocates `LES-L01, LES-L02, …`; the cloud session keeps the default `LES-NNN` sequence. Two sessions can never pick the same id, so the add/add collision is impossible regardless of merge order. Already-merged laptop lessons (LES-024/025/026/028) keep their numbers; the partition applies to new laptop lessons going forward. Generalize: any shared monotonic id under concurrent authorship (work-item ids, migration numbers) wants either a per-session namespace or a single allocator — never optimistic first-come allocation.
- Loop feed: consumed here — `.gitattributes` already union-merges the index; the laptop session now uses the `LES-L##` band (this lesson is `LES-L02`; the doc-staleness self-heal lesson was renumbered `LES-029 -> LES-L01`). Encoded in the lessons index Update rule and the playbook Tandem section; relayed to the cloud session via the operator.
- Status: closed (convention adopted).
