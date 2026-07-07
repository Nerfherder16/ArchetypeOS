# AOS-SELFHEAL-003 — Conflict self-learn nightly (harvest → distill lessons)

- Status: In Review
- Owner: laptop session (parallel Orchestrator)
- Branch: `laptop/aos-selfheal-conflict-learn` (fresh, from `origin/main`)
- Follows: the self-heal family (AOS-SELFHEAL-001/002/002b). Operator idea: "a
  self-learn nightly to pick up on all conflicts of the day's session."

## Why

The tandem treadmill (parallel sessions rebasing the same shared files) was a
recurring pain we kept paying by hand and encoding as one-off lessons (LES-026
union driver, LES-L02 id partition). `docs/NIGHTLY_SELF_LEARNING_LOOP.md` calls
for "detect repeated pain points" — this applies it to merge friction so the repo
proposes its own lessons instead of waiting for a human to notice the pattern.

## Design (two-tier, opens a PR for review)

**Deterministic floor — `tools/conflict_digest.py`.** Harvests the day's friction
from two git-native substrates and writes `.archetype/conflicts/<date>.md` + JSON:
- **git rerere** rr-cache preimages — marker conflicts + resolved/unresolved
  state (keyed by content hash, so a hunk preview not a filename).
- **git reflog** — rebase/merge/reset/pull events. The treadmill signal:
  union-auto-resolved coordination-doc conflicts never emit markers (rerere misses
  them) but always leave a rebase behind. Validated live: today's tree recorded 0
  rerere conflicts but the reflog showed 2 rebases / 3 merges / 3 resets — the
  real friction the union driver silently absorbed.

Stdlib-only, hermetic. TDD: `apps/api/tests/test_conflict_digest.py` (9 tests).

**Reasoned tier — the distiller.** `scripts/nightly/conflict_learn.sh` gates on
`signal=true`, then a headless `claude` follows
`scripts/nightly/conflict_learn.prompt.md`: read the digest, compare against prior
digests / existing lessons / `git log`, and **only if a pattern genuinely
recurs**, write an `LES-L##` lesson (file + union-safe index row) and open a PR.
One-off noise → nothing (Article XII). Never merges; refuses a dirty tree; one
fresh branch per day; `DRY_RUN=1` rehearsal.

`scripts/install-hooks.sh` now enables `rerere` so conflicts are recorded going
forward. New skill: `skills/ci_devops/conflict_distill.md`.

## In-Scope Files
- `tools/conflict_digest.py` (new) · `apps/api/tests/test_conflict_digest.py` (new)
- `scripts/nightly/conflict_learn.sh` (new, executable) ·
  `scripts/nightly/conflict_learn.prompt.md` (new)
- `scripts/install-hooks.sh` (enable rerere)
- `skills/ci_devops/conflict_distill.md` (new)
- `.gitignore` (ignore `.archetype/conflicts/`)
- `docs/CAPABILITY_MAP.md` (Layer 8 bullet) · `docs/ACTIVE_WORK.md` +
  `docs/RECENT_CHANGES.md` (own entries — union-safe)

## Out-of-Scope
- Auto-merging any lesson PR (human gate stays on).
- Implementing mechanical fixes surfaced by a pattern (a merge driver, a hook) —
  the lesson notes them as follow-ups; lessons only in the lesson PR.
- Filename-level attribution of rerere conflicts (rr-cache is content-keyed;
  hunk preview + reflog carry enough for the distiller).

## Acceptance Criteria
1. `tools/conflict_digest.py` tests pass (9, hermetic); ruff clean; `bash -n`
   clean on the wrapper. — evidence: pytest + ruff + bash -n output.
2. Live smoke: the CLI writes a digest and reports `signal=true/false` correctly
   from the real reflog. — evidence: smoke run.
3. Runtime artifacts (`.archetype/conflicts/`) gitignored. — evidence:
   `git check-ignore`.
4. Guardian PASS / PASS_WITH_WARNINGS.

## Verification Plan
- Level 2 (local): pytest (9) + ruff + `bash -n` + live CLI smoke + check-ignore.
- Level 3: first live nightly run distils a lesson PR on a friction-heavy day —
  watch the first run after registering the routine.

## Board Linkage
- Plane: AOS-SELFHEAL-003 (create Done on merge). Advances Article XX.
