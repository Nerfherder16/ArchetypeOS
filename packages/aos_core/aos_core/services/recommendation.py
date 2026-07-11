"""Technology Fitness + Recommendation generator (RFC-0015 Wave C, AOS-RECO-ENGINE-001).

Closes the compare → recommend seam (AOS-REVIEW-003 seam #4): ``Recommendation``
was hand-written CRUD (``routes/decisions.py``) that nothing generated. This
module turns it into a real generator, driven by a deterministic **Technology
Fitness** pass over rows already in the DB — no provider/LLM/network call, no
per-technology opinion beyond a small documented table (Article VIII: verify,
don't infer; Article XII: never manufacture confidence).

``score_fitness(dna)`` emits fitness signals for one :class:`RepositoryDNA`
row: each ``risk_flag`` is scored against :data:`RISK_FLAG_RULES` (a small,
documented substring table matched against the flag text — the same style
``services/digest.py`` already uses for ``"test" in flag.lower()``); anything
that doesn't match a rule gets the documented default
(:data:`DEFAULT_RISK_SCORE` / :data:`DEFAULT_RISK_SEVERITY`) rather than a
fabricated severity. Each ``framework`` / ``runtime_service`` gets a single
constant neutral-to-positive presence score
(:data:`FRAMEWORK_PRESENCE_SCORE` / :data:`RUNTIME_SERVICE_PRESENCE_SCORE`) —
deliberately uniform, not a per-technology opinion table, because this codebase
has no evidence to justify rating one framework above another.

``generate_recommendations(db, project_id=...)`` reads the project's
:class:`RepositoryDNA` (same join as ``services.council._project_dna``) and its
latest research, and derives draft :class:`~aos_core.models.Recommendation`
rows:

- every risk-flag fitness signal → a remediation recommendation
  (``evidence=[{"type": "repository_dna", "id": dna.id}]``);
- every research finding whose claim names an adoption choice (matches
  :data:`ADOPTION_KEYWORDS`) → an adoption recommendation
  (``evidence=[{"type": "research_note", "id": note.id}]``).

``confidence`` is :func:`_combine_confidence` — an equal-weighted, clamped
combination of the driving fitness/baseline signal score and the source row's
own recorded ``confidence``. Every row is draft/advisory (``approved_by`` stays
``None``; ``AuditMixin.status`` stays at its default). **Idempotent**: each
candidate's ``meta["reco_signature"]`` is a stable hash of ``(kind, subject)``;
a signature already present on an existing recommendation for the project is
skipped rather than duplicated, so re-running is a no-op after the first pass.
"""

from __future__ import annotations

import hashlib

from sqlalchemy.orm import Session

from ..models import Recommendation, ResearchNote
from .council import _project_dna

_TITLE_MAX = 255

# --- Technology Fitness: risk-flag severity table --------------------------
# Small and documented on purpose (Article XII): these are the risk-flag
# messages the deterministic repository scanner actually emits today
# (repository_scanner.py — MISSING_TESTS, NO_CI_CONFIG,
# DOCKER_WITHOUT_ENV_TEMPLATE, SCAN_TRUNCATED), matched by a case-insensitive
# substring against the flag text (mirrors services/digest.py's existing
# `"test" in flag.lower()` pattern). Each entry is
# (substring, score, severity, rationale). Checked in order; first match wins.
# A flag that matches none of these (including free-text flags seeded outside
# the scanner, e.g. by a test or a future signal source) gets the documented
# default below rather than an invented severity.
RISK_FLAG_RULES: tuple[tuple[str, float, str, str], ...] = (
    (
        "no test",
        0.25,
        "high",
        "Missing automated test coverage is a high-severity maintainability risk.",
    ),
    (
        "missing test",
        0.25,
        "high",
        "Missing automated test coverage is a high-severity maintainability risk.",
    ),
    (
        "no ci",
        0.35,
        "medium",
        "No CI configuration means changes reach the default branch unverified.",
    ),
    (
        ".env",
        0.45,
        "medium",
        "Docker files without an .env template risk undocumented configuration drift.",
    ),
    (
        "truncated",
        0.6,
        "low",
        "The scan that produced this flag was truncated; this is an incomplete-coverage "
        "signal, not a confirmed code defect.",
    ),
)
DEFAULT_RISK_SCORE = 0.5
DEFAULT_RISK_SEVERITY = "medium"
DEFAULT_RISK_RATIONALE = (
    "Unrecognized risk-flag text; scored at the documented moderate default pending "
    "manual triage rather than an invented severity."
)

# Presence of a declared framework/runtime service is a neutral-to-positive
# fitness signal (it is in active use, which is not itself a risk) — but this
# codebase has no evidence basis to rate one technology above another, so
# every framework/runtime_service gets the SAME documented constant rather
# than a fabricated per-technology opinion (Article XII).
FRAMEWORK_PRESENCE_SCORE = 0.65
RUNTIME_SERVICE_PRESENCE_SCORE = 0.6

# A research finding that names an adoption choice gets this documented
# baseline signal score (used the same way a DNA risk-flag's table score is
# used) when combined with the research note's own recorded confidence.
# Deliberately the same order of magnitude as FRAMEWORK_PRESENCE_SCORE: an
# adoption suggestion is, absent more, a neutral-to-positive signal too.
RESEARCH_ADOPTION_SIGNAL_SCORE = 0.6

# Small, documented keyword list for detecting that a research finding names
# an adoption choice, rather than merely describing or comparing evidence.
# Deliberately narrow: only findings using these verbs are treated as
# recommending something, so we never fabricate an opinion the finding text
# doesn't already state.
ADOPTION_KEYWORDS: tuple[str, ...] = (
    "adopt",
    "recommend",
    "migrate to",
    "switch to",
    "should use",
    "prefer",
)


def _classify_risk_flag(flag: str) -> tuple[float, str, str]:
    """Return (score, severity, rationale) for one risk-flag string."""
    lowered = flag.lower()
    for substring, score, severity, rationale in RISK_FLAG_RULES:
        if substring in lowered:
            return score, severity, rationale
    return DEFAULT_RISK_SCORE, DEFAULT_RISK_SEVERITY, DEFAULT_RISK_RATIONALE


def score_fitness(dna) -> list[dict]:
    """Deterministic Technology Fitness signals for one ``RepositoryDNA`` row.

    Emits one signal per non-empty ``risk_flags`` entry (``signal="risk_flag"``,
    scored via :data:`RISK_FLAG_RULES` / the documented default), plus one per
    ``frameworks`` entry (``signal="framework_present"``) and one per
    ``runtime_services`` entry (``signal="runtime_service_present"``), each at
    the documented constant presence score. No randomness, no wall-clock, no
    model call: the same DNA row always yields the same signal list.
    """
    signals: list[dict] = []

    for flag in dna.risk_flags or []:
        if not isinstance(flag, str) or not flag.strip():
            continue
        flag = flag.strip()
        score, severity, rationale = _classify_risk_flag(flag)
        signals.append(
            {
                "subject": flag,
                "signal": "risk_flag",
                "score": score,
                "severity": severity,
                "evidence": [{"type": "repository_dna", "id": dna.id, "detail": rationale}],
            }
        )

    for framework in dna.frameworks or []:
        if not isinstance(framework, str) or not framework.strip():
            continue
        signals.append(
            {
                "subject": framework.strip(),
                "signal": "framework_present",
                "score": FRAMEWORK_PRESENCE_SCORE,
                "severity": "info",
                "evidence": [{"type": "repository_dna", "id": dna.id}],
            }
        )

    for service in dna.runtime_services or []:
        if not isinstance(service, str) or not service.strip():
            continue
        signals.append(
            {
                "subject": service.strip(),
                "signal": "runtime_service_present",
                "score": RUNTIME_SERVICE_PRESENCE_SCORE,
                "severity": "info",
                "evidence": [{"type": "repository_dna", "id": dna.id}],
            }
        )

    return signals


def _combine_confidence(signal_score: float, source_confidence: float | None) -> float:
    """Documented confidence formula: equal-weighted average of the driving
    fitness/baseline signal score and the source row's own recorded
    confidence, clamped to [0, 1]. Never invents a confidence beyond what the
    two inputs already support (Article XII).
    """
    combined = 0.5 * signal_score + 0.5 * (source_confidence or 0.0)
    return round(max(0.0, min(1.0, combined)), 4)


def _signature(kind: str, subject: str) -> str:
    """Stable hash of (kind, subject) for the idempotency dedup key."""
    return hashlib.sha256(f"{kind}::{subject}".encode("utf-8")).hexdigest()


def _truncate(text: str, limit: int = _TITLE_MAX) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _names_adoption_choice(claim: str) -> bool:
    lowered = claim.lower()
    return any(keyword in lowered for keyword in ADOPTION_KEYWORDS)


def _existing_signatures(db: Session, project_id: str) -> set[str]:
    signatures: set[str] = set()
    for reco in db.query(Recommendation).filter(Recommendation.project_id == project_id).all():
        meta = reco.meta or {}
        signature = meta.get("reco_signature")
        if signature:
            signatures.add(signature)
    return signatures


def generate_recommendations(db: Session, *, project_id: str) -> list[Recommendation]:
    """Generate draft :class:`Recommendation` rows for a project.

    Reads the project's :class:`~aos_core.models.RepositoryDNA` (same join as
    ``services.council._project_dna``) and its latest 10
    :class:`~aos_core.models.ResearchNote` rows. Every DNA risk-flag fitness
    signal (via :func:`score_fitness`) becomes a remediation recommendation;
    every research finding whose claim names an adoption choice becomes an
    adoption recommendation. All rows are draft/advisory (``approved_by``
    stays ``None``). **Idempotent** via ``meta["reco_signature"]`` — a
    candidate whose signature already exists for this project is skipped, so
    re-running never duplicates. Returns only the rows newly created by this
    call (``[]`` for an empty/no-evidence project — never an error).
    """
    dna_rows = _project_dna(db, project_id)
    notes = (
        db.query(ResearchNote)
        .filter(ResearchNote.project_id == project_id)
        .order_by(ResearchNote.created_at.desc(), ResearchNote.id)
        .limit(10)
        .all()
    )

    seen_signatures = _existing_signatures(db, project_id)
    created: list[Recommendation] = []

    for dna in dna_rows:
        for signal in score_fitness(dna):
            if signal["signal"] != "risk_flag":
                continue
            flag = signal["subject"]
            signature = _signature("risk_remediation", flag)
            if signature in seen_signatures:
                continue
            confidence = _combine_confidence(signal["score"], dna.confidence)
            reco = Recommendation(
                project_id=project_id,
                title=_truncate(f"Remediate: {flag}"),
                recommendation=f"Address the repository risk flagged by scan: {flag}",
                rationale=(
                    f"{signal['evidence'][0]['detail']} (severity={signal['severity']}, "
                    f"fitness_score={signal['score']}, dna_confidence={dna.confidence})."
                ),
                risk=flag,
                evidence=[{"type": "repository_dna", "id": dna.id}],
                confidence=confidence,
                meta={"reco_signature": signature, "kind": "risk_remediation", "subject": flag},
            )
            db.add(reco)
            created.append(reco)
            seen_signatures.add(signature)

    for note in notes:
        for finding in note.findings or []:
            if isinstance(finding, dict):
                claim = str(finding.get("claim") or finding.get("option") or "").strip()
            elif isinstance(finding, str):
                claim = finding.strip()
            else:
                continue
            if not claim or not _names_adoption_choice(claim):
                continue
            signature = _signature("research_adoption", claim)
            if signature in seen_signatures:
                continue
            confidence = _combine_confidence(RESEARCH_ADOPTION_SIGNAL_SCORE, note.confidence)
            reco = Recommendation(
                project_id=project_id,
                title=_truncate(f"Consider: {claim}"),
                recommendation=claim,
                rationale=f"Cited by research note '{note.title}' (source confidence={note.confidence}).",
                evidence=[{"type": "research_note", "id": note.id}],
                confidence=confidence,
                meta={"reco_signature": signature, "kind": "research_adoption", "subject": claim},
            )
            db.add(reco)
            created.append(reco)
            seen_signatures.add(signature)

    if created:
        db.commit()
        for reco in created:
            db.refresh(reco)
    return created


__all__ = [
    "RISK_FLAG_RULES",
    "DEFAULT_RISK_SCORE",
    "DEFAULT_RISK_SEVERITY",
    "FRAMEWORK_PRESENCE_SCORE",
    "RUNTIME_SERVICE_PRESENCE_SCORE",
    "RESEARCH_ADOPTION_SIGNAL_SCORE",
    "ADOPTION_KEYWORDS",
    "score_fitness",
    "generate_recommendations",
]
