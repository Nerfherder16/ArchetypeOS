# LES-L19 — replacing a provider-selection function must preserve its hermetic/offline contract; `routed_provider` bypassed `llm_provider=deterministic` and CI hit the network

## Aliases

- routed_provider ignored llm_provider=deterministic
- CI ConnectionRefused to localhost:11434 after routing change
- worker test hit the network / LLM endpoint unreachable
- hermetic escape hatch lost when swapping get_provider for the router

## Status

validated

## Owner

Chief Architect / Orchestrator (laptop session)

## Evidence

- AOS-LLM-ROUTE-COV slice 2 switched `distillation`/`council` from
  `get_provider(settings, sink=...)` to `routed_provider(task_class, sensitivity, settings, sink=...)`.
  The `Worker tests and lint` CI job then failed:
  `RuntimeError: LLM endpoint http://localhost:11434/v1 unreachable: [Errno 111] Connection refused`.
- Root cause: `get_provider` reads `settings.llm_provider` and returns the
  `DeterministicProvider` when it is `"deterministic"` (the config default and the
  hermetic/offline signal). `route()` did NOT consult `llm_provider` — it selected by
  tier *availability*, and because `llm_base_url` defaults to
  `http://localhost:11434/v1`, the LOCAL tier read as "available" and the router tried
  to reach it. The unit router tests passed (they assert selection, never call
  `generate()`); only the worker test, which executes a task end-to-end, exercised the
  live call and exposed it.
- Fix: `route()` now short-circuits to the deterministic tier when
  `settings.llm_provider == "deterministic"`, restoring the offline contract.

## Linked Decisions / Projects

- `packages/aos_core/aos_core/services/llm_router.py` — `route()` deterministic override
- `packages/aos_core/aos_core/llm/__init__.py` — `get_provider` (the contract that was replaced)

## Content

- Event: a routing-coverage change made two services route by tier instead of by
  `llm_provider`, silently dropping the `llm_provider=deterministic` offline escape
  hatch that CI (and any reasoned-tier-opt-out node) depends on. Green unit tests hid it;
  the end-to-end worker test caught it.
- Rules:
  1. When you replace a provider/dependency-selection function, **enumerate and preserve
     its side contracts** — here, "`llm_provider=deterministic` ⇒ never touch the network."
     A drop-in that changes selection semantics must still honor the offline/hermetic mode.
  2. Unit tests that assert *selection* are not enough for a provider change — a test that
     actually *executes* the call (or an explicit "offline mode stays offline" test) is what
     proves hermeticity. Add the latter alongside any routing change.
  3. A default that makes a tier "available" (`llm_base_url` defaulting to localhost) means
     "configured," not "reachable" — availability checks must not be mistaken for a promise
     the endpoint answers.
