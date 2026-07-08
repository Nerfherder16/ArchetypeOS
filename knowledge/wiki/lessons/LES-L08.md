# LES-L08 — Naming the literal `PR_GUARDIAN_OVERRIDE_` prefix in a PR body trips `override-without-lesson-citation`, even when the sentence says NOT to use it

## Aliases

- writing about override tokens blocks the PR
- Guardian body substring match on PR_GUARDIAN_OVERRIDE_
- override-without-lesson-citation false positive
- documenting the override token trips the override gate

## Status

validated

## Owner

Chief Architect / Orchestrator (laptop session)

## Evidence

- AOS-TOIL-2026-07-08 (this change set): the `aos-ship-pr` skill PR was authored with a PR body whose guardrails list read "Guardian BLOCKs are fixed in code, not overridden with `PR_GUARDIAN_OVERRIDE_*`." Running `python3 tools/pr_guardian.py --base origin/main --head HEAD --body-file <body>` returned `Verdict: BLOCK` with the single finding `override-without-lesson-citation` ("Override tokens must cite a lesson ID (LES-<n>) per RFC-0004."), exit code 1.
- Root cause is a raw-substring test on the body, not a token-usage parse: `tools/pr_guardian.py:486` `check_override_lesson_citation(body)` does `if "PR_GUARDIAN_OVERRIDE_" in body and not LESSON_ID_PATTERN.search(body)`. It fires on ANY occurrence of the prefix in the body text — an actual override, a quoted example, or a sentence forbidding overrides all read identically to the check.
- The escape hatch requires a numeric id: `LESSON_ID_PATTERN = re.compile(r"LES-\d+")` (`tools/pr_guardian.py:113`) matches `LES-021` but NOT the laptop `LES-L08` form (the `L` is not a digit). Citing a nightly `LES-L0X` id in the body does NOT satisfy this gate.
- Fix that cleared it: reword the body to reference override tokens without the literal prefix ("not sidestepped with an override token"). Re-running Guardian returned `Verdict: PASS`, exit 0. The check scans only the body-file (`body = read_body(args.body_file)`, `tools/pr_guardian.py:620`); the SKILL.md diff is not scanned by this rule, so the skill can keep the accurate `PR_GUARDIAN_OVERRIDE_*` reference for agents.

## Linked Decisions / Projects

- [[LES-031]] — the sibling Guardian-body-behavior gotcha (CI reads the body captured at push time); both say the PR body is parsed literally, so finalize its exact wording before relying on a body-dependent gate
- `tools/pr_guardian.py` — `check_override_lesson_citation` (line 486), `LESSON_ID_PATTERN` (line 113)
- `docs/RFC/RFC-0004` — the lesson-citation requirement the override gate enforces
- AOS-TOIL-2026-07-08 — the `aos-ship-pr` skill PR that surfaced it

## Content

- Event: a self-learn PR that merely *documents* the guardrail "don't use override tokens" was BLOCKed by `override-without-lesson-citation` because its body contained the literal `PR_GUARDIAN_OVERRIDE_` prefix. No override was actually being invoked.
- Source: self-found via running `tools/pr_guardian.py` locally before push (AOS-TOIL-2026-07-08).
- Category: process.
- Why it recurs: the check is a substring test (`"PR_GUARDIAN_OVERRIDE_" in body`), not a parse of "is an override actually claimed here." Any PR body, skill, or doc that *names* the token prefix to explain or forbid it looks identical to a real, uncited override. Nightly self-learn and change-control work — which frequently writes ABOUT the gate stack — is the most likely to hit this.
- Lesson: **when a gate matches on a raw substring, writing about the thing the gate detects trips the gate.** In a PR body, refer to Guardian override tokens generically ("an override token") rather than pasting the `PR_GUARDIAN_OVERRIDE_` prefix; if the literal prefix is genuinely required in the body, also cite a numeric `LES-\d+` id (the gate accepts `LES-021`, not the laptop `LES-L0X` form). The check reads only the body-file, so documentation that must show the literal token belongs in the committed skill/doc, not the PR body.
- Fix (applied in this change set): the PR body was reworded to drop the literal prefix, turning the BLOCK into PASS; the `aos-ship-pr` SKILL.md keeps the accurate `PR_GUARDIAN_OVERRIDE_*` reference because that file is not scanned by this rule.
- Status: closed — reworded body cleared the original BLOCK, then the hardening follow-up was **applied** (AOS-SELFHEAL-GUARDIAN): `has_override` / `check_override_lesson_citation` now count an override only as a line-start directive (`^\s*(?:[-*]\s*)?PR_GUARDIAN_OVERRIDE_<KEY>`), so a prose mention no longer trips the gate — and no longer silently disables one; and `LESSON_ID_PATTERN` now matches `LES-L?\d+`, so the laptop `LES-L##` band satisfies the citation gate. Both fixes carry tests in `test_guardian_evolution.py`. This closes the class of bug, not just the instance.
