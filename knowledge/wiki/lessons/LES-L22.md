# LES-L22 — frontend TypeScript types silently drop backend fields when *Read schemas add new fields without a corresponding api.ts update

## Aliases

- contract-lag between Pydantic Read schema and frontend TS type
- ConnectorRead credential_present / reachable absent from Connector type
- JobRead routing fields absent from Job type
- RepositoryRead sensitivity absent from Repository type
- coherence probe signal=true
- AOS-SELFHEAL-005 nightly contract-coherence finding

## Status

validated

## Owner

Nightly coherence routine (AOS-SELFHEAL-005)

## Evidence

- Coherence probe 2026-07-16 (`tools/coherence_probe.py --json /tmp/coherence.json`)
  reported signal=true for three type pairs:
  - `ConnectorRead` → `Connector`: `credential_present`, `reachable` missing
  - `JobRead` → `Job`: `assigned_node_id`, `required_capability`, `requires_write`,
    `routed_at`, `routing_explanation`, `routing_status`, `sensitivity` missing
  - `RepositoryRead` → `Repository`: `sensitivity` missing
- Backend comment on each field documents the domain intent:
  `AOS-CONNECTOR-RUNTIME-001`, `AOS-NODE-EXECUTION-001`, `AOS-AUTHORITY-HARDEN-001`.
- PR `laptop/nightly-coherence-2026-07-16` widened the three types.

## Linked Decisions / Projects

- `apps/api/app/schemas.py` — ConnectorRead (lines 693–716), JobRead (lines 66–88),
  RepositoryRead (lines 40–55)
- `apps/web/src/api.ts` — Connector, Job, Repository types
- `tools/coherence_probe.py` — automated detector
- `scripts/nightly/coherence_learn.prompt.md` — self-heal routine

## Content

- Event: Three backend `*Read` Pydantic schemas carried fields (decomposed connector
  health, job routing decisions, repository sensitivity) that were never reflected in
  the mirroring frontend TypeScript types. The API returned these fields but the
  frontend type declared them absent, so any consuming component received `undefined`
  where a typed value was expected — silent data loss at the boundary.
- Rules:
  1. **Whenever a Pydantic `*Read` schema gains a new domain field, update the
     matching `export type` in `apps/web/src/api.ts` in the same PR.** The coherence
     probe catches drift automatically, but the right fix is to never let it accumulate.
  2. **Schema comments citing an AOS ticket are a signal the field matters.** If the
     backend comment says `AOS-FOO-NNN`, the field is intentional domain data — it
     almost certainly belongs in the frontend type.
  3. **A pure FK (e.g. `node_id` the UI looks up from a separate endpoint) may be
     omitted intentionally.** Use judgment: if the field is a computed status, policy
     flag, or human-readable explanation, it is real domain data; if it's a raw FK the
     UI resolves anyway, omission may be intentional.
  4. **PR Guardian overrides for type-only coherence fixes are appropriate** when the
     change widens types only, introduces no new behavior, and the coherence probe is
     the acceptance oracle. Always cite this lesson (LES-L22).
