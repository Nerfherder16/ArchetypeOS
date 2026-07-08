"""Research Engine web tier — failover discovery + fetch pools (RFC-0012 slice-2).

RFC-0011's :class:`~aos_core.services.research.LocalCorpusSource` answers *"what
does my portfolio already know"* — deterministic, hermetic, no network. This
module gives the same seam **reach**: a :class:`WebResearchSource` that discovers
and fetches real external evidence across the source-quality ladder, turning the
engine into *"what does the world know, ranked."*

The design mirrors a pattern already proven in this codebase — the
:class:`~aos_core.services.llm_pool.RotatingProvider` free-LLM pool, which fails
through to the next backend on any transient error and only raises when every
member is exhausted. We generalize that shape into
:class:`RotatingResearchSource` (adding the resilience the research surfaced:
error classification, ``Retry-After`` honoring, jittered exponential backoff, a
per-backend circuit breaker, and a retry budget) and apply it as **two
role-split failover pools**:

- **Discovery pool** (find URLs): :class:`ExaSource` (primary — semantic search)
  → :class:`SearxngSource` (quota-free self-hosted fallback).
- **Fetch pool** (URL → clean text): :class:`Crawl4aiSource` (primary workhorse —
  free, no vendor quota) → :class:`FirecrawlSource` (hard-page fallback).

Every backend speaks its HTTP API via **stdlib** :mod:`urllib` (no new Python
dependency — same discipline as ``OpenAICompatibleProvider``) with a
constructor-injected ``opener`` so tests mock it without network. Backends whose
host/key is not configured are simply absent from the pool (like
``build_free_pool``), so with nothing configured :func:`build_web_source` returns
``None`` and the engine keeps using ``LocalCorpusSource`` — **CI stays hermetic**.

Privacy (RFC-0012): the web tier is only ever constructed for ``PUBLIC`` research
(a ``PRIVATE`` question never egresses — enforced in ``research()``). **No secret
is ever logged** — backends are logged by label/name only, never by key value.
"""

from __future__ import annotations

import json
import logging
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import replace
from typing import Callable

from sqlalchemy.orm import Session

from .llm_router import Sensitivity
from .research import SourceDoc, _DEFAULT_TIER

logger = logging.getLogger("aos_core.research_web")

# Sent on every hosted HTTP call — some endpoints (Cloudflare-fronted) reject the
# default ``Python-urllib`` User-Agent as a bot. Mirrors the LLM provider seam.
_USER_AGENT = "ArchetypeOS/1.0 (+research-web)"

# Transient HTTP statuses worth failing through / retrying (RFC-0012): a rate
# limit or a transient upstream error. A network timeout is transient too (carried
# as ``transient=True`` on the error, since it has no status code).
_RETRY_STATUS: frozenset[int] = frozenset({429, 502, 503, 504})
# Permanent statuses — never retried (a bad request, bad key, or missing resource
# will not fix itself); the pool moves straight to the next backend.
_PERMANENT_STATUS: frozenset[int] = frozenset({400, 401, 403, 404})


# --- errors ---------------------------------------------------------------


class ResearchBackendError(Exception):
    """A single backend's HTTP call failed.

    Carries the ``status`` (``None`` for a transport-level timeout/unreachable),
    an optional ``retry_after`` (seconds, parsed from the header), and a
    ``transient`` flag (a timeout has no status but is retryable). The message
    never contains a secret — adapters build it from status/reason only.
    """

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        retry_after: float | None = None,
        transient: bool = False,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.retry_after = retry_after
        self.transient = transient

    @property
    def is_transient(self) -> bool:
        if self.transient:
            return True
        return self.status in _RETRY_STATUS


class ResearchPoolExhausted(Exception):
    """Every member of a rotation pool failed (or the retry budget was exceeded)."""


# --- HTTP helpers (stdlib urllib, injectable opener) ----------------------

# The opener signature mirrors ``urllib.request.urlopen(request, timeout=...)``.
Opener = Callable[..., object]


def _parse_retry_after(headers) -> float | None:
    """Parse a ``Retry-After`` header (delta-seconds form) into seconds, or None."""
    if headers is None:
        return None
    try:
        raw = headers.get("Retry-After")
    except Exception:
        raw = None
    if not raw:
        return None
    try:
        return max(0.0, float(str(raw).strip()))
    except (TypeError, ValueError):
        # HTTP-date form is valid per spec but we do not read a wall clock in
        # aos_core; fall back to backoff by returning None.
        return None


def _raise_for_http_error(exc: urllib.error.HTTPError) -> ResearchBackendError:
    """Convert a urllib ``HTTPError`` into a classified ``ResearchBackendError``.

    The key is never read here — only the status and the ``Retry-After`` header.
    """
    retry_after = _parse_retry_after(getattr(exc, "headers", None))
    return ResearchBackendError(
        f"HTTP {exc.code}",
        status=exc.code,
        retry_after=retry_after,
        transient=exc.code in _RETRY_STATUS,
    )


def _http_json(
    opener: Opener,
    url: str,
    *,
    method: str,
    headers: dict[str, str],
    body: bytes | None,
    timeout: float,
) -> dict:
    """One JSON request/response via the injected opener. Classifies failures.

    Raises :class:`ResearchBackendError` (transient/permanent classified) on any
    HTTP, transport, or decode failure so the pool can fail through. The response
    body is never logged and the request headers (which carry the key) are never
    echoed into an exception message.
    """
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with opener(request, timeout=timeout) as response:  # type: ignore[operator]
            raw = response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        raise _raise_for_http_error(exc) from exc
    except urllib.error.URLError as exc:
        # A timeout or an unreachable host — transient (worth failing through).
        raise ResearchBackendError(f"unreachable: {exc.reason}", transient=True) from exc
    except TimeoutError as exc:  # pragma: no cover - defensive
        raise ResearchBackendError("timeout", transient=True) from exc
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ResearchBackendError("non-JSON response body") from exc
    if not isinstance(payload, dict):
        raise ResearchBackendError("unexpected (non-object) JSON response")
    return payload


# --- source-tier classification (discovery) -------------------------------
# A discovered URL is tagged to a source-ladder rung by a small host/path
# heuristic so the existing quality-weighted scorer ranks web evidence the same
# way it ranks local evidence. Community posts are labelled ``community`` (→
# ``opinion``) — the Research Engine principle (opinion is never authority).

_TIER_HOST_RULES: tuple[tuple[str, str], ...] = (
    # security advisories — highest-signal safety evidence.
    ("nvd.nist.gov", "security-advisory"),
    ("cve.org", "security-advisory"),
    ("cve.mitre.org", "security-advisory"),
    ("ghsa", "security-advisory"),
    ("security", "security-advisory"),
    # standards / RFCs.
    ("ietf.org", "standard-rfc"),
    ("rfc-editor.org", "standard-rfc"),
    ("w3.org", "standard-rfc"),
    ("iso.org", "standard-rfc"),
    # benchmarks / papers.
    ("arxiv.org", "benchmark-paper"),
    ("acm.org", "benchmark-paper"),
    ("ieee.org", "benchmark-paper"),
    ("papers", "benchmark-paper"),
    # reference implementations.
    ("github.com", "reference-implementation"),
    ("gitlab.com", "reference-implementation"),
    ("pypi.org", "reference-implementation"),
    ("npmjs.com", "reference-implementation"),
    # maintainer discussion.
    ("github.com/issues", "maintainer-discussion"),
    ("discourse", "maintainer-discussion"),
    ("groups.google.com", "maintainer-discussion"),
    ("mail-archive", "maintainer-discussion"),
    # community / opinion — lowest authority.
    ("stackoverflow.com", "community"),
    ("stackexchange.com", "community"),
    ("reddit.com", "community"),
    ("news.ycombinator.com", "community"),
    ("medium.com", "community"),
    ("dev.to", "community"),
    ("blog", "community"),
)


def classify_tier(url: str, *, title: str = "") -> str:
    """Map a discovered ``url`` to a source-ladder rung (documented heuristic).

    Official documentation is the default-authority rung when a URL matches a
    ``docs.``/``/docs`` host or path but no more-specific rule; anything with no
    signal falls to ``reference-implementation`` (the neutral default the local
    corpus also uses). Never raises.
    """
    u = (url or "").lower()
    for needle, tier in _TIER_HOST_RULES:
        if needle in u:
            return tier
    # official docs — a common, high-authority shape worth its own rung.
    host = ""
    try:
        host = urllib.parse.urlparse(u).netloc
    except Exception:
        host = ""
    if host.startswith("docs.") or "/docs" in u or ".readthedocs.io" in u or "developer." in host:
        return "official-docs"
    return _DEFAULT_TIER


# --- the failover pool ----------------------------------------------------


class _Breaker:
    """A per-backend circuit breaker: opens after N consecutive failures.

    Stays open for the pool's lifetime once tripped (a success resets the
    consecutive-failure count while it is still closed). Deliberately simple — no
    wall clock is read in aos_core, so there is no time-based half-open reset; the
    breaker's job here is to stop hammering a backend that is consistently down
    within a research run.
    """

    def __init__(self, threshold: int) -> None:
        self._threshold = max(1, threshold)
        self._consecutive = 0
        self.open = False

    def record_success(self) -> None:
        self._consecutive = 0

    def record_failure(self) -> None:
        self._consecutive += 1
        if self._consecutive >= self._threshold:
            self.open = True


class _RotatingPool:
    """Shared failover engine for the discovery and fetch pools.

    Holds pre-built members (trivially testable with fakes), a round-robin start
    cursor, a per-member circuit breaker, and pool-lifetime counters for the retry
    budget. :meth:`_dispatch` runs one logical request across the members: it
    tries each member in round-robin order, retries a member up to ``max_retries``
    times on a *transient* error (honoring ``Retry-After`` then jittered
    exponential backoff), fails straight through to the next member on a
    *permanent* error, skips members whose breaker is open, and raises
    :class:`ResearchPoolExhausted` only when every member is exhausted.

    The **retry budget** caps wasteful same-member retries: once the fraction of
    attempts that hit a rate limit (429) exceeds ``retry_budget``, further
    same-member retries are disabled and the pool fails straight through instead —
    which is exactly the right behavior for a rate-limited backend (fail over, do
    not hammer). This is the operator's *"keep Exa, but don't get rate-limited"*
    constraint encoded.
    """

    def __init__(
        self,
        members: list,
        labels: list[str] | None = None,
        *,
        retry_budget: float = 0.15,
        max_retries: int = 2,
        breaker_threshold: int = 3,
        backoff_base: float = 0.5,
        backoff_cap: float = 8.0,
        jitter: float = 1.5,
        sleep: Callable[[float], None] = time.sleep,
        rng: random.Random | None = None,
    ) -> None:
        self._members = members
        self._labels = labels or [getattr(m, "name", "?") for m in members]
        self._retry_budget = max(0.0, retry_budget)
        self._max_retries = max(0, max_retries)
        self._backoff_base = backoff_base
        self._backoff_cap = backoff_cap
        self._jitter = max(0.0, jitter)
        self._sleep = sleep
        self._rng = rng or random.Random()
        self._cursor = 0
        self._breakers = [_Breaker(breaker_threshold) for _ in members]
        # Pool-lifetime counters for the retry budget.
        self._attempts = 0
        self._rate_limited = 0

    def __len__(self) -> int:
        return len(self._members)

    def _retries_allowed(self) -> bool:
        """False once the rate-limited fraction of attempts exceeds the budget."""
        if self._attempts <= 0:
            return True
        return (self._rate_limited / self._attempts) <= self._retry_budget

    def _delay_for(self, exc: ResearchBackendError, attempt: int) -> float:
        """Retry-After (+jitter) when the backend gave one, else jittered backoff."""
        if exc.retry_after is not None:
            base = exc.retry_after
        else:
            base = min(self._backoff_cap, self._backoff_base * (2 ** attempt))
        return base + self._rng.uniform(0.0, self._jitter)

    def _dispatch(self, call: Callable[[object], object], *, what: str) -> object:
        n = len(self._members)
        if n == 0:
            raise ResearchPoolExhausted(f"research {what} pool is empty")
        start = self._cursor
        self._cursor = (self._cursor + 1) % n  # spread load across calls
        errors: list[str] = []
        for offset in range(n):
            idx = (start + offset) % n
            label = self._labels[idx]
            breaker = self._breakers[idx]
            if breaker.open:
                errors.append(f"{label}: circuit-open")
                continue
            for attempt in range(self._max_retries + 1):
                self._attempts += 1
                try:
                    result = call(self._members[idx])
                except ResearchBackendError as exc:
                    if exc.status == 429:
                        self._rate_limited += 1
                    breaker.record_failure()
                    errors.append(f"{label}: {exc}")
                    logger.debug("research %s backend %s failed: %s", what, label, exc)
                    if exc.is_transient and attempt < self._max_retries and self._retries_allowed():
                        self._sleep(self._delay_for(exc, attempt))
                        continue  # retry the SAME backend
                    break  # permanent, out of retries, or over budget → next backend
                except Exception as exc:  # noqa: BLE001 — an unexpected error fails over too
                    breaker.record_failure()
                    errors.append(f"{label}: {exc}")
                    logger.debug("research %s backend %s errored: %s", what, label, exc)
                    break  # next backend
                else:
                    breaker.record_success()
                    return result
        raise ResearchPoolExhausted(
            f"all research {what} backends failed — " + " | ".join(errors)
        )


class RotatingResearchSource(_RotatingPool):
    """A failover :class:`~aos_core.services.research.ResearchSource` (discovery pool).

    Rotates across the injected discovery backends, failing through on transient
    errors and raising :class:`ResearchPoolExhausted` only when all are exhausted.
    Implements the ``ResearchSource`` protocol so it drops into ``research()``.
    """

    name = "rotating-research"

    def gather(
        self, db: Session, *, project_id: str, question: str, sensitivity: Sensitivity, limit: int
    ) -> list[SourceDoc]:
        return self._dispatch(
            lambda m: m.gather(
                db, project_id=project_id, question=question, sensitivity=sensitivity, limit=limit
            ),
            what="discovery",
        )


class RotatingFetchSource(_RotatingPool):
    """A failover fetch pool: ``fetch(url) -> str`` across the injected backends."""

    name = "rotating-fetch"

    def fetch(self, url: str) -> str:
        return self._dispatch(lambda m: m.fetch(url), what="fetch")


# --- discovery adapters ----------------------------------------------------


class ExaSource:
    """Discovery via the Exa semantic-search API (``POST {host}/search``).

    Reaches only the configured Exa host. The key is sent in the ``x-api-key``
    header and is never logged or placed in an error message.
    """

    name = "exa"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.exa.ai",
        timeout: float = 10.0,
        opener: Opener = urllib.request.urlopen,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._opener = opener

    def gather(
        self, db: Session, *, project_id: str, question: str, sensitivity: Sensitivity, limit: int
    ) -> list[SourceDoc]:
        body = json.dumps(
            {
                "query": question,
                "numResults": max(1, limit),
                "contents": {"text": {"maxCharacters": 2000}},
            }
        ).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "User-Agent": _USER_AGENT,
            "x-api-key": self._api_key,
        }
        payload = _http_json(
            self._opener,
            f"{self._base_url}/search",
            method="POST",
            headers=headers,
            body=body,
            timeout=self._timeout,
        )
        return _exa_to_docs(payload)

    def fetch(self, url: str) -> str:  # discovery-only; not a fetch backend
        raise NotImplementedError("ExaSource is a discovery backend")


def _exa_to_docs(payload: dict) -> list[SourceDoc]:
    docs: list[SourceDoc] = []
    for item in payload.get("results") or []:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "").strip()
        if not url:
            continue
        title = str(item.get("title") or url)
        snippet = str(item.get("text") or item.get("snippet") or item.get("highlights") or "").strip()
        published = item.get("publishedDate") or None
        docs.append(
            SourceDoc(
                ref=url,
                title=title,
                text=f"{title} {snippet}".strip(),
                tier=classify_tier(url, title=title),
                published=str(published) if published else None,
            )
        )
    return docs


class SearxngSource:
    """Discovery via a self-hosted SearXNG instance (``GET {url}/search?format=json``).

    Quota-free fallback for the discovery pool. Reaches only the configured host.
    """

    name = "searxng"

    def __init__(
        self,
        *,
        base_url: str,
        timeout: float = 10.0,
        opener: Opener = urllib.request.urlopen,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._opener = opener

    def gather(
        self, db: Session, *, project_id: str, question: str, sensitivity: Sensitivity, limit: int
    ) -> list[SourceDoc]:
        query = urllib.parse.urlencode({"q": question, "format": "json"})
        headers = {"User-Agent": _USER_AGENT}
        payload = _http_json(
            self._opener,
            f"{self._base_url}/search?{query}",
            method="GET",
            headers=headers,
            body=None,
            timeout=self._timeout,
        )
        return _searxng_to_docs(payload, limit=limit)

    def fetch(self, url: str) -> str:  # discovery-only
        raise NotImplementedError("SearxngSource is a discovery backend")


def _searxng_to_docs(payload: dict, *, limit: int) -> list[SourceDoc]:
    docs: list[SourceDoc] = []
    for item in (payload.get("results") or [])[: max(1, limit) if limit else None]:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "").strip()
        if not url:
            continue
        title = str(item.get("title") or url)
        snippet = str(item.get("content") or item.get("snippet") or "").strip()
        docs.append(
            SourceDoc(
                ref=url,
                title=title,
                text=f"{title} {snippet}".strip(),
                tier=classify_tier(url, title=title),
            )
        )
    return docs


# --- fetch adapters --------------------------------------------------------


class Crawl4aiSource:
    """Fetch via a self-hosted crawl4ai instance (``POST {url}/md``).

    Primary fetch workhorse — free, no vendor quota, returns LLM-ready markdown.
    Reaches only the configured host.
    """

    name = "crawl4ai"

    def __init__(
        self,
        *,
        base_url: str,
        timeout: float = 10.0,
        opener: Opener = urllib.request.urlopen,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._opener = opener

    def fetch(self, url: str) -> str:
        body = json.dumps({"url": url}).encode("utf-8")
        headers = {"Content-Type": "application/json", "User-Agent": _USER_AGENT}
        payload = _http_json(
            self._opener,
            f"{self._base_url}/md",
            method="POST",
            headers=headers,
            body=body,
            timeout=self._timeout,
        )
        return _crawl4ai_text(payload)


def _crawl4ai_text(payload: dict) -> str:
    for key in ("markdown", "raw_markdown", "fit_markdown", "content", "text"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    # some builds nest under {"result": {"markdown": ...}}
    result = payload.get("result")
    if isinstance(result, dict):
        return _crawl4ai_text(result)
    return ""


class FirecrawlSource:
    """Fetch via a self-hosted Firecrawl instance (``POST {url}/v1/scrape``).

    Hard-page fallback for the fetch pool. An optional bearer key is sent in the
    ``Authorization`` header and never logged. Reaches only the configured host.
    """

    name = "firecrawl"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str = "",
        timeout: float = 10.0,
        opener: Opener = urllib.request.urlopen,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        self._opener = opener

    def fetch(self, url: str) -> str:
        body = json.dumps({"url": url, "formats": ["markdown"]}).encode("utf-8")
        headers = {"Content-Type": "application/json", "User-Agent": _USER_AGENT}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        payload = _http_json(
            self._opener,
            f"{self._base_url}/v1/scrape",
            method="POST",
            headers=headers,
            body=body,
            timeout=self._timeout,
        )
        return _firecrawl_text(payload)


def _firecrawl_text(payload: dict) -> str:
    data = payload.get("data")
    if isinstance(data, dict):
        for key in ("markdown", "content", "text"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    for key in ("markdown", "content", "text"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


# --- the composite web source ---------------------------------------------


class WebResearchSource:
    """Compose discovery → fetch into a single :class:`ResearchSource`.

    ``gather`` runs the discovery pool to find candidate URLs, then (if a fetch
    pool is configured) fetches each result's full text through the fetch pool and
    enriches its :class:`SourceDoc`. Tolerant per RFC-0012: a discovery-pool
    exhaustion yields ``[]`` (the engine degrades to the local corpus); a
    per-result fetch failure drops that source; if every fetch fails, ``[]``. When
    no fetch pool is configured the discovery snippets are used as-is. Never raises
    out of ``gather``.
    """

    name = "web"

    def __init__(
        self,
        discovery,
        fetch_pool=None,
        *,
        max_fetch: int = 8,
    ) -> None:
        self._discovery = discovery
        self._fetch = fetch_pool
        self._max_fetch = max(0, max_fetch)

    def gather(
        self, db: Session, *, project_id: str, question: str, sensitivity: Sensitivity, limit: int
    ) -> list[SourceDoc]:
        try:
            found = self._discovery.gather(
                db, project_id=project_id, question=question, sensitivity=sensitivity, limit=limit
            )
        except Exception as exc:  # noqa: BLE001 — discovery exhausted → degrade to []
            logger.debug("web discovery pool exhausted: %s", exc)
            return []

        cap = self._max_fetch or limit or len(found)
        candidates = list(found)[:cap]

        # No fetch pool configured → use the discovery snippets directly.
        if self._fetch is None:
            return candidates

        enriched: list[SourceDoc] = []
        for doc in candidates:
            try:
                text = self._fetch.fetch(doc.ref)
            except Exception as exc:  # noqa: BLE001 — this source failed to fetch; drop it
                logger.debug("web fetch failed for %s: %s", doc.ref, exc)
                continue
            if not text:
                # nothing fetched — fall back to the discovery snippet for this doc.
                enriched.append(doc)
                continue
            enriched.append(replace(doc, text=f"{doc.title} {text}".strip()))
        return enriched


# --- assembly --------------------------------------------------------------


def build_web_source(settings) -> "WebResearchSource | None":
    """Assemble the web tier from configured hosts/keys, or ``None`` if disabled.

    Returns ``None`` when ``research_web_enabled`` is False (the CI/hermetic
    default) OR when no discovery backend is configured — so ``research()`` keeps
    using ``LocalCorpusSource`` and no network fires. Otherwise returns a
    :class:`WebResearchSource` composed of a discovery pool (Exa → SearXNG) and,
    when configured, a fetch pool (crawl4ai → Firecrawl). Adding a backend is just
    configuring its host/key (mirrors ``build_free_pool``).
    """
    if not getattr(settings, "research_web_enabled", False):
        return None

    timeout = float(getattr(settings, "research_http_timeout", 10.0))
    retry_budget = float(getattr(settings, "research_retry_budget", 0.15))
    max_fetch = int(getattr(settings, "research_max_fetch", 8))

    # Discovery pool: Exa (primary) → SearXNG (fallback).
    discovery_members: list = []
    discovery_labels: list[str] = []
    exa_key = getattr(settings, "exa_api_key", "") or ""
    if exa_key:
        discovery_members.append(ExaSource(api_key=exa_key, timeout=timeout))
        discovery_labels.append("exa")
    searxng_url = getattr(settings, "searxng_url", "") or ""
    if searxng_url:
        discovery_members.append(SearxngSource(base_url=searxng_url, timeout=timeout))
        discovery_labels.append("searxng")

    if not discovery_members:
        # Nothing to discover with → the web tier can find nothing; stay local.
        return None

    discovery = RotatingResearchSource(
        discovery_members, discovery_labels, retry_budget=retry_budget
    )

    # Fetch pool: crawl4ai (primary) → Firecrawl (fallback). Optional — with none
    # configured the discovery snippets are used directly.
    fetch_members: list = []
    fetch_labels: list[str] = []
    crawl4ai_url = getattr(settings, "crawl4ai_url", "") or ""
    if crawl4ai_url:
        fetch_members.append(Crawl4aiSource(base_url=crawl4ai_url, timeout=timeout))
        fetch_labels.append("crawl4ai")
    firecrawl_url = getattr(settings, "firecrawl_url", "") or ""
    if firecrawl_url:
        fetch_members.append(FirecrawlSource(base_url=firecrawl_url, timeout=timeout))
        fetch_labels.append("firecrawl")

    fetch_pool = (
        RotatingFetchSource(fetch_members, fetch_labels, retry_budget=retry_budget)
        if fetch_members
        else None
    )

    return WebResearchSource(discovery, fetch_pool, max_fetch=max_fetch)


__all__ = [
    "ResearchBackendError",
    "ResearchPoolExhausted",
    "RotatingResearchSource",
    "RotatingFetchSource",
    "ExaSource",
    "SearxngSource",
    "Crawl4aiSource",
    "FirecrawlSource",
    "WebResearchSource",
    "build_web_source",
    "classify_tier",
]
