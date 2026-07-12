"""Project EXISTING evidence into the RFC-0018 claim model (AOS-EVIDENCE-BACKFILL-001).

A deterministic, idempotent, re-runnable adapter over the C5 reconciliation:
it reads the platform's pre-Evidence-Spine rows (``RepositoryDNA``, ``Decision``,
``Recommendation``, ``Evaluation``, ``Risk``, ``ResearchRun``) and projects each
one into ``EvidenceSource`` -> ``EvidenceSourceVersion`` -> ``EvidenceFragment``
-> ``Claim`` through ``services/evidence.py`` — the evidence spine's ONLY write
path. This module never constructs an ``EvidenceSource``/``EvidenceSourceVersion``/
``EvidenceFragment``/``Claim`` ORM row directly; every insert is delegated so the
C1/C3/C4 guards there stay load-bearing.

**C3 mapping (the load-bearing constraint).** Backfill is a deterministic
projection, so every claim here mints as ``MinterClass.DETERMINISTIC_TOOL``.
Per ``foundation.truth._ALLOWED``, that minter may ONLY produce ``observed`` or
``inferred`` claims — never ``claimed`` (human/agent) and never ``decided``
directly (``create_claim`` refuses ``decided`` outright, C1). The mapping used:

- **observed** (measured/inspected fact): ``RepositoryDNA`` scan facts
  (languages/package_managers/frameworks/runtime_services) and an
  ``Evaluation``'s numeric ``score``.
- **inferred** (derived/analytical content): ``Recommendation`` rationale,
  ``ResearchRun`` findings, ``Risk`` items, an ``Evaluation``'s qualitative
  ``findings``, and a non-approved ``Decision`` (claim_type=decision_candidate).
- **decided**: only reachable via :func:`~aos_core.services.evidence.
  project_decided_claim`, called here for an APPROVED ``Decision`` — that path
  mints ``minted_by=approval_process`` (C1), never ``deterministic_tool``.

**Idempotency.** Sources are deduped by ``(project_id, canonical_uri)`` where
``canonical_uri`` encodes the origin row's table + id (e.g.
``backfill://repository_dna/<uuid>``) — a stable, content-independent tag
equivalent to tagging ``EvidenceSource.meta`` with the origin row, without a
second UPDATE after create. Versions are deduped by ``(source_id, version_ref)``
using the origin row id as ``version_ref``. Fragments are deduped by
``(source_version_id, content_hash)`` where ``content_hash`` is a sha256 over
the canonical JSON of the fragment's payload. Claims are deduped by predicting
the RFC-0017 ``contracts.Claim`` content hash BEFORE minting (mirroring exactly
what ``create_claim``/``project_decided_claim`` will themselves hash) and
skipping if a ``Claim`` with that ``(project_id, content_hash)`` already
exists — this also means a second :func:`backfill_project` run never calls
``link_evidence`` again for a claim that already exists (its unique
``(claim_id, fragment_id, relationship)`` constraint would otherwise raise on
a repeat insert).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy.orm import Session

from ..foundation import contracts
from ..foundation.enums import (
    ClaimType,
    DerivationMethod,
    EvidenceRelationship,
    ExtractionMethod,
    IngestionMethod,
    Materiality,
    SourceOrigin,
    SourceType,
    TruthLayer,
)
from ..foundation.serialization import content_hash as compute_content_hash
from ..foundation.truth import MinterClass, may_mint
from ..models import (
    Claim,
    Decision,
    Evaluation,
    EvidenceFragment,
    EvidenceSource,
    EvidenceSourceVersion,
    Recommendation,
    Repository,
    RepositoryDNA,
    ResearchRun,
    Risk,
    new_id,
)
from .evidence import add_fragment, add_source_version, create_claim, create_source, link_evidence, project_decided_claim

__all__ = [
    "backfill_repository_dna",
    "backfill_decision",
    "backfill_recommendation",
    "backfill_evaluation",
    "backfill_risk",
    "backfill_research_run",
    "backfill_project",
]

_CREATED_BY = "evidence_backfill"
_ORIGINATOR = "aos_core.evidence_backfill"

# The link relationship used for every backfill-created claim<->fragment edge.
# These are direct, 1:1 mechanical projections of the origin row's content into
# a claim, not corroborating third-party evidence, so "originates" (design
# §4.6) fits better than "supports" — a resolved ambiguity (see report).
_LINK_RELATIONSHIP = EvidenceRelationship.ORIGINATES

_SEVERITY_MATERIALITY: dict[str, Materiality] = {
    "critical": Materiality.CRITICAL,
    "high": Materiality.HIGH,
    "medium": Materiality.MEDIUM,
    "moderate": Materiality.MEDIUM,
    "low": Materiality.LOW,
    "informational": Materiality.INFORMATIONAL,
    "info": Materiality.INFORMATIONAL,
}


# ---------------------------------------------------------------------------
# Counting helpers
# ---------------------------------------------------------------------------


def _new_counts() -> dict[str, int]:
    return {
        "sources_created": 0,
        "sources_skipped": 0,
        "versions_created": 0,
        "versions_skipped": 0,
        "fragments_created": 0,
        "fragments_skipped": 0,
        "claims_created": 0,
        "claims_skipped": 0,
    }


def _tally(counts: dict[str, int], key: str, created: bool) -> None:
    counts[f"{key}_created" if created else f"{key}_skipped"] += 1


def _merge(target: dict[str, int], other: dict[str, int]) -> None:
    for k, v in other.items():
        target[k] = target.get(k, 0) + v


# ---------------------------------------------------------------------------
# Content helpers
# ---------------------------------------------------------------------------


def _checksum(payload: Any) -> str:
    """A stable sha256 over a canonical JSON projection of ``payload``."""
    blob = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _canonical_uri(kind: str, row_id: str) -> str:
    return f"backfill://{kind}/{row_id}"


def _stringify_list(items: list) -> str:
    parts = []
    for item in items:
        if isinstance(item, dict):
            parts.append(str(item.get("name") or item.get("title") or item.get("finding") or item))
        else:
            parts.append(str(item))
    return ", ".join(parts) if parts else "(none)"


def _severity_to_materiality(severity: str | None) -> Materiality:
    if not severity:
        return Materiality.MEDIUM
    return _SEVERITY_MATERIALITY.get(severity.strip().lower(), Materiality.MEDIUM)


# ---------------------------------------------------------------------------
# Source / version / fragment: get-or-create (idempotent)
# ---------------------------------------------------------------------------


def _get_or_create_source(
    db: Session,
    *,
    project_id: str,
    kind: str,
    row_id: str,
    title: str,
    source_type: SourceType,
    origin: SourceOrigin,
) -> tuple[EvidenceSource, bool]:
    uri = _canonical_uri(kind, row_id)
    existing = (
        db.query(EvidenceSource)
        .filter(EvidenceSource.project_id == project_id, EvidenceSource.canonical_uri == uri)
        .one_or_none()
    )
    if existing:
        return existing, False
    source = create_source(
        db,
        project_id=project_id,
        minted_by=MinterClass.DETERMINISTIC_TOOL,
        source_type=source_type,
        title=title,
        origin=origin,
        originator=_ORIGINATOR,
        canonical_uri=uri,
        created_by=_CREATED_BY,
    )
    return source, True


def _get_or_create_version(
    db: Session, *, source_id: str, row_id: str, payload: Any
) -> tuple[EvidenceSourceVersion, bool]:
    version_ref = str(row_id)
    existing = (
        db.query(EvidenceSourceVersion)
        .filter(EvidenceSourceVersion.source_id == source_id, EvidenceSourceVersion.version_ref == version_ref)
        .one_or_none()
    )
    if existing:
        return existing, False
    version = add_source_version(
        db,
        source_id=source_id,
        minted_by=MinterClass.DETERMINISTIC_TOOL,
        version_ref=version_ref,
        content_hash=_checksum(payload),
        ingestion_method=IngestionMethod.GENERATED,
        created_by=_CREATED_BY,
    )
    return version, True


def _get_or_create_fragment(
    db: Session, *, source_version_id: str, payload: Any, excerpt: str
) -> tuple[EvidenceFragment, bool]:
    fragment_hash = _checksum(payload)
    existing = (
        db.query(EvidenceFragment)
        .filter(
            EvidenceFragment.source_version_id == source_version_id,
            EvidenceFragment.content_hash == fragment_hash,
        )
        .one_or_none()
    )
    if existing:
        return existing, False
    fragment = add_fragment(
        db,
        source_version_id=source_version_id,
        minted_by=MinterClass.DETERMINISTIC_TOOL,
        content_hash=fragment_hash,
        excerpt=excerpt,
        extraction_method=ExtractionMethod.DETERMINISTIC,
        extraction_confidence=1.0,
        created_by=_CREATED_BY,
    )
    return fragment, True


# ---------------------------------------------------------------------------
# Claim: get-or-create (idempotent, C3-checked)
# ---------------------------------------------------------------------------


def _create_claim_and_link(
    db: Session,
    *,
    project_id: str,
    fragment_id: str,
    minted_by: MinterClass,
    truth_layer: TruthLayer,
    statement: str,
    claim_type: ClaimType,
    domain: str,
    derivation: contracts.Derivation,
    confidence: float = 1.0,
    materiality: Materiality = Materiality.MEDIUM,
) -> tuple[Claim, bool]:
    """Create ONE claim + its evidence link, unless an equal-content claim exists.

    C3 is asserted here (in addition to ``create_claim``'s own guard) so a
    mis-mapped call site fails loudly before touching the database.
    """
    if not may_mint(minted_by, truth_layer):
        raise ValueError(
            f"C3 violation: evidence_backfill attempted {minted_by.value!r} minting "
            f"{truth_layer.value!r}"
        )

    # Predict the content hash create_claim will compute, using the SAME
    # defaults (scope/polarity/status) it uses, so the prediction matches
    # exactly what gets persisted.
    prospective = contracts.Claim(
        id=new_id(),
        project_id=project_id,
        statement=statement,
        claim_type=claim_type,
        truth_layer=truth_layer,
        domain=domain,
        confidence=confidence,
        materiality=materiality,
        created_by=_CREATED_BY,
        derivation=derivation,
        minted_by=minted_by,
    )
    prospective_hash = compute_content_hash(prospective)

    existing = (
        db.query(Claim)
        .filter(Claim.project_id == project_id, Claim.content_hash == prospective_hash)
        .one_or_none()
    )
    if existing:
        return existing, False

    claim = create_claim(
        db,
        project_id=project_id,
        minted_by=minted_by,
        truth_layer=truth_layer,
        statement=statement,
        claim_type=claim_type,
        domain=domain,
        created_by=_CREATED_BY,
        derivation=derivation,
        confidence=confidence,
        materiality=materiality,
    )
    link_evidence(
        db,
        claim_id=claim.id,
        fragment_id=fragment_id,
        minted_by=MinterClass.DETERMINISTIC_TOOL,
        relationship=_LINK_RELATIONSHIP,
        created_by=_CREATED_BY,
    )
    return claim, True


def _predict_decided_claim_hash(decision: Decision) -> str:
    """Mirror ``services.evidence.project_decided_claim``'s contract construction exactly."""
    prospective = contracts.Claim(
        id=new_id(),
        project_id=decision.project_id,
        statement=decision.decision or decision.title,
        claim_type=ClaimType.DECISION_CANDIDATE,
        truth_layer=TruthLayer.DECIDED,
        domain="decision",
        confidence=decision.confidence or 1.0,
        materiality=Materiality.HIGH,
        created_by=decision.approved_by or "system",
        derivation=contracts.Derivation(method=DerivationMethod.APPROVED, parent_claim_ids=[]),
        minted_by=MinterClass.APPROVAL_PROCESS,
        decision_ref=decision.id,
    )
    return compute_content_hash(prospective)


# ---------------------------------------------------------------------------
# Per-source backfill helpers
# ---------------------------------------------------------------------------


def backfill_repository_dna(db: Session, dna: RepositoryDNA) -> dict[str, int]:
    """Project a scanned ``RepositoryDNA`` row into ``observed`` FACT claims.

    One ``EvidenceSource``/``EvidenceSourceVersion`` for the DNA row, then one
    ``EvidenceFragment`` + one claim per non-empty detected-fact category
    (languages, package_managers, frameworks, runtime_services).
    """
    repository = dna.repository
    project_id = repository.project_id
    counts = _new_counts()

    source, s_created = _get_or_create_source(
        db,
        project_id=project_id,
        kind="repository_dna",
        row_id=dna.id,
        title=f"Repository DNA: {repository.name}",
        source_type=SourceType.REPOSITORY,
        origin=SourceOrigin.LOCAL_FILESYSTEM,
    )
    _tally(counts, "sources", s_created)

    version_payload = {
        "language_mix": dna.language_mix,
        "package_managers": dna.package_managers,
        "frameworks": dna.frameworks,
        "runtime_services": dna.runtime_services,
        "deployment_files": dna.deployment_files,
        "risk_flags": dna.risk_flags,
        "scan_summary": dna.scan_summary,
        "confidence": dna.confidence,
    }
    version, v_created = _get_or_create_version(db, source_id=source.id, row_id=dna.id, payload=version_payload)
    _tally(counts, "versions", v_created)

    categories = [
        ("languages", list((dna.language_mix or {}).keys()), "repository.languages"),
        ("package_managers", dna.package_managers or [], "repository.package_managers"),
        ("frameworks", dna.frameworks or [], "repository.frameworks"),
        ("runtime_services", dna.runtime_services or [], "repository.runtime_services"),
    ]
    for label, items, domain in categories:
        if not items:
            continue
        fragment_payload = {"category": label, "items": items}
        excerpt = json.dumps(fragment_payload, sort_keys=True, default=str)
        fragment, f_created = _get_or_create_fragment(
            db, source_version_id=version.id, payload=fragment_payload, excerpt=excerpt
        )
        _tally(counts, "fragments", f_created)

        statement = f"{repository.name}: detected {label.replace('_', ' ')} — {_stringify_list(items)}"
        _, c_created = _create_claim_and_link(
            db,
            project_id=project_id,
            fragment_id=fragment.id,
            minted_by=MinterClass.DETERMINISTIC_TOOL,
            truth_layer=TruthLayer.OBSERVED,
            statement=statement,
            claim_type=ClaimType.FACT,
            domain=domain,
            derivation=contracts.Derivation(method=DerivationMethod.DIRECT, parent_claim_ids=[]),
            confidence=dna.confidence or 1.0,
            materiality=Materiality.MEDIUM,
        )
        _tally(counts, "claims", c_created)

    return counts


def backfill_decision(db: Session, decision: Decision) -> dict[str, int]:
    """Project a ``Decision`` row.

    APPROVED -> a ``decided`` claim via :func:`~aos_core.services.evidence.
    project_decided_claim` (C1 path, ``minted_by=approval_process``). Any
    other status -> an ``inferred`` ``decision_candidate`` claim,
    ``minted_by=deterministic_tool`` (never ``decided`` directly — C1/C3).
    """
    counts = _new_counts()

    source, s_created = _get_or_create_source(
        db,
        project_id=decision.project_id,
        kind="decision",
        row_id=decision.id,
        title=f"Decision: {decision.title}",
        source_type=SourceType.DOCUMENT,
        origin=SourceOrigin.GENERATED,
    )
    _tally(counts, "sources", s_created)

    payload = {
        "title": decision.title,
        "context": decision.context,
        "decision": decision.decision,
        "alternatives": decision.alternatives,
        "tradeoffs": decision.tradeoffs,
        "consequences": decision.consequences,
        "evidence": decision.evidence,
        "confidence": decision.confidence,
        "status": decision.status,
    }
    version, v_created = _get_or_create_version(db, source_id=source.id, row_id=decision.id, payload=payload)
    _tally(counts, "versions", v_created)

    fragment, f_created = _get_or_create_fragment(
        db, source_version_id=version.id, payload=payload, excerpt=json.dumps(payload, sort_keys=True, default=str)
    )
    _tally(counts, "fragments", f_created)

    if decision.status == "approved":
        prospective_hash = _predict_decided_claim_hash(decision)
        existing = (
            db.query(Claim)
            .filter(Claim.project_id == decision.project_id, Claim.content_hash == prospective_hash)
            .one_or_none()
        )
        if existing:
            counts["claims_skipped"] += 1
        else:
            claim = project_decided_claim(db, decision_id=decision.id)
            link_evidence(
                db,
                claim_id=claim.id,
                fragment_id=fragment.id,
                minted_by=MinterClass.DETERMINISTIC_TOOL,
                relationship=_LINK_RELATIONSHIP,
                created_by=_CREATED_BY,
            )
            counts["claims_created"] += 1
    else:
        statement = decision.decision or decision.title
        _, c_created = _create_claim_and_link(
            db,
            project_id=decision.project_id,
            fragment_id=fragment.id,
            minted_by=MinterClass.DETERMINISTIC_TOOL,
            truth_layer=TruthLayer.INFERRED,
            statement=statement,
            claim_type=ClaimType.DECISION_CANDIDATE,
            domain="decision",
            derivation=contracts.Derivation(method=DerivationMethod.INFERRED, parent_claim_ids=[]),
            confidence=decision.confidence or 0.5,
            materiality=Materiality.HIGH,
        )
        _tally(counts, "claims", c_created)

    return counts


def backfill_recommendation(db: Session, recommendation: Recommendation) -> dict[str, int]:
    """Project a ``Recommendation`` row into one ``inferred`` FINDING claim."""
    counts = _new_counts()

    source, s_created = _get_or_create_source(
        db,
        project_id=recommendation.project_id,
        kind="recommendation",
        row_id=recommendation.id,
        title=f"Recommendation: {recommendation.title}",
        source_type=SourceType.DOCUMENT,
        origin=SourceOrigin.GENERATED,
    )
    _tally(counts, "sources", s_created)

    payload = {
        "title": recommendation.title,
        "recommendation": recommendation.recommendation,
        "rationale": recommendation.rationale,
        "alternatives": recommendation.alternatives,
        "pros": recommendation.pros,
        "cons": recommendation.cons,
        "risk": recommendation.risk,
        "effort": recommendation.effort,
        "dependencies": recommendation.dependencies,
        "acceptance_criteria": recommendation.acceptance_criteria,
        "evidence": recommendation.evidence,
        "confidence": recommendation.confidence,
    }
    version, v_created = _get_or_create_version(
        db, source_id=source.id, row_id=recommendation.id, payload=payload
    )
    _tally(counts, "versions", v_created)

    fragment, f_created = _get_or_create_fragment(
        db, source_version_id=version.id, payload=payload, excerpt=json.dumps(payload, sort_keys=True, default=str)
    )
    _tally(counts, "fragments", f_created)

    statement = recommendation.recommendation or recommendation.title
    if recommendation.rationale:
        statement = f"{statement} — rationale: {recommendation.rationale}"

    _, c_created = _create_claim_and_link(
        db,
        project_id=recommendation.project_id,
        fragment_id=fragment.id,
        minted_by=MinterClass.DETERMINISTIC_TOOL,
        truth_layer=TruthLayer.INFERRED,
        statement=statement,
        claim_type=ClaimType.FINDING,
        domain="recommendation",
        derivation=contracts.Derivation(method=DerivationMethod.INFERRED, parent_claim_ids=[]),
        confidence=recommendation.confidence or 0.5,
        materiality=Materiality.MEDIUM,
    )
    _tally(counts, "claims", c_created)

    return counts


def backfill_evaluation(db: Session, evaluation: Evaluation) -> dict[str, int]:
    """Project an ``Evaluation`` row.

    A numeric ``score`` -> ``observed`` FACT (a measured result). Qualitative
    ``findings`` -> ``inferred`` FINDING (an analytical judgment).
    """
    counts = _new_counts()

    source, s_created = _get_or_create_source(
        db,
        project_id=evaluation.project_id,
        kind="evaluation",
        row_id=evaluation.id,
        title=f"Evaluation: {evaluation.evaluation_type}",
        source_type=SourceType.TEST_RUN,
        origin=SourceOrigin.GENERATED,
    )
    _tally(counts, "sources", s_created)

    payload = {
        "evaluation_type": evaluation.evaluation_type,
        "score": evaluation.score,
        "findings": evaluation.findings,
        "evidence": evaluation.evidence,
    }
    version, v_created = _get_or_create_version(db, source_id=source.id, row_id=evaluation.id, payload=payload)
    _tally(counts, "versions", v_created)

    if evaluation.score is not None:
        score_payload = {"evaluation_type": evaluation.evaluation_type, "score": evaluation.score}
        fragment, f_created = _get_or_create_fragment(
            db,
            source_version_id=version.id,
            payload=score_payload,
            excerpt=json.dumps(score_payload, sort_keys=True, default=str),
        )
        _tally(counts, "fragments", f_created)

        statement = f"Evaluation '{evaluation.evaluation_type}' measured score {evaluation.score}"
        _, c_created = _create_claim_and_link(
            db,
            project_id=evaluation.project_id,
            fragment_id=fragment.id,
            minted_by=MinterClass.DETERMINISTIC_TOOL,
            truth_layer=TruthLayer.OBSERVED,
            statement=statement,
            claim_type=ClaimType.FACT,
            domain="evaluation.score",
            derivation=contracts.Derivation(method=DerivationMethod.DIRECT, parent_claim_ids=[]),
            confidence=1.0,
            materiality=Materiality.MEDIUM,
        )
        _tally(counts, "claims", c_created)

    if evaluation.findings:
        findings_payload = {"evaluation_type": evaluation.evaluation_type, "findings": evaluation.findings}
        fragment, f_created = _get_or_create_fragment(
            db,
            source_version_id=version.id,
            payload=findings_payload,
            excerpt=json.dumps(findings_payload, sort_keys=True, default=str),
        )
        _tally(counts, "fragments", f_created)

        statement = f"Evaluation '{evaluation.evaluation_type}' findings: {_stringify_list(evaluation.findings)}"
        _, c_created = _create_claim_and_link(
            db,
            project_id=evaluation.project_id,
            fragment_id=fragment.id,
            minted_by=MinterClass.DETERMINISTIC_TOOL,
            truth_layer=TruthLayer.INFERRED,
            statement=statement,
            claim_type=ClaimType.FINDING,
            domain="evaluation.findings",
            derivation=contracts.Derivation(method=DerivationMethod.INFERRED, parent_claim_ids=[]),
            confidence=1.0,
            materiality=Materiality.MEDIUM,
        )
        _tally(counts, "claims", c_created)

    return counts


def backfill_risk(db: Session, risk: Risk) -> dict[str, int]:
    """Project a ``Risk`` row into one ``inferred`` RISK claim."""
    counts = _new_counts()

    source, s_created = _get_or_create_source(
        db,
        project_id=risk.project_id,
        kind="risk",
        row_id=risk.id,
        title=f"Risk: {risk.title}",
        source_type=SourceType.DOCUMENT,
        origin=SourceOrigin.GENERATED,
    )
    _tally(counts, "sources", s_created)

    payload = {
        "title": risk.title,
        "description": risk.description,
        "severity": risk.severity,
        "likelihood": risk.likelihood,
        "mitigation": risk.mitigation,
        "evidence": risk.evidence,
        "owner": risk.owner,
    }
    version, v_created = _get_or_create_version(db, source_id=source.id, row_id=risk.id, payload=payload)
    _tally(counts, "versions", v_created)

    fragment, f_created = _get_or_create_fragment(
        db, source_version_id=version.id, payload=payload, excerpt=json.dumps(payload, sort_keys=True, default=str)
    )
    _tally(counts, "fragments", f_created)

    statement = f"Risk '{risk.title}'"
    details = [d for d in (f"severity={risk.severity}" if risk.severity else None,
                           f"likelihood={risk.likelihood}" if risk.likelihood else None) if d]
    if details:
        statement = f"{statement} ({', '.join(details)})"
    if risk.description:
        statement = f"{statement}: {risk.description}"

    _, c_created = _create_claim_and_link(
        db,
        project_id=risk.project_id,
        fragment_id=fragment.id,
        minted_by=MinterClass.DETERMINISTIC_TOOL,
        truth_layer=TruthLayer.INFERRED,
        statement=statement,
        claim_type=ClaimType.RISK,
        domain="risk",
        derivation=contracts.Derivation(method=DerivationMethod.INFERRED, parent_claim_ids=[]),
        confidence=1.0,
        materiality=_severity_to_materiality(risk.severity),
    )
    _tally(counts, "claims", c_created)

    return counts


def backfill_research_run(db: Session, run: ResearchRun) -> dict[str, int]:
    """Project a ``ResearchRun`` row's findings into ``inferred`` FINDING claim(s)."""
    counts = _new_counts()

    source, s_created = _get_or_create_source(
        db,
        project_id=run.project_id,
        kind="research_run",
        row_id=run.id,
        title=f"Research run {run.id}",
        source_type=SourceType.EXTERNAL_REFERENCE,
        origin=SourceOrigin.GENERATED,
    )
    _tally(counts, "sources", s_created)

    payload = {
        "plan_id": run.plan_id,
        "run_status": run.run_status,
        "phases": run.phases,
        "sources": run.sources,
        "findings": run.findings,
        "conflicts": run.conflicts,
        "open_questions": run.open_questions,
        "confidence": run.confidence,
    }
    version, v_created = _get_or_create_version(db, source_id=source.id, row_id=run.id, payload=payload)
    _tally(counts, "versions", v_created)

    if run.findings:
        findings_payload = {"findings": run.findings}
        fragment, f_created = _get_or_create_fragment(
            db,
            source_version_id=version.id,
            payload=findings_payload,
            excerpt=json.dumps(findings_payload, sort_keys=True, default=str),
        )
        _tally(counts, "fragments", f_created)

        statement = f"Research run findings: {_stringify_list(run.findings)}"
        _, c_created = _create_claim_and_link(
            db,
            project_id=run.project_id,
            fragment_id=fragment.id,
            minted_by=MinterClass.DETERMINISTIC_TOOL,
            truth_layer=TruthLayer.INFERRED,
            statement=statement,
            claim_type=ClaimType.FINDING,
            domain="research.findings",
            derivation=contracts.Derivation(method=DerivationMethod.INFERRED, parent_claim_ids=[]),
            confidence=run.confidence or 0.5,
            materiality=Materiality.MEDIUM,
        )
        _tally(counts, "claims", c_created)

    return counts


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------


def backfill_project(db: Session, project_id: str) -> dict[str, dict[str, int]]:
    """Backfill every existing evidence-bearing row for ``project_id``.

    Returns per-source-type created/skipped counts plus a ``totals`` roll-up.
    Deterministic and safe to re-run: a second call on an unchanged project
    creates zero new rows (every count lands in ``*_skipped``).
    """
    totals: dict[str, dict[str, int]] = {
        "repository_dna": _new_counts(),
        "decision": _new_counts(),
        "recommendation": _new_counts(),
        "evaluation": _new_counts(),
        "risk": _new_counts(),
        "research_run": _new_counts(),
    }

    repo_ids = [row.id for row in db.query(Repository.id).filter(Repository.project_id == project_id).all()]
    if repo_ids:
        for dna in db.query(RepositoryDNA).filter(RepositoryDNA.repository_id.in_(repo_ids)).all():
            _merge(totals["repository_dna"], backfill_repository_dna(db, dna))

    for decision in db.query(Decision).filter(Decision.project_id == project_id).all():
        _merge(totals["decision"], backfill_decision(db, decision))

    for recommendation in db.query(Recommendation).filter(Recommendation.project_id == project_id).all():
        _merge(totals["recommendation"], backfill_recommendation(db, recommendation))

    for evaluation in db.query(Evaluation).filter(Evaluation.project_id == project_id).all():
        _merge(totals["evaluation"], backfill_evaluation(db, evaluation))

    for risk in db.query(Risk).filter(Risk.project_id == project_id).all():
        _merge(totals["risk"], backfill_risk(db, risk))

    for run in db.query(ResearchRun).filter(ResearchRun.project_id == project_id).all():
        _merge(totals["research_run"], backfill_research_run(db, run))

    grand_total = _new_counts()
    for per_type in totals.values():
        _merge(grand_total, per_type)
    totals["totals"] = grand_total

    return totals
