# notebooklm-py

## Aliases

- teng-lin/notebooklm-py
- unofficial NotebookLM Python API
- NotebookLM SDK / agentic skill

## Status

evaluated

## Verdict

reject (for integration) / partial-borrow (patterns only) — clean MIT license, but the capability is a **reverse-engineered client for Google NotebookLM's undocumented internal `batchexecute` RPC**. It fails AOS on privacy, verification, and reliability grounds simultaneously. Do not build an AOS pipeline on it. A few engineering-hygiene patterns are worth reading as reference; nothing greenlit.

> Not a license problem (MIT is fine) — a dependency-on-an-unofficial-cloud-service problem. Every reason to reject is about fragility, data egress, and non-determinism, not copyright.

## Repo facts

- URL: https://github.com/teng-lin/notebooklm-py
- Language: Python · License: MIT · Stars: ~17,474 · Last push: 2026-07-09 (very active; wire-shape breakage fix landed the same day)
- Shape: reverse-engineered HTTP client (not browser automation, not an official API). Every op is a POST to `/_/LabsTailwindUi/data/batchexecute` with an obfuscated 6-char method ID (35+ methods, captured from DevTools). Exposes a Python SDK, a CLI, and a `SKILL.md` agentic skill.

## AOS engines touched

- Research Engine (overlap: high — but conflicting, not additive; see below)
- Knowledge Vault (overlap: low; would require egressing vault content to Google)
- Report Generator (audio/podcast overview — tangential)

## Overlap vs additive

- Reject: grounded synthesis is NOT additive to the Research Engine. AOS needs a verifiable, local evidence chain; NotebookLM returns non-deterministic Gemini synthesis with approximate citations ("often a snippet or section header, not the full quoted passage" — its own SKILL.md). AOS already has **Qdrant + Ollama** to do local source-grounded retrieval with real citations and full control — this would duplicate that while adding egress risk.
- Out of scope: building any automated AOS pipeline on an undocumented API that breaks without warning.
- Borrow (design/engineering reference only, re-implement — not greenlit):
  1. VCR.py cassette testing pattern for HTTP adapters
  2. Per-file coverage floors in `pyproject.toml`
  3. Nightly RPC-health workflow that auto-opens issues on upstream drift (`rpc-health.yml`)
  4. Atomic `0600` credential writes for secret handling

## Risks

- **Unofficial-API fragility (critical):** 35+ obfuscated method IDs can rotate silently; the client breaks immediately with no deprecation window. Confirmed active breakage in commits as recent as the analysis day.
- **Privacy / data egress (critical):** using it sends AOS research sources / vault content / queries to Google's cloud. No self-hosted equivalent. Direct conflict with local-first + privacy-first.
- **Auth is infostealer-grade + ToS/account-ban (high):** the headless "master token" path impersonates a Chromecast Android device to mint a durable full-account token; the library's own docstring says use a dedicated/throwaway account only. Automated use of undocumented internal APIs violates Google ToS and risks account suspension with no graceful degradation.
- **Non-determinism (high):** Gemini synthesis returned as "evidence" cannot satisfy "verification preferred over inference."
- MIT license — clean; not the issue.

## Evidence

- [[../../../docs/repo-research/notebooklm-py|Full teardown]] — RPC protocol, auth paths, capability list, integration options, risk table
- `src/notebooklm/rpc/types.py` (batchexecute method IDs), `src/notebooklm/_auth/master_token.py` ("infostealer-grade" docstring), `SKILL.md` (approximate citations), `.github/workflows/rpc-health.yml` (drift auto-issues)

## Linked Decisions / Projects

- Plane AOS-65 — "Evaluate: notebooklm-py" (Done) — in the External Repo Evaluation & Adoption Pipeline module
- No borrow item created — rejected for integration; the engineering-hygiene patterns are reference-only candidates, not commitments
