"""Embedding provider abstraction for ArchetypeOS (RFC-0010, Part 1).

This is the semantic-retrieval seam, mirroring :mod:`aos_core.llm`: one minimal,
duck-typed interface — :class:`EmbeddingProvider` — resolved from settings by
:func:`get_embedder`. It is the storage/retrieval half of the Embedding Relevance
Tier, delivered **without torch** so CI stays fast and hermetic.

Part 1 ships exactly one concrete backend:

- :class:`DeterministicEmbedder` — the CI/hermetic default. ``embed()`` returns
  ``None`` (no vector), which every caller reads as "fall back to the
  deterministic lexical Layer-0 path". It imports nothing heavy, makes no network
  call, and needs no model — so the whole vector-store + retrieval path can be
  wired, migrated, and (Postgres-gated) tested with synthetic vectors + fake
  embedders, all off the torch dependency path.

The real ``sentence-transformers`` (torch) backend — :class:`!SentenceTransformerEmbedder`
— is **AOS-EMBED-002** (Part 2). It registers here behind a *lazy* import so that
importing this module, and running with the deterministic default, never pulls in
torch. Do NOT add a torch import to this file.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..config import EMBEDDING_DIM


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Minimal text-embedding contract. Adapters live behind this protocol.

    ``name`` gates behaviour (e.g. ``"deterministic"`` → no vector → lexical
    fallback), ``dim`` is the vector width, and ``embed`` returns a ``dim``-length
    vector or ``None`` (meaning "no embedding available; use the lexical path").
    """

    name: str
    dim: int

    def embed(self, text: str) -> list[float] | None:
        ...


class DeterministicEmbedder:
    """Offline, no-op embedder. CI runs this.

    ``embed`` always returns ``None`` — there is no torch, no model, no network.
    A ``None`` embedding is the explicit signal to callers (distillation, transfer)
    to keep today's deterministic lexical behaviour: the embedding column stays
    NULL and :func:`~aos_core.services.transfer.recommend_reuse` uses need coverage.
    This is a *real, shippable* backend (the hermetic default), not a test double.
    """

    name = "deterministic"
    dim = EMBEDDING_DIM

    def embed(self, text: str) -> list[float] | None:
        return None


def get_embedder(settings) -> EmbeddingProvider:
    """Select an embedder from ``settings.embedding_provider`` (default deterministic).

    ``deterministic`` → :class:`DeterministicEmbedder`. The real
    ``sentence_transformers`` (torch) tier is AOS-EMBED-002 and will register here
    behind a lazy import — no torch is imported in Part 1. Any other name is an
    explicit error (surface a misconfiguration rather than silently mis-embed).
    """
    name = getattr(settings, "embedding_provider", "deterministic")
    if name == "deterministic":
        return DeterministicEmbedder()
    # Seam for AOS-EMBED-002: ``if name == "sentence_transformers": from
    # ._sentence_transformers import SentenceTransformerEmbedder (lazy torch)``.
    raise ValueError(
        f"Unknown embedding_provider: {name!r} "
        "(Part 1 ships 'deterministic'; the sentence-transformers tier is AOS-EMBED-002)"
    )


__all__ = [
    "EMBEDDING_DIM",
    "EmbeddingProvider",
    "DeterministicEmbedder",
    "get_embedder",
]
