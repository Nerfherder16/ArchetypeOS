# LES-L22 — A resolved conflict's rerere entry persists after the root cause is fixed, making healed patterns appear as recurring friction until the cache is pruned

## Aliases

- phantom rerere after structural fix
- rerere long tail
- old branches replaying cached resolutions post-fix
- rerere cache polluting the digest after healing
- hot-file conflict surviving its own fix

## Status

open

## Owner

Chief Architect / Orchestrator (laptop session)

## Evidence

Three rerere hashes appear in ALL four consecutive conflict digests (2026-07-08, 2026-07-10,
2026-07-11, 2026-07-12), yet each underlying root cause was already structurally fixed before
today's run:

- `07508cfb` — `apps/worker/app/worker.py` import block: two sessions diverged at
  `from aos_core.services.council import ...`, one adding `council_provider`, the other
  adding `make_ledger_sink` + `get_provider`. Root cause eliminated by
  **AOS-WORKER-HANDLERS-001**: handlers moved to per-type modules under `app/handlers/`;
  new job types no longer edit `worker.py`. Confirmed by the comment at
  `apps/worker/app/worker.py:27-30`. Rerere entry retained in
  `.git/rr-cache/07508cfb5e201873e907de271679941072af99d7/` and still applied on every
  auto-rebase of old branches.

- `d9d1177e` — `docs/CAPABILITY_MAP.md` tandem-treadmill: parallel branches appending to the
  same per-layer bullet lists. Root cause eliminated by **AOS-DOCS-CAPMAP-SPLIT**: monolithic
  file replaced by per-layer fragments (`docs/capability-map/layer-NN.md`), so concurrent
  branches touch different files. LES-L07 status: closed. Rerere entry retained.

- `133417e7` — `knowledge/wiki/lessons/LES-L16.md` add/add collision: two sessions wrote
  competing LES-L16 content (override-token citation lesson vs. GITHUB_TOKEN CI gate lesson).
  Root cause eliminated by **LES-L02** id-namespace partition (laptop `LES-L##`, cloud
  `LES-NNN`); the two drafts were reconciled into LES-L16 + LES-L17. Rerere entry retained.

All three entries remain in `.git/rr-cache/`. The auto-rebase runner
(`.github/workflows/auto-rebase-prs.yml`, AOS-CI-AUTOREBASE-001/002) fires on every push to
main and rebases open PR branches that predate the structural fixes. Those branches still carry
the old conflict preimages, so rerere auto-applies the cached resolution silently. The harvester
(`tools/conflict_digest.py`) counts each application, making fixed conflicts look recurring.

## Linked Decisions / Projects

- [[LES-L07]] — CAPABILITY_MAP.md tandem-treadmill (closed via fragment split; `d9d1177e` is
  its residual rerere)
- [[LES-L02]] — id-namespace partition (closed; `133417e7` is its residual rerere)
- `AOS-WORKER-HANDLERS-001` — handler registry (fixes `07508cfb` root cause)
- `.github/workflows/auto-rebase-prs.yml` — auto-rebase runner that replays cached rerere
- `tools/conflict_digest.py` — harvester that counts applied rerere entries
- `.git/rr-cache/` — where the three stale entries live

## Content

- **Event**: Three conflict hashes appear in all four conflict digests across five days. Each
  root cause was already fixed (handler registry, capability-map fragment split, lesson
  id-namespace partition), yet all three hashes remain in the rerere cache and keep appearing
  daily because the auto-rebase runner replays open branches through old preimages.

- **Root cause**: `git rerere` caches a resolved hunk indefinitely. When a structural fix
  eliminates the conflict source at HEAD but leaves the entry in `.git/rr-cache/`, any PR branch
  that predates the fix still carries the old preimage. The auto-rebase runner applies cached
  resolutions silently, the branches merge cleanly, and the digest counts the application as
  recurring conflict — even though no new human friction occurred.

- **Rules**:
  1. After merging a structural fix that eliminates a conflict class (file split, registry
     refactor, namespace partition, union driver), **purge the rerere cache entry immediately**
     on the main checkout and in the CI runner workspace:
     `rm -rf .git/rr-cache/<HASH>`. Otherwise every subsequent auto-rebase applies the stale
     entry and the digest reads as if the conflict is still live.
  2. **Rebase or close open PR branches** that predate the fix in the same release window.
     They are the replay source. A branch stops triggering the old rerere only once it has been
     rebased past the commit that introduced the fix.
  3. **Use the digest's "same hash, multiple days" signal** as a trigger to verify: is this
     hash firing because the root cause is still active, or because the rerere entry was never
     pruned after the fix merged? Check `git log --oneline --all | head -20` for the fix commit,
     then inspect the hash in `.git/rr-cache/` to confirm it should be retired.
  4. **The hot-file root cause discipline** (upstream of this lesson): any file that PR Guardian
     or project policy forces every branch to modify (central dispatch, shared guardian-mandated
     doc) will produce persistent rerere conflicts under parallel sessions. Make the file
     modification-free by construction (registry pattern, union driver, fragment split) before
     the conflict count accumulates, not after. The three patterns above are evidence that the
     fix works — and that the cache cleanup step is the one that is consistently missed.

- **Fix** (mechanical follow-up, NOT implemented in this lessons-only PR):
  Prune the three stale rerere entries from the main checkout after confirming their root causes
  are merged:
  ```
  rm -rf .git/rr-cache/07508cfb5e201873e907de271679941072af99d7
  rm -rf .git/rr-cache/133417e7de7f5e61238be807a74d8125ac8f3de5
  rm -rf .git/rr-cache/d9d1177e7cf4b7a6ca8397627e094886e6806daf
  ```
  Track as a one-line cleanup ticket; do not bundle into a feature PR. The CI runner workspace
  needs the same treatment if rerere is enabled there.
