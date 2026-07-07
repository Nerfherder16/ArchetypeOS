# Runbook: LLM provider (local + free hosted)

ArchetypeOS reasons through the `llm_provider` seam
(`packages/aos_core/aos_core/llm/__init__.py`). Three backends:

| `LLM_PROVIDER` | Backend | Cost | When |
|---|---|---|---|
| `deterministic` (default) | offline, no network | free | CI / hermetic tests — never calls a model |
| `claude_code` | local `claude` CLI (subscription auth) | Claude tokens | highest quality; the operator's node |
| `openai_compatible` | any OpenAI `/chat/completions` | **free** (local) or free-tier (hosted) | **save Claude tokens** (AOS-LLM-LOCAL-001) |

`openai_compatible` is one adapter for both a **local** model and a **free hosted
API** — only `LLM_BASE_URL` / `LLM_MODEL` / `LLM_API_KEY` differ.

## Profile A — local model on teevee's RTX 3070 (Ollama)

ArchetypeOS runs on teevee, so "local" is `localhost`. One-time on teevee:

```bash
# install Ollama, then pull a model that fits 8 GB VRAM:
ollama pull qwen2.5-coder:7b     # coding-oriented, ~5 GB q4 — good for the 3070
# (alternatives: qwen3:8b, llama3.1:8b)
```

Then in `.env`:

```
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=qwen2.5-coder:7b
LLM_API_KEY=
```

Free, private, no key. Best for research/distillation/council reasoning. Note:
Ollama "thinking" models (e.g. `qwen3`) spend tokens on an internal `reasoning`
field first — give them a generous `max_tokens` or prefer a non-thinking coder
model.

## Profile B — free hosted API (free-llm-api-resources catalog)

Stronger models for heavy coding, rate-limited, needs a key. E.g. Groq:

```
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=llama-3.3-70b-versatile
LLM_API_KEY=<key>     # env / chmod-600 .env only — never commit
```

Other OpenAI-compatible free tiers work the same way (Cerebras, OpenRouter free,
Google AI Studio). ArchetypeOS has already scanned `free-llm-api-resources` — use
its catalog to pick a provider + model.

## Mixing per task

Because selection is config-driven, you can run different use sites against
different backends (local Ollama for cheap research, a free API for coding) by
setting the env for that process/run. The reasoned tiers read `get_provider(get_settings())`;
override the three `LLM_*` vars in that process's environment.

## Safety / contract

- Deterministic stays the default so CI is hermetic (this backend is never
  selected in CI).
- Isolation (LES-021) is inherent — an HTTP provider sends only `system` +
  `prompt`, no working directory or ambient `CLAUDE.md`.
- `LLM_API_KEY` is read from the env, never committed.
