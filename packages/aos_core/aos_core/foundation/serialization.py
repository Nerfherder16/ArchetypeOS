"""C4 — canonical serialization and content-hashing spec.

Deterministic, cross-process, language-independent. Each contract model
declares a ``CONTENT_FIELDS`` projection (the substantive fields — what a row
*asserts* — excluding surrogate/volatile fields: ``id``, ``created_at``,
``updated_at``, ``version``, ``status``). ``content_hash`` is stable across two
constructions of the same content and across dict-key insertion order; it
changes iff a content field changes (not when only ``id``/timestamps change).
``set_hash`` is permutation-invariant (sorts member hashes before hashing) —
this is ``claim_set_hash`` (design §5) and the Merkle-style roll-up
``baseline_hash`` (design §14) uses.
"""
from __future__ import annotations

import hashlib
import json
import unicodedata
from collections.abc import Iterable
from datetime import datetime
from enum import Enum

from pydantic import BaseModel

from . import contracts

# Surrogate/volatile fields excluded from every model's content projection —
# they identify or track the row's lifecycle, not what it asserts.
_EXCLUDED_FIELDS: frozenset[str] = frozenset({"id", "created_at", "updated_at", "version", "status"})

_ALL_CONTRACT_MODELS: tuple[type[BaseModel], ...] = (
    contracts.Locator,
    contracts.EvidenceSource,
    contracts.EvidenceSourceVersion,
    contracts.EvidenceFragment,
    contracts.ClaimScope,
    contracts.Derivation,
    contracts.Claim,
    contracts.ClaimEvidenceLink,
    contracts.ClaimRelationshipEdge,
    contracts.EvidenceConflict,
    contracts.RepositoryRef,
    contracts.CorpusSnapshot,
    contracts.OpenQuestion,
    contracts.Archetype,
    contracts.GenomeSnapshot,
    contracts.GenomeTrait,
    contracts.FoundationRequirement,
    contracts.FoundationCandidate,
    contracts.FoundationElement,
    contracts.CandidateScore,
    contracts.ValidationTask,
    contracts.FoundationBaseline,
    contracts.SelectionStageEvent,
)

# Module-level dict: model class -> tuple of substantive (content) field names.
CONTENT_FIELDS: dict[type[BaseModel], tuple[str, ...]] = {
    model_cls: tuple(name for name in model_cls.model_fields if name not in _EXCLUDED_FIELDS)
    for model_cls in _ALL_CONTRACT_MODELS
}


def _encode(value: object) -> object:
    """Recursively project a field value into a plain JSON-able shape.

    Order matters: our enums are ``(str, Enum)`` so ``Enum`` must be checked
    before ``str``; ``bool`` must be checked before ``int`` (bool is an int
    subclass in Python).
    """
    if isinstance(value, BaseModel):
        return _project(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, bool):
        return value
    if isinstance(value, float):
        # Fixed float policy: stable across platforms for confidence/relevance/weight.
        return format(value, ".6g")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, dict):
        return {str(k): _encode(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_encode(v) for v in value]
    return value


def _project(model: BaseModel) -> dict:
    """Project ``model`` to its CONTENT_FIELDS (or all fields if unregistered)."""
    fields = CONTENT_FIELDS.get(type(model))
    if fields is None:
        fields = tuple(model.__class__.model_fields.keys())
    return {name: _encode(getattr(model, name)) for name in fields}


def canonical_bytes(model: BaseModel) -> bytes:
    """The canonical UTF-8 JSON bytes for ``model``'s content projection.

    Keys sorted lexicographically; no insignificant whitespace; arrays
    preserve order (order is significant); strings NFC-normalized.
    """
    obj = _project(model)
    text = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return text.encode("utf-8")


def content_hash(model: BaseModel) -> str:
    """sha256 of ``canonical_bytes(model)``, hex-encoded."""
    return hashlib.sha256(canonical_bytes(model)).hexdigest()


def set_hash(hashes: Iterable[str]) -> str:
    """Permutation-invariant hash over a set of member content hashes.

    sha256 over the SORTED list of ``hashes`` joined by ``"\\n"`` — order of
    the input iterable does not affect the result.
    """
    joined = "\n".join(sorted(hashes))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()
