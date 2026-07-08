# LES-L05 — adding an API route needs the frozen route-inventory (set + count) updated in the same change, or the governance test fails

## Aliases

- test_route_inventory_matches_frozen_set failed
- "unexpected routes" in the inventory diff
- frozen route set / EXPECTED_ROUTES
- new endpoint breaks the route count assertion

## Status

validated

## Owner

Chief Architect / Orchestrator (laptop session)

## Evidence

- Self-found (2026-07-08, AOS-VOICE-001): adding `POST /voice/turns` and `GET /voice/inbox` made `apps/api/tests/test_route_inventory.py` fail two ways: `test_route_inventory_matches_frozen_set` (actual - EXPECTED = the two new routes) and `test_route_inventory_count` (`len == 49` assertion). The full API suite reported exactly these 2 failures out of 279; the new voice tests themselves passed.
- Root cause: `EXPECTED_ROUTES` is a hand-maintained `frozenset[(method, path)]` plus two hard-coded length assertions (`== 49`). It is deliberately a governance tripwire — any route added or removed must be reflected there, so a route can't be added (or silently dropped) without a reviewer seeing it in the diff. Forgetting it is caught pre-commit, not a runtime bug.

## Linked Decisions / Projects

- `apps/api/tests/test_route_inventory.py` — the frozen inventory (updated 49→51 for the voice routes)
- `docs/ACTIVE_WORK.md` — AOS-VOICE-001
- [[LES-031]] — the other "governance test reads frozen state" gotcha (PR body captured at push time)

## Content

- Event: a new domain (voice) added its two routes and the frozen inventory test failed on both the set-equality check and the `== 49` count. Fix is trivial (add the two `(method, path)` tuples under a labelled comment, bump both counts to 51, update the running-total comment) but it must land in the SAME change set as the route, or CI is red.
- Generalization: this repo encodes several "frozen snapshots of reality that a test guards" — the route inventory (count + set), the Alembic single-head assertion, the PR-body verification-metadata gate. When you change the reality (add a route, add a migration, add a high-risk file), update its guard in the same commit. Treat a failing guard as the system doing its job, not as noise: the diff it forces is the audit trail. Checklist when adding an endpoint: register the router in `main.py`, add the `(METHOD, path)` pair(s) to `EXPECTED_ROUTES`, bump both length assertions and the tally comment, add route tests.
