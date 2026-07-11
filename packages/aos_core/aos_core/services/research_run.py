"""The research-run executor (AOS-RESEARCH-003, acceptance criteria 2-5).

Executes a persisted :class:`ResearchPlan` through the phases plan → search →
fetch → verify → synthesize, reusing the deterministic research engine
(:mod:`aos_core.services.research`) for gathering, ranking, and synthesis rather
than reimplementing it. It records:

- every source it considered, each with an accept/reject decision AND a reason
  (criterion 2);
- findings that cite accepted sources (criterion 4);
- conflicting evidence, kept visible as its own field (criterion 3);
- open questions, each of which is turned into a follow-up ResearchPlan
  (criterion 5).

Deterministic and hermetic — same plan + same corpus → same run.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import ResearchNote, ResearchPlan, ResearchRun
from .llm_router import Sensitivity
from .research import LocalCorpusSource, _rank, synthesize_dossier

# Gather at most this many candidate sources from the local corpus per run.
_GATHER_LIMIT = 25


def _title_for(question: str) -> str:
    """Derive a ResearchNote title from a question, truncated to fit String(255).

    Mirrors the ``research.py`` convention (:func:`aos_core.services.research._title_for`)
    so a deep run's note reads the same as the deterministic-floor's note.
    """
    q = (question or "").strip()
    if not q:
        return "Research: (no question provided)"
    return f"Research: {q}"[:255]


def _decide_sources(ranked: list[dict], gathered_refs: list[str], top_n: int) -> list[dict]:
    """Attach an accept/reject decision + reason to every considered source.

    Accepted: the top-N ranked sources (what synthesis cites). Rejected: ranked
    sources below the cut ("below the top-N relevance cut"), plus gathered sources
    that scored zero relevance and never entered the ranking ("does not address
    the question").
    """
    decided: list[dict] = []
    ranked_refs = set()
    for index, entry in enumerate(ranked):
        ranked_refs.add(entry["ref"])
        accepted = index < top_n
        decided.append(
            {
                "ref": entry["ref"],
                "title": entry["title"],
                "tier": entry["tier"],
                "score": entry["composite"],
                "accepted": accepted,
                "reason": None if accepted else "below the top-N relevance cut",
            }
        )
    for ref in gathered_refs:
        if ref not in ranked_refs:
            decided.append(
                {
                    "ref": ref,
                    "title": ref,
                    "tier": None,
                    "score": 0.0,
                    "accepted": False,
                    "reason": "does not address the question (no relevance to the query)",
                }
            )
    return decided


def execute_research_run(
    db: Session, plan: ResearchPlan, *, job_id: str | None = None
) -> ResearchRun:
    """Run a plan end to end, persist the ResearchRun, and spawn follow-up plans."""
    question = plan.question
    top_n = int((plan.synthesis_policy or {}).get("top_n", 3))
    try:
        sensitivity = Sensitivity(plan.sensitivity)
    except ValueError:
        sensitivity = Sensitivity.PUBLIC

    phases: list[dict] = [{"phase": "plan", "detail": f"{len(plan.search_queries)} queries planned"}]

    # search + fetch: the local-corpus source gathers candidate documents (the
    # floor's fetch is the DB read; a network tier plugs in behind the same call).
    sources = LocalCorpusSource().gather(
        db, project_id=plan.project_id, question=question, sensitivity=sensitivity, limit=_GATHER_LIMIT
    )
    gathered_refs = [s.ref for s in sources]
    phases.append({"phase": "search", "detail": f"{len(plan.search_queries)} queries over local corpus"})
    phases.append({"phase": "fetch", "detail": f"gathered {len(sources)} candidate sources"})

    # verify: rank + decide accept/reject with reasons.
    ranked = _rank(question, sources)
    decided = _decide_sources(ranked, gathered_refs, top_n)
    accepted_count = sum(1 for s in decided if s["accepted"])
    phases.append(
        {"phase": "verify", "detail": f"{accepted_count} accepted, {len(decided) - accepted_count} rejected"}
    )

    # synthesize: findings cite accepted sources; conflicts stay visible.
    dossier = synthesize_dossier(question, ranked, top_n=top_n)
    phases.append({"phase": "synthesize", "detail": f"{len(dossier['findings'])} findings"})

    run = ResearchRun(
        plan_id=plan.id,
        project_id=plan.project_id,
        job_id=job_id,
        run_status="completed",
        phases=phases,
        sources=decided,
        findings=dossier["findings"],
        conflicts=dossier.get("conflicting_evidence", []),
        open_questions=dossier.get("open_questions", []),
        confidence=float(dossier.get("confidence", 0.0)),
    )
    db.add(run)

    # AOS-RESEARCH-COUNCIL-001: mirror the run into a ResearchNote so the Agent
    # Council's evidence selector (which reads ResearchNote, not ResearchRun) picks
    # up deep multi-phase research too. Only when the run belongs to a job — a
    # get-or-create keyed on job_id keeps this idempotent under job redelivery and
    # respects the table's own uq_research_notes_job_id constraint. A direct call
    # with no job_id leaves behavior unchanged (no note).
    if job_id is not None:
        note = db.query(ResearchNote).filter(ResearchNote.job_id == job_id).one_or_none()
        if note is None:
            db.add(
                ResearchNote(
                    project_id=plan.project_id,
                    title=_title_for(question),
                    question=question,
                    summary=dossier["summary"],
                    sources=decided,
                    findings=dossier["findings"],
                    freshness=dossier["freshness"],
                    confidence=float(dossier.get("confidence", 0.0)),
                    job_id=job_id,
                )
            )

    # criterion 5: each open question becomes a follow-up plan.
    for open_question in run.open_questions:
        follow_up = ResearchPlan(
            project_id=plan.project_id,
            question=open_question,
            sensitivity=plan.sensitivity,
            plan_status="follow_up",
            required_source_types=list(plan.required_source_types),
            search_queries=[open_question],
            verification_steps=list(plan.verification_steps),
            synthesis_policy=dict(plan.synthesis_policy),
        )
        db.add(follow_up)

    plan.plan_status = "researched"
    db.commit()
    db.refresh(run)
    return run
