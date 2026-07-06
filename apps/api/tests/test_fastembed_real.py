"""Real-fastembed embedder tests (RFC-0010 / AOS-EMBED-002).

Gated by ``@pytest.mark.embedder`` and skipped unless ``fastembed`` is importable
(the "Embedder tests" CI job installs ``requirements-embeddings.txt`` — fastembed,
NO torch). Unlike the hermetic ``test_embeddings.py`` (which mocks fastembed), this
loads the actual ``all-MiniLM-L6-v2`` ONNX model and asserts genuine semantic
behaviour: a real 384-length unit vector, and paraphrases closer than unrelated text.

This is the affordable real-embedder gate torch could never have paid for.
"""

from __future__ import annotations

import math

import pytest

from aos_core.config import EMBEDDING_DIM, Settings

pytestmark = pytest.mark.embedder

fastembed = pytest.importorskip("fastembed", reason="fastembed not installed (real embedder tier)")


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


def _embedder():
    from aos_core.embeddings import get_embedder

    return get_embedder(Settings(embedding_provider="fastembed"))


def test_real_embed_returns_384_unit_vector() -> None:
    emb = _embedder()
    vec = emb.embed("A library for routing HTTP requests in a web service.")
    assert vec is not None
    assert len(vec) == EMBEDDING_DIM == 384
    assert all(isinstance(x, float) for x in vec)
    # L2-normalized by the embedder → unit length.
    assert math.sqrt(sum(x * x for x in vec)) == pytest.approx(1.0, abs=1e-4)
    # Empty/whitespace still degrades to None with the real model.
    assert emb.embed("   ") is None


def test_real_paraphrases_closer_than_unrelated() -> None:
    emb = _embedder()

    a = emb.embed("How do I deploy containers across a cluster of machines?")
    a_paraphrase = emb.embed("Scheduling and orchestrating containers over many servers.")
    unrelated = emb.embed("A recipe for baking chocolate chip cookies.")

    assert a is not None and a_paraphrase is not None and unrelated is not None

    sim_paraphrase = _cosine(a, a_paraphrase)
    sim_unrelated = _cosine(a, unrelated)

    assert sim_paraphrase > sim_unrelated, (
        f"paraphrase cosine {sim_paraphrase:.3f} should exceed unrelated {sim_unrelated:.3f}"
    )
