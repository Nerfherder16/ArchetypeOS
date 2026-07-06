# AOS-LLM-ISOLATION-001 — Isolate the ClaudeCodeProvider from ambient project context (LES-021)

## Status

Done (merged verification pending)

## Origin

Operator direction: "lets pick up your recommendations" → LES-021 (provider isolation) as the tactical prerequisite for RFC-0008. LES-021 was surfaced by the `free-llm-api-resources` ingestion reality test: the real `claude_code` provider's `technology_fitness_judge`, given only the target repo's fingerprint, described **ArchetypeOS itself** (FastAPI/apps/worker/psycopg) because `claude -p` ran in the repo's cwd and inherited `CLAUDE.md` + filesystem — violating the council's "reason only from supplied evidence" contract.

## Change

`packages/aos_core/aos_core/llm/__init__.py` — `ClaudeCodeProvider`:
- `generate` now runs the `claude -p` subprocess in a **fresh empty `tempfile.TemporaryDirectory`** (`cwd=`), so there is no project `CLAUDE.md` and no repo files in the working tree.
- `_build_argv` appends `--disallowedTools` (Bash/BashOutput/KillShell/Read/Edit/Write/NotebookEdit/Glob/Grep/WebFetch/WebSearch/Task) + `--strict-mcp-config`, denying every state-reading/acting tool and ignoring ambient MCP.
- Net effect: the provider output is a pure function of `system` + `prompt`.

## Verification

- **Live-validated** (authed node): re-ran the free-llm `technology_fitness_judge` prompt through the fixed provider — it now reasons only from the supplied evidence ("a lightweight Python project … using pip") with **zero** ArchetypeOS leakage (no FastAPI/apps-worker/psycopg markers).
- **Hermetic regression**: `apps/api/tests/test_council.py::test_claude_code_provider_mocked` asserts the subprocess `cwd` is set and ≠ `os.getcwd()`, and that `--disallowedTools` (incl. Bash/Read/Write/WebFetch/Task) + `--strict-mcp-config` are in the argv.
- api 132 / worker 7 green; ruff full CI scope + compileall clean. No new deps, no migration, no frontend. `DeterministicProvider` (CI default) unaffected.

## Out-of-Scope

- RFC-0008 (repository content extraction) — this is its prerequisite, built next.
