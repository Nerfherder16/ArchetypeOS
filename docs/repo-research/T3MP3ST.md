# Repo Research: elder-plinius/T3MP3ST

**Analyzed:** 2026-07-09 · **Stack:** TypeScript 5.3 / Node.js 18+ · **License:** AGPL-3.0-or-later · **Stars:** ~4,097 · **Activity:** Multiple PRs merged 2026-07-09 (pushed same day as analysis)

---

## Executive Summary (Read First)

**Fit verdict: REJECT for code integration / MONITOR as external reference.**

The AGPL-3.0 license is the hard blocker. Any AOS component that imports or bundles T3MP3ST source becomes subject to AGPL copyleft, which requires open-sourcing AOS itself or negotiating a commercial license from the maintainer. Running T3MP3ST as a fully isolated, separate network service (no shared code, called only via its HTTP API or CLI) avoids contamination but introduces a different class of risk: an autonomous offensive agent with real exploitation tools operating adjacent to the AOS control plane.

On scope: T3MP3ST fills a narrow security-validation niche that AOS does not yet have. The recon engine and white-box source analysis capabilities are genuinely useful for evaluating systems AOS builds. The autonomous exploitation kill-chain is a distinct, higher-risk domain that is mostly still scaffolding anyway. The decomposition orchestrator pattern (`src/orchestration/orchestrator.ts`) is the single most architecturally interesting piece and is worth studying for ideas, not copying.

**Top-2 integration options:** (1) Borrow the orchestrator pattern as a design reference only, re-implement cleanly in AOS under AOS's own license. (2) Run the stable recon/scan surface as an isolated sidecar service and call it from AOS's Engineering Evaluation Standard via HTTP, never touching its source.

**Top-3 risks:** (1) AGPL contamination if any T3MP3ST code is vendored into AOS. (2) Mis-targeted autonomous offensive action if the agent is mis-configured or miscalled by AOS automation. (3) Dual-use surface: the same tooling that validates security can be turned on unauthorized targets.

---

## 1. License Analysis (Lead Finding)

### What the LICENSE says

The `LICENSE` file is the unmodified GNU Affero General Public License Version 3, 19 November 2007. `package.json` declares `"license": "AGPL-3.0-or-later"` (`package.json`, `"license"` field). `THIRD-PARTY.md` confirms: "T3MP3ST's own source (`src/`, `scripts/`) is AGPL-3.0-licensed."

The key clause that differentiates AGPL from ordinary GPL is AGPL Section 13 (Remote Network Interaction):

> "if you modify the Program, your modified version must prominently offer all users interacting with it remotely through a computer network... an opportunity to receive the Corresponding Source of your version."

### Integration scenarios and their license consequences

**Scenario A: Copy or import any T3MP3ST source into AOS.**
Result: The combined work becomes a derivative of T3MP3ST and the entire combined work must be distributed under AGPL-3.0. If AOS has any proprietary components, or Tim intends to keep AOS source private, this is incompatible. Copying even a single significant function (e.g., the `DecompositionOrchestrator` class, the `ApprovalController` class, the payload databases) triggers this.

**Scenario B: Link to T3MP3ST as an npm dependency.**
Result: Same as Scenario A if the dependency is bundled or tightly coupled. The AGPL "network service" clause applies if T3MP3ST runs as part of a service AOS users interact with remotely. Even if AOS is only used internally by Tim, strong copyleft still propagates to the combined work. If AOS ever becomes a service, the AGPL source-offer obligation activates.

**Scenario C: Run T3MP3ST as a separate, standalone process and call it via its HTTP API or CLI only.**
Result: This is the only license-safe integration path. AGPL copyleft does not cross process boundaries via network calls. AOS would call `POST /api/tools/recon` or `POST /api/mission/start` over localhost/Tailscale, receive JSON results, and pass them to its own evaluation logic. No T3MP3ST source enters the AOS codebase. AOS does not need to be AGPL. This is how tools like Nuclei, Nmap, and Semgrep are safely used in security pipelines today.

**Scenario D: Study the architecture and re-implement equivalent ideas from scratch in AOS.**
Result: Clean. Ideas are not copyrightable. AOS can implement its own decomposition orchestrator, its own approval gate, its own ReAct agent loop, independently. This is the "borrow pattern, not code" option.

**No commercial license is available** (as of analysis date). There is no dual-license or commercial tier mentioned anywhere in the repo. The only path to embed the code into a non-AGPL codebase would be negotiating a separate license directly with elder-plinius, who maintains sole copyright.

**Bottom line on licensing:** Do not copy, import, or bundle any T3MP3ST source into AOS. Run it as an external service (Scenario C) or re-implement ideas independently (Scenario D). Nothing else is license-safe.

---

## 2. File Inventory and Architecture

### Top-level structure

```
T3MP3ST/
  README.md              # Primary overview, benchmarks, quick-start, architecture
  WHITEPAPER.md          # 34KB technical deep-dive, honest about scaffolding vs. live
  FEATURES.md            # 28KB per-feature [x]/[~]/[ ] status table
  SECURITY.md            # Authorized-use policy, vuln reporting, data handling
  THIRD-PARTY.md         # Attribution; confirms bench corpora are NOT distributed
  CONTRIBUTING.md        # Contribution rules
  VISION.md              # Aspirational goals
  package.json           # Manifest, scripts, deps, bin aliases (tempest / t3mp3st)
  LICENSE                # Full AGPL-3.0 text
  index.ts               # Root re-export (delegates to src/)
  src/                   # All TypeScript source
  tools/                 # Docker image (Kali Linux + tools)
  scripts/               # 40+ benchmark and utility scripts (.mjs)
  bench/                 # Benchmark oracles (gitignored corpora, own JSON annotations)
  ctf/                   # CTF practice challenges
  docs/                  # Docs + single-page Web UI (index.html, ~1.5MB)
  examples/              # (dir exists, not deeply read)
  .github/               # CI, issue templates
  .githooks/             # Git hooks
```

### Core source modules (src/)

| Module | Size | Purpose |
|--------|------|---------|
| `src/index.ts` | 55KB | `TempestCommand` central orchestrator, factory functions, exported API |
| `src/server.ts` | 340KB | Express HTTP server, War Room UI server, all REST endpoints, SSE streaming |
| `src/cli.ts` | 20KB | Interactive CLI (commander + inquirer + chalk) |
| `src/mcp-server.ts` | 7.5KB | MCP server exposing `security_recon` (nmap/DNS). Note: size in repo listing says 7.5KB, but WHITEPAPER claims 83KB - likely the WHITEPAPER quoted an older bundled version. Current file is 7.5KB. |
| `src/operators/index.ts` | 37KB | 8 operator archetypes (Recon, Scanner, Exploiter, Infiltrator, Exfiltrator, Ghost, Coordinator, Analyst), state machine, OperatorCell pool |
| `src/arsenal/index.ts` | 131KB | 35 built-in tools (real Node.js implementations); 48 optional adapter tool wrappers |
| `src/arsenal/catalog.ts` | 40KB | Typed catalog of all 83 tools with risk tier, execution mode, families |
| `src/arsenal/approval.ts` | 9KB | Human-veto gate: ApprovalController, fail-safe deny for ungated headless runs |
| `src/arsenal/post-ex.ts` | 13KB | Post-exploitation tools (Metasploit, Hydra - catalog-only gating) |
| `src/orchestration/orchestrator.ts` | 22KB | DecompositionOrchestrator: master-builder/worker multi-LLM whitebox analysis |
| `src/mission/index.ts` | 19KB | MissionControl, TaskQueue, Rules of Engagement, kill chain phases |
| `src/mission/adjudicate.ts` | 32KB | Finding adjudication and validation |
| `src/agent/index.ts` | 21KB | AgentLoop: ReAct tool-calling loop (up to 15 iterations, 50K token budget) |
| `src/agent/local-agents.ts` | 16KB | Local agent bridge (Claude Code, Codex, Hermes) - keyless mode |
| `src/llm/index.ts` | 58KB | LLMBackbone: multi-provider abstraction (OpenRouter, Anthropic, OpenAI, Ollama, Mock) |
| `src/recon/code-ingest.ts` | 32KB | White-box source ingestion, repo analysis |
| `src/recon/whitebox.ts` | 9.8KB | White-box vuln analysis pipeline |
| `src/recon/attack-graph.ts` | 10.6KB | Attack graph construction from findings |
| `src/opsec/index.ts` | 7.6KB | OpsecController: detection events, cooldowns, IOC tracking, jitter |
| `src/stubs/index.ts` | 40KB | Advanced module stubs (SwarmController, CognitionEngine, CloudSecurity, etc.) |
| `src/evidence/` | - | EvidenceVault: findings, credentials, CVSS, artifact storage |
| `src/analysis/` | - | AnalysisEngine: executive summary, technical reports, Markdown export |
| `src/prompts/` | - | System prompts for each of the 8 operator archetypes |
| `src/comms/` | - | CommsChannel: inter-agent messaging (broadcast, direct, team) |
| `src/target/` | - | TargetEnvironment: attack surface model, status transitions |
| `src/types/` | - | Shared TypeScript type definitions |

### tools/Dockerfile

Kali Linux rolling base with: radare2, gdb, binutils, john, hashcat, nmap, nikto, sqlmap, gobuster, ffuf, hydra, whois, dnsutils, openssl, binwalk, yara, z3-solver, sympy, pwntools, fpylll, pycryptodome, pip-audit, semgrep, slither-analyzer, mythril, SageMath (via conda-forge), and the ProjectDiscovery Go suite (httpx, katana, naabu, subfinder, nuclei, dalfox). This is a substantial (~multi-GB) image, not in CI, built on demand.

### Architecture topology (verified from WHITEPAPER + source)

```
TempestCommand (src/index.ts)
  |-- OperatorCell (8 agent archetypes, ReAct loops)
  |-- MissionControl (task queue, kill chain phases, RoE)
  |-- TargetEnvironment (attack surface model)
  |-- EvidenceVault (findings, credentials, artifacts)
  |-- Arsenal (35 built-in + 48 adapter tools, approval gate)
  |-- OpsecController (detection, jitter, cooldowns)
  |-- CommsChannel (inter-agent messaging)
  |-- AnalysisEngine (reports)
  |-- LLMBackbone (OpenRouter / Anthropic / OpenAI / Ollama / Mock)
  |-- DecompositionOrchestrator (whitebox: master-builder + worker LLMs)

Exposed via:
  CLI (src/cli.ts) -- interactive REPL
  HTTP API (src/server.ts, :3333) -- mission control + tools
  MCP Server (src/mcp-server.ts) -- security_recon only
  Web UI (docs/index.html) -- War Room dashboard
```

The orchestration model for white-box analysis is a two-tier LLM split: an unrestricted "master builder" model holds the offensive objective and decomposes it into innocuous analytical sub-queries dispatched to a potentially restricted "worker" model. The worker sees only benign code-analysis questions. Only the master synthesizes the offensive picture. This is documented explicitly in `src/orchestration/orchestrator.ts` lines 1-14:

> "The worker never sees the offensive framing -- only benign code-analysis questions... The orchestrator does all the offensive reasoning. Only the master builder knows the plan."

---

## 3. Capabilities (What It Actually Does)

### Confirmed working (benchmarked)

- **Black-box web recon/exploit (XBEN):** 90.1% pass@1 on XBOW's 104-challenge suite. Driven by a single-agent ReAct loop, not the 8-operator swarm. Tools: nmap, dig, DNS resolution, HTTP fingerprinting, XSS scan, SQLi scan, dir bruteforce, header analysis, tech detection, subdomain enum.
- **CTF solving (Cybench):** 23/40 hint-free, single-run pass@1. Uses the same ReAct loop against sandboxed CTF challenges.
- **White-box CVE hunting:** 8/10 post-cutoff 2026 CVEs identified to exact file/line/CWE on a held-out 10-CVE set across 7 languages. The `DecompositionOrchestrator` is the mechanism.
- **Network recon via MCP:** `security_recon` tool in `src/mcp-server.ts` runs nmap + dig, validates target against strict regex (`/^[A-Za-z0-9._:-]+$/`), uses `execFile` (no shell spawn), returns structured JSON.

### Confirmed scaffolding / unproven (per FEATURES.md and WHITEPAPER)

- **8-operator swarm exploitation:** "0 executed exploits in full-chain runs." The downstream kill-chain phases (Exploiter, Infiltrator, Exfiltrator, Ghost) run the same ReAct loop but end-to-end swarm coordination is unbenchmarked.
- **Cloud (AWS/GCP/Azure) live exploitation:** IaC misconfig detection scaffolded; live-cloud exploitation not benchmarked.
- **Mobile dynamic analysis, binary pwn/ROP, AD/Kerberos:** In development.
- **Advanced modules:** SwarmController, CognitionEngine, PersistenceController, LearningEngine are all stubs in `src/stubs/index.ts`.
- **"Pliny Specials" (LEVIATHAN, SPHINX, GORGON, etc.):** RETIRED as of 2026-06. Explicitly removed from both the MCP server and HTTP API. FEATURES.md section 7 marks them all as "RETIRED." Only `security_recon` survives as a live MCP tool.

### Target classes supported

Web apps, APIs, CTF challenges, OSS source code repos (white-box), robotics/embedded OSS (CVE disclosure pipeline), smart contracts (Slither/Mythril, reproduction only), network infra (recon live, lateral movement experimental).

### LLM providers

OpenRouter (50+ models including Claude Opus/Sonnet, GPT-4o, Grok 4, DeepSeek R1, Gemini), direct Anthropic, OpenAI, Ollama (local), mock (tests). No key required if piping through a locally-connected Claude Code / Codex / Hermes agent.

---

## 4. Dependencies and Runtime

### Node.js requirement

`"engines": { "node": ">=18.0.0" }` (`package.json`). Uses ESM (`"type": "module"`).

### Production dependencies (12 total)

`@modelcontextprotocol/sdk ^1.25.1`, `express ^4.18.2`, `cors ^2.8.5`, `commander ^12.1.0`, `inquirer ^9.2.15`, `chalk ^5.3.0`, `boxen ^7.1.1`, `cli-table3 ^0.6.3`, `conf ^12.0.0`, `eventemitter3 ^5.0.1`, `dotenv ^16.4.5`, `figlet ^1.7.0`, `gradient-string ^2.0.2`, `ora ^8.0.1`, `tsx ^4.7.0`.

No heavy ML dependencies. No database. No Python. All LLM inference is remote API calls.

### Security dependency note

`npm audit` reportedly returns 0 vulnerabilities as of 2026-07-02 (SECURITY.md). The `overrides` in `package.json` pin `qs ^6.15.2`, `hono ^4.12.25`, and `js-yaml ^4.2.0` -- these are explicit security patches for known vulnerabilities in transitive deps.

### External tool requirements (optional)

For full arsenal: nmap, dig, whois, curl, nikto, gobuster, ffuf, nuclei, subfinder, httpx, sqlmap, dalfox, semgrep, gitleaks, trufflehog, trivy, radare2, ghidra, etc. All installed on-demand via `scripts/install-tools.sh` or the Kali Docker image. The system degrades gracefully if tools are missing (tool is cataloged but unavailable).

### Cloud LLM dependency vs. local-first

T3MP3ST is explicitly designed to be keyless when used with a locally-connected agent (Claude Code, Codex, Hermes) or Ollama. `TEMPEST_LOCAL_BASE_URL` and `TEMPEST_LOCAL_MODEL` env vars point it at any OpenAI-compatible local server. This is compatible with AOS's local-first preference.

### Containerization

No `docker-compose.yml` for the main application. The `tools/Dockerfile` is the Kali arsenal image only. T3MP3ST itself runs as a Node.js process or `npm run server`. Containerizing it for AOS integration would require writing a Dockerfile for the Node.js process -- straightforward but not provided.

---

## 5. Integration Fit with ArchetypeOS

### What AOS currently has (relevant to this assessment)

AOS is an Engineering Intelligence Platform with a Research Engine, multi-agent Council, Engineering Evaluation Standard (EES), PR Guardian, and Build/Validation gates. It researches, models, evaluates, recommends, builds, validates, and evolves software systems. It does not currently have an autonomous security validation capability.

### Where T3MP3ST could add value

**Security scoring in the EES:** AOS evaluates repos for production-readiness. T3MP3ST's white-box source analysis (`DecompositionOrchestrator` + `src/recon/code-ingest.ts`) could provide a security sub-score: "run white-box analysis against this repo, report CVE candidates and vulnerability classes." This would feed into AOS's existing evaluation scoring rather than replacing it.

**Validation of systems AOS builds:** When AOS builds or evaluates a system, it could invoke T3MP3ST's recon engine (`POST /api/tools/recon`) against a staging deployment to confirm the system is not obviously exploitable before promoting it.

**CTF-style regression testing:** The CTF solving capability could be adapted to run against AOS-designed test harnesses to validate that security properties hold.

### Where T3MP3ST is out-of-scope or redundant

**Multi-agent orchestration overlap:** AOS has its own Council multi-agent model. T3MP3ST's 8-operator cell is a separate orchestration model designed for offensive security workflows, not engineering evaluation. They are not architecturally compatible -- they would run in parallel, not integrate. There is no meaningful way to merge the two agent topologies.

**Autonomous exploitation is out-of-scope for AOS:** AOS's mandate is engineering intelligence, not autonomous offensive operations. Recon, scanning, and SAST-style analysis (the benchmarked parts of T3MP3ST) are in-scope as validation inputs. Full kill-chain exploitation automation (which T3MP3ST is mostly still scaffolding anyway) is not an AOS concern.

**Swarm architecture:** T3MP3ST's swarm is explicitly unproven. The Council's reasoning model is more mature for AOS's decision-making needs.

### Additive vs. redundant assessment

Additive (narrow, defensible): Recon engine + white-box analysis as an external validation sidecar, results piped into EES security scoring.

Redundant: Multi-agent orchestration, LLM provider management, mission lifecycle management -- AOS has all of this already.

Out-of-scope for AOS: Full kill-chain exploitation, persistence, lateral movement, C2.

---

## 6. Integration Options

### Option 1: External AGPL-isolated service, HTTP API only (Recommended for exploration)

Run T3MP3ST as a Docker container (write a Node.js Dockerfile wrapping `npm run server`). AOS calls `POST /api/tools/recon` or `POST /api/whitebox/analyze` over localhost/Tailscale. Results (JSON findings, severity, CVE candidates) are ingested by AOS's Research Engine or EES. No T3MP3ST source enters AOS.

- **Effort:** Low (1-2 days: Dockerfile, API client in AOS)
- **License risk:** None if process boundary is maintained
- **Coupling:** Loose (HTTP, version-pinned container)
- **Local-first:** Yes, if run on CasaOS
- **Limitation:** Only the stable recon + whitebox surface is useful today. Swarm exploitation is unbenchmarked.
- **Operational risk:** An autonomous agent with real network tools (nmap, gobuster, sqlmap) running adjacent to AOS. Requires strict scope configuration; every call must specify authorized targets.

### Option 2: Borrow architecture patterns, re-implement in AOS (Recommended for long-term)

Study `src/orchestration/orchestrator.ts` (the decomposition orchestrator), `src/arsenal/approval.ts` (the human-veto gate), `src/arsenal/catalog.ts` (the tiered risk catalog), and `src/opsec/index.ts` (detection/jitter management). Re-implement equivalent functionality in AOS's own codebase under AOS's license. The ideas are:

- Master-builder/worker LLM split for sensitive tasks (keeps offensive framing away from restricted models)
- Risk-tiered tool catalog with execution mode gating (safe_command / receipt_required / catalog_only)
- Human approval gate with fail-safe deny for headless runs
- Egress scope containment (refuse off-scope targets at the tool layer)

- **Effort:** Medium-High (1-3 weeks depending on depth)
- **License risk:** None (re-implementing ideas, not copying code)
- **Coupling:** Zero (AOS owns the implementation)
- **Benefit:** These patterns apply to AOS's general tool execution model, not just security

### Option 3: Adopt specific benchmark oracles as an evaluation reference (Low effort, no license risk)

T3MP3ST's `bench/` directory (gitignored, fetched on demand) and `verify-claims` system demonstrate a reproducible benchmark framework. AOS can adopt the same discipline for its own evaluation claims: committed ground-truth oracles + a re-derivation script that proves every headline number. No T3MP3ST code required; this is a methodology borrow.

- **Effort:** Very low (design reference only)
- **License risk:** None
- **Value:** High for AOS's credibility on EES scoring

### Option 4: Reject integration, monitor for maturity

Do nothing now. Re-evaluate when T3MP3ST's exploitation swarm moves from scaffolding to benchmarked capability, and when/if a commercial license or MIT-licensed fork appears.

- **Effort:** Zero
- **License risk:** Zero
- **Value:** Avoids premature integration of an immature capability

---

## 7. Risks and Rough Edges

### Risk 1: AGPL contamination (Critical)

Any import, bundle, or vendoring of T3MP3ST source into AOS propagates AGPL to the entire combined work. The license text is unambiguous. There is no dual-license option. This is a legal risk, not a technical one. The only mitigation is strict process isolation (Option 1) or clean reimplementation (Option 2). Rating: Critical if violated, avoidable by design.

### Risk 2: Autonomous offensive agent mis-targeting (High)

T3MP3ST with its full arsenal executes real network operations: TCP scans, HTTP requests, XSS payload injection, SQLi probes, subdomain enumeration, password spraying. If AOS automation misconfigures a target (wrong IP, staging vs. production, authorized vs. unauthorized), T3MP3ST will run real attacks against it. The scope containment (`docs/SCOPE_AND_AUTHORIZATION.md`) is documented but not enforced by a hardware air-gap -- it is a software check. In an automated AOS pipeline, a logic error in target selection becomes an unauthorized attack.

Mitigation: Run T3MP3ST in a dedicated container with outbound network restricted to explicitly allow-listed CIDR ranges. Never pass production hostnames; use staging/lab targets only. Every AOS call to T3MP3ST must pass explicit scope receipts and be audited.

### Risk 3: Dual-use payload surface (Medium)

T3MP3ST's `src/arsenal/index.ts` (131KB) contains hundreds of live attack payloads (SQL injection, XSS, SSTI, command injection, XXE, SSRF) and active tools (password_spray, hash_crack). Running this in AOS's environment means the AOS control plane is co-located with offensive tooling. If AOS is ever compromised, T3MP3ST becomes an attack vector. Mitigation: container isolation, least-privilege networking, separate credentials.

### Risk 4: Single maintainer, high bus-factor (Medium)

elder-plinius is the primary author and appears to be a solo maintainer (commit history shows primary author `pliny` with GitHub squash-merge PRs from contributors). No governance, no foundation, no SLA. The `9 Pliny Specials were retired in 2026-06` with minimal notice -- the API surface can change without deprecation windows. If AOS integrates against the HTTP API, a version pin is essential.

### Risk 5: Benchmarks are system-level claims, not unit-testable guarantees (Low-Medium)

The 90.1% XBEN score is for the whole harness driving a specific model (gpt-5.5). It is not a property of T3MP3ST in isolation. If AOS uses a different model (e.g., local Llama), results will differ significantly. The benchmark is honest and reproducible, but the number does not transfer across model choices. AOS should not assume T3MP3ST provides 90%+ efficacy with local models.

### Risk 6: Cloud LLM dependency for peak performance (Low)

The best results require GPT-4o / Claude Opus / gpt-5.5 class models. The "keyless" local mode works but produces lower-quality analysis. AOS's local-first preference will cap T3MP3ST's offensive reasoning quality at whatever Ollama model is available.

### Rough edges observed in the code

- `src/mcp-server.ts` contains empty comment blocks labeled "COMPREHENSIVE PAYLOAD DATABASES," "SECRET PATTERNS DATABASE (GRIFFIN)," "PRIVILEGE ESCALATION DATABASE (CERBERUS)," and "WAF BYPASS TECHNIQUES (TYPHON)" -- sections of the MCP server that previously contained these but were gutted when the Pliny Specials were retired. The scaffolding comments remain, which is mildly misleading.
- FEATURES.md notes the MCP server exposes `security_recon` only. The WHITEPAPER (written in February 2026) still lists the retired Pliny MCP tools. The WHITEPAPER is partially stale.
- `src/server.ts` is 340KB -- a monolithic server file that has grown without modular decomposition. This is a maintenance risk for the project but does not affect AOS integration.
- The 8-operator swarm is explicitly unbenchmarked. The benchmark numbers in the README come from a single-agent ReAct loop. Marketing the architecture as a multi-agent system while benchmarking only single-agent runs is technically honest (they do label it) but visually misleading.

---

## 8. Notable Patterns Worth Borrowing (as design references, not code)

| Pattern | Where (file:line) | Why it's useful |
|---------|-------------------|-----------------|
| Risk-tiered tool catalog with execution mode | `src/arsenal/catalog.ts`, `ToolRisk` / `ToolExecutionMode` types | Clean taxonomy: `local_read / passive / active / intrusive / credential / dangerous` paired with `safe_command / receipt_required / catalog_only / import_only`. AOS's tool execution model could use this. |
| Human-veto approval gate with fail-safe deny | `src/arsenal/approval.ts`, `ApprovalController.gate()` | Headless runs that encounter a gated tool are denied by default (not silently allowed). "Approve once, then free for the session." Pure module, no I/O, fully testable. |
| Master-builder / worker LLM decomposition | `src/orchestration/orchestrator.ts`, `DecompositionOrchestrator.run()` | The offensive objective is held only by the unrestricted orchestrator; the worker sees only benign code-analysis questions. Useful for any AOS task where the goal is sensitive but the sub-queries should be model-agnostic. |
| Egress scope containment at the tool layer | `src/mcp-server.ts`, TARGET_RE regex + docs/SCOPE_AND_AUTHORIZATION.md | Validate target before any subprocess call. "Once a mission target is set, built-in networked tools refuse off-scope public hosts." |
| Reproducible benchmark with committed oracles | `scripts/verify-claims.mjs` + `bench/*.json` | Every headline number re-derives from committed ground-truth data. AOS's EES scoring should adopt this discipline: no claim without a committed oracle and a re-run script. |
| Refusal detection with length guard | `src/orchestration/orchestrator.ts`, `looksLikeRefusal()` | Only treats as a refusal if the content is short AND matches refusal patterns. Long analysis that mentions inability to determine something is not a refusal. Prevents false-positive refusal classification. |

---

## 9. Recommendation

### Summary

T3MP3ST is a technically honest, actively maintained, AGPL-3.0-licensed offensive security harness with a proven recon/white-box analysis surface (benchmarked) and an ambitious but mostly-scaffolded exploitation swarm (unbenchmarked). The license is the dominant integration constraint: no code can enter AOS without triggering AGPL copyleft on the combined work.

### Evidence

- License: `LICENSE` file (full AGPL-3.0 text), `package.json` `"license": "AGPL-3.0-or-later"`, `THIRD-PARTY.md` confirmation of scope.
- Benchmarks: README benchmark table, `bench/` oracles, `scripts/verify-claims.mjs`.
- What is real vs. scaffolding: FEATURES.md `[x]/[~]/[ ]` table, WHITEPAPER.md opening caveat, README "What ships today" table.
- Tool architecture: `src/arsenal/catalog.ts`, `src/arsenal/approval.ts`, `src/mcp-server.ts`.
- Decomposition orchestrator: `src/orchestration/orchestrator.ts`.
- HTTP API: WHITEPAPER.md section 10.2, `src/server.ts` (not read in full due to size but API surface confirmed from docs).

### Recommendation

**PARTIAL-BORROW + MONITOR** with the following breakdown by integration option:

| Option | Verdict | Condition |
|--------|---------|-----------|
| Vendor T3MP3ST source into AOS | REJECT | AGPL contamination, incompatible |
| Run as isolated external service | CONDITIONAL ADOPT | Only for recon/whitebox surface; requires container isolation + scope enforcement |
| Borrow patterns (re-implement) | ADOPT | Risk-tiered catalog, approval gate, decomposition orchestrator -- implement natively in AOS |
| Monitor for maturity | ADOPT | Re-evaluate when exploitation swarm is benchmarked and if commercial license appears |

### Alternatives considered

- **Semgrep + Trivy + Nuclei directly:** These individual tools cover SAST, container scanning, and web scanning without the AGPL risk or autonomous offensive footprint. They are referenced in T3MP3ST's own catalog. For AOS's EES security scoring, integrating these directly (each is permissively licensed) may be sufficient without T3MP3ST's orchestration layer.
- **Garak / promptfoo for LLM security testing:** These are also in T3MP3ST's catalog. If AOS needs to red-team LLM agents it builds, these tools address that more specifically than T3MP3ST's general offensive harness.

### Pros and cons

**Pros:**
- Reproducible, honest benchmark methodology is rare and worth studying
- Decomposition orchestrator is a novel multi-LLM architecture for sensitive analysis tasks
- Local-first capable (Ollama support), compatible with AOS's preferences
- Genuine web/CTF performance (90.1% XBEN, 58% Cybench) on the benchmarked surface
- Active development with community contributors

**Cons:**
- AGPL-3.0 blocks all source integration paths
- Exploitation swarm (the "multi-agent" headline) is unbenchmarked scaffolding
- Single maintainer, no governance, API surface can change abruptly (Pliny Specials retired without deprecation window)
- Co-locating autonomous offensive tooling with AOS's engineering control plane is an operational risk
- Peak performance requires cloud LLM APIs, not local models

### Risk

- Legal (AGPL): High if source is vendored; Zero if process-isolated.
- Operational (mis-targeting): High if called by AOS automation without strict scope enforcement; Medium with proper container isolation and target allow-listing.
- Dual-use liability: Always present with offensive security tooling. AOS operator is responsible for ensuring every T3MP3ST invocation has written authorization for the target system.

### Effort

- Option 1 (external service): 1-2 days to containerize + write AOS API client + define scope enforcement protocol.
- Option 2 (re-implement patterns): 1-3 weeks for risk-tiered catalog + approval gate + decomposition orchestrator in AOS's own stack.

### Dependencies

- Option 1 requires: Node.js container, network access from AOS to T3MP3ST sidecar, target allow-list enforcement.
- Option 2 requires: None (pure AOS development).

### Acceptance criteria

- If Option 1: AOS can call T3MP3ST recon and receive structured findings that feed EES security scoring. T3MP3ST runs in an isolated container with outbound allow-list. No T3MP3ST source in AOS repo. AGPL audit passes.
- If Option 2: AOS implements a risk-tiered tool catalog and approval gate. The decomposition orchestrator is available for whitebox analysis tasks. All code is AOS-licensed.

### Next steps

1. Decide whether AOS's EES needs a security sub-score now (if yes, pursue Option 1 or Option 2; if not, pursue Option 4 - monitor only).
2. If Option 1: write a minimal `t3mp3st-sidecar` Docker image, implement `SecurityReconClient` in AOS's Python/TypeScript layer, define target scope enforcement protocol, test against an authorized staging system.
3. If Option 2: design the AOS tool-execution catalog using T3MP3ST's risk-tier taxonomy as a reference; implement `ApprovalGate` and `DecompositionOrchestrator` equivalents in AOS's own stack.
4. In either case: adopt the `verify-claims` reproducible benchmark pattern for AOS's own EES scoring -- this is a methodology borrow with zero license risk and high credibility value.

---

## Appendix: Commit Activity Sample

Top commits from list_commits (2026-07-09):
- `ae32cf5` Merge PR #54: "feat(arsenal): real invocations for the reverse-engineering / mobile / smart-contract analysis loadout" (pliny, 2026-07-09T12:51)
- `30aa72d` (parent, same date, 2026-07-09T12:50)

Activity cadence: Multiple PRs merged per day from community contributors, with pliny as sole merge authority. Highly active as of analysis date.
