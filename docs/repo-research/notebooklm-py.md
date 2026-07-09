# Repo Research: teng-lin/notebooklm-py

**Analyzed:** 2026-07-09
**Stack:** Python 3.10-3.14, httpx, click, rich, Playwright (optional), fastmcp (optional), FastAPI (optional)
**Activity:** Multiple commits per day; issue #1854 merged 2026-07-09; daily automated RPC health check; single maintainer (Teng Lin) with Claude Code co-authorship on most recent PRs
**License:** MIT (clean, legally adoptable)
**Version:** 0.8.0a3 (pre-release; 0.x semantics, minor releases may break APIs)
**Stars:** ~17,474

---

## Executive Summary (Integration Fit Verdict)

**Verdict: REJECT for direct integration; MONITOR for pattern borrowing.**

The library is technically impressive and actively maintained, but three structural facts make it incompatible with AOS's core principles:

1. **Unofficial reverse-engineered API.** Every call goes to Google's undocumented `batchexecute` RPC protocol with obfuscated 6-character method IDs (`wXbhsf`, `CCqFvf`, etc.). Google can silently rotate any ID or change the wire format at any time, breaking the library without notice. The maintainer runs a nightly automated health check specifically because these breaks happen.

2. **Hard data-egress conflict.** Using this tool sends AOS research sources to Google's cloud. AOS is local-first, privacy-first, and "research before implementation, evidence over opinion." Routing AOS's Knowledge Vault or Research Engine output through a third-party cloud LLM for synthesis violates both the privacy posture and the evidence-chain integrity: NotebookLM's output is non-deterministic Gemini synthesis, not a verifiable citation chain.

3. **Account-ban risk and Google ToS.** The auth mechanism impersonates a web browser session using cookies and CSRF tokens from a Playwright-captured browser session. The master-token path goes deeper: it exchanges an OAuth token via the Chromecast Android app credentials (`com.google.android.apps.chromecast.app`), impersonating an Android device to mint web cookies. The library itself warns this credential is "infostealer-grade" and recommends a throwaway account. Automated use at scale risks account suspension.

These are not incidental concerns. They are structural properties of the upstream service. No amount of wrapper engineering resolves them.

---

## Verdict

`notebooklm-py` is a well-engineered, actively maintained Python wrapper around Google NotebookLM's undocumented internal RPC API. It is genuinely capable: grounded multi-source Q&A with citations, audio/podcast/video generation, bulk export of structured artifacts, and an MCP server for agent integration. For personal research workflows and prototyping it is useful. For AOS integration it conflicts with local-first, privacy-first, and evidence-chain principles at the foundational level. The code quality and patterns (async layered client, VCR-backed integration tests, strict schema validation, RPC override env vars) are worth studying as engineering references.

---

## Architecture

### What It Actually Is

This is a **reverse-engineered client for Google's undocumented `batchexecute` RPC protocol**, confirmed by reading the source. It is not a browser automation wrapper (Playwright is used only for auth cookie capture, not for driving the UI). It is not an official Google API. It is a carefully reverse-engineered HTTP client that speaks Google's internal RPC wire format.

The protocol (grounded in `src/notebooklm/rpc/types.py` and `docs/rpc-development.md`):
- Endpoint: `https://notebooklm.google.com/_/LabsTailwindUi/data/batchexecute`
- Each operation is a POST with a `f.req` URL-encoded JSON body in the form `[[[rpc_id, json_params, null, "generic"]]]`
- Responses have a `)]}'\n` anti-XSSI prefix, followed by chunked JSON keyed with `wrb.fr` envelopes
- RPC IDs are 6-character obfuscated strings: `wXbhsf` (LIST_NOTEBOOKS), `CCqFvf` (CREATE_NOTEBOOK), `R7cb6c` (CREATE_ARTIFACT), `QA9ei` (START_DEEP_RESEARCH), etc. (35+ methods in `src/notebooklm/rpc/types.py`)
- Chat/query uses a separate streaming endpoint: `/_/LabsTailwindUi/data/google.internal.labs.tailwind.orchestration.v1.LabsTailwindOrchestrationService/GenerateFreeFormStreamed`

### Component Map

```
Entry Points
  notebooklm (CLI)          src/notebooklm/notebooklm_cli.py + src/notebooklm/cli/
  NotebookLMClient (Python) src/notebooklm/client.py
  MCP Server                src/notebooklm/mcp/
  REST Server (exp.)        src/notebooklm/server/

Client Layer
  NotebookLMClient          Composed facade: .notebooks, .sources, .artifacts,
                            .chat, .research, .notes, .labels, .mind_maps, .settings, .sharing
  _client_assembly.py       Constructor + lifecycle
  _client_composed.py       Namespace assembly
  _client_metrics.py        Telemetry and RPC timing

Business Logic (one module per domain)
  _notebooks.py             CRUD + metadata
  _sources.py               Add/delete/wait/fulltext (URL, file, YouTube, Drive)
  _artifacts.py             Generate, poll, download all artifact types
  _research.py              Fast/deep web+Drive research agents
  _note_service.py          Notes + mind-map note-backed kind
  _labels.py                AI topic labels
  _sharing.py               Public/private sharing management
  _mind_maps_api.py         Interactive (Veo-style) mind map

RPC Layer
  _rpc_executor.py          HTTP dispatch, auth refresh, retry, idempotency
  rpc/types.py              RPCMethod enum + ArtifactTypeCode + all status enums
  rpc/encoder.py            f.req payload builder
  rpc/decoder.py            Response stripper and wrb.fr chunk parser

Auth Layer
  _auth/browser_capture.py  Playwright-based interactive login (cookie capture)
  _auth/cookies.py          Cookie loading, Playwright storage_state parsing
  _auth/extraction.py       WIZ_global_data CSRF/session-ID regex extraction
  _auth/keepalive.py        RotateCookies POST keepalive (15-20min cadence)
  _auth/master_token.py     Headless: Android OAuth -> uberauth -> MergeSession
  _auth/refresh.py          Server-side SIDTS refresh, coalesced refresh logic
  _auth/psidts_recovery.py  Inline __Secure-1PSIDTS recovery from SID+APISID

Adapters
  mcp/                      fastmcp-based MCP server (stdio + HTTP remote)
  server/                   FastAPI single-tenant REST server (experimental)

Infrastructure
  _idempotency.py           Request dedup for retried mutations
  _atomic_io.py             File writes with locking
  _backoff.py               Exponential backoff
  _deadline.py              Timeout/deadline propagation
  _logging.py               Structured logging + correlation IDs
```

---

## Auth Mechanism (Grounded in Source)

There are three auth paths. All require a real Google account. None use an official Google API.

### Path 1: Interactive Playwright Login (primary, `notebooklm login`)

Playwright launches a Chromium browser, the user signs in to Google normally, and the resulting browser storage state (cookies) is saved to `~/.notebooklm/profiles/<profile>/storage_state.json` at mode `0600`. On subsequent requests, the client:
1. Loads cookies from `storage_state.json`
2. GETs `https://notebooklm.google.com/` and parses the embedded `WIZ_global_data` JavaScript object for two tokens: `SNlM0e` (CSRF, required as the `at` parameter on every batchexecute POST) and `FdrFJe` (session ID). See `src/notebooklm/_auth/extraction.py:extract_csrf_from_html`.
3. Fires a periodic `RotateCookies` POST to `KEEPALIVE_ROTATE_URL` to refresh `__Secure-1PSIDTS`. See `src/notebooklm/_auth/keepalive.py`.

### Path 2: Browser Cookie Import (`--browser-cookies chrome`)

Uses `rookiepy` (optional extra, broken on Python 3.13+) to extract cookies from an already-signed-in Chrome/Firefox profile. Converts them to Playwright storage_state format.

### Path 3: Master Token / Headless (`--master-token`, requires `[headless]` extra)

The most fragile and highest-risk path. Documented in `src/notebooklm/_auth/master_token.py`:

```
oauth_token (single-use, from one EmbeddedSetup browser sign-in)
  --gpsoauth.exchange_token-->  aas_et/ master token   (durable, saved 0600)
  --gpsoauth.perform_oauth-->   ya29 OAuthLogin bearer  (via com.google.android.apps.chromecast.app)
  --OAuthLogin?issueuberauth=1-->  uberauth token
  --MergeSession-->              SID/SAPISID/__Secure-1PSID... cookie jar
```

The `_MASTER_APP = "com.google.android.apps.chromecast.app"` constant reveals that this path impersonates a Google Chromecast Android device to obtain a `ya29` bearer token capable of issuing uberauth. The library's own docstring warns: "SECURITY: the master token is full-account, durable, infostealer-grade — use a dedicated/throwaway account only."

**Fragility summary:** Any Google-side change to the `WIZ_global_data` CSRF field names, the batchexecute response format, cookie names, or the Chromecast OAuth endpoint breaks one or more paths immediately. The nightly `rpc-health.yml` workflow exists precisely because these breaks happen regularly.

---

## File Inventory

Significant files with one-line annotations:

```
README.md                           Full capability survey and use-case recipes
SKILL.md                            39KB agentic skill for Claude Code / Codex (autonomy rules, all commands)
AGENTS.md                           Codex-specific agent guidance
SECURITY.md                         Credential storage, security policy, threat model
CHANGELOG.md                        Version history (183KB+ - very active)
pyproject.toml                      Deps, extras, coverage floors, mypy config
docs/architecture.md                123KB architectural overview
docs/auth-cookie-lifecycle.md       52KB deep dive on cookie lifecycle
docs/rpc-development.md             Protocol capture workflow, adding new RPC methods
docs/rpc-reference.md               94KB - all RPC payload structures
docs/stability.md                   Versioning policy, what breaks, self-recovery
docs/mcp-guide.md                   MCP server setup + remote connector (Tailscale/Cloudflare)
src/notebooklm/rpc/types.py         The RPCMethod enum: 35+ obfuscated method IDs with comments
src/notebooklm/_auth/master_token.py  Android-impersonation headless auth path
src/notebooklm/_auth/extraction.py  WIZ_global_data regex extractor (CSRF, session)
src/notebooklm/_auth/keepalive.py   RotateCookies keepalive loop
src/notebooklm/_rpc_executor.py     26KB - HTTP dispatch, auth retry, idempotency
src/notebooklm/client.py            46KB - top-level NotebookLMClient with all namespaces
src/notebooklm/_artifacts.py        39KB - all artifact generation + download logic
src/notebooklm/_notebooks.py        40KB - notebook CRUD
src/notebooklm/_sources.py          38KB - source add/delete/fulltext
src/notebooklm/_research.py         43KB - web/Drive research agents
src/notebooklm/exceptions.py        56KB - full exception hierarchy (RPCError, AuthError, etc.)
src/notebooklm/mcp/server.py        fastmcp server registration
src/notebooklm/mcp/tools/           MCP tool handlers (one per operation family)
tests/unit/                         Unit tests (90% coverage floor enforced)
tests/integration/                  VCR.py cassette-backed integration tests
tests/e2e/                          Live authenticated E2E tests (skipped by default)
tests/_guardrails/                  Public surface contract tests, CLI boundary enforcement
```

---

## Key Capabilities

**Grounded, cited Q&A:** `client.chat.ask(notebook_id, "question")` returns an `AskResult` with `.answer` (string with `[1]` citation markers) and `.references` (list of `ChatReference` with `.source_id` and `.cited_text`). Source-grounded synthesis is the core differentiator.

**Full artifact generation pipeline:** Audio (4 formats, 3 lengths, 50+ languages), Video (4 formats, 8 visual styles, Veo 3 cinematic), Slide Deck (PDF/PPTX), Infographic (PNG), Quiz, Flashcards, Report (briefing-doc/study-guide/blog-post/custom), Data Table (CSV), Mind Map (interactive JSON or note-backed JSON). All downloadable locally.

**Web and Drive research agents:** `source add-research "query" --mode deep` triggers Google's "DiscoverSources" pipeline, which finds and imports 20+ web sources automatically. Fast mode takes seconds; deep mode takes 15-30 minutes.

**Source breadth:** URLs, YouTube, PDFs, text, Markdown, Word/EPUB, Google Drive (Docs/Sheets/Slides), audio/video/image files, pasted text. Up to 600 sources per notebook (Ultra tier).

**Batch/export extras (beyond web UI):** Batch artifact download (`--all`), quiz/flashcard JSON/Markdown/HTML export, mind map JSON export, slide deck as editable PPTX, slide revision via natural language, source fulltext retrieval, programmatic sharing management.

**MCP server:** Can serve as an MCP tool to Claude Desktop/Code or as a self-hosted remote connector behind Tailscale or Cloudflare, reachable from the claude.ai mobile app.

**Multi-account profiles:** Named profiles for CI, parallel agents, or multiple Google accounts. `NOTEBOOKLM_AUTH_JSON` env var for secrets injection.

---

## Notable Patterns (Worth Borrowing)

| Pattern | Where | Why It Is Useful |
|---------|-------|-----------------|
| Nightly automated RPC health check that opens a GitHub issue on breakage | `docs/stability.md` + `.github/workflows/rpc-health.yml` (referenced) | External-API clients always break silently; proactive detection with labeled issues is a disciplined approach AOS could use for any cloud-API dependency |
| `NOTEBOOKLM_RPC_OVERRIDES` env var for zero-downtime method-ID hotfixes | `docs/stability.md#self-recovery`, `src/notebooklm/rpc/overrides.py` | Override a broken API endpoint without a code change or redeploy while a patch release is cut |
| VCR.py cassette-backed integration tests for HTTP APIs | `tests/vcr_config.py`, `tests/integration/` | Lets integration tests run in CI without real credentials; cassettes are checked in and re-recorded on breakage. AOS research adapters should follow this pattern |
| Strict schema validation with `UnknownRPCMethodError` on drift (no silent None returns) | `docs/stability.md#strict-decoding`, `src/notebooklm/rpc/decoder.py` | Fails fast and loudly when upstream shape changes; compatible with AOS "verification over inference" principle |
| Per-file coverage floors table in `pyproject.toml` | `pyproject.toml:[tool.notebooklm.per_file_coverage_floors]` | Enforces minimum coverage on historically weak files without blocking all other files. Simple to adopt |
| Coalesced async refresh (multiple concurrent requests share one refresh) | `src/notebooklm/_auth/refresh.py:_coalesced_run_refresh_cmd` | Prevents thundering-herd auth refresh when many concurrent requests hit an expired token simultaneously |
| Atomic file writes with `0600` permissions for credential files | `src/notebooklm/_auth/master_token.py:write_master_token`, `persist_minted_jar` | Write to `.{name}.tmp` at the correct permissions first, then `os.replace()`. Avoids partial writes and permission widening |
| `NOTEBOOKLM_DEBUG_RPC=1` env var that logs RPC ID round-trips | `docs/rpc-development.md#debug-mode` | Operator-facing debug mode without changing code. AOS engine adapters should expose similar debug env vars |
| Public-surface contract tests enforced by a `_guardrails/` test directory | `tests/_guardrails/` | Snapshot-tests the exact `__all__` export list and enforces that CLI modules don't import private submodules. Catches accidental API surface changes |

---

## Integration Fit with ArchetypeOS

### Research Engine

AOS's Research Engine gathers evidence from docs, reference implementations, benchmarks, and community sources, recording ResearchNotes. NotebookLM's grounded Q&A does something superficially similar: loads sources, uses Gemini to synthesize answers with citations.

**Assessment: Not additive as designed. Conflicted on privacy.**

The Research Engine needs to produce verifiable, local evidence records that can be traced to source material. NotebookLM's synthesis is non-deterministic Gemini output, not a retrievable citation chain. `cited_text` is described in SKILL.md as "often a snippet or section header, not the full quoted passage." The `start_char`/`end_char` positions reference NotebookLM's internal chunked index, not raw source offsets. You cannot independently verify a NotebookLM answer against source material without re-querying NotebookLM - which means all sources sent to it have left AOS's trust boundary.

More fundamentally: using NotebookLM as a Research Engine component would require uploading AOS's knowledge vault contents to Google's cloud, producing Gemini synthesis as AOS "evidence." This violates "evidence over opinion" (non-deterministic LLM synthesis is not evidence), "verification preferred over inference" (cannot verify without re-querying the cloud), and "local-first preferred" (all data leaves the perimeter).

### Knowledge Vault

The Knowledge Vault is AOS's internal store of human-readable research and decision notes. NotebookLM's "note" features (`note create`, `ask --save-as-note`, `history --save`) are cloud-side notebook notes, not local files. Using NotebookLM as a cloud-side cache for AOS's vault ("persistent cross-session memory" pattern from README) means all vault content is replicated to Google.

**Assessment: Out of scope. Privacy conflict is categorical.**

### Report Generator

AOS's Report Generator produces operator-facing briefings. NotebookLM can generate briefing-doc reports, audio overviews, and study guides from a source set. These are appealing capabilities on their face.

**Assessment: Partially interesting, but data-egress problem remains.**

If AOS were willing to accept cloud synthesis for non-sensitive operator briefings, the `generate audio --format brief` + `download audio` pipeline could produce MP3 briefings. `generate report --format briefing-doc` produces Markdown reports. However: (a) AOS cannot control what Gemini says, (b) the output is non-deterministic, (c) sources must be uploaded to Google, (d) the API is fragile. There is no local equivalent available through this library - this capability is inherently cloud-bound.

### Council / Decision Intelligence

Council uses grounded Q&A over evidence sets to inform architectural decisions. NotebookLM's `ask` with `--json` returns cited answers. For a set of architecture documents loaded as sources, this could surface relevant passages with citation numbers.

**Assessment: Conceptually aligned, practically conflicted.**

The capability maps well to Council's needs. But the same privacy/integrity issues apply: decision-support evidence that depends on sending AOS's architecture docs to Google and receiving non-deterministic Gemini synthesis cannot satisfy "evidence over opinion" or "human approval for destructive actions" (the evidence supporting those actions is unverifiable).

---

## Integration Options

### Option A: Vendor the MIT SDK as an Optional AOS Research Adapter (privacy-acknowledged, out-of-scope by default)

Wrap `NotebookLMClient` as an optional `ExternalSynthesisAdapter` behind an explicit data-egress consent flag. Only activated when the operator explicitly opts in for non-sensitive materials.

- **Effort:** Medium (2-3 days to write adapter + tests)
- **Risk:** High (auth fragility, ToS, API breakage)
- **Coupling:** Tight to Google cloud
- **Privacy:** Requires explicit operator opt-in; not local-first
- **AOS gain:** Grounded audio briefings, multi-format artifact generation for non-sensitive outputs
- **Verdict:** Technically feasible but requires accepting the risks. Not recommended for core evidence workflows.

### Option B: Use Only the CLI / Skill as an External Tool (operator-driven, manual)

Install `notebooklm` as a CLI tool available to AOS agents. Agents invoke it via subprocess for specific one-off tasks (e.g., "generate a podcast from this set of public URLs"). Data egress is operator-initiated and intentional, not automated.

- **Effort:** Low (document the tool, add to agent skill catalog)
- **Risk:** Medium (still requires Google account, ToS concerns, but usage is deliberate)
- **Coupling:** Loose (external process invocation)
- **Privacy:** Operator-controlled; no automated data egress
- **AOS gain:** Occasional audio briefing or study guide generation when operator chooses to use it
- **Verdict:** Acceptable as an optional operator tool, not as an automated AOS subsystem component.

### Option C: Borrow the Source-Grounding and Citation Pattern as an Architecture Reference

Study how NotebookLM's grounded Q&A (source upload -> indexed retrieval -> cited synthesis -> structured references) is exposed programmatically. Use this as a design reference for AOS's own local grounded Q&A (e.g., using Qdrant + local Ollama, which already exists in Tim's stack).

- **Effort:** None (read-only)
- **Risk:** None
- **Coupling:** None
- **Privacy:** Full local control
- **AOS gain:** Design patterns: structured citation response shapes (`AskResult.references`, `ChatReference.cited_text`, `find_citation_context()`), the "source-as-indexed-unit" model, the polling pattern for async artifact generation
- **Verdict:** Recommended. The patterns are sound and local implementations can replicate the capability.

### Option D: Reject Integration Entirely

Do not integrate or reference `notebooklm-py` in AOS. Monitor it for evidence of Google publishing an official API.

- **Effort:** Zero
- **Risk:** Zero
- **AOS gain:** None immediate; avoids coupling to fragile unofficial API
- **Verdict:** Acceptable default position if Option C is not acted on.

---

## Risks and Rough Edges

### Risk 1: Unofficial Reverse-Engineered API (Highest)

Every RPC method ID in `src/notebooklm/rpc/types.py` is an obfuscated 6-character string reverse-engineered from network traffic. The maintainer acknowledges: "Google can change internal endpoints anytime." The nightly `rpc-health.yml` workflow exists to detect silent ID rotations, which happen regularly enough to warrant automation. Recent commit #1854 (2026-07-09) fixes a wire-shape change where Drive-hosted PDFs were mislabeled due to a `type_code 14` overload in the response format. This is not theoretical fragility - it is active maintenance burden.

If any of the 35+ RPC IDs rotates during AOS operation, all calls to that method fail with `UnknownRPCMethodError` until the library is updated. There is no fallback, no deprecation window, and no Google-side notification.

### Risk 2: Privacy and Data Egress (Highest)

Using this library sends sources to Google's NotebookLM service. This is processed by Gemini (Google's LLM). There is no on-premise or self-hosted equivalent. For AOS, which handles architecture docs, research sources, decision notes, and potentially internal code, this means:

- AOS's research evidence leaves the trust boundary and enters Google's data pipeline
- Output is non-deterministic Gemini synthesis; different runs produce different answers
- Citations are approximate (snippets/headers, not full-text positions)
- "Verification preferred over inference" cannot be satisfied: verification requires re-querying Google

This is not a configuration problem. NotebookLM is Google's cloud-only service.

### Risk 3: Account-Ban Risk and Terms of Service

The library uses undocumented internal APIs. Google's ToS prohibit automated access to services unless explicitly permitted. The master-token path impersonates an Android device (Chromecast app). Heavy automated use risks account suspension. The library's own security doc notes: "Account restrictions are possible for unusual usage patterns."

If AOS integrated this library and the Google account were suspended, all AOS workflows depending on it would fail immediately with no graceful degradation path.

### Risk 4: Single Maintainer / Bus Factor

All commits are from `teng-lin` (with Claude Code co-authorship on recent PRs). The project is in pre-release (0.8.0a3). While the codebase is high quality and well-tested (90% coverage floor), a single maintainer means response time to Google API breaks depends on one person's availability. The nightly health check auto-opens issues, but fixes require maintainer action.

### Risk 5: Auth Secret Handling

`storage_state.json` contains full Google session cookies. SECURITY.md correctly warns these are "full-account, durable" and "anyone with access to this file can impersonate your Google account." In a multi-agent AOS deployment, each agent would need its own profile/home directory to avoid context collisions (documented in SKILL.md's parallel-agent section). Credential rotation requires periodic browser re-authentication.

The `NOTEBOOKLM_AUTH_JSON` env var path is safer for CI (keeps credentials in memory), but the underlying Google session is still a full-account credential.

### Risk 6: Non-Deterministic Output Conflicts with "Verification Over Inference"

NotebookLM synthesizes answers using Gemini. The same question on the same source set on different days can produce different answers. AOS's governing principle "verification preferred over inference" means AOS should be able to check any claim against its source. NotebookLM's cited_text is "often a snippet or section header" (SKILL.md) and positions reference NotebookLM's internal chunked index. A downstream AOS agent cannot independently verify a NotebookLM answer without re-querying the same cloud service.

### Minor Rough Edges

- `QuizQuantity.MORE` is an alias for `STANDARD` (`rpc/types.py`): the API does not actually support "more" quantity, so the flag silently does nothing.
- Rate limits on audio, video, quiz, flashcard, infographic generation are significant and non-deterministic (SKILL.md: "These may fail due to Google's rate limits").
- `fastmcp` pinned at `==3.4.2` because `3.4.3` broke the OAuth discovery route (`pyproject.toml`). Pinned exact-version dependencies in optional extras are a maintenance risk.
- `rookiepy` (cookie import) does not install on Python 3.13+ due to build issues; excluded from the `all` extra.
- Python API is 0.x with no 1.0 stability guarantee; minor releases may break APIs.

---

## Recommendations

**Summary:** Do not integrate `notebooklm-py` as an AOS subsystem component. The privacy conflict is categorical (data leaves the trust boundary), the API is fragile by design (unofficial, breaks on Google changes), and the output is non-deterministic (conflicts with evidence standards). The code contains several patterns worth borrowing for AOS's own adapters and test infrastructure.

**Evidence:** All claims above are grounded in: `src/notebooklm/rpc/types.py` (RPC method IDs confirmed as obfuscated strings); `src/notebooklm/_auth/master_token.py` (Android impersonation confirmed, "infostealer-grade" warning in source); `src/notebooklm/_auth/extraction.py` (CSRF extraction via WIZ_global_data regex); SKILL.md (cited_text described as "often a snippet or section header"); `docs/stability.md` (acknowledges "No stability guarantees from Google"); SECURITY.md (acknowledges "Account restrictions are possible for unusual usage patterns"); commit #1854 (2026-07-09) (demonstrates active wire-shape breaks requiring fixes).

**Recommendation:** REJECT for integration. PARTIAL-BORROW for patterns.

**Alternatives Considered:**
- Local RAG with Qdrant + Ollama (already in Tim's stack): full local control, deterministic retrieval, no data egress. AOS's existing stack can replicate the grounded-Q&A capability without cloud dependency.
- Perplexity API or similar for web research: official API, documented rate limits, no account-ban risk. Still cloud (data egress concern remains), but significantly more stable.
- Self-hosted document Q&A (LlamaIndex, Haystack, or RAG pipeline): fully local, verifiable citations, deterministic retrieval. Consistent with AOS local-first principle.

**Pros of accepting:** Multi-format artifact generation (audio briefings, quizzes, mind maps) is genuinely hard to replicate locally. The web research agent capability (find + import 20+ sources on a topic) saves meaningful work. Zero-token offload pattern is architecturally interesting.

**Cons of accepting:** Privacy violation is categorical. API fragility requires active maintenance. Non-deterministic output conflicts with evidence standards. Account-ban risk creates operational fragility. Single-maintainer bus factor.

**Risk:** High for any automated integration. Low if used only as an occasional manual operator tool (Option B).

**Effort:** Option B (CLI tool only): 1 day. Option C (borrow patterns): 0 days. Option A (full adapter): 2-3 days plus ongoing maintenance.

**Dependencies:** Option B requires a dedicated Google account and periodic credential refresh.

**Acceptance Criteria (if Option B were adopted):**
- Dedicated throwaway Google account with no link to AOS infrastructure credentials
- Explicit data-egress consent documented in AOS configuration
- Circuit-breaker: AOS does not use the tool for any sensitive research materials (internal architecture docs, decision notes, proprietary code)
- Operator-initiated only: no automated AOS pipeline invokes the tool without explicit operator approval

**Next Steps:**
1. If local grounded Q&A is needed, evaluate AOS's existing Qdrant + Ollama stack for source-grounded retrieval with citations. This is the local-first path.
2. If audio briefing generation is a priority, note this as a future feature and monitor for Google releasing an official NotebookLM API.
3. Borrow the VCR.py cassette testing pattern and the per-file coverage floor table for AOS's own research adapter tests.
4. Borrow the nightly RPC health check pattern for any AOS component that calls an external API.
5. Revisit if Google publishes an official NotebookLM API (would eliminate the ToS and fragility concerns, though privacy concerns would remain).
