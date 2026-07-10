# LES-L21 — apps/worker/app/worker.py's import block is a tandem-treadmill hot-spot: every service-integration branch appends to it, generating additive rerere conflicts on concurrent merges

## Aliases

- worker import block conflict
- additive-import rerere recurrence
- worker.py hot import region

## Status

open

## Owner

Chief Architect / Orchestrator (laptop session)

## Evidence

- Conflict digest `2026-07-08` (`.archetype/conflicts/2026-07-08.md`): rerere hash `07508cfb5e201873e907de271679941072af99d7` recorded, preview: "from __future__ import annotations / from datetime import datetime, timezone / import logging / import time / import redis / from aos_core.config import get_settings". The 2026-07-08 self-learn run explicitly noted this as a single-day instance and held off.
- Conflict digest `2026-07-10` (`.archetype/conflicts/2026-07-10.md`): the same rerere hash `07508cfb5e201873e907de271679941072af99d7` appears again. Two-day recurrence — same conflict region, same file, different concurrent feature branches.
- Rerere preimage (`.git/rr-cache/07508cfb.../preimage`) shows the conflict is in the `from aos_core.services.council import ...` line: left side adds `council_provider`, right side adds `run_council` + `make_ledger_sink` + `get_provider`. Postimage shows the resolution is a union: `council_provider, run_council` and `make_ledger_sink` are both kept. The conflict is always additive — no semantic disagreement, no rewrite of an existing line.
- Root pressure: every feature branch that integrates a new backend service (council, ledger, research, voice, router, distillation) must add an import to `apps/worker/app/worker.py`. The file is the central dispatcher. AOS-WORKER-ROUTER-001 introduced a handler-registry pattern (commit `f901892`) but handler modules still require explicit top-level imports to register; the flat import block has grown to ~18 lines and continues to be the mandatory touchpoint.
- Structurally identical to the tandem-treadmill pattern that produced LES-026, LES-L03, and LES-L07: a file that every concurrent branch must append to, with resolutions that are always additive unions.

## Linked Decisions / Projects

- [[LES-026]] — the union merge driver for the three coordination logs (the pattern this lesson parallels for source code)
- [[LES-L07]] — CAPABILITY_MAP.md received the same treatment; its lesson and resolution are the direct model here
- [[LES-L03]] — the CI auto-rebase runner (AOS-CI-AUTOREBASE-001) that makes union viable by running git drivers where GitHub cannot
- `apps/worker/app/worker.py` — the file generating the recurring conflict
- `.gitattributes` — where the follow-up union line belongs
- `AOS-WORKER-ROUTER-001` — the self-registering handler registry (structural long-term fix)

## Content

- Event: rerere hash `07508cfb` appeared in the conflict digest on 2026-07-08 and again on 2026-07-10. Two consecutive digest days. The 2026-07-08 self-learn run deliberately held off (single-day); today's recurrence confirms the structural pressure is real.
- Source: conflict self-learn digests 2026-07-08 and 2026-07-10 (`.archetype/conflicts/`).
- Category: process.
- Why it recurs: `apps/worker/app/worker.py` is the central dispatch point for all background job execution. Every branch adding a new service capability (research, ledger, distillation, council, voice) must import that service in this file. The import block is physically small (concentrated in the first 20 lines), so any two concurrent branches touching it produce a conflict marker on the same region. The rerere resolution is mechanically the same each time: union both sets of imports. This is exactly the condition LES-026 identified for coordination logs and LES-L07 identified for CAPABILITY_MAP.md — mandatory shared append region, additive edits, no semantic disagreement.
- Lesson: **when a source file is a mandatory integration point that every feature branch must append to, apply the same union-driver remedy used for shared docs — the tandem-treadmill pattern is not limited to Markdown.** `merge=union` is safe when the conflict is provably additive (both sides only add lines, neither edits an existing line). The rerere postimage is the evidence: the resolution is the full union. The auto-rebase runner (LES-L03) is what makes this viable on GitHub, where git drivers do not run natively.
- Fix (mechanical follow-up — NOT implemented in this lessons-only PR): add `apps/worker/app/worker.py merge=union` to `.gitattributes`. The LES-026 same-line caveat applies: union does NOT resolve two sides editing the same existing import line (e.g. renaming an import or changing `import X` to `from X import Y`); those remain single-writer conflicts. In practice, the worker import block has been append-only for 10+ commits, so union is correct. Longer term: if AOS-WORKER-ROUTER-001's registry is extended so handler modules are discovered and imported automatically (plugin-dir scan or entry-points), the central import block pressure disappears and this remedy becomes unnecessary. Track as a follow-up; do not bundle into a lesson PR.
