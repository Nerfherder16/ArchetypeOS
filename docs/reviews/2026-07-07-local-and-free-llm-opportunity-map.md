# Local & Free-API LLM Opportunity Map (2026-07-07)

Where ArchetypeOS can route its own reasoning onto the local 3070 (teevee) and
free hosted APIs instead of Claude — to cut token cost, unlock always-on work,
and add capability. Grounds on the `OpenAICompatibleProvider` seam
(AOS-LLM-LOCAL-001) and the just-validated local reviewer.

## 1. Thesis

ArchetypeOS is already a **deterministic-floor + reasoned-tier** system. Today the
reasoned tier = Claude (expensive, rate-limited, on-demand). The provider seam
turns the reasoned tier into a **routed pool of four tiers**, and the vision docs
already anticipate it (Engine Catalog: Build Intelligence "hands work to Claude
Code, **local LLMs**, or other builders"; Agent Catalog: Builder Agent runs
"through Claude Code, **local tools**, or other coding agents").

| Tier | Backend | Cost | Latency | Privacy | Use for |
|---|---|---|---|---|---|
| 0 Deterministic | in-process | free | instant | total | hermetic floor, CI, structural extraction |
| 1 Local 7B | teevee 3070 (Ollama) | free | ~2–10s | **total (private)** | bounded, private, high-volume: code review, classification, structured extraction |
| 2 Free hosted | Gemini/Groq/Cerebras/DeepSeek | free* | fast | **external (non-private only)** | capable reasoning on non-sensitive input: research, council, design, narrative |
| 3 Claude | subscription | $$ | on-demand | private | highest-stakes: Final Judge, hard reasoning, private + critical |

\* rate-limited (see §3).

## 2. The free-hosted catalog (from `cheahjs/free-llm-api-resources`)

Genuinely powerful, genuinely free (rate-limited), all OpenAI-compatible so they
drop into our provider with only a base_url + key change:

- **Google AI Studio — Gemini 2.5/3.x Flash**: 250k tok/min, ~20 req/day. Huge
  context, **multimodal**, strong reasoning. The best free "smart" model.
- **Groq — Llama-3.3-70B / Llama-4-Scout**: 1,000 req/day, very fast. Best for
  volume + speed.
- **Cerebras — GPT-OSS-120B**: 30 req/min, 60k tok/min. A 120B-class model, free.
- **Mistral La Plateforme**: 500k tok/min, **1B tok/month** — enormous volume.
- **Cloudflare Workers AI**: Llama-3.3-70B, DeepSeek-R1, Qwen — 10k neurons/day.
- **SambaNova / GitHub Models / NVIDIA NIM**: DeepSeek-V3, GPT-4o, o1 (tighter
  limits).

## 3. Governance (non-negotiable constraints)

1. **Privacy tiering (constitutional — local-first + IP protection).** Most free
   tiers train on submitted data. So: **private/proprietary code → Tier 1 (local)
   or Tier 3 (Claude) ONLY.** Free hosted (Tier 2) is allowed only for
   non-sensitive input: public repos, general reasoning, design, research. The
   router must know each task's data-sensitivity class.
2. **Rate-limit resilience.** Free tiers are capped; a **provider-rotation pool**
   (round-robin across Gemini/Groq/Cerebras/Mistral with fallback on 429) is
   required before Tier 2 is production-reliable. The catalog is the pool's input.
3. **Eval-driven routing.** `AOS-LLM-EVAL-001` decides which tier per task-class
   from measured quality/latency/cost — never by guess.
4. **Deterministic stays the CI default** — no tier reaches CI.

## 4. Opportunity map (per reasoning surface)

| Surface (Engine/Agent) | Today | Recommended tier | Payoff |
|---|---|---|---|
| **PR Guardian reviewer** | deterministic + local (built) | **1 local** (per-category) | ✅ done — free, private, fast |
| **Agent Council — per-agent outputs** | deterministic / claude_code | **2 free, one model PER agent** | ⭐ a real **multi-model** council for free (see §5) |
| **Final Judge** | claude_code | **3 Claude** | keep — highest stakes |
| **Distillation (repo purpose/summary)** | deterministic + claude_code | 1 local (private repos) / 2 free (public) | offload Claude; 70B narrative > 7B |
| **Research Engine / Librarian** | — | **2 free** (Gemini/Groq, big ctx) | research synthesis off Claude |
| **Continuous Research Engine** | — | 1 local + 2 free, **always-on** | ⭐ idle compute → continuous research (see §5) |
| **Design Intelligence / Architecture Studio** | — | **2 free — Gemini multimodal** | ⭐ free vision for diagrams/UI (see §5) |
| **Doc-staleness reconciliation narrative** | claude nightly | 2 free (Llama-70B) / 1 local | offload the nightly Claude routine |
| **Conflict-learn lesson distillation** | claude nightly | 1 local / 2 free | offload |
| **Nightly Self-Learning digest** | in-container (blocked) | **1 local always-on** | idle 3070 overnight |
| **Build Intelligence / Builder** | Claude Code | 1 local-coder (scaffold) / 3 Claude (hard) | offload boilerplate |
| **Technology Fitness / Recommendation / Evolution** | — | 2 free (reasoning) | offload meta-analysis |
| **Meta Agent / Prompt+Workflow Evolution** | — | 2 free | offload self-improvement grind |

## 5. Top 3 highest-leverage opportunities

**A. A genuine multi-model Agent Council — for free.** The council architecture
already runs N independent agents → Final Judge. Today they share one provider.
Route **each agent to a different free frontier model** (Gemini Flash + Llama-3.3-70B
via Groq + GPT-OSS-120B via Cerebras + DeepSeek-V3), with **Claude as Final Judge
only**. That is a true diverse-model council (real independence, not one model
role-played N times — the exact value the council is meant to capture), at ~zero
marginal cost. Biggest capability+independence win; directly advances RFC-0005.
Constraint: only for non-private questions (§3.1).

**B. Always-on continuous engineering.** Local inference is free-per-token and the
3070 idles ~20h/day; free tiers add huge volume (Mistral 1B tok/month, Groq 1,000
req/day). This makes work that was never economical on Claude routine: overnight
architecture-drift detection, continuous distillation of the repo portfolio,
pre-reviewed PRs waiting by morning, a continuously-refreshed research corpus.
The scarcity that started this becomes the engine that makes ArchetypeOS
self-hosting.

**C. Free multimodal for Design/Architecture.** Gemini Flash is multimodal and
free. Design Intelligence and Architecture Studio ingest diagrams, screenshots,
and uploaded images — route those to free Gemini vision. Capability Claude would
otherwise bill for, at zero cost.

## 6. Recommended sequencing

1. **Land the local reviewer** (AOS-LLM-REVIEW-001) — proven; smallest, private,
   Tier 1. Ship first.
2. **Build the eval-driven router + provider-rotation pool** (AOS-LLM-EVAL-001 +
   a rotation layer) — the governance substrate every Tier-2 use depends on.
3. **Multi-model Council** (opportunity A) on the router — the flagship capability.
4. **Point the nightly routines** (reconcile narrative, conflict-learn, digest) at
   Tier 1/2 — recurring token savings, always-on.
5. **Distillation + Research** onto Tier 2 for public inputs; **Design** onto
   Gemini multimodal.

Each step is measured on the eval harness before it's trusted; privacy tiering
(§3.1) gates every Tier-2 route.
