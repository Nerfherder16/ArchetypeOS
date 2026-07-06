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
**deterministic lexical** score — normalized token overlap (Jaccard) plus a light
technology-match boost. No model, no network — CI-runnable and reproducible
(embeddings are the deferred enhancement behind this same scoring seam).

Tolerant: an empty portfolio / empty need / missing DNA yields ``[]`` and never
raises out of :func:`recommend_reuse`.
"""

from __future__ import annotations

import re

from sqlalchemy.orm import Session

from ..models import KnowledgePage, Repository

_PAGE_TYPE = "repository"

# Technology matches count extra (they are strong reuse signals). The boost is
# additive per matched technology term; the total score is capped at 1.0.
_TECH_BOOST = 0.15

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
    """Deterministic lexical relevance: Jaccard overlap + a technology-match boost.

    ``|need ∩ cand| / |need ∪ cand|`` over the candidate text, plus
    ``_TECH_BOOST * |need ∩ tech|`` (technology matches count extra), capped at 1.0.
    Returns ``(round(score, 4), sorted(matched_terms))`` where ``matched_terms`` is
    ``(need ∩ cand) ∪ (need ∩ tech)`` — the provenance for the recommendation's
    reason. An empty ``need`` yields ``(0.0, [])``.
    """
    if not need_tokens:
        return 0.0, []
    text_overlap = need_tokens & cand_tokens
    union = need_tokens | cand_tokens
    jaccard = len(text_overlap) / len(union) if union else 0.0
    tech_overlap = need_tokens & tech_tokens
    score = min(jaccard + _TECH_BOOST * len(tech_overlap), 1.0)
    matched = text_overlap | tech_overlap
    return round(score, 4), sorted(matched)


def recommend_reuse(
    db: Session, *, need: str, exclude_project_id: str | None = None, limit: int = 5
) -> list[dict]:
    """Rank the portfolio's distilled repos for a target ``need`` (advisory, compute-and-return).

    Tokenizes ``need``; scores every repository :class:`KnowledgePage` against its
    candidate text + technologies; drops zero-score matches and any repo owned by
    ``exclude_project_id``; sorts by score desc (stable tiebreak by source repository
    name); returns the top ``limit``. Each result carries the documented recommendation
    format (source repository / reusable asset / reason / evidence / required changes /
    risks / confidence). Tolerant: empty portfolio / empty need / no matches → ``[]``,
    never raises.
    """
    need_tokens = _tokenize(need or "")
    if not need_tokens:
        return []

    pages = db.query(KnowledgePage).filter(KnowledgePage.page_type == _PAGE_TYPE).all()

    results: list[dict] = []
    for page in pages:
        candidate = _candidate(db, page)
        repo = candidate["repository"]
        if exclude_project_id is not None and repo is not None and repo.project_id == exclude_project_id:
            continue

        score, matched_terms = score_relevance(need_tokens, _tokenize(candidate["text"]), candidate["tech_terms"])
        if score <= 0.0:
            continue

        name = repo.name if repo is not None else page.title
        evidence: list[dict] = [{"type": "distillation", "ref": page.vault_path}]
        if repo is not None:
            evidence.append({"type": "repository", "id": repo.id})

        results.append(
            {
                "source_repository": name,
                "source_project_id": repo.project_id if repo is not None else None,
                "reusable_asset": f"{name} (distilled repository knowledge)",
                "reason": "; ".join(matched_terms) or "portfolio match",
                "matched_terms": matched_terms,
                "evidence": evidence,
                "required_changes": "Review the source distillation and adapt interfaces/config to the target.",
                "risks": "Version/API drift and integration effort not yet quantified (MVP heuristic).",
                "confidence": score,
            }
        )

    results.sort(key=lambda r: (-r["confidence"], str(r["source_repository"])))
    return results[:limit]


__all__ = ["score_relevance", "recommend_reuse"]
