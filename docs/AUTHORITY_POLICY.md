# Authority Action Policy (AOS-AUTHORITY-001)

## Purpose

ArchetypeOS's constitution requires human approval for destructive actions. As
agents gain capabilities, "review-first" must be **enforced infrastructure, not
convention** (2026-07-08 system evaluation, Finding 10). The authority engine makes
every high-impact operation pass through one central policy evaluator.

## Action classes

Every high-impact operation maps to exactly one `ActionClass`, ordered by escalating
risk (`packages/aos_core/aos_core/services/authority.py`):

| Level | Class | Requires approval | Meaning |
| --- | --- | --- | --- |
| 0 | `capture_only` | no | Capture input for later review (voice/command turns). Performs nothing. |
| 1 | `read_only` | no | Read data or run analysis with no side effects. |
| 2 | `draft_artifact` | no | Produce a draft artifact awaiting review (never executes it). |
| 3 | `external_network` | **only if sensitive** | Send data to an external network. |
| 4 | `repo_write` | **always** | Write to a repository working tree. |
| 5 | `git_commit` | **always** | Commit/push to version control. |
| 6 | `deploy` | **always** | Deploy or restart a running service. |
| 7 | `delete_destructive` | **always** | Delete data or perform an irreversible operation. |

## The evaluator

```text
requires_approval(action_type, target=None, sensitivity="public", capability=None) -> bool
```

The policy is a **pure, total function** — trivially testable and impossible to
bypass silently:

1. **Write/destructive classes (`repo_write`, `git_commit`, `deploy`,
   `delete_destructive`) ALWAYS require approval** — no `sensitivity` value and no
   claimed `capability` can waive it. This is the enforcement backbone.
2. **`external_network` requires approval iff the data is sensitive** — `private`,
   `internal`, `confidential`, `restricted`, or `secret`. Public data may egress
   freely (research web services stay off by default; this governs their egress).
3. **`capture_only` / `read_only` / `draft_artifact` never require approval** — they
   have no side effects. This is why voice/command mode is safe: it captures and
   prepares work as drafts, and the draft's promotion into a concrete action is a
   separate, approvable step.
4. An **unknown action type raises** rather than defaulting to "allowed".

`evaluate(...)` returns the same decision plus the level and a human-readable reason
for the audit trail and the dashboard.

## How routes ask

A route or client asks the engine two ways:

- In-process: call `requires_approval(...)` / `evaluate(...)` directly.
- Over HTTP: `POST /authority/evaluate` with `{action_type, target?, sensitivity?, capability?}` returns the decision. `GET /authority/action-classes` lists the catalog.

## The pending queue

Actions awaiting a human decision are `ApprovalRecord` rows with
`approval_status = "pending"`. `GET /authority/pending` surfaces the queue for the
operator dashboard (the "Awaiting You" surface).

## Who may approve (AOS-AUTH-BOUNDARY-001)

Approving or rejecting an action changes authority state, so it is an
**operator-owned** mutation. `POST /authority/actions/{id}/authorize` and
`.../reject` are gated by the reusable `require_operator` dependency
(`apps/api/app/security.py`):

- When `operator_token` is set, the request must carry a matching `X-Operator-Token`
  (compared in constant time). The approver's `X-Operator-Id` (default `operator`)
  is recorded as `updated_by` on the `ActionRequest`, so approvals are attributable.
- When no token is set, the routes run open **only** if `auth_dev_mode` is true (the
  local/tailnet default, logged as a warning). The shipped `docker-compose.yml` sets
  `AUTH_DEV_MODE=false`, so a deployed profile with no operator secret **fails
  closed** (`503`) rather than accepting anonymous approvals.

The same `require_operator` gate governs the node-registry control plane: node
enrollment, credential rotation (`POST /nodes/{id}/rotate-credential`), and
revocation (`POST /nodes/{id}/revoke-credential`). A node's own `X-Node-Token`
governs node-owned actions (heartbeat, and re-registration of an already-enrolled
node) — a node can never approve an authority action or enroll/repolicy another node.

## Applies to

- Voice promotions (draft -> concrete action)
- Research web egress
- Future repo write actions
- Deploy jobs
- PR actions
- Connector egress

## Acceptance criteria (Finding 10)

- Every high-impact operation declares an action class. ✔ (the `ActionClass` enum)
- Routes can ask the Authority Engine whether approval is required. ✔ (`requires_approval` / `POST /authority/evaluate`)
- Dashboard shows pending authority actions. ✔ (`GET /authority/pending`)
- No destructive/write action can bypass authority policy. ✔ (write/destructive classes always gate; locked by `test_write_and_destructive_classes_always_require_approval`)
