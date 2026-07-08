# LES-L06 — an optimistic local update that patches only the field you changed drops server-computed fields; merge the full response

## Aliases

- promoted badge did not appear after approve
- optimistic update lost a server field
- "I set review_state locally but the promotion linkage never showed"
- patch-one-field vs replace-with-response

## Status

validated

## Owner

Chief Architect / Orchestrator (laptop session)

## Evidence

- Self-found (2026-07-08, AOS-VOICE-005): the Voice Inbox card's `handleResolved` did `{ ...it, review_state: state }` — updating only the field the click changed. But `PATCH /voice/inbox/{id}` also computes `promoted_kind` / `promoted_id` server-side (approval promotes a mapped intent into a draft ResearchNote/Decision). The optimistic merge kept the stale `promoted_kind: null`, so the "→ research note" badge never rendered even though the API had set it. The Playwright spec asserting the badge failed at the assertion line, catching it before commit.
- Fix: `updateVoiceInboxItem` already returns the updated entity; the card now passes that whole object up and `handleResolved` replaces the item with the server's version (`it.id === updated.id ? updated : it`) instead of spreading one field onto the stale copy.

## Linked Decisions / Projects

- `apps/web/src/features/voice/VoiceInboxView.tsx` — the fix (merge the PATCH response)
- `apps/api/app/routes/voice.py` — the PATCH that computes promotion server-side
- [[LES-L05]] — the sibling "keep the guard in sync" lesson (frozen route inventory)

## Content

- Event: a mutation endpoint returns a richer entity than the one field the UI toggled, and an optimistic update that only patches the toggled field silently discards the rest. The bug is invisible unless a test asserts the server-derived field — here the e2e badge assertion did exactly that.
- Generalization: when a write endpoint returns the updated resource, treat that response as the source of truth and replace the local copy with it. Reserve field-level optimistic patches for when you deliberately do NOT round-trip (and then reconcile on the next fetch). Any field the server computes on write (derived status, linkage ids, timestamps, promotion targets) will be missed by a `{ ...old, oneField }` merge. Corollary for tests: assert on a server-computed field, not just the field you clicked — that is what turns this class of bug from silent to caught.
