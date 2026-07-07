# Skill: Conflict Distill (learn from the day's merge friction)

## Purpose

Close a second self-learning loop (AOS-SELFHEAL-003, Article XX): make the repo
learn from its own **merge friction**. The `docs/NIGHTLY_SELF_LEARNING_LOOP.md`
mandate to "detect repeated pain points" applied to conflicts — the tandem
treadmill (parallel sessions rebasing the same shared files) is the pain point we
kept paying by hand. This turns recurring friction into durable `LES-L##` lessons.

## Owner

CI / DevOps Agent (or the reconciliation-owning laptop Orchestrator — the
`LES-L##` band is the laptop session's).

## Two tiers

**Deterministic floor — `tools/conflict_digest.py`.** Harvests the day's friction
from two git-native substrates and writes `.archetype/conflicts/<date>.md` (+ a
`.json`):
- **git rerere** (`.git/rr-cache/*/preimage`) — conflicts that produced markers,
  with resolved/unresolved state. Requires `rerere.enabled` (set by
  `scripts/install-hooks.sh`); keys by content hash, so records carry a hunk
  preview, not a filename.
- **git reflog** — rebase/merge/reset/pull events. This is the treadmill signal:
  union-auto-resolved coordination-doc conflicts never emit markers (rerere misses
  them) but always leave a rebase behind. Stdlib-only, hermetic; tests at
  `apps/api/tests/test_conflict_digest.py`.

**Reasoned tier — the distiller.** `scripts/nightly/conflict_learn.prompt.md` is
the headless contract: read today's digest, compare against prior digests /
existing lessons / `git log`, and **only if a pattern genuinely recurs**, write an
`LES-L##` lesson (file + a union-safe index row) and open a PR. One-off noise
produces nothing (Article XII — do not manufacture lessons).

## Triggers

- **Nightly automation** (recommended): `scripts/nightly/conflict_learn.sh` gates
  deterministically (harvest → `signal=true`?) then wakes headless `claude` to
  distill + open a PR. Register as a `/schedule` routine or a local crontab entry
  (see `docs/runbooks/nightly-routines.md`). Refuses a dirty tree; one fresh
  branch per day; `DRY_RUN=1` for a harvest-only rehearsal.
- Manual: run `python3 tools/conflict_digest.py`, read the digest, and apply this
  skill after a friction-heavy day.

## Non-goals

- Auto-merging any lesson PR (human gate stays on).
- Implementing mechanical fixes (a merge driver, a hook) in the lesson PR — note
  them as follow-ups; lessons only here.
- Manufacturing a lesson from unrepeatable noise.
