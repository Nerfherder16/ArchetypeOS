# LES-L14 — a stop-hook auto-commit can slip an UNRELATED commit between origin/main and your work, so Guardian (and the PR diff) attribute its files to your PR

## Aliases

- Guardian BLOCK for docs I never added (capability-map-not-updated)
- PR diff contains files from another commit
- stop-hook auto-committed scan/keep-pile artifacts onto my branch
- rebase --onto origin/main to drop an unrelated ancestor commit
- git diff --name-only origin/main..HEAD before pushing

## Status

validated

## Owner

Chief Architect / Orchestrator (laptop session)

## Evidence

- AOS-SELFHEAL-006's PR committed exactly six intended files, yet `pr_guardian.py`
  BLOCKed with `capability-map-not-updated`, listing `docs/repo-research/*` and
  `knowledge/wiki/repositories/*` as "new docs" — files the commit did not touch.
- Root cause: the stop-guard hook (per the standing rule, it auto-commits dirty
  session files before stopping) had earlier created `ac2bac4`
  ("chore(knowledge): external repo eval keep-pile …") capturing scan/repo-research
  test artifacts. That commit sat **between** `origin/main` and the session-pain
  commit (`origin/main → ac2bac4 → mine`). Guardian diffs `origin/main..HEAD`, so
  it (correctly, mechanically) saw ac2bac4's files as part of the PR.
- The files were NOT test pollution to `rm` (an earlier wrong reflex): `git status`
  showed them as `D` (tracked deletions) because ac2bac4 had committed them. They
  were tracked in HEAD but absent from `origin/main`.
- Fix: `git rebase --onto origin/main HEAD~1` replayed only the session-pain commit
  onto origin/main, dropping ac2bac4. `git diff --name-only origin/main..HEAD` then
  showed exactly the six intended files; Guardian went to PASS.

## Linked Decisions / Projects

- `tools/session_pain_digest.py` — the change under the BLOCK (the probe was fine;
  the branch history was not)
- [[LES-L11]] — sibling "green/red is often the environment, not your change —
  separate the two before acting" discipline, here applied to a git-history artifact

## Content

- Event: a Guardian BLOCK cited docs the commit never added; the reflex "these are
  test pollution, `rm` them" was wrong and briefly deleted tracked files.
- Root cause: an auto-commit (stop-hook) inserted an unrelated commit as the
  parent of the working commit. Anything that diffs `base..HEAD` — Guardian, the PR
  view, code review — attributes that ancestor's files to the PR. The branch was
  also left on the hook's `chore/repo-eval-keep-pile` name rather than the intended
  one.
- Rules:
  1. Before pushing a PR, verify the diff is exactly what you intend:
     `git diff --name-only origin/main..HEAD` (and `git log --oneline origin/main..HEAD`
     should show only YOUR commits). An extra file or commit = investigate, do not
     push.
  2. If an unrelated ancestor commit rode along (often a stop-hook auto-commit of
     scan/keep-pile/session artifacts), drop it with
     `git rebase --onto origin/main <unwanted-commit> <branch>` — do NOT `rm` its
     files (they are tracked; deleting them just stages deletions).
  3. A Guardian BLOCK naming files you did not touch is a history/diff-base problem,
     not a content problem — fix the branch, not the code.
  4. Confirm you are on the intended branch after any stop-hook fires; it may have
     created and left you on its own branch.
