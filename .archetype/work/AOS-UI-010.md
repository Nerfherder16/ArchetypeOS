# AOS-UI-010 — Per-agent model badge in the Council dashboard

## Summary

Surface the **model that produced each Council agent's output** in the Council & Decisions
dashboard, completing the cross-session handoff from the laptop's AOS-LLM-EVAL-001 (#101), which
added `CouncilAgentOutput.agent_model` and exposed it in `CouncilAgentOutputRead` — the API already
returns it; the UI just discards it. When the multi-model council is enabled, each agent draws a
different free model, and this badge makes that diversity visible.

**Frontend only.** No backend/API/schema change, no new dependencies. Trivial (one type field +
one conditional badge + a test), so built directly by the Orchestrator and verified independently
(the build + full Playwright + a route-stubbed screenshot are the independent check).

## Scope

- `apps/web/src/api.ts` — add `agent_model?: string | null;` to the `CouncilAgentOutput` type
  (matches `CouncilAgentOutputRead.agent_model: str | None`).
- `apps/web/src/main.tsx` — in the council agent card (`data-testid="council-agent-card"`),
  render a small model badge (`.aos-pill info`, `data-testid="council-agent-model"`) showing
  `output.agent_model` **only when present** (deterministic-provider outputs have `agent_model =
  null` → no badge; multi-model outputs show e.g. `llama-3.3-70b`).
- `apps/web/e2e/council-dashboard.spec.ts` — assert the badge renders when `agent_model` is
  present (route-stub a review with agent outputs carrying `agent_model`), and that its absence
  does not break the card. Keep the existing worker-driven assertions unchanged.

## Non-goals

- No change to the council run, provider selection, or `agent_model` population (that's the
  laptop's AOS-LLM-EVAL track).
- No new surface; this augments the existing Council view.

## Acceptance criteria

1. When an agent output has `agent_model`, the council agent card shows a model badge; when null,
   no badge and the card is unchanged.
2. `npm run build` clean; full Playwright suite green incl. the new assertion; PR Guardian PASS.

## Verification (Orchestrator)

- `npm run build` clean; full `npx playwright test` green.
- Route-stubbed screenshot of a council review whose agent outputs carry `agent_model`, showing
  the badge on each agent card.
