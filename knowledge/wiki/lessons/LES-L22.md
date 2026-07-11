# LES-L22 — Dispatch entry-point files become import-block hotspots under concurrent development; self-registering registries eliminate this by design

## Aliases

- worker.py import conflict
- dispatch entry-point merge hotspot
- concurrent sessions colliding on service imports
- handler import accumulation friction

## Status

closed

## Owner

Chief Architect / Orchestrator (laptop session)

## Evidence

- Rerere hash `07508cfb5e201873e907de271679941072af99d7` appears in all three conflict digests: `2026-07-08`, `2026-07-10`, `2026-07-11` (`.archetype/conflicts/`).
- Preimage (`.git/rr-cache/07508cfb.../preimage`) shows an import-block conflict in `apps/worker/app/worker.py`: one branch added `from aos_core.services.council import council_provider, run_council`; a concurrent branch added `from aos_core.services.council import run_council`, `from aos_core.services.usage import make_ledger_sink`, and `from aos_core.llm import get_provider` to the same import block.
- `git log -- apps/worker/app/worker.py` shows 14+ commits from parallel sessions, each adding service module imports for a new handler type (`AOS-LLM-EVAL-001`, `AOS-USAGE-001`, `AOS-RESEARCH-001`, etc.) to the same top-level dispatch file.
- The conflict was auto-resolved by rerere each time, but the same import-region fingerprint kept recurring as long as the entry-point accumulated explicit per-service imports.
- The structural fix arrived with AOS-WORKER-HANDLERS-001 (PR #189), which replaced explicit imports per handler with a self-registering registry. `apps/worker/app/worker.py` no longer imports individual service modules; handlers register themselves. The hash `07508cfb` can no longer be triggered by new feature branches.

## Linked Decisions / Projects

- `apps/worker/app/worker.py` — the affected file
- AOS-WORKER-HANDLERS-001 (PR #189) — the structural fix: self-registering handler registry
- [[LES-L26]] — the same additive-append hotspot pattern for coordination log docs (union driver fix)
- [[LES-L07]] — the same pattern for `docs/CAPABILITY_MAP.md` (union driver + fragment split fix)
- `.archetype/conflicts/` — the daily conflict digests that surfaced this

## Content

- Event: during the AOS-REVIEW-002 remediation sprint (PRs #185-#195), multiple concurrent laptop and cloud sessions each added a new job handler to `apps/worker/app/worker.py` by appending imports at the top of the file. Because worker.py was the single dispatch entry-point — importing every service it needed to call — it became the one file every handler-adding branch must touch. The same narrow import region conflicted on every concurrent merge. git rerere cached the resolution (`07508cfb`) and auto-applied it on subsequent hits, but the fingerprint kept accumulating because new sessions kept adding imports the same way.
- Root cause: a monolithic dispatch entry-point that holds explicit `from service import fn` lines for every handler is structurally identical to a shared coordination log or a capability map: every concurrent branch MUST append to the same region, making conflicts mathematically guaranteed when two sessions land in the same window.
- Why union merge driver alone is insufficient here: unlike additive markdown lists, an import block can have real semantic conflicts (same name from different modules, circular import order dependencies, intentional removals). A union driver would silently keep both sides of an import rename or a deliberate deletion — the wrong fix for source code. The right fix is to eliminate the shared mutation surface, not tolerate it.
- Fix (structural, already implemented): AOS-WORKER-HANDLERS-001 introduced a self-registering handler registry. Each handler module registers itself at import time; worker.py imports the registry loader, not the individual handlers. Adding a new handler type creates a new file and does not touch worker.py at all. The dispatch entry-point is now closed for modification and open for extension (OCP). The conflict hash `07508cfb` cannot recur under the new structure.
- General rule: any file that MUST be modified for every new "thing" added to the system — a dispatcher, a route registry, a feature flag enum, a factory switch statement — is a structural merge hotspot in a concurrent build environment. The correct fix is always to invert control: make the new "thing" register itself, rather than requiring the central file to import it. Detect this pattern early (when a file is touched by 5+ independent branches in a short window) and convert before the friction compounds.
