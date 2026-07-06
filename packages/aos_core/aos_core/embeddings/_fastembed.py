"""The real embedding backend for ArchetypeOS (RFC-0010, Part 2 / AOS-EMBED-002).

:class:`FastEmbedEmbedder` fills the Part-1 :class:`~aos_core.embeddings.EmbeddingProvider`
seam with genuine vectors, using **fastembed** (ONNX runtime) — *not* torch /
sentence-transformers. It runs the same ``all-MiniLM-L6-v2`` model (384-dim,
drop-in for the existing pgvector column) at ~50 MB via onnxruntime, the right
footprint for a local-first box. torch buys training/GPU we don't do; we only run
inference on short text.

This module is imported **lazily** — only when ``settings.embedding_provider`` is
``"fastembed"`` (see :func:`aos_core.embeddings.get_embedder`). The ``fastembed``
import itself is deferred further, into :func:`_load_model`, so that merely
importing this module still pulls in no onnxruntime. Importing
``aos_core.embeddings`` never touches any of this (Part 1's torch-free / hermetic
CI invariant is preserved).
"""

from __future__ import annotations

import math

from ..config import EMBEDDING_DIM

# Module-level singleton cache of loaded models, keyed by model name. Loading a
# ``TextEmbedding`` (model init + ONNX session) is expensive; do it once per model.
_MODEL_CACHE: dict = {}


def _load_model(model_name: str):
    """Return a cached loaded ``TextEmbedding`` for ``model_name``, loading once.

    The ``fastembed`` import lives here (not at module top), so nothing heavy is
    imported unless a model is actually loaded. A load/import failure raises a
    clear, actionable error: a node configured for the real tier without fastembed
    installed is a misconfiguration, not a case to silently degrade.
    """
    cached = _MODEL_CACHE.get(model_name)
    if cached is not None:
        return cached
    try:
        from fastembed import TextEmbedding
    except ImportError as exc:  # pragma: no cover - exercised only without fastembed
        raise RuntimeError(
            "embedding_provider='fastembed' requires the 'fastembed' package, which is "
            "not installed. Install the embedding extras (apps/api/requirements-embeddings.txt "
            "or apps/worker/requirements-embeddings.txt), or set embedding_provider='deterministic' "
            "to use the lexical fallback."
        ) from exc
    try:
        model = TextEmbedding(model_name=model_name)
    except Exception as exc:
        raise RuntimeError(
            f"Failed to load fastembed model {model_name!r}: {exc}. Verify the model id is "
            "supported by fastembed and that the model files are available (pre-download during "
            "the image build, or allow the first-use fetch)."
        ) from exc
    _MODEL_CACHE[model_name] = model
    return model


class FastEmbedEmbedder:
    """Real fastembed (ONNX) embedder — the Part-2 backend behind the seam.

    ``embed`` returns an L2-normalized ``dim``-length ``list[float]`` (a unit
    vector, so cosine is clean and matches pgvector ``vector_cosine_ops``), or
    ``None`` for empty/whitespace input. A per-call embed failure is caught and
    returned as ``None`` (one bad input never breaks distillation); a model
    load/import failure raises (surfaced by :func:`_load_model`).
    """

    name = "fastembed"
    dim = EMBEDDING_DIM

    def __init__(self, settings=None, model_name: str | None = None) -> None:
        if model_name is None:
            model_name = getattr(settings, "embedding_model", "sentence-transformers/all-MiniLM-L6-v2")
        self.model_name = model_name

    def embed(self, text: str) -> list[float] | None:
        if text is None or not text.strip():
            return None
        model = _load_model(self.model_name)  # raises on load/import failure
        try:
            vectors = list(model.embed([text]))
            vector = vectors[0]
            values = [float(x) for x in vector]
        except Exception:
            # A single bad input must never break distillation — degrade to None.
            return None
        norm = math.sqrt(sum(x * x for x in values))
        if norm == 0.0:
            return None
        return [x / norm for x in values]


__all__ = ["FastEmbedEmbedder"]
