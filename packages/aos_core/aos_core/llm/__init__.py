"""LLM provider abstraction for ArchetypeOS (RFC-0005).

One minimal, duck-typed interface for text generation — :class:`Provider` — with
two shipping backends:

- :class:`DeterministicProvider` — the CI/hermetic default. It makes no network
  call, uses no credentials, and derives a stable, structured JSON response only
  from its inputs (``system`` + ``prompt``). Equal inputs always yield equal
  output. This is a *real, shippable* backend, not a test double: it lets the
  whole council pipeline run and be asserted offline.
- :class:`ClaudeCodeProvider` — the operator's real reasoning backend. It shells
  to the local headless ``claude`` CLI (``claude -p <prompt> --output-format
  json``) using the operator's Claude Code **subscription** auth already on the
  node — no API keys are read from repo config or committed. It is importable in
  CI but never invoked there (CI selects ``deterministic``); its subprocess
  boundary is unit-tested with a mocked invocation.

``get_provider(settings)`` selects a backend from ``settings.llm_provider``.
Further backends (Ollama / vLLM on the GPU node; a hosted fallback) register here
later without touching callers — Constitution Art. XI (Modular Intelligence).
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class ProviderResult:
    """The standardized result every provider returns.

    ``text`` is the model's raw output (the council parses it tolerantly as a
    JSON agent output); the rest is lightweight provenance metadata.
    """

    text: str
    provider: str
    model: str | None
    finish_reason: str


@runtime_checkable
class Provider(Protocol):
    """Minimal text-generation contract. Adapters live behind this protocol."""

    def generate(self, *, system: str, prompt: str, max_tokens: int = 1024) -> ProviderResult:
        ...


# Keywords the deterministic reasoner treats as a raised concern. Kept in the
# provider (where a real model would form the judgement), not in the selector.
_RISK_KEYWORDS = (
    "risk",
    "missing",
    "no test",
    "without test",
    "vuln",
    "cve",
    "insecure",
    "unsafe",
    "fail",
    "deprecat",
    "unsupported",
    "critical",
    "warning",
    "secret",
    "exposed",
)


def _extract_line_value(prompt: str, marker: str) -> str:
    for line in prompt.splitlines():
        if line.startswith(marker):
            return line[len(marker):].strip()
    return ""


def _extract_evidence(prompt: str) -> list:
    """Pull the single-line JSON evidence array embedded in a council prompt.

    Tolerant: an absent or unparseable block yields ``[]`` (→ a Needs Evidence
    output), so the provider never raises on prompt shape.
    """
    lines = prompt.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("Evidence (JSON array):"):
            raw = lines[index + 1] if index + 1 < len(lines) else ""
            try:
                data = json.loads(raw)
            except Exception:
                return []
            return data if isinstance(data, list) else []
    return []


class DeterministicProvider:
    """Offline, seedless, reproducible backend. CI runs this.

    ``generate`` transforms ``(system, prompt)`` into a stable JSON agent output.
    There is no randomness, no seed, and no clock: equal inputs → identical text.
    """

    name = "deterministic"

    def generate(self, *, system: str, prompt: str, max_tokens: int = 1024) -> ProviderResult:
        persona = _extract_line_value(prompt, "Persona:") or "agent"
        evidence_items = _extract_evidence(prompt)

        findings: list[str] = []
        evidence_refs: list[str] = []
        concerns: list[str] = []
        for item in evidence_items:
            if isinstance(item, dict):
                kind = str(item.get("kind", "signal"))
                detail = str(item.get("detail", ""))
                ref = str(item.get("ref", detail))
            else:
                kind = "signal"
                detail = str(item)
                ref = detail
            findings.append(f"{kind}: {detail}")
            evidence_refs.append(ref)
            if any(keyword in detail.lower() for keyword in _RISK_KEYWORDS):
                concerns.append(detail)

        count = len(evidence_items)
        if count == 0:
            summary = f"{persona}: no evidence available to assess the question."
            confidence = 0.0
            status = "Needs Evidence"
        else:
            base = 0.4 + 0.1 * min(count, 4)  # 0.5 .. 0.8
            penalty = 0.1 * min(len(concerns), 3)
            confidence = round(max(0.0, min(0.95, base - penalty)), 4)
            stance = "concerns identified" if concerns else "no blocking concerns"
            summary = f"{persona}: assessed {count} evidence item(s); {stance}."
            status = "Complete"

        obj = {
            "summary": summary,
            "findings": findings,
            "evidence": evidence_refs,
            "concerns": concerns,
            "confidence": confidence,
            "status": status,
        }
        return ProviderResult(
            text=json.dumps(obj, sort_keys=True),
            provider=self.name,
            model=None,
            finish_reason="stop",
        )


def _extract_claude_text(stdout: str) -> str:
    """Map ``claude --output-format json`` stdout to the model's text.

    ``claude -p ... --output-format json`` emits an envelope like
    ``{"type": "result", "result": "<text>", ...}``. Tolerant: if stdout is not
    that envelope, the raw stdout is returned unchanged.
    """
    try:
        envelope = json.loads(stdout)
    except Exception:
        return stdout
    if isinstance(envelope, dict) and "result" in envelope:
        return str(envelope["result"])
    return stdout


class ClaudeCodeProvider:
    """Real backend: the local headless ``claude`` CLI via subscription auth.

    Thin and defensive — a bounded timeout, an explicit decode, and a clear
    error surface on a missing binary / non-zero exit. Never invoked in CI.
    """

    name = "claude_code"

    def __init__(self, binary: str = "claude", timeout: float = 120.0, model: str | None = None) -> None:
        self.binary = binary
        self.timeout = timeout
        self.model = model

    def _build_argv(self, *, system: str, prompt: str) -> list[str]:
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        argv = [self.binary, "-p", full_prompt, "--output-format", "json"]
        if self.model:
            argv += ["--model", self.model]
        return argv

    def generate(self, *, system: str, prompt: str, max_tokens: int = 1024) -> ProviderResult:
        argv = self._build_argv(system=system, prompt=prompt)
        try:
            completed = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"claude binary not found: {self.binary!r} — install Claude Code or set llm_provider=deterministic"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"claude invocation timed out after {self.timeout}s") from exc

        if completed.returncode != 0:
            raise RuntimeError(
                f"claude exited with code {completed.returncode}: {(completed.stderr or '').strip()}"
            )

        return ProviderResult(
            text=_extract_claude_text(completed.stdout or ""),
            provider=self.name,
            model=self.model,
            finish_reason="stop",
        )


def get_provider(settings) -> Provider:
    """Select a provider from ``settings.llm_provider``.

    ``deterministic`` → :class:`DeterministicProvider`;
    ``claude_code`` → :class:`ClaudeCodeProvider`; anything else → ``ValueError``.
    """
    name = getattr(settings, "llm_provider", "deterministic")
    if name == "deterministic":
        return DeterministicProvider()
    if name == "claude_code":
        return ClaudeCodeProvider()
    raise ValueError(f"Unknown llm_provider: {name!r} (expected 'deterministic' or 'claude_code')")


__all__ = [
    "ProviderResult",
    "Provider",
    "DeterministicProvider",
    "ClaudeCodeProvider",
    "get_provider",
]
