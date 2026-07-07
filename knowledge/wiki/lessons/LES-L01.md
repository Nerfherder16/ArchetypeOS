# LES-L01 — A detector without a remediation trigger is not self-learning

## Aliases

- detect-only anti-pattern
- smoke alarm without a sprinkler
- close the loop (detect -> correct)

## Status

validated

## Owner

Chief Architect / Orchestrator (laptop session)

## Evidence

- The AOS-20 doc-staleness detector fired repeatedly (guardian WARN on PRs #74, #78, …) and each time the remediation was deferred to a manual human step; the state docs stayed 5 PRs behind git. Operator correction (2026-07-06): "why are we not learning from doc-staleness state? … I would have written a hook or skill at this point."

## Linked Decisions / Projects

- [[index]] — lessons registry
- [[LES-007]] / [[LES-024]] — the detector (AOS-20)
- [[LES-009]] — a forcing function that DID close its loop (dated warning-acceptance)
- `.archetype/work/AOS-SELFHEAL-001.md`; `docs/ENGINEERING_CONSTITUTION.md` Article XX

## Content

- Event: AOS-20 shipped a doc-staleness *detector* but no *remediation trigger*. Every WARN was treated as a one-off to defer, so drift accumulated — a smoke alarm with no sprinkler. This violates Article XX ("ArchetypeOS Must Improve Itself"): the platform detected its own drift and did nothing automatic about it.
- Source: operator correction, 2026-07-06.
- Category: process (operator-correction).
- Lesson: **a detector is only half a self-learning loop.** When a recurring signal (doc drift, an ID collision, a manual reconciliation ritual) keeps firing, encode the *correction*, not just the detection — a `--fix` / hook / skill — so detection triggers correction without a human noticing. Guard against gaming the metric (Article XII): the correction must be derived from ground truth and, for anything requiring judgment, drafted for approval — never a watermark bump that silences the alarm without a real fix. General rule for this repo: if you catch yourself doing the same manual remediation twice, that is the signal to write the hook/skill.
- Loop feed: consumed by AOS-SELFHEAL-001 — `doc_staleness.py --fix` generates a deterministic reconciliation draft from `git log` (never edits prose), a `post-merge` git hook (+ `install-hooks.sh`) regenerates it when `main` advances, and the `/reconcile-state` skill applies the narrative half for approval. Follow-ups: a Stop hook + a CI-on-main auto-reconciliation PR + wiring findings into the nightly self-learning loop.
- Status: closed (loop closed for doc-staleness; the general "encode the correction" discipline is the durable takeaway).
