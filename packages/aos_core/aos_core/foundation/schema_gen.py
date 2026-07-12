"""Generate JSON Schemas from the Pydantic contract models (design §"JSON Schema").

Pydantic is the single source; JSON Schema is a derived artifact for the
eventual UI/external consumers. ``scripts/gen_foundation_schemas.py`` is the
thin CLI wrapper; a unit test regenerates in-memory and asserts equality with
the checked-in ``schemas/foundation/*.json`` files (the drift guard).
"""
from __future__ import annotations

import json
from pathlib import Path

from . import contracts

# Every contract entity that gets its own generated schema file.
_ENTITIES: dict[str, type] = {
    "Locator": contracts.Locator,
    "EvidenceSource": contracts.EvidenceSource,
    "EvidenceSourceVersion": contracts.EvidenceSourceVersion,
    "EvidenceFragment": contracts.EvidenceFragment,
    "ClaimScope": contracts.ClaimScope,
    "Derivation": contracts.Derivation,
    "Claim": contracts.Claim,
    "ClaimEvidenceLink": contracts.ClaimEvidenceLink,
    "ClaimRelationshipEdge": contracts.ClaimRelationshipEdge,
    "EvidenceConflict": contracts.EvidenceConflict,
    "RepositoryRef": contracts.RepositoryRef,
    "CorpusSnapshot": contracts.CorpusSnapshot,
    "OpenQuestion": contracts.OpenQuestion,
    "Archetype": contracts.Archetype,
    "GenomeSnapshot": contracts.GenomeSnapshot,
    "GenomeTrait": contracts.GenomeTrait,
    "FoundationRequirement": contracts.FoundationRequirement,
    "FoundationCandidate": contracts.FoundationCandidate,
    "FoundationElement": contracts.FoundationElement,
    "CandidateScore": contracts.CandidateScore,
    "ValidationTask": contracts.ValidationTask,
    "FoundationBaseline": contracts.FoundationBaseline,
    "SelectionStageEvent": contracts.SelectionStageEvent,
}


def generate_schemas() -> dict[str, dict]:
    """{EntityName: model_json_schema()} for every contract model."""
    return {name: model_cls.model_json_schema() for name, model_cls in _ENTITIES.items()}


def write_schemas(dest: Path) -> None:
    """Write each schema as ``dest/<EntityName>.json``, sorted keys, indent=2."""
    dest.mkdir(parents=True, exist_ok=True)
    for name, schema in generate_schemas().items():
        out_path = dest / f"{name}.json"
        out_path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
