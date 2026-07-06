"""Knowledge Transfer Engine — portfolio reuse recommendations (RFC-0009 MVP).

RFC-0008 answered *"feed a repo → extract what's useful → durable knowledge in
the vault."* This engine answers the other half of the founding intent: given a
**target need**, search the **portfolio** of distilled repository knowledge for
the **relevant, reusable** parts and return ranked, provenance-tagged reuse
recommendations. It is **advisory** (it recommends; a human decides — it feeds
the Decision loop).

The scorable corpus is DB-native and hermetic (the Verified Baseline): the
distilled summary lives in :attr:`RepositoryDNA.purpose`, the technologies in the
DNA (``language_mix`` keys + ``package_managers`` + ``frameworks``), and the
repository :class:`~aos_core.models.KnowledgePage` (``page_type="repository"``)
carries the ``title`` + the ``vault_path`` we cite as evidence. Relevance is a
**deterministic lexical** score — **need coverage**: the fraction of the target
need's meaningful terms the candidate covers (via its text or its technologies).
No model, no network — CI-runnable and reproducible (embeddings are the deferred
enhancement behind this same scoring seam).

Tolerant: an empty portfolio / empty need / missing DNA yields ``[]`` and never
raises out of :func:`recommend_reuse`.
"""

from __future__ import annotations

import re

import sqlalchemy as sa
from sqlalchemy.orm import Session

from ..config import get_settings
from ..embeddings import get_embedder
from ..models import KnowledgePage, Repository

# RFC-0010 confidence calibration. The semantic path blends the calibrated cosine
# similarity ``sem = clamp(1 - cosine_distance, 0, 1)`` with the lexical need
# coverage, and never emits a raw cosine (LES-023). Semantic carries the majority
# weight (it is the richer signal) but the blend is floored at the lexical coverage
# so a strong keyword match is never dragged below its honest coverage:
#     confidence = round(max(coverage, _W_SEM * sem + _W_COV * coverage), 4)
_W_SEM = 0.6
_W_COV = 0.4

_PAGE_TYPE = "repository"

# A small English stopword set — dropped from both the need and each candidate so
# scoring rests on meaningful terms, not connective tissue.
_STOPWORDS: frozenset[str] = frozenset(
    {
        "the", "a", "an", "of", "for", "to", "and", "or", "with", "in", "on",
        "is", "it", "this", "that", "as", "at", "by", "be", "are", "was", "from",
        "but", "not", "can", "will", "would", "should", "into", "than", "then",
        "our", "your", "their", "its", "these", "those", "which", "who", "what",
    }
)

# Split on any run of non-alphanumeric characters (ASCII-lowercased first).
_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> set[str]:
    """Lowercase, split on non-alphanumeric, drop stopwords + tokens shorter than 3."""
    if not text:
        return set()
    return {tok for tok in _TOKEN_RE.findall(text.lower()) if len(tok) >= 3 and tok not in _STOPWORDS}


def _candidate(db: Session, page: KnowledgePage) -> dict:
    """Assemble a repository page's scorable text + technology terms (tolerant).

    Resolves the page's :class:`Repository` via the ``{"type":"repository","id":...}``
    entry in ``source_refs`` (falling back to the first repo of ``page.project_id``),
    loads its :class:`RepositoryDNA`, and returns
    ``{"page", "repository", "text": title + " " + purpose, "tech_terms": {...}}``
    where ``tech_terms`` are the tokenized ``language_mix`` keys + ``package_managers``
    + ``frameworks``. Tolerant of a missing repo / DNA (empty purpose / tech).
    """
    repo: Repository | None = None
    try:
        for ref in page.source_refs or []:
            if isinstance(ref, dict) and ref.get("type") == "repository" and ref.get("id"):
                repo = db.get(Repository, ref["id"])
                if repo is not None:
                    break
        if repo is None and page.project_id is not None:
            repo = (
                db.query(Repository)
                .filter(Repository.project_id == page.project_id)
                .order_by(Repository.created_at.asc())
                .first()
            )
    except Exception:
        repo = None

    dna = repo.dna if repo is not None else None
    purpose = (dna.purpose if dna is not None else None) or ""
    text = f"{page.title or ''} {purpose}".strip()

    tech_terms: set[str] = set()
    if dna is not None:
        terms = (
            list((dna.language_mix or {}).keys())
            + list(dna.package_managers or [])
            + list(dna.frameworks or [])
        )
        for term in terms:
            tech_terms |= _tokenize(str(term))

    return {"page": page, "repository": repo, "text": text, "tech_terms": tech_terms}


def score_relevance(
    need_tokens: set[str], cand_tokens: set[str], tech_tokens: set[str]
) -> tuple[float, list[str]]:
    """Deterministic lexical relevance as **need coverage** — an intuitive, calibrated score.

    The score is the fraction of the target need's meaningful terms that the
    candidate's knowledge covers, via its text **or** its technologies::

        covered = (need ∩ cand) ∪ (need ∩ tech)
        score   = |covered| / |need|

    This answers "how much of what you asked for does this repo cover?" — a bounded
    ``0..1`` value that reads honestly (2 of 3 need terms → ``0.667``), unlike a raw
    Jaccard over the candidate's whole vocabulary (which the distillation reality
    test showed collapses to near-zero magnitudes even for the correct #1 match). A
    technology match counts the same as a text match here; ties are broken in favour
    of more technology hits by :func:`recommend_reuse`. Returns
    ``(round(score, 4), sorted(covered))`` — ``covered`` is the matched-term
    provenance. An empty ``need`` yields ``(0.0, [])``.
    """
    if not need_tokens:
        return 0.0, []
    covered = (need_tokens & cand_tokens) | (need_tokens & tech_tokens)
    score = len(covered) / len(need_tokens)
    return round(score, 4), sorted(covered)


def _recommendation(
    page: KnowledgePage, repo: Repository | None, matched_terms: list[str], tech_hits: int, confidence: float
) -> dict:
    """Assemble the documented recommendation dict (shared by the lexical + semantic paths)."""
    name = repo.name if repo is not None else page.title
    evidence: list[dict] = [{"type": "distillation", "ref": page.vault_path}]
    if repo is not None:
        evidence.append({"type": "repository", "id": repo.id})
    return {
        "source_repository": name,
        "source_project_id": repo.project_id if repo is not None else None,
        "reusable_asset": f"{name} (distilled repository knowledge)",
        "reason": "; ".join(matched_terms) or "portfolio match",
        "matched_terms": matched_terms,
        "evidence": evidence,
        "required_changes": "Review the source distillation and adapt interfaces/config to the target.",
        "risks": "Version/API drift and integration effort not yet quantified (MVP heuristic).",
        "confidence": confidence,
        "_tech_hits": tech_hits,
    }


def _finalize(results: list[dict], limit: int) -> list[dict]:
    """Sort by confidence desc, tech-match count desc, name (stable); strip the transient key; cap."""
    results.sort(key=lambda r: (-r["confidence"], -r["_tech_hits"], str(r["source_repository"])))
    for result in results:
        del result["_tech_hits"]
    return results[:limit]


def _recommend_lexical(
    db: Session, need_tokens: set[str], exclude_project_id: str | None, limit: int
) -> list[dict]:
    """The deterministic Layer-0 lexical path — need coverage over text + technologies.

    This is the pre-RFC-0010 behaviour, unchanged: it runs for the deterministic
    embedder, on sqlite, or whenever no candidate carries a usable embedding.
    """
    pages = db.query(KnowledgePage).filter(KnowledgePage.page_type == _PAGE_TYPE).all()

    results: list[dict] = []
    for page in pages:
        candidate = _candidate(db, page)
        repo = candidate["repository"]
        if exclude_project_id is not None and repo is not None and repo.project_id == exclude_project_id:
            continue

        tech_terms = candidate["tech_terms"]
        score, matched_terms = score_relevance(need_tokens, _tokenize(candidate["text"]), tech_terms)
        if score <= 0.0:
            continue

        tech_hits = len(need_tokens & tech_terms)
        results.append(_recommendation(page, repo, matched_terms, tech_hits, score))

    return _finalize(results, limit)


def _recommend_semantic(
    db: Session, need_tokens: set[str], need_vec: list[float], exclude_project_id: str | None, limit: int
) -> list[dict]:
    """The RFC-0010 semantic path (Postgres + pgvector) — cosine retrieval, calibrated confidence.

    Orders embedding-bearing repository pages by ``embedding <=> need_vec`` (cosine
    distance) and blends the calibrated similarity with the lexical need coverage
    (see ``_W_SEM``/``_W_COV``) so the reported confidence is a bounded ``0..1``
    coverage-like value, never a raw cosine (LES-023); lexical ``matched_terms`` are
    kept as provenance. Candidates without an embedding fall back to their lexical
    coverage. Any DB error degrades to the lexical path (never raises).
    """
    try:
        rows = db.execute(
            sa.select(KnowledgePage.id, KnowledgePage.embedding.cosine_distance(need_vec).label("distance"))
            .where(KnowledgePage.page_type == _PAGE_TYPE, KnowledgePage.embedding.isnot(None))
        ).all()
    except Exception:
        return _recommend_lexical(db, need_tokens, exclude_project_id, limit)
    distances: dict = {row[0]: float(row[1]) for row in rows if row[1] is not None}

    pages = db.query(KnowledgePage).filter(KnowledgePage.page_type == _PAGE_TYPE).all()

    results: list[dict] = []
    for page in pages:
        candidate = _candidate(db, page)
        repo = candidate["repository"]
        if exclude_project_id is not None and repo is not None and repo.project_id == exclude_project_id:
            continue

        tech_terms = candidate["tech_terms"]
        coverage, matched_terms = score_relevance(need_tokens, _tokenize(candidate["text"]), tech_terms)
        tech_hits = len(need_tokens & tech_terms)

        distance = distances.get(page.id)
        if distance is None:
            # No embedding → lexical coverage only (identical to Layer-0 for this repo).
            confidence = coverage
        else:
            sem = max(0.0, min(1.0, 1.0 - distance))
            confidence = round(max(coverage, _W_SEM * sem + _W_COV * coverage), 4)

        if confidence <= 0.0:
            continue
        results.append(_recommendation(page, repo, matched_terms, tech_hits, confidence))

    return _finalize(results, limit)


def recommend_reuse(
    db: Session, *, need: str, exclude_project_id: str | None = None, limit: int = 5, embedder=None
) -> list[dict]:
    """Rank the portfolio's distilled repos for a target ``need`` (advisory, compute-and-return).

    Tokenizes ``need``; scores every repository :class:`KnowledgePage` and returns
    the top ``limit`` documented recommendations (source repository / reusable asset /
    reason / evidence / required changes / risks / confidence). Tolerant: empty
    portfolio / empty need / no matches → ``[]``, never raises.

    Two paths behind one seam (RFC-0010): the **semantic** path is taken only when
    the ``embedder`` returns a non-``None`` vector for ``need`` **and** the DB dialect
    is ``postgresql`` — then candidates are ordered by ``embedding <=> need_vec`` and
    the confidence is a calibrated blend of cosine similarity + lexical coverage
    (never a raw cosine, LES-023). Otherwise — the deterministic embedder, sqlite, or
    an embedder error — it is **exactly today's lexical Layer-0** need-coverage
    behaviour. The return shape/schema is identical for both.
    """
    need_tokens = _tokenize(need or "")
    if not need_tokens:
        return []

    if embedder is None:
        embedder = get_embedder(get_settings())
    try:
        need_vec = embedder.embed(need or "")
    except Exception:
        need_vec = None

    bind = getattr(db, "bind", None)
    dialect = getattr(getattr(bind, "dialect", None), "name", None)
    if need_vec is not None and dialect == "postgresql":
        return _recommend_semantic(db, need_tokens, need_vec, exclude_project_id, limit)
    return _recommend_lexical(db, need_tokens, exclude_project_id, limit)


__all__ = ["score_relevance", "recommend_reuse"]
