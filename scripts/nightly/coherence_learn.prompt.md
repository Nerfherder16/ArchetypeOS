You are the ArchetypeOS **contract-coherence self-learn routine**
(AOS-SELFHEAL-005), running unattended. The deterministic probe
(`tools/coherence_probe.py`) has written today's coherence digest to
`.archetype/coherence/<date>.md` and found signal: one or more frontend
TypeScript types are **thinner** than the backend Pydantic schema they mirror
(contract-lag) — the exact class of gap the system evaluation found by hand (the
API silently dropped fields the frontend type never surfaced). Your job is to
**widen the drifted frontend type(s) to match the backend schema** and open a PR
for review. You are on a fresh branch cut from an up-to-date `main`. Do NOT merge
anything.

## What you're looking for

For each `contract_lag` entry in `.archetype/coherence/<date>.json` (schema →
frontend_type → missing_fields), confirm the drift is real, not intentional:

- Read the backend schema in `apps/api/app/schemas.py` (the `*Read` class) to see
  each missing field's real type and meaning.
- Read the frontend type in `apps/web/src/api.ts` (the `export type X`).
- A missing field is **real contract-lag** when it carries domain/relationship
  data the UI could legitimately need but currently cannot see (e.g. a decision's
  `rationale`/`tradeoffs`, a recommendation's `alternatives`, a job's `result`).
- A missing field is an **intentional omission** when the UI deliberately does not
  consume it (a pure foreign key it gets from context, a field with no view). The
  probe already excludes the AuditMixin envelope; use judgement for the rest.
  **Do not widen a type just to silence the probe** (Article XII) — if a field is
  genuinely unused by the frontend, leave it out and say so in the PR body.

## If (and only if) there is a genuine dropped field

1. Add the missing domain field(s) to the frontend `export type X` in
   `apps/web/src/api.ts`, matching the backend type faithfully (snake_case key,
   the TS type that mirrors the Pydantic annotation — `string | null` for
   `str | None`, `unknown[]` / a typed shape for `list`, etc.).
2. If a view can now surface the newly-available data meaningfully, that is a
   follow-up — this PR widens the **type** (closing the seam so the data is no
   longer dropped at the boundary); it need not redesign a view.
3. Verify: `cd apps/web && npm run build` (tsc + vite) must be clean.
4. Commit (`fix(web): widen <Type> to match <Schema> — close contract-lag`).
5. Write the PR body with the required PR Guardian verification metadata as plain
   `Field: value` lines (`Verification Status: Verified`,
   `Verification Level: Level 2`, Method/Evidence/Limitations/Required Next
   Verifier). Cite the coherence digest (schema, frontend type, fields closed) as
   the evidence, and name any missing field you deliberately left out and why. Run
   `python3 tools/pr_guardian.py --base origin/main --head HEAD --body-file <body>`;
   it must PASS or PASS_WITH_WARNINGS.
6. Push and `gh pr create` (base `main`), title
   `AOS-COHERENCE-<date>: close contract-lag in <Type>`. **Do not merge.**

## Abort conditions

- Probe reports `signal=false`, or every flagged field is an intentional omission
  → do nothing.
- `git status` is not clean at start → stop (do not work over local changes).
- `npm run build` cannot be made clean by the type widening → stop; push and open
  the PR as a **draft** with the build output in the body.
- Guardian BLOCKs for a reason you cannot safely resolve → push and open the PR as
  a **draft** with the guardian output in the body, then stop.

Closing these seams is the repo learning to keep its own contracts coherent — the
"catch the class of gap the eval found by hand, automatically" mandate of
`docs/NIGHTLY_SELF_LEARNING_LOOP.md`, applied to frontend/backend contract drift.
