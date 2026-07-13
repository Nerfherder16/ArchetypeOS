"""Unit tests for the Agent Council service + LLM provider abstraction (RFC-0005)."""

from __future__ import annotations

import json
import os
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
from aos_core.services.council import (
    VERDICTS,
    _parse_agent_output,
    run_council,
    synthesize_verdict,
)


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


def test_select_architecture_cites_operator_corrections(db):
    """AOS-ARCH-STUDIO-001 (Finding 7 criterion 4): the Council must cite the
    operator's corrected architecture, not only the raw scanner labels — otherwise
    a correction the operator makes on the dashboard never reaches the reasoning."""
    from aos_core.models import ArchitectureEdge
    from aos_core.services.council import _select_architecture

    project = Project(name="Corrected", slug="corrected")
    db.add(project)
    db.flush()
    repo = Repository(project_id=project.id, name="svc", local_path="svc")
    db.add(repo)
    db.flush()
    corrected_node = ArchitectureNode(
        project_id=project.id,
        repository_id=repo.id,
        label="service",
        type="directory",
        confidence=0.4,
        manual_correction="actually the auth gateway",
    )
    plain_node = ArchitectureNode(
        project_id=project.id, repository_id=repo.id, label="db", type="datastore", confidence=0.6
    )
    db.add_all([corrected_node, plain_node])
    db.flush()
    edge = ArchitectureEdge(
        project_id=project.id,
        repository_id=repo.id,
        from_node_id=corrected_node.id,
        to_node_id=plain_node.id,
        type="depends_on",
        confidence=0.3,
        manual_correction="operator: read-replica access only",
    )
    db.add(edge)
    db.commit()

    items = _select_architecture(db, project.id)

    corrected = [i for i in items if i["ref"] == f"node:{corrected_node.id}"]
    assert corrected, items
    assert "auth gateway" in corrected[0]["detail"], "the correction text must reach the Council"
    assert corrected[0].get("corrected") is True

    plain = [i for i in items if i["ref"] == f"node:{plain_node.id}"]
    assert plain, items
    assert not plain[0].get("corrected"), "an uncorrected node is not flagged corrected"

    edge_items = [i for i in items if i["ref"] == f"edge:{edge.id}"]
    assert edge_items, "a corrected edge is citable as architecture evidence"
    assert "read-replica" in edge_items[0]["detail"]
    assert edge_items[0].get("corrected") is True


class _SpreadFake:
    """A fake multi-model provider: a different model per call (like the pool)."""

    name = "rotating"

    def __init__(self, models):
        self._models = models
        self._i = 0

    def generate(self, *, system, prompt, max_tokens=1024, response_format=None):
        model = self._models[self._i % len(self._models)]
        self._i += 1
        text = json.dumps({
            "summary": f"assessed via {model}", "findings": [f"finding-{model}"],
            "evidence": ["e"], "concerns": [], "confidence": 0.7, "status": "Complete",
        })
        return types.SimpleNamespace(
            text=text, provider="openai_compatible", model=model, finish_reason="stop"
        )


def test_run_council_records_per_agent_model(db):
    # AOS-LLM-EVAL-001: a multi-model council records WHICH model each agent used.
    project_id = _seed_rich_project(db, risk_flags=["x"])
    provider = _SpreadFake(["groq-70b", "gemini-flash", "cerebras-120b", "mistral-large"])

    review = run_council(db, project_id=project_id, question="Q?", provider=provider)

    outputs = db.query(CouncilAgentOutput).filter(CouncilAgentOutput.review_id == review.id).all()
    models = [o.agent_model for o in outputs]
    assert all(models), "every agent output records its model"
    assert len(set(models)) == 4, "four agents -> four distinct models (genuine diversity)"
    assert review.provider == "rotating"  # top-level provider name, not the per-call backend


def test_council_provider_single_when_multimodel_off():
    from aos_core.services.council import council_provider

    s = types.SimpleNamespace(llm_provider="deterministic", council_multi_model=False)
    assert type(council_provider(s)).__name__ == "DeterministicProvider"


def test_council_provider_uses_pool_when_enabled(monkeypatch):
    import aos_core.services.council as council_mod

    class _Pool:
        name = "rotating"

        def __len__(self):
            return 2

    monkeypatch.setattr(council_mod, "free_pool_provider", lambda: _Pool())
    s = types.SimpleNamespace(llm_provider="deterministic", council_multi_model=True)
    assert council_mod.council_provider(s).name == "rotating"


def test_council_provider_falls_back_when_pool_too_small(monkeypatch):
    import aos_core.services.council as council_mod

    monkeypatch.setattr(council_mod, "free_pool_provider", lambda: None)
    s = types.SimpleNamespace(llm_provider="deterministic", council_multi_model=True)
    assert type(council_mod.council_provider(s)).__name__ == "DeterministicProvider"


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
    assert "--output-format" in argv and argv[argv.index("--output-format") + 1] == "json"
    assert captured["kwargs"].get("timeout") == provider.timeout
    # LES-021: the subprocess must be isolated from ambient project context —
    # a fresh empty cwd (not the process cwd) so no CLAUDE.md / repo files leak,
    # plus denied state-reading/acting tools and strict MCP so the agent reasons
    # only from the prompt.
    cwd = captured["kwargs"].get("cwd")
    assert cwd is not None and cwd != os.getcwd()
    assert "--strict-mcp-config" in argv
    assert "--disallowedTools" in argv
    disallowed = argv[argv.index("--disallowedTools") + 1]
    for tool in ("Bash", "Read", "Write", "WebFetch", "Task"):
        assert tool in disallowed
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


# --- OpenAICompatibleProvider (AOS-LLM-LOCAL-001) ---------------------------


class _FakeHTTPResponse:
    def __init__(self, payload: dict):
        self._body = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self._body


def test_get_provider_openai_compatible():
    import aos_core.llm as llm

    settings = types.SimpleNamespace(
        llm_provider="openai_compatible",
        llm_base_url="http://localhost:11434/v1",
        llm_model="qwen2.5-coder:7b",
        llm_api_key="",
    )
    provider = get_provider(settings)
    assert isinstance(provider, llm.OpenAICompatibleProvider)
    assert provider.base_url == "http://localhost:11434/v1"
    assert provider.model == "qwen2.5-coder:7b"


def test_openai_compatible_provider_builds_request_and_parses(monkeypatch):
    import aos_core.llm as llm

    captured = {}

    def fake_urlopen(request, timeout=None):
        captured["url"] = request.full_url
        captured["method"] = request.get_method()
        captured["timeout"] = timeout
        captured["auth"] = request.has_header("Authorization")
        captured["ua"] = request.get_header("User-agent")
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return _FakeHTTPResponse(
            {
                "model": "qwen2.5-coder:7b",
                "choices": [
                    {"message": {"content": '{"summary": "ok"}'}, "finish_reason": "stop"}
                ],
            }
        )

    monkeypatch.setattr(llm.urllib.request, "urlopen", fake_urlopen)

    provider = llm.OpenAICompatibleProvider(
        base_url="http://localhost:11434/v1", model="qwen2.5-coder:7b", api_key="secret"
    )
    result = provider.generate(system="SYS", prompt="PROMPT", max_tokens=256)

    assert captured["url"] == "http://localhost:11434/v1/chat/completions"
    assert captured["method"] == "POST"
    assert captured["auth"] is True  # bearer header present when api_key set
    assert captured["ua"] and "ArchetypeOS" in captured["ua"]  # UA set (Cloudflare 403s the urllib default)
    assert captured["body"]["model"] == "qwen2.5-coder:7b"
    assert captured["body"]["max_tokens"] == 256
    assert captured["body"]["messages"] == [
        {"role": "system", "content": "SYS"},
        {"role": "user", "content": "PROMPT"},
    ]
    assert isinstance(result, ProviderResult)
    assert result.text == '{"summary": "ok"}'
    assert result.provider == "openai_compatible"
    assert result.provider != "deterministic"  # treated as a real provider


def test_openai_compatible_provider_omits_auth_without_key(monkeypatch):
    import aos_core.llm as llm

    captured = {}

    def fake_urlopen(request, timeout=None):
        captured["auth"] = request.has_header("Authorization")
        return _FakeHTTPResponse(
            {"choices": [{"message": {"content": "hi"}, "finish_reason": "stop"}]}
        )

    monkeypatch.setattr(llm.urllib.request, "urlopen", fake_urlopen)
    llm.OpenAICompatibleProvider(base_url="http://localhost:11434/v1", model="m").generate(
        system="", prompt="p"
    )
    assert captured["auth"] is False  # local Ollama needs no auth header


def test_openai_compatible_provider_http_error_raises(monkeypatch):
    import urllib.error

    import aos_core.llm as llm

    def fake_urlopen(request, timeout=None):
        raise urllib.error.HTTPError(request.full_url, 429, "Too Many Requests", {}, None)

    monkeypatch.setattr(llm.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(RuntimeError, match="429"):
        llm.OpenAICompatibleProvider(base_url="http://x/v1", model="m").generate(
            system="", prompt="p"
        )


def test_openai_compatible_provider_missing_content_raises(monkeypatch):
    import aos_core.llm as llm

    def fake_urlopen(request, timeout=None):
        return _FakeHTTPResponse({"choices": []})  # no message

    monkeypatch.setattr(llm.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(RuntimeError, match="content"):
        llm.OpenAICompatibleProvider(base_url="http://x/v1", model="m").generate(
            system="", prompt="p"
        )


class _RawResponse:
    """A 2xx response whose body is arbitrary bytes (not necessarily JSON)."""

    def __init__(self, body: bytes):
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self._body


def test_openai_compatible_provider_non_json_body_raises(monkeypatch):
    # A 200 with an HTML/proxy error body must surface a legible RuntimeError,
    # not a raw JSONDecodeError (AOS-LLM-LOCAL-001 spike finding).
    import aos_core.llm as llm

    monkeypatch.setattr(
        llm.urllib.request,
        "urlopen",
        lambda *a, **k: _RawResponse(b"<html><body>502 Bad Gateway</body></html>"),
    )
    with pytest.raises(RuntimeError, match="non-JSON"):
        llm.OpenAICompatibleProvider(base_url="http://x/v1", model="m").generate(
            system="", prompt="p"
        )


def test_openai_compatible_provider_passes_response_format(monkeypatch):
    # Structured-output passthrough (AOS-LLM-LOCAL-001): response_format reaches
    # the request body when supplied, and is absent when not.
    import aos_core.llm as llm

    captured = {}

    def fake_urlopen(request, timeout=None):
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return _FakeHTTPResponse(
            {"choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}]}
        )

    monkeypatch.setattr(llm.urllib.request, "urlopen", fake_urlopen)
    provider = llm.OpenAICompatibleProvider(base_url="http://x/v1", model="m")

    rf = {"type": "json_object"}
    provider.generate(system="", prompt="p", response_format=rf)
    assert captured["body"]["response_format"] == rf

    provider.generate(system="", prompt="p")
    assert "response_format" not in captured["body"]


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


# LES-018: real `claude -p --output-format json` output is frequently wrapped in
# a Markdown code fence (or prefixed with prose); the tolerant parser must strip
# it so findings/confidence are not silently lost to the prose fallback. Found on
# the first real Council run over pydantic-ai (3 of 4 agents came back fenced).

_AGENT_JSON = (
    '{"summary": "s", "findings": ["f1", "f2"], "evidence": ["e1"], '
    '"concerns": ["c1"], "confidence": 0.35, "status": "Needs Evidence"}'
)

# Plain strings in the raw agent JSON are coerced to typed {kind, detail, ref}
# items by ``_parse_agent_output`` (AOS-COUNCIL-TYPED-001) — this is the
# expected coerced shape for the two findings/one evidence/one concern above.
_EXPECTED_FINDINGS = [
    {"kind": "finding", "detail": "f1", "ref": None},
    {"kind": "finding", "detail": "f2", "ref": None},
]
_EXPECTED_EVIDENCE = [{"kind": "evidence", "detail": "e1", "ref": None}]
_EXPECTED_CONCERNS = [{"kind": "concern", "detail": "c1", "ref": None}]


def test_parse_agent_output_bare_json():
    out = _parse_agent_output(_AGENT_JSON)
    assert out["findings"] == _EXPECTED_FINDINGS
    assert out["evidence"] == _EXPECTED_EVIDENCE
    assert out["confidence"] == 0.35
    assert out["status"] == "Needs Evidence"


def test_parse_agent_output_fenced_json():
    fenced = f"```json\n{_AGENT_JSON}\n```"
    out = _parse_agent_output(fenced)
    # Without fence-stripping this degraded to the prose fallback (conf 0.05,
    # empty findings). The fix must recover the real content.
    assert out["findings"] == _EXPECTED_FINDINGS
    assert out["concerns"] == _EXPECTED_CONCERNS
    assert out["confidence"] == 0.35
    assert not out["summary"].startswith("```")


def test_parse_agent_output_prose_then_json_object():
    messy = f"Here is my assessment:\n{_AGENT_JSON}\nHope that helps."
    out = _parse_agent_output(messy)
    assert out["findings"] == _EXPECTED_FINDINGS
    assert out["confidence"] == 0.35


def test_parse_agent_output_true_prose_falls_back():
    out = _parse_agent_output("I could not produce structured output.")
    assert out["status"] == "Needs Evidence"
    assert out["confidence"] == 0.05
    assert out["findings"] == []


# --- AOS-LLM-ROUTE-COV: council_provider fallback uses routed_provider ---


def _council_route_settings(**over):
    """Minimal hermetic settings for router-selection assertions."""
    base = dict(
        llm_base_url="http://localhost:11434/v1",
        llm_model="qwen2.5-coder:7b",
        llm_api_key="",
        llm_free_base_url="https://api.groq.com/openai/v1",
        llm_free_model="llama-3.3-70b-versatile",
        llm_free_api_key="gsk_test",
        llm_claude_enabled=False,
        council_multi_model=False,
    )
    base.update(over)
    return types.SimpleNamespace(**base)


def test_council_provider_fallback_routes_to_free_when_local_absent(monkeypatch):
    """Single-provider path picks FREE_HOSTED when LOCAL is unconfigured (no pool)."""
    import aos_core.services.council as council_mod
    import aos_core.services.llm_router as router_mod

    monkeypatch.setattr(router_mod, "build_free_pool", lambda: [])
    monkeypatch.setattr(router_mod, "free_pool_provider", lambda: None)
    monkeypatch.setattr(council_mod, "free_pool_provider", lambda: None)

    from aos_core.llm import OpenAICompatibleProvider

    s = _council_route_settings(llm_base_url="", llm_model="")
    p = council_mod.council_provider(s)
    assert isinstance(p, OpenAICompatibleProvider)


def test_council_provider_fallback_deterministic_when_nothing_configured(monkeypatch):
    """With nothing configured and multi-model off, fallback yields deterministic (hermetic)."""
    import aos_core.services.council as council_mod
    import aos_core.services.llm_router as router_mod

    monkeypatch.setattr(router_mod, "build_free_pool", lambda: [])
    monkeypatch.setattr(router_mod, "free_pool_provider", lambda: None)
    monkeypatch.setattr(council_mod, "free_pool_provider", lambda: None)

    s = _council_route_settings(llm_base_url="", llm_model="", llm_free_api_key="")
    p = council_mod.council_provider(s)
    assert isinstance(p, DeterministicProvider)
