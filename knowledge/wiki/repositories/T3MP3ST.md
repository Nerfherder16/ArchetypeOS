# T3MP3ST

## Aliases

- elder-plinius/T3MP3ST
- Tempest — autonomous red-team harness
- offensive-security meta-harness

## Status

evaluated

## Verdict

partial-borrow (patterns only) / monitor — **do not integrate any code.** The AGPL-3.0 network-copyleft license is the dominant constraint: copying, importing, or bundling any T3MP3ST source makes the combined work AGPL. Value is (1) re-implementing several genuinely good safety/orchestration patterns cleanly, and (2) optionally running it as an AGPL-isolated external service for recon/whitebox findings. Full autonomous kill-chain exploitation is out of scope for an engineering-intelligence platform.

> Authorization note: this is offensive security tooling. It runs real TCP scans, HTTP requests, and XSS/SQLi probes. Any use must be strictly scoped to systems the operator owns or is explicitly authorized to test. Mis-targeting = a real unauthorized attack.

## Repo facts

- URL: https://github.com/elder-plinius/T3MP3ST
- Language: TypeScript (Node 18+) · License: **AGPL-3.0-or-later** · Stars: ~4,097 · Last push: 2026-07-09 (very active)
- Shape: standalone application (not a library) with 4 interfaces — CLI, HTTP REST API (Express :3333), MCP server (stdio, one live tool `security_recon`), and a web UI. 8 "operator" agents run ReAct loops; a MissionControl lifecycle + RoE/approval gates wrap them.

## AOS engines touched

- Engineering Evaluation Standard (overlap: low; additive — a security sub-score from recon/whitebox)
- Council / multi-agent orchestration (overlap: high but incompatible — parallel architecture, not mergeable)
- Build / Validation gates (out of scope — offensive kill-chain is a different domain)

## Overlap vs additive

- Reject (code): AGPL forbids copying any source into AOS. Multi-agent orchestration, LLM provider management, mission lifecycle are also redundant with AOS's Council.
- Out of scope: full kill-chain exploitation, persistence, lateral movement, C2 — AOS is an engineering-intelligence platform, not an offensive platform.
- Additive (narrow): recon engine + white-box CVE analysis as an external, AGPL-isolated security sub-score feeding the Engineering Evaluation Standard.
- Borrow (design only, re-implement clean — zero license risk):
  1. **Risk-tiered tool catalog** (`src/arsenal/catalog.ts`): `local_read / passive / active / intrusive / credential / dangerous` + execution modes. Directly applicable to AOS's own tool-execution safety model.
  2. **Fail-safe human-veto approval gate** (`src/arsenal/approval.ts`): gated tools deny by default in headless runs; approve-once-per-session. Highly relevant given AOS's autonomous agents.
  3. **Master-builder/worker LLM decomposition** (`src/orchestration/orchestrator.ts`): keeps sensitive objectives out of a restricted worker model.
  4. **Egress scope containment at the tool layer** (`src/mcp-server.ts`: target regex + scope check before subprocess).
  5. **Reproducible-benchmark discipline** (`scripts/verify-claims.mjs`): committed ground-truth oracles + re-run scripts for every EES claim.

## Risks

- **AGPL contamination (critical):** any source import propagates AGPL to the combined work. No commercial/dual license exists. Only process-isolation (external service) or clean re-implementation are safe.
- **Autonomous offensive mis-targeting (high):** a target-selection bug becomes a real unauthorized attack. Requires container + outbound CIDR allow-list, never production hostnames, every call audited.
- **Dual-use blast radius (medium):** co-locating attack tooling with the AOS control plane raises risk if AOS is compromised. Separate container, least-privilege, separate creds.
- **Single maintainer, no deprecation governance (medium):** "Pliny Specials" tools were retired with no window. Version-pin the container image if used via API.
- **Benchmarks don't transfer to local models (low):** 90.1% XBEN was gpt-5.5; local Ollama will do far worse. Conflicts with local-first if strong results are needed.
- Maturity: the 8-operator exploitation swarm is unbenchmarked ("0 executed exploits in full-chain runs" per the whitepaper); recon/whitebox are the proven parts.

## Evidence

- [[../../../docs/repo-research/T3MP3ST|Full teardown]] — license analysis, architecture, verified capabilities, 4 integration options, risk table, borrow-pattern table
- `LICENSE` (AGPL-3.0) + `THIRD-PARTY.md` ("src/, scripts/ is AGPL-3.0-licensed") + `package.json` (`"license": "AGPL-3.0-or-later"`)
- `WHITEPAPER.md` ("0 executed exploits in full-chain runs"); XBEN 90.1% pass@1 (single-agent, gpt-5.5)

## Linked Decisions / Projects

- Plane AOS-63 — "Evaluate: T3MP3ST" (Done) — in the External Repo Evaluation & Adoption Pipeline module
- No borrow item created — pattern borrows and the external-service recon option are candidates pending operator greenlight (each needs a scope/authorization + AGPL-isolation decision)
