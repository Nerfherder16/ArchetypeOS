"""AOS-COUNCIL-TYPED-001 (RFC-0016 §11): typed council finding/evidence/concern
payloads.

The per-agent evidence selectors already build typed items ``{kind, detail,
ref}``; this closes the seam so that typed shape survives selector -> provider
-> ``_parse_agent_output`` -> storage instead of being flattened to a plain
string. Backward compatible both directions: a plain string is coerced to a
typed item on write, and every reader tolerates either shape.
"""

from __future__ import annotations

import json
import types

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from aos_core.database import Base
from aos_core.llm import DeterministicProvider
from aos_core.models import (
    ArchitectureNode,
    CouncilAgentOutput,
    Decision,
    Project,
    Repository,
    RepositoryDNA,
    ResearchNote,
)
from aos_core.services.council import (
    _coerce_finding_item,
    _item_text,
    _parse_agent_output,
    run_council,
    synthesize_verdict,
)
from aos_core.services.decisions import draft_decision_from_review


def _db(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'typed.db'}",
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    return session_local()


def _seed_project(db, *, risk_flags: list[str]) -> str:
    """A project with evidence for every persona (mirrors test_council.py's
    ``_seed_rich_project``) so every agent's findings are non-empty."""
    project = Project(name="Typed", slug="typed")
    db.add(project)
    db.flush()
    repo = Repository(project_id=project.id, name="svc", local_path="svc")
    db.add(repo)
    db.flush()
    db.add(
        RepositoryDNA(
            repository_id=repo.id,
            language_mix={"python": 0.9, "toml": 0.1},
            frameworks=["fastapi", "sqlalchemy"],
            package_managers=["pip"],
            runtime_services=["postgres"],
            risk_flags=risk_flags,
            maturity="beta",
        )
    )
    db.add(
        ArchitectureNode(project_id=project.id, repository_id=repo.id, label="svc", type="repository", confidence=0.9)
    )
    db.add(Decision(project_id=project.id, title="Adopt FastAPI for the service API"))
    db.add(ResearchNote(project_id=project.id, title="Framework landscape survey"))
    db.commit()
    return project.id


# --- write path: deterministic provider persists typed items ---------------


def test_deterministic_run_persists_typed_findings(tmp_path):
    db = _db(tmp_path)
    try:
        project_id = _seed_project(db, risk_flags=["missing tests for the auth module"])
        review = run_council(
            db, project_id=project_id, question="Ship it?", provider=DeterministicProvider()
        )
        outputs = db.query(CouncilAgentOutput).filter(CouncilAgentOutput.review_id == review.id).all()
        assert outputs
        for output in outputs:
            assert output.findings, output
            for item in output.findings:
                assert isinstance(item, dict)
                assert set(item) == {"kind", "detail", "ref"}
                assert isinstance(item["kind"], str) and item["kind"]
                assert isinstance(item["detail"], str)
            for item in output.evidence:
                assert isinstance(item, dict)
                assert set(item) == {"kind", "detail", "ref"}
        # The security agent's risk-flag concern is a typed item, not a string.
        security = next(o for o in outputs if o.agent_name == "security_agent")
        assert security.concerns
        assert all(isinstance(c, dict) for c in security.concerns)
        assert any("missing tests" in c["detail"] for c in security.concerns)
    finally:
        db.close()


# --- write path: string-coercion fallback -----------------------------------


def test_parse_agent_output_coerces_plain_strings_to_typed_items():
    raw = json.dumps(
        {
            "summary": "s",
            "findings": ["plain string finding"],
            "evidence": ["plain string evidence"],
            "concerns": ["plain string concern"],
            "confidence": 0.6,
            "status": "Complete",
        }
    )
    out = _parse_agent_output(raw)
    assert out["findings"] == [{"kind": "finding", "detail": "plain string finding", "ref": None}]
    assert out["evidence"] == [{"kind": "evidence", "detail": "plain string evidence", "ref": None}]
    assert out["concerns"] == [{"kind": "concern", "detail": "plain string concern", "ref": None}]


def test_parse_agent_output_mixed_shapes_never_crashes():
    """A real-model agent that mixes typed items and plain strings in one list."""
    raw = json.dumps(
        {
            "summary": "s",
            "findings": [
                {"kind": "structural", "detail": "no circuit breaker", "ref": "node:1"},
                "a bare string finding",
                {"detail": "typed without explicit kind"},
            ],
            "evidence": [],
            "concerns": [],
            "confidence": 0.5,
            "status": "Complete",
        }
    )
    out = _parse_agent_output(raw)
    assert out["findings"] == [
        {"kind": "structural", "detail": "no circuit breaker", "ref": "node:1"},
        {"kind": "finding", "detail": "a bare string finding", "ref": None},
        {"kind": "finding", "detail": "typed without explicit kind", "ref": None},
    ]


class _LegacyStringFake:
    """A fake real-model provider that ignores the typed contract entirely."""

    name = "legacy_fake"

    def generate(self, *, system, prompt, max_tokens=1024, response_format=None):
        text = json.dumps(
            {
                "summary": "assessed",
                "findings": ["legacy finding"],
                "evidence": ["legacy evidence"],
                "concerns": [],
                "confidence": 0.7,
                "status": "Complete",
            }
        )
        return types.SimpleNamespace(text=text, provider="legacy_fake", model="legacy-model", finish_reason="stop")


def test_run_council_coerces_old_shape_agent_output(tmp_path):
    db = _db(tmp_path)
    try:
        project_id = _seed_project(db, risk_flags=[])
        review = run_council(db, project_id=project_id, question="Q?", provider=_LegacyStringFake())
        outputs = db.query(CouncilAgentOutput).filter(CouncilAgentOutput.review_id == review.id).all()
        assert outputs
        for output in outputs:
            assert output.findings == [{"kind": "finding", "detail": "legacy finding", "ref": None}]
            assert output.evidence == [{"kind": "evidence", "detail": "legacy evidence", "ref": None}]
    finally:
        db.close()


# --- read path: synthesize_verdict tolerates both shapes -------------------


def test_synthesize_verdict_over_typed_findings_and_concerns():
    outputs = [
        CouncilAgentOutput(
            agent_name="a",
            agent_type="t",
            status="Complete",
            summary="",
            findings=[{"kind": "finding", "detail": "unsupported claim", "ref": None}],
            evidence=[],
            concerns=[{"kind": "concern", "detail": "needs review", "ref": "node:1"}],
            confidence=0.8,
        ),
        CouncilAgentOutput(
            agent_name="b",
            agent_type="t",
            status="Complete",
            summary="",
            findings=[{"kind": "finding", "detail": "ok", "ref": None}],
            evidence=[{"kind": "evidence", "detail": "e", "ref": None}],
            concerns=[],
            confidence=0.8,
        ),
    ]
    result = synthesize_verdict(outputs)
    # unsupported_claims: agent "a" offered a finding with no evidence — the
    # typed item is preserved (not flattened) in the claim.
    assert {"agent": "a", "claim": {"kind": "finding", "detail": "unsupported claim", "ref": None}} in (
        result["unsupported_claims"]
    )
    # follow_up text is built from the concern's readable detail, not a dict repr.
    assert any("needs review" in entry for entry in result["follow_up"])
    assert not any("{'kind'" in entry for entry in result["follow_up"])


def test_synthesize_verdict_over_legacy_string_findings_still_works():
    """Old-shape (plain string) findings/concerns must not crash the Final Judge."""
    outputs = [
        CouncilAgentOutput(
            agent_name="a",
            agent_type="t",
            status="Complete",
            summary="",
            findings=["legacy unsupported claim"],
            evidence=[],
            concerns=["legacy concern"],
            confidence=0.8,
        ),
    ]
    result = synthesize_verdict(outputs)
    assert result["unsupported_claims"] == [{"agent": "a", "claim": "legacy unsupported claim"}]
    assert any("legacy concern" in entry for entry in result["follow_up"])


def test_item_text_and_coerce_helpers_tolerate_both_shapes():
    assert _item_text({"kind": "finding", "detail": "x", "ref": None}) == "x"
    assert _item_text("plain string") == "plain string"
    assert _coerce_finding_item("s", "finding") == {"kind": "finding", "detail": "s", "ref": None}
    assert _coerce_finding_item({"kind": "risk", "detail": "d", "ref": "r"}, "finding") == {
        "kind": "risk",
        "detail": "d",
        "ref": "r",
    }


# --- read path: draft_decision_from_review over a typed-findings review ----


def test_draft_decision_from_review_with_typed_findings(tmp_path):
    db = _db(tmp_path)
    try:
        project_id = _seed_project(db, risk_flags=["exposed secret"])
        review = run_council(
            db, project_id=project_id, question="Ship it?", provider=DeterministicProvider()
        )
        decision = draft_decision_from_review(db, review_id=review.id)
        assert decision.status in {"draft", "needs_evidence"}
        assert {"type": "council_review", "id": review.id} in decision.evidence
        # tradeoffs carries the review's unsupported_claims verbatim (typed or not).
        assert isinstance(decision.tradeoffs, list)
    finally:
        db.close()


# --- read path: the council API response serializes typed items ------------


def test_council_review_api_response_serializes_typed_items(client, tmp_path):
    project_id = client.post("/projects", json={"name": "Typed API", "slug": "typed-api"}).json()["id"]

    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False, "timeout": 30},
        pool_pre_ping=True,
    )
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)()
    try:
        repo = Repository(project_id=project_id, name="svc", local_path="svc")
        session.add(repo)
        session.flush()
        session.add(
            RepositoryDNA(
                repository_id=repo.id,
                language_mix={"python": 1.0},
                frameworks=["fastapi"],
                risk_flags=["missing tests"],
            )
        )
        session.add(
            ArchitectureNode(project_id=project_id, repository_id=repo.id, label="svc", type="repository", confidence=0.9)
        )
        session.add(Decision(project_id=project_id, title="Adopt FastAPI for the service API"))
        session.add(ResearchNote(project_id=project_id, title="Framework landscape survey"))
        session.commit()
        review = run_council(session, project_id=project_id, question="Ready?", provider=DeterministicProvider())
        review_id = review.id
    finally:
        session.close()

    resp = client.get(f"/council-reviews/{review_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["agent_outputs"]
    for output in body["agent_outputs"]:
        assert output["findings"], output
        for item in output["findings"]:
            assert isinstance(item, dict)
            assert {"kind", "detail", "ref"} <= set(item)


class _MixedShapeFake:
    """A fake real-model provider mixing a typed item with a bare string."""

    name = "mixed_fake"

    def generate(self, *, system, prompt, max_tokens=1024, response_format=None):
        text = json.dumps(
            {
                "summary": "assessed",
                "findings": [{"kind": "structural", "detail": "typed one", "ref": "node:1"}, "a bare string"],
                "evidence": [],
                "concerns": [],
                "confidence": 0.6,
                "status": "Complete",
            }
        )
        return types.SimpleNamespace(text=text, provider="mixed_fake", model="mixed-model", finish_reason="stop")


def test_council_review_api_serializes_mixed_shape_findings(client, tmp_path):
    project_id = client.post("/projects", json={"name": "Mixed API", "slug": "mixed-api"}).json()["id"]

    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False, "timeout": 30},
        pool_pre_ping=True,
    )
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)()
    try:
        review = run_council(session, project_id=project_id, question="Ready?", provider=_MixedShapeFake())
        review_id = review.id
    finally:
        session.close()

    resp = client.get(f"/council-reviews/{review_id}")
    assert resp.status_code == 200
    body = resp.json()
    findings = body["agent_outputs"][0]["findings"]
    assert findings == [
        {"kind": "structural", "detail": "typed one", "ref": "node:1"},
        {"kind": "finding", "detail": "a bare string", "ref": None},
    ]
