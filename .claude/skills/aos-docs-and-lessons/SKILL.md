---
name: aos-docs-and-lessons
description: Use when updating ArchetypeOS state docs (docs/CURRENT_STATE.md, ACTIVE_WORK.md, RECENT_CHANGES.md), when APPLYING the reconciliation after tools/doc_staleness.py reports STALE or a doc-staleness WARN fires in PR Guardian (running/interpreting the detector itself is aos-diagnostics-and-tooling), when .archetype/reconciliation/PENDING.md exists, when merges conflict on ACTIVE_WORK/RECENT_CHANGES/lessons index, when a lesson is required (Guardian BLOCK, CI failure, review remediation, LES id allocation), when authoring an RFC in docs/rfc/, or when capability-map-not-updated blocks.
---

# AOS Docs and Lessons

## 1. Overview

ArchetypeOS treats documentation as governed state, not commentary. Three markdown "state docs" are the durable record of what the system is and what is in flight; a deterministic staleness detector plus a reconciliation loop keeps them honest; every learning event (Guardian BLOCK, CI failure, review remediation, self-found defect, operator correction) becomes a durable lesson page under `knowledge/wiki/lessons/` per RFC-0004; and major changes are argued first in RFCs under `docs/rfc/`.

This skill is the runbook for maintaining all of that: the state-doc contract, the union merge driver for parallel sessions, the doc-staleness loop end to end, lesson authoring, RFC authoring, the capability map rule, and the house style. All commands run from the repo root (`cd` to the ArchetypeOS checkout first).

## 2. When to use / When NOT to use

Use this skill when:

- You merged (or pulled) work and need to update the state docs.
- `python3 tools/doc_staleness.py` says STALE, or a PR Guardian run shows a `doc-staleness:*` WARN.
- `.archetype/reconciliation/PENDING.md` exists and needs applying.
- A merge produced a conflict (or a union-merge artifact) in `docs/ACTIVE_WORK.md`, `docs/RECENT_CHANGES.md`, or `knowledge/wiki/lessons/index.md`.
- You need to write a lesson (LES page + index row) or an RFC, or pick a lesson id.
- Guardian blocked with `capability-map-not-updated`.

Do NOT use this skill for:

- Guardian verdict handling, override tokens, or the merge gate: see `aos-change-control`.
- The content and history of the lessons themselves (what was learned): see `aos-failure-archaeology`.
- Interpreting detector output beyond docs (scanner, guardian internals): see `aos-diagnostics-and-tooling`.
- Test and evidence standards for the code a doc describes: see `aos-validation-and-qa`.
- Which model tier should do the writing: see `aos-model-routing`.

## 3. The state docs and their contract

| File | Role | Update cadence |
| --- | --- | --- |
| `docs/CURRENT_STATE.md` | Durable project checkpoint. "Status" block carries phase, current sprint narrative, and the newest merged PR references. Every new session reads it before planning. | After every meaningful merge |
| `docs/ACTIVE_WORK.md` | Execution board (markdown fallback for the Plane board). Work items with Status in: Proposed, Ready, In Progress, Blocked, In Review, Merged, Deferred. | On claim, status change, merge |
| `docs/RECENT_CHANGES.md` | Chronological human-readable merge log. Dated `## YYYY-MM-DD` entries, newest near the top. Not a replacement for git history. | After every meaningful merge |

Supporting: `docs/HANDOFF.md` (session handoff pack) and `.archetype/roadmap.md` (the "Current phase" line the staleness detector reads).

Precedence rule (verified in `docs/PLANE_PROJECT_BLUEPRINT.md`): Plane is the live working board, but the markdown state files are the durable fallback and win on conflict. "On conflict, markdown wins. Fix Plane to match markdown, never the reverse." When Plane is unreachable, continue on markdown alone and record deferred board changes under Blocked Work in `docs/ACTIVE_WORK.md`.

Post-merge update rule (verified in `docs/ORCHESTRATOR_PLAYBOOK.md`, work-package loop step 5): state updates ride IN the work PR itself. ACTIVE_WORK, CURRENT_STATE, HANDOFF, and RECENT_CHANGES are updated in the same PR as the work, and the previous PR's post-merge reconciliation is folded in too. Historically some reconciliations were separate follow-up PRs ("Post-merge state reconciliation for ..."); the current practice is in-PR.

Single-writer discipline: status flips on existing lines (for example "In Review" to "Merged") belong to the reconciliation owner. The union merge driver (next section) only protects additive edits, not two sessions editing the same line.

## 4. The union merge driver (parallel sessions, LES-026)

Two Orchestrator sessions appending to the same coordination logs used to conflict on every merge (the "tandem treadmill", LES-026: PR #68 was re-synced 3 times behind PRs #69/#70). Fix: git's built-in `union` merge driver, declared in `.gitattributes` at the repo root:

```text
docs/ACTIVE_WORK.md              merge=union
docs/RECENT_CHANGES.md           merge=union
knowledge/wiki/lessons/index.md  merge=union
```

What it does: on conflict, keep BOTH sides' lines instead of emitting conflict markers. Correct for additive edits (a new work item, a new changelog entry, a new lesson row) and makes these PRs auto-mergeable on GitHub.

What it does NOT do: resolve two sides editing the same existing line. Those stay single-writer by protocol (the reconciliation owner flips statuses). Worktrees do not help here: they isolate working directories, not the merge graph.

Side effect to expect: union merges can interleave entries, so `docs/RECENT_CHANGES.md` chronology is only approximately newest-first (a 2026-07-07 entry can sit below a 2026-07-06 one). Do not mass-reorder the file to "fix" this; add your entry near the top and move on.

## 5. The doc-staleness loop, end to end

Terms: HARD findings are definitive drift (CLI exit 1, Guardian WARN); SOFT findings are the normal one-PR reconciliation lag (advisory, exit 0, dropped by the Guardian).

### 5.1 Detector: tools/doc_staleness.py (AOS-20, closes LES-007)

Stdlib-only, hermetic, fail-open (never crashes a caller). Two signals as of 2026-07-06:

| Signal | Trigger | Severity |
| --- | --- | --- |
| `roadmap-phase-stale` | `.archetype/roadmap.md` "Current phase" starts with an early-phase token (foundation, phase 0, documentation foundation, scaffold) while `docs/CURRENT_STATE.md` carries a completion marker (regex: `v0.N complete`, `post-v0.N`, `sprint 1-9`) | HARD |
| `state-docs-pr-lag` | Newest `Merge pull request #N` in `git log --oneline -60` exceeds the newest `#N` referenced in CURRENT_STATE + RECENT_CHANGES | SOFT if lag 1 to 3, HARD if lag > 3 (`DEFAULT_HARD_THRESHOLD = 3`, tunable via `--hard-threshold`) |

Run it:

```bash
python3 tools/doc_staleness.py                      # report; exit 1 only on HARD
python3 tools/doc_staleness.py --hard-threshold 3   # explicit threshold
```

Verdicts: `FRESH` (no findings), `ADVISORY` (SOFT only, exit 0), `STALE` (any HARD, exit 1).

### 5.2 Guardian integration (WARN only, never BLOCK)

`tools/pr_guardian.py` has `check_doc_staleness()`: it imports the detector defensively (missing module = silent no-op), calls `evaluate()`, and surfaces only HARD findings as `Finding("warn", "doc-staleness:<signal>", ...)`. It never emits a block, fails open on any exception, and drops SOFT drift to keep the Guardian quiet. Do not try to "fix" a doc-staleness WARN by weakening the detector or the Guardian; reconcile the docs instead (Article XII of the Constitution: never game the alarm).

### 5.3 Correction: --fix, the post-merge hook, and /reconcile-state (AOS-SELFHEAL-001, merged as PR #80)

Everything in this subsection shipped on branch `laptop/aos-selfheal-doc-loop` (HEAD commit AOS-SELFHEAL-001), merged to main as PR #80. Motivation: LES-L01, a detector without a remediation trigger is not self-learning (the WARN fired on PRs #74 and #78 and was deferred every time, leaving the state docs 5 PRs behind).

The loop:

1. Draft generation:

   ```bash
   python3 tools/doc_staleness.py --fix
   ```

   Deterministically derives, from `git log`, every merged PR beyond the newest one the state docs reference (with merge-branch provenance) and writes a DRAFT to `.archetype/reconciliation/PENDING.md`. The directory is gitignored (machine-owned). `--fix` NEVER edits the state docs and never silences the HARD finding; the finding stands until the docs are genuinely reconciled.

2. Automatic trigger: `scripts/hooks/post-merge` reruns `--fix` after any local merge/pull and prints the draft path if one was written. Always exits 0 (a hook must never break a merge). Install once per clone:

   ```bash
   bash scripts/install-hooks.sh    # sets core.hooksPath -> scripts/hooks
   ```

3. Apply: the `/reconcile-state` skill, defined at `skills/ci_devops/reconcile_state.md` (note: repo `skills/` dir, not `.claude/skills/`). Its procedure: read the draft, gather substance per listed PR (`gh pr view <n>` or the PR's own notes), update RECENT_CHANGES (dated entry), CURRENT_STATE (the sprint/status line, reconciliation-owner only), and roadmap only on a genuine roadmap-phase HARD finding. Never fabricate; every reconciled claim traces to a merged PR. Then re-run the detector, confirm FRESH (or SOFT-only), delete `PENDING.md`, and commit (the touched files are union-merge-safe).

Declared follow-ups (open, not built): a Claude Code Stop hook, a CI-on-main auto-reconciliation PR, nightly-loop wiring.

## 6. Lesson authoring (RFC-0004)

RFC-0004 (`docs/rfc/RFC-0004-Learning-Feedback-Loop.md`, Accepted) makes lessons mandatory. A lesson is a durable, structured page in `knowledge/wiki/lessons/`, registered in `knowledge/wiki/lessons/index.md`, recorded in the SAME change set as the work that surfaced it (or the next reconciliation PR for post-merge events).

### 6.1 What requires a lesson

1. Every PR Guardian BLOCK on a real PR (true or false positive, both teach).
2. Every CI failure whose cause was not already a recorded lesson.
3. Every review remediation (a defect a reviewer or the Orchestrator catches that the builder missed).
4. Every live defect the system finds in itself.
5. Every operator correction of agent behavior worth keeping.

Anti-duplication rule: check the index FIRST. If the event repeats an existing lesson, cite that lesson (in the PR body or the doc) instead of writing a new page.

### 6.2 Categories and status

RFC-0004 categories: `guardian-catch`, `guardian-gap`, `ci-failure`, `review-remediation`, `self-found-defect`, `process`. Practice has added `design-insight` (LES-019, LES-023); acceptable, but prefer an RFC-0004 category when one fits.

Content-block Status lifecycle: `open` (not yet fed into a loop; open lessons are the visible improvement queue) or `closed` (consumed: cite the PR, guardian rule, or work package that consumed it). The index table is the single registry; on conflict between a lesson page and the index, the index wins. Open as of 2026-07-06 per the index: LES-019 and LES-029. LES-014 is closed (consumed by AOS-ARCH-EDGES-001, merged via PR #78); its remaining source import-graph edges are a separately scoped follow-up work item, not an open lesson.

### 6.3 ID allocation (tandem sessions, LES-L02)

Two concurrent sessions racing the next sequential `LES-NNN` produced add/add collisions twice (LES-027 on PR #74, LES-029 on PR #80). The namespace is now partitioned: the cloud session keeps `LES-NNN`; the laptop session allocates `LES-L01, LES-L02, ...`. Already-merged ids keep their numbers. Any new shared monotonic id under concurrent authorship follows the same rule: per-session namespace or single allocator, never optimistic first-come.

### 6.4 Lesson file format

Every lesson follows the vault page template (`knowledge/templates/page-template.md`) with the RFC-0004 fixed Content block. Strong exemplar: `knowledge/wiki/lessons/LES-023.md`. Minimal skeleton (derived from LES-023 and LES-003):

```markdown
# LES-XXX - <the transferable rule stated as a sentence, not a topic>

## Aliases

- <search terms a future agent might use>

## Status

validated

## Owner

Chief Architect / Orchestrator

## Evidence

- <verbatim finding / error line / run id, with PR numbers and dates>

## Linked Decisions / Projects

- [[index]] - lessons registry
- <related [[LES-nnn]] pages, .archetype/work/ specs, docs/rfc/ files>

## Content

- Event: <what happened, verbatim where possible>
- Source: <PR number(s), CI run id, or session date>
- Category: <guardian-catch | guardian-gap | ci-failure | review-remediation | self-found-defect | process>
- Lesson: <the rule, stated so a future agent can apply it without this context>
- Loop feed: <which loop consumes it: guardian rule candidate, work-package candidate, spec/checklist change, or "validated existing rule">
- Status: <open | closed - cite what consumed it and when to cite this row>
```

Formatting note: existing lesson titles and index rows use the em dash character (U+2014) as the id/title separator; match the surrounding file when adding rows. The `## Status` header of the page itself is `raw | validated` per the template (some pages carry `closed` there instead; the index Status column is authoritative either way).

Then add a row to the `knowledge/wiki/lessons/index.md` table: `| [[LES-XXX]] | date | category | short lesson | source | status | consumed by |`. The index is union-merged (LES-026), so parallel additions do not conflict.

Vault hygiene before marking a page validated (from the template): no dead links, not an orphan, no duplicate concept, not stale, has aliases, evidence, owner, and at least one decision/project link.

### 6.5 How lessons feed the loops

- Guardian evolution (AOS-PRG-003): every guardian rule change must cite at least one lesson by ID. Rules evolve from logged reality, never speculation, and are never silenced in place.
- Recurring or self-found-defect lessons become spec'd work packages (precedent: LES-005 became AOS-RUNTIME-004).
- `process` lessons amend the work-package template, PR conventions, or CLAUDE.md operating rules.

## 7. RFC authoring

Location and naming: `docs/rfc/RFC-NNNN-Title-With-Hyphens.md`, four-digit sequential numbering (RFC-0000 through RFC-0010 exist as of 2026-07-06). Required for: new engines, agents, runtime services, provider integrations, governance/security/data-model changes, major UI/UX changes, autonomous action capabilities, external integrations (`docs/RFC_PROCESS.md`).

Lifecycle: `Draft -> Council Review -> Final Judge -> Accepted / Rejected / Deferred -> Implementation -> Validation -> Knowledge`.

Section reality check: `docs/RFC_PROCESS.md` lists 14 required sections (Summary, Problem, Goals, Non-goals, Proposal, Alternatives, Evidence, Risks, Security impact, Compliance impact, Migration plan, Acceptance criteria, Open questions, Final Judge verdict). Recent RFCs in the repo (RFC-0004 Accepted, RFC-0009 Accepted/MVP landed, RFC-0010 Proposed) actually use a leaner practical set. Skeleton matching current practice (derived from RFC-0009 and RFC-0010):

```markdown
# RFC-NNNN - <Title>

## Status

Proposed (<operator direction or motivating event, dated>). <What it builds on.>

## Summary

<2 to 5 sentences: what ships, why now, the seam it extends.>

## Problem

<Concrete gap, with evidence from a real run or lesson id.>

## Goals

- <in scope, testable>

## Non-goals (explicitly deferred)

- <named deferrals so scope creep is visible>

## Design (or Proposal)

<The mechanism. Cite files and seams by path.>

## Alternatives considered

- <option>: <why rejected, with evidence>

## Acceptance criteria

- <machine-checkable where possible>

## Dependencies

- <RFCs, packages, infra>

## Next steps

- <the first work package(s)>
```

Add sections from the full RFC_PROCESS list (Security impact, Migration plan, Final Judge verdict, ...) whenever they are non-trivial for the change. Never skip Alternatives or Acceptance criteria. RFC status updates (Proposed to Accepted) go through the normal PR path; do not flip them ad hoc.

## 8. The capability map rule (LES-003)

`docs/CAPABILITY_MAP.md` maps every engine, agent, dashboard, workflow, and runtime component to one of 13 capability layers (Layer 0 Constitution through Layer 12 Orchestration). Guardian rule `check_capability_map` in `tools/pr_guardian.py`: any PR that ADDS a `docs/*.md` file (git status `A`), excluding `docs/rfc/` and the governance allowlist (`CAPABILITY_MAP.md`, `ENGINEERING_CONSTITUTION.md`, `MASTER_ROADMAP.md`, `V0_1_SCOPE_LOCK.md`, `CONCRETE_BUILD_PATH.md`), must also touch `docs/CAPABILITY_MAP.md` or the PR BLOCKs with `capability-map-not-updated`.

The fix is a genuine map update (place the new doc's capability in its layer), not the `PR_GUARDIAN_OVERRIDE_CAPABILITY_MAP` token. The record (audited in aos-change-control section 8, the home of this fact): no substantive code BLOCK (tests, secrets, metadata, acceptance) has ever been overridden, but override tokens do appear in merged PR bodies, including three early `_CAPABILITY_MAP` suppressions on docs PRs #7, #10, and #12. Since then the practice is the genuine map update, never the token. LES-003 is the incident history: PR #37 double-blocked on exactly this rule plus metadata format, and both were fixed, not overridden.

## 9. House style (extracted from CURRENT_STATE, RECENT_CHANGES, lessons index)

- Every doc opens with `# Title` then `## Purpose` stating what the file is for in one or two sentences.
- `docs/RECENT_CHANGES.md` entries: `## YYYY-MM-DD` + separator + short title, then a `### Merged` / `### In Review` subsection, then dense bullets. The separator in existing headings is the em dash character (U+2014); match the file.
- Evidence is inline and specific: PR numbers (`PR #76`), CI run ids (`run 28822124340`), commit SHAs, lesson ids (`LES-026`), spec paths (`.archetype/work/AOS-X.md`). Claims without a traceable source do not belong in state docs.
- Bold is used for load-bearing phrases (verdicts, package names, the one-line takeaway), not decoration.
- Date-stamp anything volatile; sessions are identified where relevant ("laptop session", "remote session").
- ACTIVE_WORK items carry: Status, Owner, Branch (with base SHA), Summary (with spec path), Verification Status.

## 10. Task tier guide (candidate; routing home is aos-model-routing)

| Task in this skill's scope | Tier |
| --- | --- |
| Run `doc_staleness.py`, read the verdict, regenerate/inspect PENDING.md | Haiku |
| Add a RECENT_CHANGES entry or index row for a merge you performed | Sonnet |
| Apply a full /reconcile-state pass (multi-PR narrative reconciliation) | Sonnet |
| Author a lesson page (extract the transferable rule from an incident) | Sonnet, Opus if the root cause is contested |
| Author or revise an RFC | Opus |
| Resolve a same-line state-doc conflict between sessions | Opus (reconciliation owner) |

Tier labels are operator guidance, candidate status as of 2026-07-06, not enforced.

## 11. Common mistakes

- Bumping a PR number in CURRENT_STATE just to silence the staleness detector, without reconciling the narrative. Article XII violation: never game the alarm.
- Editing the state docs directly with `--fix` output expectations: `--fix` writes only the draft; a human or LLM applies the narrative half via `/reconcile-state`.
- Committing `.archetype/reconciliation/PENDING.md`. It is gitignored and machine-owned; apply it, then delete it.
- Flipping another session's work-item status line. Union merge does not protect same-line edits; status flips are reconciliation-owner only.
- Grabbing the next `LES-NNN` in a laptop/tandem session. Use the `LES-L##` band (LES-L02).
- Pinning a specific lesson id as perpetually `open` in tests or docs. Closed lessons are stable anchors; open ones are not (LES-025).
- Writing a new doc under `docs/` without touching `docs/CAPABILITY_MAP.md` (Guardian BLOCK, LES-003).
- Recording the lesson in a later "cleanup" PR. RFC-0004 requires the same change set (next reconciliation PR only for post-merge events).
- Mass-reordering RECENT_CHANGES to restore strict chronology after a union merge.
- Reconstructing PR numbers, SHAs, or run ids from memory instead of copying them from tool output (LES-008).
- Treating a doc-staleness WARN as blocking, or trying to make it blocking. It is WARN-only by design; never weaken, never escalate without an RFC.

## 12. Provenance and maintenance

Authored 2026-07-06 on branch `laptop/aos-selfheal-doc-loop` (HEAD = AOS-SELFHEAL-001, since merged as PR #80). Derived from: `docs/CURRENT_STATE.md`, `docs/ACTIVE_WORK.md`, `docs/RECENT_CHANGES.md`, `docs/PLANE_PROJECT_BLUEPRINT.md`, `docs/ORCHESTRATOR_PLAYBOOK.md`, `.gitattributes`, `tools/doc_staleness.py`, `tools/pr_guardian.py`, `scripts/hooks/post-merge`, `scripts/install-hooks.sh`, `skills/ci_devops/reconcile_state.md`, `docs/RFC_PROCESS.md`, `docs/rfc/RFC-0004-Learning-Feedback-Loop.md`, `docs/rfc/RFC-0009-*.md`, `docs/rfc/RFC-0010-*.md`, `docs/CAPABILITY_MAP.md`, `knowledge/templates/page-template.md`, `knowledge/wiki/lessons/` (LES-003, LES-023, LES-L01, LES-L02, index.md).

Re-verification commands (run from repo root):

| Fact | Re-verify with |
| --- | --- |
| Markdown wins over Plane | `grep -n "markdown wins" docs/PLANE_PROJECT_BLUEPRINT.md` |
| Union-merged files list | `cat .gitattributes` |
| Staleness signals + threshold | `grep -n "DEFAULT_HARD_THRESHOLD\|roadmap-phase-stale\|state-docs-pr-lag" tools/doc_staleness.py` |
| Guardian WARN-only integration | `grep -n "check_doc_staleness" -A 5 tools/pr_guardian.py` |
| AOS-SELFHEAL-001 merged yet? | `git log origin/main --oneline \| grep -i selfheal` |
| Hook + installer behavior | `cat scripts/hooks/post-merge scripts/install-hooks.sh` |
| /reconcile-state steps | `cat skills/ci_devops/reconcile_state.md` |
| Lesson contract + categories | `sed -n 15,50p docs/rfc/RFC-0004-Learning-Feedback-Loop.md` |
| Open lessons + id bands | `sed -n 60,75p knowledge/wiki/lessons/index.md` |
| RFC required sections | `grep -n "^## \|^- " docs/RFC_PROCESS.md` |
| Capability map guardian scope | `grep -n "GOVERNANCE_DOC_ALLOWLIST" -A 8 tools/pr_guardian.py; grep -n "check_capability_map" -A 15 tools/pr_guardian.py` |
| Override-token record | `gh pr list --state merged --limit 200 --json number,body --jq '[.[] \| select(.body \| contains("PR_GUARDIAN_OVERRIDE")) \| .number]'` (expect a nonzero list of PR numbers; see aos-change-control section 8 for the per-PR breakdown, none of which suppressed a substantive code BLOCK) |
| State-docs-in-PR rule | `sed -n 35,45p docs/ORCHESTRATOR_PLAYBOOK.md` |
