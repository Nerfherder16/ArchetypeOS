"""Tests for the contract-coherence probe (AOS-SELFHEAL-005).

Hermetic: the harvest functions receive the two source strings (a slice of a
Pydantic schemas module and a slice of the frontend api.ts), so no test reads the
real tree. Like the other tool tests, these live under apps/api/tests (CI's pytest
target) with an explicit path bootstrap.

Contract-lag = a frontend TypeScript type thinner than the backend Pydantic schema
it mirrors — the class of gap the system evaluation found by hand.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.coherence_probe import (  # noqa: E402
    ContractLag,
    build_digest,
    digest_payload,
    find_contract_lag,
    has_signal,
    parse_pydantic_read_schemas,
    parse_ts_types,
)


_SCHEMAS = """
class ResearchPlanCreate(BaseModel):
    question: str


class ResearchPlanRead(BaseModel):
    id: str
    question: str
    search_queries: list
    synthesis_policy: dict
    status: str

    model_config = {"from_attributes": True}


class InternalOnlyRead(BaseModel):
    id: str
    secret: str
"""

_FRONTEND = """
export type ResearchPlan = {
  id: string;
  question: string;
  search_queries: string[];
  status: string;
  // note: synthesis_policy dropped here — this is the contract-lag under test
};

export type Unrelated = {
  foo: string;
};
"""


def test_parse_pydantic_read_schemas_only_read_models() -> None:
    schemas = parse_pydantic_read_schemas(_SCHEMAS)
    # Only *Read response schemas are harvested; Create schemas are ignored.
    assert "ResearchPlanCreate" not in schemas
    assert set(schemas) == {"ResearchPlanRead", "InternalOnlyRead"}
    # model_config is not a field.
    assert schemas["ResearchPlanRead"] == ["id", "question", "search_queries", "synthesis_policy", "status"]


def test_parse_ts_types_extracts_field_names() -> None:
    types = parse_ts_types(_FRONTEND)
    assert set(types) == {"ResearchPlan", "Unrelated"}
    assert types["ResearchPlan"] == ["id", "question", "search_queries", "status"]


def test_find_contract_lag_flags_thin_frontend_type() -> None:
    backend = parse_pydantic_read_schemas(_SCHEMAS)
    frontend = parse_ts_types(_FRONTEND)
    lags = find_contract_lag(backend, frontend)
    # ResearchPlan is thinner than ResearchPlanRead (missing synthesis_policy).
    assert len(lags) == 1
    lag = lags[0]
    assert lag.schema == "ResearchPlanRead"
    assert lag.frontend_type == "ResearchPlan"
    assert lag.missing_fields == ["synthesis_policy"]


def test_no_frontend_counterpart_is_not_flagged() -> None:
    # InternalOnlyRead has no frontend `InternalOnly` type → not contract-lag
    # (backend-internal schemas legitimately have no frontend mirror).
    backend = parse_pydantic_read_schemas(_SCHEMAS)
    frontend = parse_ts_types(_FRONTEND)
    lags = find_contract_lag(backend, frontend)
    assert all(lag.schema != "InternalOnlyRead" for lag in lags)


def test_covered_frontend_type_is_not_flagged() -> None:
    backend = {"WidgetRead": ["id", "name"]}
    frontend = {"Widget": ["id", "name", "extra"]}  # superset → covered, no lag
    assert find_contract_lag(backend, frontend) == []


def test_audit_envelope_fields_are_not_contract_lag() -> None:
    # A frontend type omitting only AuditMixin envelope fields is not drift — those
    # are universally-dropped boilerplate, not domain data. Only the domain field
    # (`rationale`) should be flagged.
    backend = {
        "WidgetRead": ["id", "name", "rationale", "status", "version", "created_at", "updated_at"]
    }
    frontend = {"Widget": ["id", "name"]}
    lags = find_contract_lag(backend, frontend)
    assert len(lags) == 1
    assert lags[0].missing_fields == ["rationale"]


def test_has_signal_and_digest_payload() -> None:
    lags = [ContractLag(schema="XRead", frontend_type="X", missing_fields=["a", "b"])]
    assert has_signal(lags) is True
    assert has_signal([]) is False
    payload = digest_payload(lags=lags, day_label="2026-07-09")
    assert payload["probe"] == "coherence"
    assert payload["signal"] is True
    assert payload["contract_lag"][0]["missing_fields"] == ["a", "b"]


def test_build_digest_clean_and_dirty() -> None:
    clean = build_digest(lags=[], day_label="2026-07-09")
    assert "No contract-lag detected" in clean

    lags = [ContractLag(schema="ResearchPlanRead", frontend_type="ResearchPlan", missing_fields=["synthesis_policy"])]
    dirty = build_digest(lags=lags, day_label="2026-07-09")
    assert "ResearchPlan" in dirty
    assert "synthesis_policy" in dirty
    assert "contract-lag" in dirty
