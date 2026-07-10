"""Free-API rotation pool (AOS-LLM-EVAL-001, slice 3) — makes Tier-2 reliable
under rate limits.

Free hosted tiers are generous but capped (Groq 1,000 req/day, etc.). A single
provider will eventually 429. ``RotatingProvider`` wraps a pool of Tier-2
providers and, on any per-call failure (429, 5xx, timeout, auth on one bad key),
falls through to the next member; it only raises when EVERY member fails. A
round-robin cursor spreads load across members so no single daily quota is burned
first.

The pool is assembled from whichever free providers have a key in the
environment (``build_free_pool``), so adding a provider is just exporting its key
— no code change. Privacy tiering still applies upstream: the router only reaches
the free tier (this pool) for non-private tasks.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from ..llm import OpenAICompatibleProvider, Provider, ProviderResult


@dataclass
class PoolMember:
    name: str
    base_url: str
    model: str
    key_env: str


# The known OpenAI-compatible free providers (cheahjs/free-llm-api-resources).
# A member is included only when its key env var is set.
DEFAULT_FREE_POOL: list[PoolMember] = [
    PoolMember("groq", "https://api.groq.com/openai/v1", "llama-3.3-70b-versatile", "GROQ_API_KEY"),
    PoolMember("cerebras", "https://api.cerebras.ai/v1", "gpt-oss-120b", "CEREBRAS_API_KEY"),
    PoolMember(
        "gemini",
        "https://generativelanguage.googleapis.com/v1beta/openai",
        "gemini-2.5-flash",
        "GEMINI_API_KEY",
    ),
    PoolMember("mistral", "https://api.mistral.ai/v1", "mistral-large-latest", "MISTRAL_API_KEY"),
]


class RotatingProvider:
    """Rotate across Tier-2 providers; fall through on failure, round-robin start.

    Holds pre-built providers (so it is trivially testable with fakes). Implements
    the :class:`~aos_core.llm.Provider` protocol.
    """

    name = "rotating"

    def __init__(self, providers: list[Provider], labels: list[str] | None = None) -> None:
        self._providers = providers
        self._labels = labels or [getattr(p, "name", "?") for p in providers]
        self._cursor = 0

    def __len__(self) -> int:
        return len(self._providers)

    def generate(
        self,
        *,
        system: str,
        prompt: str,
        max_tokens: int = 1024,
        response_format: dict | None = None,
    ) -> ProviderResult:
        n = len(self._providers)
        if n == 0:
            raise RuntimeError("rotation pool is empty")
        start = self._cursor
        self._cursor = (self._cursor + 1) % n  # spread load across calls
        errors: list[str] = []
        for offset in range(n):
            idx = (start + offset) % n
            try:
                result = self._providers[idx].generate(
                    system=system,
                    prompt=prompt,
                    max_tokens=max_tokens,
                    response_format=response_format,
                )
                # Report the pool's identity ("rotating") on the result so the usage
                # ledger tiers it as FREE (derive_tier maps "rotating" -> free). The
                # member's model name is kept; only the provider LABEL is normalized.
                # Without this the member's "openai_compatible" + a None base_url fell
                # through to the local branch, mis-tagging every free-pool call "local"
                # (LES-L20: gemini/llama-70b/mistral/120b all showed up as local tier).
                result.provider = "rotating"
                return result
            except Exception as exc:  # noqa: BLE001 — try the next member on ANY failure
                errors.append(f"{self._labels[idx]}: {exc}")
        raise RuntimeError("all rotation-pool providers failed — " + " | ".join(errors))


def build_free_pool(env: dict | None = None, *, timeout: float = 120.0) -> list[tuple[str, Provider]]:
    """Return [(name, provider)] for each free provider whose key is in ``env``."""
    env = os.environ if env is None else env
    out: list[tuple[str, Provider]] = []
    for m in DEFAULT_FREE_POOL:
        key = env.get(m.key_env, "")
        if key:
            out.append(
                (m.name, OpenAICompatibleProvider(
                    base_url=m.base_url, model=m.model, api_key=key, timeout=timeout
                ))
            )
    return out


def free_pool_provider(env: dict | None = None, *, timeout: float = 120.0) -> RotatingProvider | None:
    """A RotatingProvider over the configured free pool, or None if none configured."""
    members = build_free_pool(env, timeout=timeout)
    if not members:
        return None
    return RotatingProvider([p for _, p in members], labels=[n for n, _ in members])
