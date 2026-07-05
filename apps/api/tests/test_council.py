"""Unit tests for the Agent Council service + LLM provider abstraction (RFC-0005)."""

from __future__ import annotations

import json
import types

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from aos_core.database import Base
from aos_core.llm import (
    ClaudeCodeProvider,
    DeterministicProvider,
    ProviderResult,
    get_provider,
)
from aos_core.models import (
    ArchitectureNode,
    CouncilAgentOutput,
    CouncilReview,
    Decision,
    Project,
    Repository,
    RepositoryDNA,
    ResearchNote,
)
from aos_core.services.council import VERDICTS, run_council, synthesize_verdict


@pytest.fixture()
def db(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'council.db'}",
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    session = session_local()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def _seed_rich_project(db, *, risk_flags: list[str]) -> str:
    """A project with evidence for every persona; risk_flags drive the security agent."""
    project = Project(name="Rich", slug="rich")
    db.add(project)
    db.flush()
    repo = Repository(project_id=project.id, name="svc", local_path="svc")
    db.add(repo)
    db.flush()
    dna = RepositoryDNA(
        repository_id=repo.id,
        language_mix={"python": 0.9, "toml": 0.1},
        frameworks=["fastapi", "sqlalchemy"],
        package_managers=["pip"],
        runtime_services=["postgres", "redis"],
        risk_flags=risk_flags,
        maturity="beta",
    )
    db.add(dna)
    db.add(
        ArchitectureNode(project_id=project.id, repository_id=repo.id, label="svc", type="repository", confidence=0.9)
    )
    db.add(Decision(project_id=project.id, title="Adopt FastAPI for the service API"))
    db.add(ResearchNote(project_id=project.id, title="Framework landscape survey"))
    db.commit()
    return project.id


def test_run_council(db):
    project_id = _seed_rich_project(db, risk_flags=["missing tests for the auth module"])

    review = run_council(db, project_id=project_id, question="Is this service ready?", provider=DeterministicProvider())

    assert isinstance(review, CouncilReview)
    outputs = db.query(CouncilAgentOutput).filter(CouncilAgentOutput.review_id == review.id).all()
    assert len(outputs) == 4
    names = {o.agent_name for o in outputs}
    assert names == {
        "research_librarian",
        "architecture_cartographer",
        "technology_fitness_judge",
        "security_agent",
    }
    for output in outputs:
        assert output.summary
        assert output.findings
        assert output.status
        assert output.confidence >= 0.0
    assert review.verdict in VERDICTS
    assert review.provider == "deterministic"


def test_council_surfaces_disagreement(db):
    # Security sees a risk flag (unfavorable); the other agents see clean signals
    # (favorable) -> the Final Judge must surface the split.
    project_id = _seed_rich_project(db, risk_flags=["exposed secret in config"])

    review = run_council(db, project_id=project_id, question="Ship it?", provider=DeterministicProvider())

    assert review.disagreements
    entry = review.disagreements[0]
    assert "security_agent" in entry["unfavorable"]
    assert entry["favorable"]
    assert review.verdict == "Escalate to human"


def test_council_abstains(db):
    project = Project(name="Empty", slug="empty")
    db.add(project)
    db.commit()

    review = run_council(db, project_id=project.id, question="Anything?", provider=DeterministicProvider())

    assert review.verdict == "Insufficient evidence"
    assert review.follow_up
    outputs = db.query(CouncilAgentOutput).filter(CouncilAgentOutput.review_id == review.id).all()
    assert len(outputs) == 4
    assert all(o.status == "Needs Evidence" for o in outputs)


def test_run_council_missing_project(db):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        run_council(db, project_id="00000000-0000-0000-0000-000000000000", question="x", provider=DeterministicProvider())
    assert exc.value.status_code == 404


def test_deterministic_provider_stable():
    provider = DeterministicProvider()
    first = provider.generate(system="sys", prompt="Persona: security_agent\nEvidence (JSON array):\n[]\n")
    second = provider.generate(system="sys", prompt="Persona: security_agent\nEvidence (JSON array):\n[]\n")
    assert first.text == second.text
    assert first.provider == "deterministic"
    # Output is valid, parseable JSON with the structured-output keys.
    obj = json.loads(first.text)
    assert set(obj) >= {"summary", "findings", "evidence", "concerns", "confidence", "status"}


def test_get_provider_mapping():
    assert isinstance(get_provider(types.SimpleNamespace(llm_provider="deterministic")), DeterministicProvider)
    assert isinstance(get_provider(types.SimpleNamespace(llm_provider="claude_code")), ClaudeCodeProvider)
    with pytest.raises(ValueError):
        get_provider(types.SimpleNamespace(llm_provider="gpt-9"))


def test_claude_code_provider_mocked(monkeypatch):
    import aos_core.llm as llm

    captured = {}

    class _Completed:
        returncode = 0
        stdout = json.dumps({"type": "result", "result": '{"summary": "ok", "status": "Complete"}'})
        stderr = ""

    def fake_run(argv, **kwargs):
        captured["argv"] = argv
        captured["kwargs"] = kwargs
        return _Completed()

    monkeypatch.setattr(llm.subprocess, "run", fake_run)

    provider = ClaudeCodeProvider(binary="claude")
    result = provider.generate(system="SYS", prompt="PROMPT")

    argv = captured["argv"]
    assert argv[0] == "claude"
    assert "-p" in argv
    # system is prepended to the prompt in the single -p argument.
    prompt_arg = argv[argv.index("-p") + 1]
    assert prompt_arg == "SYS\n\nPROMPT"
    assert argv[-2:] == ["--output-format", "json"]
    assert captured["kwargs"].get("timeout") == provider.timeout
    # stdout envelope's "result" field becomes the ProviderResult text.
    assert isinstance(result, ProviderResult)
    assert result.text == '{"summary": "ok", "status": "Complete"}'
    assert result.provider == "claude_code"


def test_claude_code_provider_nonzero_exit(monkeypatch):
    import aos_core.llm as llm

    class _Failed:
        returncode = 2
        stdout = ""
        stderr = "boom"

    monkeypatch.setattr(llm.subprocess, "run", lambda *a, **k: _Failed())
    with pytest.raises(RuntimeError, match="exited with code 2"):
        ClaudeCodeProvider().generate(system="", prompt="p")


def test_claude_code_provider_missing_binary(monkeypatch):
    import aos_core.llm as llm

    def _raise(*a, **k):
        raise FileNotFoundError()

    monkeypatch.setattr(llm.subprocess, "run", _raise)
    with pytest.raises(RuntimeError, match="not found"):
        ClaudeCodeProvider(binary="nope").generate(system="", prompt="p")


def test_synthesize_verdict_abstains_below_floor():
    outputs = [
        CouncilAgentOutput(
            agent_name="a", agent_type="t", status="Needs Evidence",
            summary="", findings=[], evidence=[], concerns=[], confidence=0.0,
        )
    ]
    result = synthesize_verdict(outputs)
    assert result["verdict"] == "Insufficient evidence"
    assert result["follow_up"]
