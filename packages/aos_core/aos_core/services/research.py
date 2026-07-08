"""Research Engine — ranked evidence dossiers over a local corpus (RFC-0011 slice-1).

The Research Engine answers the founding intent *"research before implementation;
evidence over opinion"* by gathering engineering evidence for a **question**,
ranking it by **source quality × relevance**, synthesizing a deterministic
**dossier** (summary + findings-cite-source + open questions + calibrated
confidence), and persisting it as a durable :class:`~aos_core.models.ResearchNote`
that the Agent Council can then reason over (closing LES-019 — a structural scan
is the wrong evidence class for an adoption question; a research note is the right
one).

This is the **deterministic floor** (slice-1): the corpus is the local,
DB-native, hermetic knowledge already in the project — repository distillation
pages (``KnowledgePage`` ``page_type="repository"``), prior ``ResearchNote``s, and
recorded ``Decision``s. There is **no network** and **no model**; relevance is the
same calibrated **need-coverage** lexical score the Transfer Engine uses (LES-023 —
never a raw score that reads near-zero for a genuine match), with the 7-rung source
ladder (``docs/RESEARCH_ENGINE.md``) supplying a quality weight that dominates
ties. A ``WebResearchSource`` and reasoned LLM synthesis are deferred slices behind
this same seam.

The provider is still resolved through :func:`~aos_core.services.llm_router.route`
(task class ``"research"``) even though the floor's synthesis is deterministic — so
the **privacy guardrail** (a ``PRIVATE`` question never reaches a free hosted tier)
is exercised now and inherited by slice-3.

Tolerant: an empty corpus / empty question yields a persisted "no evidence found"
note (explicit open question, confidence ``0.0``) and never raises out of
:func:`research`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import Decision, KnowledgePage, ResearchNote
from .llm_router import Sensitivity, route

# --- source ladder ---------------------------------------------------------
# The 7-rung source ladder from docs/RESEARCH_ENGINE.md, each rung mapped to a
# tier_rank (1 = highest authority) and a quality weight in (0, 1]. The quality
# weight is a *boost / tie-break* over the relevance-dominant composite: at equal
# relevance an official-doc source outranks a community post, but a genuinely more
# relevant community post still outranks a barely-relevant official doc. Community
# opinion is explicitly labelled ``"opinion"`` (the Research Engine principle).


@dataclass(frozen=True)
class TierInfo:
    tier_rank: int
    quality: float
    label: str


SOURCE_TIERS: dict[str, TierInfo] = {
    # rung 1: official documentation — highest authority.
    "official-docs": TierInfo(tier_rank=1, quality=1.0, label="documentation"),
    # rung 2: standards and RFCs.
    "standard-rfc": TierInfo(tier_rank=2, quality=0.95, label="standard"),
    # rung 3: maintained reference implementations.
    "reference-implementation": TierInfo(tier_rank=3, quality=0.85, label="reference"),
    # rung 4: benchmarks and papers.
    "benchmark-paper": TierInfo(tier_rank=4, quality=0.78, label="benchmark"),
    # rung 5: security advisories.
    "security-advisory": TierInfo(tier_rank=5, quality=0.72, label="advisory"),
    # rung 6: maintainer discussions.
    "maintainer-discussion": TierInfo(tier_rank=6, quality=0.6, label="maintainer-discussion"),
    # rung 7: community reports and opinions — lowest authority, labelled opinion.
    "community": TierInfo(tier_rank=7, quality=0.4, label="opinion"),
}

# The default rung when a local-corpus kind carries no recorded tier.
_DEFAULT_TIER = "reference-implementation"

# Local-corpus kind → source-ladder rung (documented mapping):
#   * a repository distillation page  → reference-implementation (rung 3) — it is
#     distilled knowledge of a real, maintained codebase.
#   * a prior research note           → its own recorded tier if present, else the
#     reference-implementation default.
#   * a recorded decision             → maintainer-discussion (rung 6) — a decision
#     is the project's own maintainers' recorded reasoning, not an external source.
_KIND_TO_TIER = {
    "repo_distillation": "reference-implementation",
    "research_note": "reference-implementation",
    "decision": "maintainer-discussion",
}


def _tier_for_local(kind: str, recorded_tier: str | None = None) -> str:
    """Map a local-corpus item ``kind`` (with an optional recorded tier) to a rung."""
    if recorded_tier and recorded_tier in SOURCE_TIERS:
        return recorded_tier
    return _KIND_TO_TIER.get(kind, _DEFAULT_TIER)


# --- source document -------------------------------------------------------


@dataclass
class SourceDoc:
    """One candidate evidence source, tier-classified and scorable.

    ``ref`` is the durable citation (vault path / ``research_note:<id>`` /
    ``decision:<id>`` / an external url in later slices); ``text`` is the scorable
    content; ``published`` is an optional freshness marker (a source may carry
    none — the floor never invents a wall-clock timestamp).
    """

    ref: str
    title: str
    text: str
    tier: str = _DEFAULT_TIER
    tier_rank: int = field(default=0)
    label: str = field(default="")
    published: str | None = None

    def __post_init__(self) -> None:
        info = SOURCE_TIERS.get(self.tier, SOURCE_TIERS[_DEFAULT_TIER])
        # tier_rank / label are always derived from the ladder so they cannot drift
        # from the tier key (a caller may leave them at their defaults).
        self.tier_rank = info.tier_rank
        self.label = info.label

    @property
    def quality(self) -> float:
        return SOURCE_TIERS.get(self.tier, SOURCE_TIERS[_DEFAULT_TIER]).quality


# --- research source protocol ---------------------------------------------


@runtime_checkable
class ResearchSource(Protocol):
    """Gathers candidate :class:`SourceDoc`s for a question (network in later slices)."""

    def gather(
        self, db: Session, *, project_id: str, question: str, sensitivity: Sensitivity, limit: int
    ) -> list[SourceDoc]:
        ...


class LocalCorpusSource:
    """The deterministic, hermetic slice-1 source — the project's own DB corpus.

    Gathers repository distillation pages (``KnowledgePage`` ``page_type=
    "repository"``), prior ``ResearchNote``s, and recorded ``Decision``s for the
    project and returns them as tier-classified :class:`SourceDoc`s. No network.
    Tolerant of empty results (returns ``[]``, never raises).
    """

    def gather(
        self, db: Session, *, project_id: str, question: str, sensitivity: Sensitivity, limit: int
    ) -> list[SourceDoc]:
        docs: list[SourceDoc] = []
        try:
            for page in (
                db.query(KnowledgePage)
                .filter(KnowledgePage.project_id == project_id, KnowledgePage.page_type == "repository")
                .order_by(KnowledgePage.updated_at.desc(), KnowledgePage.id)
                .limit(50)
                .all()
            ):
                # KnowledgePage carries no summary column; the scorable text is the
                # page title + the vault path (which encodes the repo/topic).
                text = f"{page.title or ''} {page.vault_path or ''}".strip()
                docs.append(
                    SourceDoc(
                        ref=page.vault_path,
                        title=page.title or page.vault_path,
                        text=text,
                        tier=_tier_for_local("repo_distillation"),
                    )
                )

            for note in (
                db.query(ResearchNote)
                .filter(ResearchNote.project_id == project_id)
                .order_by(ResearchNote.created_at.desc(), ResearchNote.id)
                .limit(50)
                .all()
            ):
                text = f"{note.title or ''} {note.summary or ''} {note.question or ''}".strip()
                docs.append(
                    SourceDoc(
                        ref=f"research_note:{note.id}",
                        title=note.title,
                        text=text,
                        tier=_tier_for_local("research_note"),
                    )
                )

            for decision in (
                db.query(Decision)
                .filter(Decision.project_id == project_id)
                .order_by(Decision.created_at.desc(), Decision.id)
                .limit(50)
                .all()
            ):
                text = f"{decision.title or ''} {decision.decision or ''}".strip()
                docs.append(
                    SourceDoc(
                        ref=f"decision:{decision.id}",
                        title=decision.title,
                        text=text,
                        tier=_tier_for_local("decision"),
                    )
                )
        except Exception:
            # Tolerant: a query failure degrades to whatever was gathered so far.
            return docs
        return docs


# --- scoring ---------------------------------------------------------------
# Reuse the Transfer Engine's calibrated need-coverage discipline (LES-023): the
# tokenizer is identical and relevance is the fraction of the question's meaningful
# terms a source covers — a bounded 0..1 value that reads honestly, never a raw
# Jaccard that collapses to near-zero for a genuine match.

_STOPWORDS: frozenset[str] = frozenset(
    {
        "the", "a", "an", "of", "for", "to", "and", "or", "with", "in", "on",
        "is", "it", "this", "that", "as", "at", "by", "be", "are", "was", "from",
        "but", "not", "can", "will", "would", "should", "into", "than", "then",
        "our", "your", "their", "its", "these", "those", "which", "who", "what",
        "we", "should", "do", "does", "use", "using", "how", "why", "when",
    }
)

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# The quality boost weight: composite = relevance * ((1 - w) + w * quality). At
# w = 0.25 an official doc (quality 1.0) keeps its full relevance while a community
# post (quality 0.4) is scaled to 0.85 of it — enough to break ties toward the
# higher rung without ever dragging a strongly-relevant low-tier source below a
# barely-relevant high-tier one (relevance stays dominant).
_QUALITY_WEIGHT = 0.25


def _tokenize(text: str) -> set[str]:
    """Lowercase, split on non-alphanumeric, drop stopwords + tokens shorter than 3."""
    if not text:
        return set()
    return {tok for tok in _TOKEN_RE.findall(text.lower()) if len(tok) >= 3 and tok not in _STOPWORDS}


def score_source(question_tokens: set[str], source: SourceDoc) -> tuple[float, list[str]]:
    """Need-coverage relevance of ``source`` for a tokenized question.

    ``relevance = |question ∩ source| / |question|`` — the fraction of the
    question's meaningful terms the source covers. Returns
    ``(round(relevance, 4), sorted(matched_terms))``; an empty question yields
    ``(0.0, [])``.
    """
    if not question_tokens:
        return 0.0, []
    covered = question_tokens & _tokenize(source.text)
    relevance = len(covered) / len(question_tokens)
    return round(relevance, 4), sorted(covered)


def _composite(relevance: float, quality: float) -> float:
    """Relevance-dominant blend with the tier quality as a boost / tie-break."""
    return round(relevance * ((1.0 - _QUALITY_WEIGHT) + _QUALITY_WEIGHT * quality), 4)


def _rank(question: str, sources: list[SourceDoc]) -> list[dict]:
    """Score, drop zero-relevance, and rank sources into structured provenance dicts.

    Ordered by composite (quality × relevance) desc, then tier_rank asc (higher
    authority first) and ref (stable). Each entry carries the documented provenance
    ``{ref, title, tier, tier_rank, quality, relevance, matched_terms, label,
    composite}``.
    """
    question_tokens = _tokenize(question)
    ranked: list[dict] = []
    for source in sources:
        relevance, matched_terms = score_source(question_tokens, source)
        if relevance <= 0.0:
            continue
        ranked.append(
            {
                "ref": source.ref,
                "title": source.title,
                "tier": source.tier,
                "tier_rank": source.tier_rank,
                "quality": source.quality,
                "relevance": relevance,
                "matched_terms": matched_terms,
                "label": source.label,
                "composite": _composite(relevance, source.quality),
                "published": source.published,
            }
        )
    ranked.sort(key=lambda e: (-e["composite"], e["tier_rank"], str(e["ref"])))
    return ranked


# --- dossier synthesis -----------------------------------------------------

# Coverage below this on the top source means the dossier flags an open question.
_THIN_COVERAGE = 0.5


def _freshness(ranked: list[dict], as_of: str | None) -> str:
    """Freshest source ``published`` marker, or an as-of-corpus marker (no clock).

    NO wall-clock is read in aos_core: freshness is either the freshest source's
    own ``published`` value or an injected ``as_of`` marker; absent both it is a
    static "local corpus" marker.
    """
    published = sorted((e.get("published") for e in ranked if e.get("published")), reverse=True)
    if published:
        return f"as-of source: {published[0]}"
    if as_of:
        return f"as-of: {as_of}"
    return "as-of: local corpus (no timestamp)"


def synthesize_dossier(question: str, ranked: list[dict], *, as_of: str | None = None, top_n: int = 3) -> dict:
    """Deterministic dossier over the ranked sources.

    Produces ``summary`` (names the top sources), ``findings`` (one
    ``{claim, source_ref, tier, label}`` per top-N source, each citing its
    source), ``open_questions`` (when coverage is thin), ``conflicting_evidence``
    (a lightweight signal — a high-authority source and a community *opinion* both
    address the question), ``confidence`` (calibrated: the top source's composite
    quality × coverage, bounded ``[0, 1]``, never near-zero for a strong match),
    and ``freshness`` (no wall-clock).
    """
    if not ranked:
        return {
            "summary": (
                f"No local evidence found for: {question or '(empty question)'}. "
                "The local corpus (repository distillations, prior research notes, decisions) "
                "did not cover this question."
            ),
            "findings": [],
            "open_questions": [
                f"Gather primary sources (official docs, references, decisions) for: "
                f"{question or '(empty question)'}."
            ],
            "conflicting_evidence": [],
            "confidence": 0.0,
            "freshness": _freshness(ranked, as_of),
        }

    top = ranked[:top_n]
    named = ", ".join(f"{e['title']} [{e['label']}]" for e in top)
    findings = [
        {
            "claim": f"{e['title']} covers {', '.join(e['matched_terms']) or 'the topic'} "
            f"(relevance {e['relevance']}, {e['label']}).",
            "source_ref": e["ref"],
            "tier": e["tier"],
            "label": e["label"],
        }
        for e in top
    ]

    open_questions: list[str] = []
    if ranked[0]["relevance"] < _THIN_COVERAGE or len(ranked) < 2:
        open_questions.append(
            f"Coverage is thin for: {question}; gather additional primary sources before deciding."
        )

    # Conflicting-evidence heuristic (lightweight, documented): a high-authority
    # source (tier_rank <= 3) and a community *opinion* both rank among the top
    # sources for the same question — a stance conflict worth a human's attention.
    conflicting: list[str] = []
    has_authority = any(e["tier_rank"] <= 3 for e in top)
    has_opinion = any(e["label"] == "opinion" for e in top)
    if has_authority and has_opinion:
        conflicting.append(
            "A high-authority source and a community opinion both address this question; "
            "verify the opinion against the authoritative source before relying on it."
        )

    # Confidence: the top source's composite (relevance-dominant, quality-boosted),
    # bounded [0, 1]. A strong match on an authoritative source approaches 1.0; a
    # thin match reads as a correspondingly modest but non-zero value.
    confidence = round(max(0.0, min(1.0, ranked[0]["composite"])), 4)

    summary = f"Top evidence for '{question}': {named}. "
    summary += f"Ranked {len(ranked)} source(s) by source-quality × relevance."
    if open_questions:
        summary += " Open question: " + open_questions[0]
    if conflicting:
        summary += " Conflicting evidence: " + conflicting[0]

    return {
        "summary": summary,
        "findings": findings,
        "open_questions": open_questions,
        "conflicting_evidence": conflicting,
        "confidence": confidence,
        "freshness": _freshness(ranked, as_of),
    }


# --- the engine ------------------------------------------------------------


def _title_for(question: str) -> str:
    q = (question or "").strip()
    if not q:
        return "Research: (no question provided)"
    title = f"Research: {q}"
    return title[:255]


def research(
    db: Session,
    *,
    project_id: str,
    question: str,
    sensitivity: Sensitivity = Sensitivity.PUBLIC,
    source: ResearchSource | None = None,
    limit: int = 8,
    as_of: str | None = None,
) -> ResearchNote:
    """Research ``question`` over ``project_id``'s corpus → a persisted ``ResearchNote``.

    Resolves ``source`` (default :class:`LocalCorpusSource`), gathers candidate
    sources, scores + ranks them by source-quality × relevance (dropping
    zero-relevance), synthesizes a deterministic dossier, and persists a
    :class:`ResearchNote` with the ranked structured ``sources`` + citing
    ``findings`` + calibrated ``confidence`` + ``freshness``. Returns the note.

    The provider is resolved via :func:`route` (task class ``"research"``) so the
    **privacy guardrail is exercised** even though the floor's synthesis is
    deterministic (a ``PRIVATE`` question never routes to a free hosted tier).

    Tolerant: an empty corpus / empty question persists a graceful "no evidence
    found" note (explicit open question, confidence ``0.0``) and never raises.
    """
    # Exercise the routing guardrail (its result is not consumed by the
    # deterministic floor — slice-3's reasoned synthesis will consume it).
    route("research", sensitivity, get_settings())

    src = source if source is not None else LocalCorpusSource()

    try:
        gathered = src.gather(
            db, project_id=project_id, question=question, sensitivity=sensitivity, limit=limit
        )
    except Exception:
        gathered = []

    ranked = _rank(question, gathered)[:limit]
    dossier = synthesize_dossier(question, ranked, as_of=as_of)

    note = ResearchNote(
        project_id=project_id,
        title=_title_for(question),
        question=question,
        summary=dossier["summary"],
        sources=ranked,
        findings=dossier["findings"],
        freshness=dossier["freshness"],
        confidence=dossier["confidence"],
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


__all__ = [
    "SOURCE_TIERS",
    "TierInfo",
    "SourceDoc",
    "ResearchSource",
    "LocalCorpusSource",
    "score_source",
    "synthesize_dossier",
    "research",
]
