"""The evidence spine's only write path (RFC-0018, AOS-EVIDENCE-MODELS-001).

Every mutation to the ten evidence tables (``models.py``) goes through this
module. Each function builds the matching RFC-0017 Pydantic contract from the
caller's fields FIRST — so the contract's own C1/C3 validators (``contracts.
Claim._check_c1_and_c3``) run as defense-in-depth — then persists the ORM row,
computing the C4 content hash where the row needs one.

Guards enforced here (RFC-0016 reconciliations, moved from pure functions into
the write path):

- **C3** (:func:`create_claim`): ``foundation.truth.may_mint(minted_by,
  truth_layer)`` must hold, else ``ValueError``. An ``agent`` can never mint an
  ``observed`` claim; only ``deterministic_tool`` can.
- **C1** (:func:`create_claim` / :func:`project_decided_claim`):
  ``create_claim`` refuses ``truth_layer="decided"`` outright — the only path
  to a decided claim is :func:`project_decided_claim`, which loads an
  **approved** ``Decision`` (else a 409 ``HTTPException`` naming the approval
  requirement) and sets ``decision_id``/``derivation.method="approved"``/
  ``minted_by=approval_process``.
- **C4** (every immutable-row insert): ``content_hash`` (or, for
  :class:`~aos_core.models.CorpusSnapshot`, ``claim_set_hash``) is computed via
  ``foundation.serialization`` at insert time. A ``before_update`` guard on the
  ORM models themselves (``models._assert_evidence_content_immutable``)
  refuses any UPDATE that touches a content field — corrections create a new
  row (:func:`add_source_version`) rather than editing one in place.

Design note on ``content_hash`` (resolved ambiguity, see RFC-0018 §Open
questions #1): ``EvidenceSource`` and ``Claim`` have no ``content_hash`` field
on their RFC-0017 contract, so their ORM ``content_hash`` column is a pure C4
audit hash computed here as ``foundation.serialization.content_hash(contract)``.
``EvidenceSourceVersion`` and ``EvidenceFragment`` *do* declare ``content_hash``
on their contract (documented there as "of the source content" — e.g. a file/
blob checksum) — that value is supplied by the caller and stored verbatim;
deriving a second hash from the contract would be self-referential (the
contract's own ``content_hash`` field feeds the hash), so it is not attempted.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..foundation import contracts
from ..foundation.authority import AuthorityDomain
from ..foundation.enums import (
    ClaimType,
    ConflictStatus,
    ConflictType,
    EvidenceRelationship,
    ExtractionMethod,
    ClaimRelationship as ClaimRelationshipEnum,
    DerivationMethod,
    IngestionMethod,
    Materiality,
    Polarity,
    ClaimStatus,
    SourceOrigin,
    SourceStatus,
    SourceType,
    Strength,
    TruthLayer,
)
from ..foundation.serialization import content_hash as compute_content_hash
from ..foundation.serialization import set_hash as compute_set_hash
from ..foundation.truth import MinterClass, may_mint
from ..models import (
    Claim,
    ClaimEvidenceLink,
    ClaimRelationship,
    CorpusSnapshot,
    CorpusSnapshotSource,
    Decision,
    EvidenceConflict,
    EvidenceFragment,
    EvidenceSource,
    EvidenceSourceVersion,
    new_id,
)
from ..sensitivity import Sensitivity

__all__ = [
    "create_source",
    "add_source_version",
    "add_fragment",
    "create_claim",
    "link_evidence",
    "relate_claims",
    "open_conflict",
    "resolve_conflict",
    "freeze_corpus",
    "project_decided_claim",
]


def _coerce(enum_cls, value):
    """Accept either a raw value/string or an already-constructed enum member."""
    return value if isinstance(value, enum_cls) else enum_cls(value)


def create_source(
    db: Session,
    *,
    project_id: str,
    minted_by: MinterClass | str,
    source_type: SourceType | str,
    title: str,
    origin: SourceOrigin | str,
    originator: str,
    canonical_uri: str | None = None,
    sensitivity: Sensitivity | str = Sensitivity.INTERNAL,
    authority_domains: list[AuthorityDomain | str] | None = None,
    access_policy_id: str | None = None,
    status: SourceStatus | str = SourceStatus.ACTIVE,
    created_at: datetime | None = None,
    created_by: str = "system",
) -> EvidenceSource:
    """Create an :class:`~aos_core.models.EvidenceSource` (design §4.2)."""
    contract = contracts.EvidenceSource(
        id=new_id(),
        project_id=project_id,
        source_type=_coerce(SourceType, source_type),
        title=title,
        origin=_coerce(SourceOrigin, origin),
        originator=originator,
        canonical_uri=canonical_uri,
        sensitivity=_coerce(Sensitivity, sensitivity),
        authority_domains=[_coerce(AuthorityDomain, d) for d in (authority_domains or [])],
        access_policy_id=access_policy_id,
        status=_coerce(SourceStatus, status),
        created_at=created_at,
        minted_by=_coerce(MinterClass, minted_by),
    )
    row = EvidenceSource(
        project_id=contract.project_id,
        source_type=contract.source_type.value,
        title=contract.title,
        origin=contract.origin.value,
        originator=contract.originator,
        canonical_uri=contract.canonical_uri,
        sensitivity=contract.sensitivity.value,
        authority_domains=[d.value for d in contract.authority_domains],
        access_policy_id=contract.access_policy_id,
        status=contract.status.value,
        minted_by=contract.minted_by.value,
        created_by=created_by,
        content_hash=compute_content_hash(contract),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def add_source_version(
    db: Session,
    *,
    source_id: str,
    minted_by: MinterClass | str,
    version_ref: str,
    content_hash: str,
    ingestion_method: IngestionMethod | str,
    captured_at: datetime | None = None,
    effective_from: datetime | None = None,
    effective_until: datetime | None = None,
    supersedes_version_id: str | None = None,
    parser_version: str | None = None,
    created_by: str = "system",
) -> EvidenceSourceVersion:
    """Append a new :class:`~aos_core.models.EvidenceSourceVersion` (design §4.3).

    Append-only: a correction is a NEW row (``supersedes_version_id`` points at
    the version it corrects), never an edit of an existing one.
    """
    contract = contracts.EvidenceSourceVersion(
        id=new_id(),
        source_id=source_id,
        version_ref=version_ref,
        content_hash=content_hash,
        captured_at=captured_at,
        effective_from=effective_from,
        effective_until=effective_until,
        supersedes_version_id=supersedes_version_id,
        ingestion_method=_coerce(IngestionMethod, ingestion_method),
        parser_version=parser_version,
        minted_by=_coerce(MinterClass, minted_by),
    )
    row = EvidenceSourceVersion(
        source_id=contract.source_id,
        version_ref=contract.version_ref,
        content_hash=contract.content_hash,
        captured_at=contract.captured_at,
        effective_from=contract.effective_from,
        effective_until=contract.effective_until,
        supersedes_version_id=contract.supersedes_version_id,
        ingestion_method=contract.ingestion_method.value,
        parser_version=contract.parser_version,
        minted_by=contract.minted_by.value,
        created_by=created_by,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def add_fragment(
    db: Session,
    *,
    source_version_id: str,
    minted_by: MinterClass | str,
    content_hash: str,
    excerpt: str,
    extraction_method: ExtractionMethod | str,
    locator: dict | None = None,
    extraction_confidence: float = 0.0,
    created_by: str = "system",
) -> EvidenceFragment:
    """Append a new :class:`~aos_core.models.EvidenceFragment` (design §4.4)."""
    contract = contracts.EvidenceFragment(
        id=new_id(),
        source_version_id=source_version_id,
        locator=contracts.Locator(**(locator or {})),
        content_hash=content_hash,
        excerpt=excerpt,
        extraction_method=_coerce(ExtractionMethod, extraction_method),
        extraction_confidence=extraction_confidence,
        minted_by=_coerce(MinterClass, minted_by),
    )
    row = EvidenceFragment(
        source_version_id=contract.source_version_id,
        locator=contract.locator.model_dump(mode="json"),
        content_hash=contract.content_hash,
        excerpt=contract.excerpt,
        extraction_method=contract.extraction_method.value,
        extraction_confidence=contract.extraction_confidence,
        minted_by=contract.minted_by.value,
        created_by=created_by,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def create_claim(
    db: Session,
    *,
    project_id: str,
    minted_by: MinterClass | str,
    truth_layer: TruthLayer | str,
    statement: str,
    claim_type: ClaimType | str,
    domain: str,
    created_by: str,
    derivation: dict | contracts.Derivation,
    scope: dict | contracts.ClaimScope | None = None,
    polarity: Polarity | str = Polarity.AFFIRMING,
    confidence: float = 1.0,
    materiality: Materiality | str = Materiality.MEDIUM,
    status: ClaimStatus | str = ClaimStatus.ACTIVE,
    valid_from: datetime | None = None,
    valid_until: datetime | None = None,
) -> Claim:
    """Create a :class:`~aos_core.models.Claim` (design §4.5).

    **C3**: raises ``ValueError`` unless ``foundation.truth.may_mint(minted_by,
    truth_layer)`` holds (e.g. an ``agent`` may never mint ``observed``).
    **C1**: refuses ``truth_layer="decided"`` outright — a decided claim is
    minted ONLY by :func:`project_decided_claim`, from an approved ``Decision``.
    """
    minted_by_enum = _coerce(MinterClass, minted_by)
    truth_layer_enum = _coerce(TruthLayer, truth_layer)

    if truth_layer_enum == TruthLayer.DECIDED:
        raise ValueError(
            "C1 violation: create_claim refuses truth_layer='decided'; a decided claim is "
            "minted only by project_decided_claim, from an approved Decision."
        )
    if not may_mint(minted_by_enum, truth_layer_enum):
        raise ValueError(
            f"C3 violation: {minted_by_enum.value!r} may not mint a {truth_layer_enum.value!r} claim"
        )

    scope_obj = scope if isinstance(scope, contracts.ClaimScope) else contracts.ClaimScope(**(scope or {}))
    derivation_obj = (
        derivation if isinstance(derivation, contracts.Derivation) else contracts.Derivation(**derivation)
    )

    contract = contracts.Claim(
        id=new_id(),
        project_id=project_id,
        statement=statement,
        claim_type=_coerce(ClaimType, claim_type),
        truth_layer=truth_layer_enum,
        domain=domain,
        scope=scope_obj,
        polarity=_coerce(Polarity, polarity),
        confidence=confidence,
        materiality=_coerce(Materiality, materiality),
        status=_coerce(ClaimStatus, status),
        valid_from=valid_from,
        valid_until=valid_until,
        created_by=created_by,
        derivation=derivation_obj,
        minted_by=minted_by_enum,
        decision_ref=None,
    )
    row = _claim_row_from_contract(contract, decision_id=None)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _claim_row_from_contract(contract: contracts.Claim, *, decision_id: str | None) -> Claim:
    return Claim(
        project_id=contract.project_id,
        statement=contract.statement,
        claim_type=contract.claim_type.value,
        truth_layer=contract.truth_layer.value,
        domain=contract.domain,
        scope=contract.scope.model_dump(mode="json"),
        polarity=contract.polarity.value,
        confidence=contract.confidence,
        materiality=contract.materiality.value,
        status=contract.status.value,
        valid_from=contract.valid_from,
        valid_until=contract.valid_until,
        created_by=contract.created_by,
        derivation=contract.derivation.model_dump(mode="json"),
        minted_by=contract.minted_by.value,
        decision_id=decision_id,
        content_hash=compute_content_hash(contract),
    )


def link_evidence(
    db: Session,
    *,
    claim_id: str,
    fragment_id: str,
    minted_by: MinterClass | str,
    relationship: EvidenceRelationship | str,
    relevance: float = 1.0,
    strength: Strength | str = Strength.MODERATE,
    notes: str | None = None,
    created_by: str = "system",
) -> ClaimEvidenceLink:
    """Create a :class:`~aos_core.models.ClaimEvidenceLink` (design §4.6)."""
    contract = contracts.ClaimEvidenceLink(
        claim_id=claim_id,
        fragment_id=fragment_id,
        relationship=_coerce(EvidenceRelationship, relationship),
        relevance=relevance,
        strength=_coerce(Strength, strength),
        notes=notes,
        minted_by=_coerce(MinterClass, minted_by),
    )
    row = ClaimEvidenceLink(
        claim_id=contract.claim_id,
        fragment_id=contract.fragment_id,
        relationship=contract.relationship.value,
        relevance=contract.relevance,
        strength=contract.strength.value,
        notes=contract.notes,
        minted_by=contract.minted_by.value,
        created_by=created_by,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def relate_claims(
    db: Session,
    *,
    from_claim_id: str,
    to_claim_id: str,
    minted_by: MinterClass | str,
    relationship: ClaimRelationshipEnum | str,
    notes: str | None = None,
    created_by: str = "system",
) -> ClaimRelationship:
    """Create a :class:`~aos_core.models.ClaimRelationship` edge (design §4.8)."""
    contract = contracts.ClaimRelationshipEdge(
        from_claim_id=from_claim_id,
        to_claim_id=to_claim_id,
        relationship=_coerce(ClaimRelationshipEnum, relationship),
        notes=notes,
        minted_by=_coerce(MinterClass, minted_by),
    )
    row = ClaimRelationship(
        from_claim_id=contract.from_claim_id,
        to_claim_id=contract.to_claim_id,
        relationship=contract.relationship.value,
        notes=contract.notes,
        minted_by=contract.minted_by.value,
        created_by=created_by,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def open_conflict(
    db: Session,
    *,
    project_id: str,
    claim_ids: list[str],
    minted_by: MinterClass | str,
    conflict_type: ConflictType | str,
    materiality: Materiality | str,
    blocking_stages: list[str] | None = None,
    created_by: str = "system",
) -> EvidenceConflict:
    """Open an :class:`~aos_core.models.EvidenceConflict` (design §4.9), status ``open``.

    Stays visible (``status="open"``) until an explicit later resolution
    transition sets ``status="resolved"``/``resolution``/
    ``resolution_decision_id`` — no route in this package resolves it.
    """
    contract = contracts.EvidenceConflict(
        id=new_id(),
        project_id=project_id,
        claim_ids=list(claim_ids),
        conflict_type=_coerce(ConflictType, conflict_type),
        materiality=_coerce(Materiality, materiality),
        status=ConflictStatus.OPEN,
        resolution=None,
        resolution_decision_id=None,
        blocking_stages=list(blocking_stages or []),
        minted_by=_coerce(MinterClass, minted_by),
    )
    row = EvidenceConflict(
        project_id=contract.project_id,
        claim_ids=list(contract.claim_ids),
        conflict_type=contract.conflict_type.value,
        materiality=contract.materiality.value,
        status=contract.status.value,
        blocking_stages=list(contract.blocking_stages),
        minted_by=contract.minted_by.value,
        created_by=created_by,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def resolve_conflict(
    db: Session,
    *,
    conflict_id: str,
    status: ConflictStatus | str,
    resolution: str,
    resolution_decision_id: str | None = None,
) -> EvidenceConflict:
    """Transition an open :class:`~aos_core.models.EvidenceConflict` to a resolution (AOS-EVIDENCE-API-001).

    ``status``/``resolution``/``resolution_decision_id`` are annotation
    fields, not content — ``EvidenceConflict`` has no entry in
    ``models._EVIDENCE_IMMUTABLE_CONTENT_FIELDS`` (RFC-0018 leaves conflicts
    un-hashed/un-guarded), so this UPDATE is permitted by the C4 guard.
    404s a missing conflict; raises ``ValueError`` for any status other than
    ``resolved``/``accepted_exception`` (only those two are a resolution).
    """
    conflict = db.get(EvidenceConflict, conflict_id)
    if not conflict:
        raise HTTPException(status_code=404, detail="Evidence conflict not found")

    status_enum = _coerce(ConflictStatus, status)
    if status_enum not in (ConflictStatus.RESOLVED, ConflictStatus.ACCEPTED_EXCEPTION):
        raise ValueError(
            f"resolve_conflict: status must be 'resolved' or 'accepted_exception', got {status_enum.value!r}"
        )

    conflict.status = status_enum.value
    conflict.resolution = resolution
    if resolution_decision_id is not None:
        conflict.resolution_decision_id = resolution_decision_id
    db.commit()
    db.refresh(conflict)
    return conflict


def freeze_corpus(
    db: Session,
    *,
    project_id: str,
    source_version_ids: list[str],
    purpose: str,
    repository_refs: list[dict] | None = None,
    created_by: str = "system",
) -> CorpusSnapshot:
    """Freeze a :class:`~aos_core.models.CorpusSnapshot` (design §5).

    ``claim_set_hash`` is ``set_hash`` over the ``content_hash`` of every claim
    currently recorded for ``project_id`` — permutation-invariant (sorted
    before hashing), so it is independent of ``source_version_ids`` order.
    Also records the normalized membership rows
    (:class:`~aos_core.models.CorpusSnapshotSource`).
    """
    member_claims = (
        db.query(Claim)
        .filter(Claim.project_id == project_id, Claim.content_hash.isnot(None))
        .all()
    )
    claim_set_hash = compute_set_hash([c.content_hash for c in member_claims]) if member_claims else None

    contract = contracts.CorpusSnapshot(
        id=new_id(),
        project_id=project_id,
        source_version_ids=list(source_version_ids),
        repository_refs=[contracts.RepositoryRef(**ref) for ref in (repository_refs or [])],
        claim_set_hash=claim_set_hash,
        created_at=None,
        created_by=created_by,
        purpose=purpose,
    )
    row = CorpusSnapshot(
        project_id=contract.project_id,
        source_version_ids=list(contract.source_version_ids),
        repository_refs=[r.model_dump(mode="json") for r in contract.repository_refs],
        claim_set_hash=contract.claim_set_hash,
        created_by=contract.created_by,
        purpose=contract.purpose,
    )
    db.add(row)
    db.flush()  # need row.id to attach membership rows before commit

    for source_version_id in source_version_ids:
        db.add(
            CorpusSnapshotSource(
                snapshot_id=row.id, source_version_id=source_version_id, created_by=created_by
            )
        )

    db.commit()
    db.refresh(row)
    return row


def project_decided_claim(db: Session, *, decision_id: str, created_by: str = "system") -> Claim:
    """**C1**: the ONLY minter of a ``truth_layer="decided"`` claim.

    Loads ``decision_id``; 404s if missing. Raises a 409 ``HTTPException``
    naming the approval requirement unless ``decision.status == "approved"``.
    On success, creates a ``Claim`` with ``truth_layer="decided"``,
    ``derivation={"method": "approved", "parent_claim_ids": []}``,
    ``minted_by=MinterClass.APPROVAL_PROCESS``, and ``decision_id`` set —
    mirroring ``services.decisions.approve_decision``'s status gate.
    """
    decision = db.get(Decision, decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    if decision.status != "approved":
        raise HTTPException(
            status_code=409,
            detail=(
                f"Decision in status '{decision.status}' is not approved; only an approved "
                "Decision may be projected into a decided claim (C1)."
            ),
        )

    contract = contracts.Claim(
        id=new_id(),
        project_id=decision.project_id,
        statement=decision.decision or decision.title,
        claim_type=ClaimType.DECISION_CANDIDATE,
        truth_layer=TruthLayer.DECIDED,
        domain="decision",
        scope=contracts.ClaimScope(),
        polarity=Polarity.AFFIRMING,
        confidence=decision.confidence or 1.0,
        materiality=Materiality.HIGH,
        status=ClaimStatus.ACTIVE,
        created_by=decision.approved_by or created_by,
        derivation=contracts.Derivation(method=DerivationMethod.APPROVED, parent_claim_ids=[]),
        minted_by=MinterClass.APPROVAL_PROCESS,
        decision_ref=decision.id,
    )
    row = _claim_row_from_contract(contract, decision_id=decision.id)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
