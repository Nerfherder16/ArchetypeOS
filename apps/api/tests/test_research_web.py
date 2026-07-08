"""Hermetic tests for the Research Engine web tier (RFC-0012 slice-2, AOS-RESEARCH-002).

Every test is mocked — NO network fires under pytest, no new dependency executes.
The failover pool is exercised with injected fake backends; the adapters are
exercised with an injected fake urllib opener over recorded fixtures. Mirrors the
``test_research.py`` tmp-sqlite harness for the ``research()`` integration cases.
"""

from __future__ import annotations

import json
import logging
import random
import types
import urllib.error
from unittest import mock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from aos_core.database import Base
from aos_core.models import KnowledgePage, Project, ResearchNote
from aos_core.services.llm_router import Sensitivity
from aos_core.services.research import SourceDoc, research
from aos_core.services.research_web import (
    Crawl4aiSource,
    ExaSource,
    FirecrawlSource,
    ResearchBackendError,
    ResearchPoolExhausted,
    RotatingResearchSource,
    SearxngSource,
    WebResearchSource,
    build_web_source,
    classify_tier,
)


# --- fixtures / fakes ------------------------------------------------------


@pytest.fixture()
def db(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'research_web.db'}",
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


def _project(db, name="ResearchWeb") -> str:
    project = Project(name=name, slug=name.lower())
    db.add(project)
    db.commit()
    return project.id


class _FakeDiscovery:
    """A fake discovery ``ResearchSource``: returns docs or always raises ``error``."""

    def __init__(self, name, *, docs=None, error=None):
        self.name = name
        self._docs = docs or []
        self._error = error
        self.calls = 0

    def gather(self, db, *, project_id, question, sensitivity, limit):
        self.calls += 1
        if self._error is not None:
            raise self._error
        return list(self._docs)


class _FakeResp:
    def __init__(self, body: str) -> None:
        self._body = body.encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakeOpener:
    """A fake ``urllib`` opener: records reached URLs, returns a fixed JSON body."""

    def __init__(self, payload) -> None:
        self._body = payload if isinstance(payload, str) else json.dumps(payload)
        self.urls: list[str] = []

    def __call__(self, request, timeout=None):
        self.urls.append(request.full_url)
        return _FakeResp(self._body)


def _settings(**kw):
    base = dict(
        research_web_enabled=False,
        exa_api_key="",
        crawl4ai_url="",
        searxng_url="",
        firecrawl_url="",
        research_http_timeout=10.0,
        research_max_fetch=8,
        research_retry_budget=0.15,
    )
    base.update(kw)
    return types.SimpleNamespace(**base)


def _doc(ref, text="text") -> SourceDoc:
    return SourceDoc(ref=ref, title=ref, text=text)


def _gather(pool, **kw):
    params = dict(project_id="p", question="asyncpg pooling", sensitivity=Sensitivity.PUBLIC, limit=5)
    params.update(kw)
    return pool.gather(None, **params)


# --- 1. pool fails through + honors Retry-After ----------------------------


def test_pool_fails_through_and_honors_retry_after():
    """A 429 backend (with Retry-After) is retried honoring the header, then the
    pool fails through to the next healthy backend; only-all-fail raises."""
    sleeps: list[float] = []
    flaky = _FakeDiscovery(
        "flaky", error=ResearchBackendError("HTTP 429", status=429, retry_after=5.0)
    )
    healthy = _FakeDiscovery("healthy", docs=[_doc("http://ok")])

    pool = RotatingResearchSource(
        [flaky, healthy],
        ["flaky", "healthy"],
        retry_budget=1.0,        # allow the same-backend retry so Retry-After is exercised
        max_retries=1,
        sleep=sleeps.append,
        rng=random.Random(0),
    )

    docs = _gather(pool)
    assert [d.ref for d in docs] == ["http://ok"]   # failed through to healthy
    assert flaky.calls == 2                          # retried once before failing over
    assert sleeps and sleeps[0] >= 5.0               # Retry-After honored (+jitter)


def test_pool_round_robins_start_cursor():
    """The start cursor rotates across gather() calls (spread load, RFC-0012)."""
    a = _FakeDiscovery("a", docs=[_doc("a")])
    b = _FakeDiscovery("b", docs=[_doc("b")])
    pool = RotatingResearchSource([a, b], ["a", "b"])
    assert _gather(pool)[0].ref == "a"   # start 0
    assert _gather(pool)[0].ref == "b"   # rotated to 1
    assert _gather(pool)[0].ref == "a"   # wrapped back to 0


# --- 2. circuit breaker + retry budget -------------------------------------


def test_circuit_breaker_and_retry_budget():
    """The retry budget disables wasteful same-backend 429 retries (immediate
    failover), and the circuit breaker opens a backend after N consecutive fails."""
    # --- retry budget: default 0.15 → a 429 backend is NOT retried; fail over now.
    sleeps: list[float] = []
    budget_flaky = _FakeDiscovery(
        "budget", error=ResearchBackendError("HTTP 429", status=429)
    )
    healthy = _FakeDiscovery("healthy", docs=[_doc("http://ok")])
    pool = RotatingResearchSource(
        [budget_flaky, healthy],
        ["budget", "healthy"],
        retry_budget=0.15,
        max_retries=3,
        sleep=sleeps.append,
    )
    docs = _gather(pool)
    assert [d.ref for d in docs] == ["http://ok"]
    assert budget_flaky.calls == 1   # budget disallowed the retry → single attempt
    assert sleeps == []              # no retry sleep happened

    # --- circuit breaker: a single always-failing member opens after threshold
    # consecutive fails and is thereafter skipped (its call count freezes).
    broken = _FakeDiscovery(
        "broken", error=ResearchBackendError("HTTP 503", status=503, transient=True)
    )
    breaker_pool = RotatingResearchSource(
        [broken], ["broken"], breaker_threshold=2, max_retries=0, retry_budget=1.0,
        sleep=lambda _s: None,
    )
    with pytest.raises(ResearchPoolExhausted):
        _gather(breaker_pool)
    assert broken.calls == 1
    with pytest.raises(ResearchPoolExhausted):
        _gather(breaker_pool)
    assert broken.calls == 2         # breaker trips here (2 consecutive fails)
    with pytest.raises(ResearchPoolExhausted):
        _gather(breaker_pool)
    assert broken.calls == 2         # breaker OPEN → member skipped, not called again


def test_pool_raises_only_when_all_members_fail():
    """The pool raises ResearchPoolExhausted only when every member is exhausted."""
    a = _FakeDiscovery("a", error=ResearchBackendError("HTTP 500", status=500))
    b = _FakeDiscovery("b", error=ResearchBackendError("HTTP 404", status=404))
    pool = RotatingResearchSource([a, b], ["a", "b"], max_retries=0, retry_budget=1.0)
    with pytest.raises(ResearchPoolExhausted):
        _gather(pool)
    assert a.calls == 1 and b.calls == 1


# --- 3. build_web_source assembly ------------------------------------------


def test_build_web_source_absent_when_unconfigured():
    """None when disabled, or enabled-but-nothing-configured, or only-fetch (no
    discovery) configured."""
    assert build_web_source(_settings(research_web_enabled=False)) is None
    assert build_web_source(_settings(research_web_enabled=True)) is None
    # a fetch host with no discovery backend → nothing to discover → None.
    assert build_web_source(_settings(research_web_enabled=True, crawl4ai_url="http://c")) is None


def test_build_web_source_assembles_configured_pools():
    """Assembles a discovery pool (Exa→SearXNG) + fetch pool (crawl4ai→Firecrawl)."""
    src = build_web_source(
        _settings(
            research_web_enabled=True,
            exa_api_key="k",
            searxng_url="http://searx",
            crawl4ai_url="http://crawl",
            firecrawl_url="http://fire",
        )
    )
    assert isinstance(src, WebResearchSource)
    assert isinstance(src._discovery, RotatingResearchSource)
    assert len(src._discovery) == 2                 # exa + searxng
    assert src._fetch is not None
    assert len(src._fetch) == 2                      # crawl4ai + firecrawl

    # Discovery-only assembly (no fetch host) → a web source with no fetch pool.
    disc_only = build_web_source(_settings(research_web_enabled=True, exa_api_key="k"))
    assert isinstance(disc_only, WebResearchSource)
    assert disc_only._fetch is None
    assert len(disc_only._discovery) == 1


# --- 4. CI-hermetic default: research() → LocalCorpusSource -----------------


def test_research_defaults_to_local_when_web_absent(db):
    """With nothing configured (CI default) research() uses the local corpus and
    build_web_source(get_settings()) is None — the RFC-0011 path is unchanged."""
    from aos_core.config import get_settings

    assert build_web_source(get_settings()) is None   # CI default → no web tier

    project_id = _project(db)
    db.add(
        KnowledgePage(
            project_id=project_id,
            title="asyncpg postgres pooling",
            vault_path="vault/repos/asyncpg.md",
            page_type="repository",
        )
    )
    db.commit()

    # No source passed → PUBLIC default resolution → build_web_source None → local.
    note = research(db, project_id=project_id, question="asyncpg postgres pooling")
    assert note.sources                                 # ranked from the local corpus
    assert note.sources[0]["ref"] == "vault/repos/asyncpg.md"


# --- 5. privacy: PRIVATE never constructs a web source ---------------------


def test_private_skips_web_tier(db, monkeypatch):
    """A PRIVATE research call never consults build_web_source (no query egress);
    a PUBLIC call does."""
    import aos_core.services.research_web as rw

    spy = mock.MagicMock(return_value=None)
    monkeypatch.setattr(rw, "build_web_source", spy)
    project_id = _project(db)

    research(db, project_id=project_id, question="proprietary internal question", sensitivity=Sensitivity.PRIVATE)
    assert spy.call_count == 0     # PRIVATE forced to LocalCorpusSource — no web construction

    research(db, project_id=project_id, question="a public question", sensitivity=Sensitivity.PUBLIC)
    assert spy.call_count == 1     # PUBLIC consults the web tier


# --- 6. degradation: an all-failed web pool degrades gracefully ------------


def test_web_all_failed_degrades_gracefully(db, monkeypatch):
    """An exhausted web discovery pool yields [] → research() still persists a
    graceful 'no evidence' note without raising."""
    import aos_core.services.research_web as rw

    broken = _FakeDiscovery("broken", error=ResearchBackendError("HTTP 503", status=503, transient=True))
    pool = RotatingResearchSource([broken], ["broken"], max_retries=0, retry_budget=1.0, sleep=lambda _s: None)
    web = WebResearchSource(pool, None)
    monkeypatch.setattr(rw, "build_web_source", lambda settings: web)

    project_id = _project(db)
    note = research(db, project_id=project_id, question="anything at all here")
    assert isinstance(note, ResearchNote)
    assert note.sources == []
    assert note.confidence == 0.0
    assert "no local evidence" in note.summary.lower()


# --- 7. composite: enrich via fetch, drop unfetchable ----------------------


def test_web_source_enriches_and_drops_unfetchable():
    """WebResearchSource enriches each discovered doc via the fetch pool; a doc
    whose fetch fails is dropped (RFC-0012 tolerance)."""
    docs = [_doc("http://a", text="snippet a"), _doc("http://b", text="snippet b")]
    discovery = _FakeDiscovery("d", docs=docs)

    class _FetchPool:
        def fetch(self, url):
            if url == "http://b":
                raise ResearchBackendError("HTTP 404", status=404)
            return "full body text for A"

    web = WebResearchSource(discovery, _FetchPool(), max_fetch=8)
    out = _gather(web)
    assert [d.ref for d in out] == ["http://a"]        # b dropped (fetch failed)
    assert "full body text for A" in out[0].text        # a enriched with fetched text


# --- 8. adapters parse their fixtures into SourceDocs ----------------------


def test_adapters_parse_fixtures():
    """Each adapter parses its API response shape and reaches only its host."""
    # Exa discovery → SourceDocs (url + snippet + tier), reaches api.exa.ai only.
    exa_opener = _FakeOpener(
        {
            "results": [
                {"url": "https://docs.example.com/guide", "title": "Guide", "text": "pooling docs"},
                {"url": "https://github.com/acme/lib", "title": "acme lib", "text": "impl"},
                {"url": "https://stackoverflow.com/q/1", "title": "SO", "text": "opinion"},
            ]
        }
    )
    exa = ExaSource(api_key="secret-key", opener=exa_opener)
    exa_docs = _gather(exa)
    assert [d.ref for d in exa_docs] == [
        "https://docs.example.com/guide",
        "https://github.com/acme/lib",
        "https://stackoverflow.com/q/1",
    ]
    assert exa_docs[0].tier == "official-docs"
    assert exa_docs[1].tier == "reference-implementation"
    assert exa_docs[2].tier == "community"           # stackoverflow → opinion
    assert exa_docs[2].label == "opinion"
    assert exa_opener.urls == ["https://api.exa.ai/search"]

    # SearXNG discovery → SourceDocs, reaches the configured host only.
    searx_opener = _FakeOpener({"results": [{"url": "https://github.com/acme/lib", "title": "acme", "content": "snip"}]})
    searx = SearxngSource(base_url="http://searx.local", opener=searx_opener)
    searx_docs = _gather(searx)
    assert searx_docs[0].ref == "https://github.com/acme/lib"
    assert searx_docs[0].tier == "reference-implementation"
    assert searx_opener.urls[0].startswith("http://searx.local/search?")

    # crawl4ai fetch → markdown text, reaches /md on the configured host.
    crawl_opener = _FakeOpener({"markdown": "# Title\n\nBody text here"})
    crawl = Crawl4aiSource(base_url="http://crawl.local", opener=crawl_opener)
    assert "Body text here" in crawl.fetch("https://example.com/page")
    assert crawl_opener.urls == ["http://crawl.local/md"]

    # Firecrawl fetch → nested data.markdown, reaches /v1/scrape.
    fire_opener = _FakeOpener({"data": {"markdown": "scraped markdown"}})
    fire = FirecrawlSource(base_url="http://fire.local", api_key="fk", opener=fire_opener)
    assert fire.fetch("https://example.com") == "scraped markdown"
    assert fire_opener.urls == ["http://fire.local/v1/scrape"]


def test_classify_tier_defaults_to_reference_implementation():
    """An unrecognized host falls to the neutral reference-implementation rung."""
    assert classify_tier("https://some-random-host.example/thing") == "reference-implementation"
    assert classify_tier("https://nvd.nist.gov/vuln/detail/CVE-1") == "security-advisory"
    assert classify_tier("https://arxiv.org/abs/2401.00001") == "benchmark-paper"


# --- 9. no secret is ever logged -------------------------------------------


def test_no_key_in_logs(caplog):
    """A failing adapter logs the backend by label only — never the key value, in
    the logs or the raised exception."""
    key = "super-secret-exa-key-abc123"

    def failing_opener(request, timeout=None):
        raise urllib.error.HTTPError(request.full_url, 500, "server error", hdrs=None, fp=None)

    exa = ExaSource(api_key=key, opener=failing_opener)
    pool = RotatingResearchSource([exa], ["exa"], max_retries=0, retry_budget=1.0, sleep=lambda _s: None)

    with caplog.at_level(logging.DEBUG, logger="aos_core.research_web"):
        with pytest.raises(ResearchPoolExhausted) as exc_info:
            _gather(pool)

    assert key not in caplog.text          # never logged
    assert key not in str(exc_info.value)  # never in the exhaustion message
    assert "exa" in caplog.text            # backend identified by label
