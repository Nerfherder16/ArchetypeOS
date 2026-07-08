"""Unit tests for the Research Engine (RFC-0011 slice-1, AOS-RESEARCH-001).

Hermetic and deterministic — no network, no model. Mirrors the council/transfer
test harness (a tmp sqlite session). The centerpiece,
``test_research_run_clears_council_abstention``, closes LES-019 against the REAL
``synthesize_verdict`` (no staged constant).
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from aos_core.database import Base
from aos_core.llm import DeterministicProvider
from aos_core.models import (
    Decision,
    KnowledgePage,
    Project,
    Repository,
    RepositoryDNA,
    ResearchNote,
)
from aos_core.services.council import ABSTAIN_CONFIDENCE, run_council
from aos_core.services.llm_router import Sensitivity, Tier, route
from aos_core.services.research import (
    SOURCE_TIERS,
    LocalCorpusSource,
    SourceDoc,
    research,
)

import pytest


@pytest.fixture()
def db(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'research.db'}",
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


def _project(db, name="Research") -> str:
    project = Project(name=name, slug=name.lower())
    db.add(project)
    db.commit()
    return project.id


# --- 1. ranking by quality × relevance + structured provenance --------------


def test_ranks_by_quality_and_relevance(db):
    """Sources ranked by source-quality × relevance, with structured provenance,
    tier labels (community → 'opinion'), and a calibrated confidence."""
    project_id = _project(db)
    question = "Should we adopt asyncpg for postgres connection pooling?"

    # A repository distillation (reference-implementation, quality 0.85) covering
    # 4 of the 5 meaningful question terms (relevance 0.8).
    db.add(
        KnowledgePage(
            project_id=project_id,
            title="asyncpg postgres connection pooling",
            vault_path="vault/repos/asyncpg.md",
            page_type="repository",
        )
    )
    # A distractor page with zero relevance — must be dropped.
    db.add(
        KnowledgePage(
            project_id=project_id,
            title="unrelated logging helper utility",
            vault_path="vault/repos/logging.md",
            page_type="repository",
        )
    )
    # A decision (maintainer-discussion, quality 0.6) at the SAME relevance (0.8)
    # as the distillation — the higher-quality distillation must outrank it (the
    # quality tie-break).
    db.add(
        Decision(
            project_id=project_id,
            title="asyncpg postgres connection pooling",
            decision="Notes on asyncpg postgres connection pooling.",
        )
    )
    # A decision (quality 0.6) at HIGHER relevance (covers all 5 terms incl.
    # 'adopt') — relevance dominates, so it must outrank the higher-tier
    # distillation despite the lower quality.
    db.add(
        Decision(
            project_id=project_id,
            title="adopt asyncpg postgres connection pooling",
            decision="Team resolved to adopt asyncpg.",
        )
    )
    db.commit()

    note = research(db, project_id=project_id, question=question, source=LocalCorpusSource())

    sources = note.sources
    # The zero-relevance distractor is dropped; 3 sources ranked.
    assert len(sources) == 3
    refs = [s["ref"] for s in sources]
    assert "vault/repos/logging.md" not in refs

    # Relevance dominates: the full-coverage decision ranks #1 despite lower tier.
    assert sources[0]["relevance"] == 1.0
    assert sources[0]["tier"] == "maintainer-discussion"
    # Quality breaks the tie between the two 0.8-relevance sources: the
    # reference-implementation distillation (0.85) outranks the decision (0.6).
    assert sources[1]["ref"] == "vault/repos/asyncpg.md"
    assert sources[1]["tier"] == "reference-implementation"
    assert sources[2]["tier"] == "maintainer-discussion"
    assert sources[1]["relevance"] == sources[2]["relevance"] == 0.8
    assert sources[1]["composite"] > sources[2]["composite"]  # quality tie-break

    # Full documented provenance on every ranked source.
    for s in sources:
        assert set(s) >= {
            "ref", "title", "tier", "tier_rank", "quality", "relevance", "matched_terms", "label",
        }
        assert s["matched_terms"]  # non-empty for a ranked (relevant) source

    # Findings each cite a source.
    assert note.findings
    for f in note.findings:
        assert f["source_ref"] in refs
        assert f["tier"] and f["label"]

    # Calibrated confidence: a strong top match is intuitive and NOT near-zero.
    assert note.confidence >= 0.85
    assert note.confidence <= 1.0

    # Community is labelled 'opinion' in the ladder (the Research Engine principle).
    assert SOURCE_TIERS["community"].label == "opinion"
    # tier_rank ordering is authoritative-first.
    assert SOURCE_TIERS["official-docs"].tier_rank < SOURCE_TIERS["community"].tier_rank


# --- 2. LES-019 close: research clears a council abstention ------------------


class _StubResearchSource:
    """An injected research corpus (simulating the web / broader knowledge a
    later slice would fetch) that is NOT one of the council-visible local rows.

    This lets the BASELINE be genuinely research-class-empty (no notes, no
    decisions, no distillations → research_librarian starts empty) while research()
    still does real work: it scores these documents and synthesizes a substantive
    note. The persisted note is the new research-class evidence the council reads.
    """

    def __init__(self, docs):
        self._docs = docs

    def gather(self, db, *, project_id, question, sensitivity, limit):
        return list(self._docs)


def _research_empty_structural_baseline(db) -> str:
    """A project with STRUCTURAL evidence only (a scan/DNA) and NO research class.

    architecture + fitness each get exactly one evidence item (deterministic
    confidence 0.5 each); research_librarian and security get nothing. The
    4-agent mean = (0 + 0.5 + 0.5 + 0) / 4 = 0.25, which is below the 0.35
    abstention floor — so the real Final Judge abstains for want of the research
    class, even though structural evidence is present. This is the LES-019
    scenario (a structural scan is the wrong evidence class for the question).
    """
    project = Project(name="StructuralOnly", slug="structural-only")
    db.add(project)
    db.flush()
    repo = Repository(project_id=project.id, name="svc", local_path="svc")
    db.add(repo)
    db.flush()
    db.add(
        RepositoryDNA(
            repository_id=repo.id,
            language_mix={"python": 1.0},        # fitness: 1 item -> conf 0.5
            frameworks=[],
            package_managers=[],
            runtime_services=["postgres"],       # architecture: 1 item -> conf 0.5
            risk_flags=[],                        # security: empty -> conf 0.0
            maturity=None,
        )
    )
    db.commit()
    return project.id


def test_research_run_clears_council_abstention(db):
    project_id = _research_empty_structural_baseline(db)
    question = "Should we adopt asyncpg for postgres access in the service?"

    # BASELINE — the REAL council over the research-empty project. It must abstain,
    # and it must abstain on CONFIDENCE (structural evidence is present, so the
    # abstention is driven by the sub-floor mean, not a zero evidence count).
    baseline = run_council(db, project_id=project_id, question=question, provider=DeterministicProvider())
    assert baseline.verdict == "Insufficient evidence"
    assert baseline.confidence < ABSTAIN_CONFIDENCE
    baseline_total_evidence = sum(len(o.evidence or []) for o in baseline.agent_outputs)
    assert baseline_total_evidence >= 1  # structural evidence present, research absent

    baseline_rl = next(o for o in baseline.agent_outputs if o.agent_name == "research_librarian")
    assert baseline_rl.status == "Needs Evidence"
    assert baseline_rl.confidence == 0.0
    assert not baseline_rl.evidence  # research class genuinely empty at baseline

    # RESEARCH — add research-class evidence by scoring a real (injected) corpus
    # and persisting a substantive note.
    docs = [
        SourceDoc(
            ref="https://magicstack.github.io/asyncpg/",
            title="asyncpg official docs",
            text="asyncpg postgres async driver connection pooling adopt",
            tier="official-docs",
        ),
        SourceDoc(
            ref="https://example.com/asyncpg-benchmark",
            title="asyncpg vs psycopg benchmark",
            text="asyncpg postgres benchmark throughput adopt",
            tier="benchmark-paper",
        ),
    ]
    note = research(
        db, project_id=project_id, question=question, sensitivity=Sensitivity.PUBLIC,
        source=_StubResearchSource(docs),
    )
    # The note is substantive (real scoring, real citing findings, non-zero conf).
    assert note.sources and note.findings
    assert note.confidence > 0.0

    # POST-RESEARCH — the same real council on the same question. The persisted
    # research note lifts research_librarian to Complete/confident, the mean clears
    # the floor, total_evidence rises, and the verdict is no longer an abstention.
    after = run_council(db, project_id=project_id, question=question, provider=DeterministicProvider())
    after_rl = next(o for o in after.agent_outputs if o.agent_name == "research_librarian")
    assert after_rl.status == "Complete"
    assert after_rl.confidence > 0.0
    assert after_rl.evidence  # research class now non-empty

    after_total_evidence = sum(len(o.evidence or []) for o in after.agent_outputs)
    assert after_total_evidence > baseline_total_evidence

    assert after.verdict != "Insufficient evidence"
    assert after.confidence >= ABSTAIN_CONFIDENCE


# --- 3. privacy guardrail in code ------------------------------------------


def test_private_never_routes_to_free_hosted():
    """route('research', PRIVATE, ...) never resolves to the FREE_HOSTED tier —
    even when a free tier IS configured (so the guardrail is what strips it)."""
    import types

    # A free hosted tier is available (a key is configured) — PUBLIC would use it.
    settings = types.SimpleNamespace(
        llm_base_url="",
        llm_model="",
        llm_free_base_url="https://api.groq.com/openai/v1",
        llm_free_model="llama-3.3-70b-versatile",
        llm_free_api_key="configured-key",
        llm_claude_enabled=False,
    )

    # PUBLIC would route to FREE_HOSTED (proving it is genuinely available)...
    public = route("research", Sensitivity.PUBLIC, settings)
    assert public.tier is Tier.FREE_HOSTED

    # ...but PRIVATE must never — the guardrail strips it.
    private = route("research", Sensitivity.PRIVATE, settings)
    assert private.tier is not Tier.FREE_HOSTED


# --- 4. tolerant: empty corpus / empty question ----------------------------


def test_empty_corpus_graceful(db):
    """An empty corpus / empty question persists a 'no evidence' note (explicit
    open question, confidence 0.0) and never raises."""
    project_id = _project(db, name="EmptyCorpus")

    # Empty corpus (no pages/notes/decisions), non-empty question.
    note = research(db, project_id=project_id, question="Anything to know here?", source=LocalCorpusSource())
    assert isinstance(note, ResearchNote)
    assert note.sources == []
    assert note.findings == []
    assert note.confidence == 0.0
    assert "no local evidence" in note.summary.lower()

    # Empty question too — still graceful, still persisted, still 0.0.
    note2 = research(db, project_id=project_id, question="", source=LocalCorpusSource())
    assert note2.confidence == 0.0
    assert note2.sources == []
