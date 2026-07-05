# LLM Provider Abstraction

Status: shipped in AOS-COUNCIL-001 (RFC-0005 Phase 1). Backend only.

The reasoning backend for ArchetypeOS is a **swappable, local-first concern**,
not a hardcoded dependency. Every text-generation call in the platform goes
through one minimal interface — the `Provider` protocol in
`packages/aos_core/aos_core/llm/__init__.py` — so a real model drops in behind
the seam without changing any caller. This mirrors the existing Verification
Provider Interface (`docs/VERIFICATION_PROTOCOL.md`: declare → standardized
result) and satisfies Constitution **Article XI (Modular Intelligence)**:
"engines, agents, models, providers … must be replaceable without redesigning
the whole platform."

## The protocol

```python
@dataclass
class ProviderResult:
    text: str            # the model's raw output (parsed tolerantly downstream)
    provider: str        # "deterministic" | "claude_code" | ...
    model: str | None
    finish_reason: str

class Provider(Protocol):
    def generate(self, *, system: str, prompt: str, max_tokens: int = 1024) -> ProviderResult: ...
```

`generate` is duck-typed and has no hard dependency on any SDK. Callers
(currently the Agent Council service) build a `system` persona prompt and a
`prompt` carrying the question + evidence, and receive a `ProviderResult`. The
council parses `result.text` **tolerantly** as a structured JSON agent output
(`summary` / `findings` / `evidence` / `concerns` / `confidence` / `status`);
unparseable prose degrades to `status="Needs Evidence"` with low confidence and
the raw text in `summary`. Both backends flow through that one parser, so the
seam is uniform.

## The two shipping backends

### `DeterministicProvider` (the CI / hermetic default)

A **real, shippable** backend — not a test double. `generate` derives a stable,
structured JSON response **only** from its inputs: no randomness, no seed, no
clock. Equal inputs always produce identical output. It parses the evidence
embedded in the council prompt, emits one finding per evidence item, flags
risk-keyworded items as concerns, and computes a deterministic confidence from
the evidence/concern counts.

This is the local-first, verification-over-inference stance applied to the
reasoning layer: **deterministic by default, probabilistic only when a model is
deliberately attached.** It lets the entire council pipeline run and be asserted
offline, with zero external calls — which is exactly what CI does.

### `ClaudeCodeProvider` (the operator's real backend)

The operator's chosen real reasoning backend. `generate` shells to the local
headless `claude` CLI:

```
claude -p "<system>\n\n<prompt>" --output-format json
```

via `subprocess.run` with a bounded timeout, and maps the JSON envelope's
`result` field to `ProviderResult.text`. It authenticates through the operator's
**Claude Code subscription** — the local `claude` install's own auth — so:

- **No API keys** are read from repo config or committed anywhere.
- **No metered, per-token spend** → no budget gate is required (this is why
  RFC-0005 supersedes the board note's env-keyed-API framing).

It is importable in CI but **never invoked there** (CI selects `deterministic`,
which needs no auth). Its subprocess boundary is unit-tested with a mocked
invocation (`test_claude_code_provider_mocked`): the test asserts the argv is
built correctly (system prepended to the prompt, `--output-format json`) and
that stdout maps to `ProviderResult`; a non-zero exit or a missing binary raises
a clear `RuntimeError`. No live `claude` call ever runs in a test.

## Selection

```python
Settings.llm_provider: str = "deterministic"   # aos_core.config
get_provider(settings) -> Provider             # aos_core.llm
```

`get_provider` maps `deterministic` → `DeterministicProvider`, `claude_code` →
`ClaudeCodeProvider`, and raises `ValueError` on anything else. Existing
deployments need no config change; the operator sets `LLM_PROVIDER=claude_code`
on an authed node (WSL / `teevee-1`) to enable real council reasoning.

## Adding a backend

1. Write a class with a `generate(*, system, prompt, max_tokens=...) ->
   ProviderResult` method (and a `name` attribute). Keep any SDK/process call
   thin and defensive — timeout, decode, clear error surface.
2. Register it in `get_provider`.
3. Add a mocked-boundary unit test (no live call in CI).
4. Document its selection value here.

No caller changes are required — that is the point of the seam.

## Local-first routing policy (forward-looking)

Per `docs/LOCAL_LLM_GPU_NODE.md`, the intended routing once GPU/hosted backends
land behind this protocol: **use local models where they are sufficient, expensive
models where they matter.** Local models (Ollama / vLLM / an OpenAI-compatible
endpoint on the 3090 node) handle low-risk, repetitive work — first-pass scans,
triage, summaries; cloud/premium models are reserved for high-stakes
architecture / security / compliance reasoning and final recommendations. The
ordering is: local endpoint on the GPU node → hosted fallback. The GPU node
itself is deferred until the WSL target is verified; the seam accepts these
backends without any caller change.

## Why CI stays deterministic

CI has no GPU, no network to a model, and no credentials — and the council
pipeline must be *real and deterministically verifiable today*. Running the
`DeterministicProvider` in CI keeps the whole pipeline hermetic and repeatable
while the same interface carries a probabilistic backend on an authed node. A
probabilistic capability thus enters the system **behind a deterministic default
provider**, so CI never depends on a live model.
