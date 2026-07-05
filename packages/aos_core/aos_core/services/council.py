"""Agent Council + Final Judge (RFC-0005 Phase 1).

Four MVP personas — Research Librarian, Architecture Cartographer, Technology
Fitness Judge, Security Agent — each read the project's latest scan / DNA /
decisions as evidence, are run through a :class:`~aos_core.llm.Provider`, and
emit a structured :class:`CouncilAgentOutput`. A rule-based **Final Judge**
(:func:`synthesize_verdict`) then synthesizes those outputs into a governed
:class:`CouncilReview`: points of agreement / disagreement, unsupported claims,
aggregate confidence, follow-up, and a verdict from the documented set — with an
**abstention** to ``Insufficient evidence`` when evidence/confidence is thin.

The *first-pass reasoning* is the provider (swappable, possibly probabilistic);
the *judgment rules* are code (deterministic + auditable). Council output is
advisory only — it drafts, it never approves or acts.
"""

from __future__ import annotations

import json

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models import (
    ArchitectureNode,
    CouncilAgentOutput,
    CouncilReview,
    Decision,
    Project,
    RepositoryDNA,
    ResearchNote,
    Repository,
)

# Final Judge abstention floors (RFC-0005 Open Question 3 — conservative,
# documented, tunable later behind an Arbiter/AuthorityGrant config).
ABSTAIN_CONFIDENCE = 0.35
MIN_EVIDENCE = 1

# The documented verdict vocabulary (docs/ARBITER_FINAL_JUDGE.md).
VERDICTS = (
    "Accept",
    "Accept with warnings",
    "Reject",
    "Defer",
    "Research further",
    "Simulate first",
    "Escalate to human",
    "Insufficient evidence",
)


# --- evidence selectors ----------------------------------------------------
# Each returns a list of evidence items {kind, detail, ref} for one persona,
# read from durable rows already in the DB. Details are short, single-line.


def _project_dna(db: Session, project_id: str) -> list[RepositoryDNA]:
    return (
        db.query(RepositoryDNA)
        .join(Repository, RepositoryDNA.repository_id == Repository.id)
        .filter(Repository.project_id == project_id)
        .order_by(RepositoryDNA.updated_at.desc(), RepositoryDNA.id)
        .all()
    )


def _select_research(db: Session, project_id: str) -> list[dict]:
    items: list[dict] = []
    for note in (
        db.query(ResearchNote)
        .filter(ResearchNote.project_id == project_id)
        .order_by(ResearchNote.created_at.desc(), ResearchNote.id)
        .limit(10)
        .all()
    ):
        items.append({"kind": "research_note", "detail": note.title, "ref": f"research_note:{note.id}"})
    for decision in (
        db.query(Decision)
        .filter(Decision.project_id == project_id)
        .order_by(Decision.created_at.desc(), Decision.id)
        .limit(10)
        .all()
    ):
        items.append({"kind": "decision", "detail": decision.title, "ref": f"decision:{decision.id}"})
    return items


def _select_architecture(db: Session, project_id: str) -> list[dict]:
    items: list[dict] = []
    for node in (
        db.query(ArchitectureNode)
        .filter(ArchitectureNode.project_id == project_id)
        .order_by(ArchitectureNode.created_at.desc(), ArchitectureNode.id)
        .limit(20)
        .all()
    ):
        items.append({"kind": "architecture_node", "detail": f"{node.type}: {node.label}", "ref": f"node:{node.id}"})
    for dna in _project_dna(db, project_id):
        for framework in dna.frameworks or []:
            items.append({"kind": "framework", "detail": str(framework), "ref": f"dna:{dna.id}"})
        for service in dna.runtime_services or []:
            items.append({"kind": "runtime_service", "detail": str(service), "ref": f"dna:{dna.id}"})
    return items


def _select_fitness(db: Session, project_id: str) -> list[dict]:
    items: list[dict] = []
    for dna in _project_dna(db, project_id):
        for language in (dna.language_mix or {}):
            items.append({"kind": "language", "detail": str(language), "ref": f"dna:{dna.id}"})
        for framework in dna.frameworks or []:
            items.append({"kind": "framework", "detail": str(framework), "ref": f"dna:{dna.id}"})
        for manager in dna.package_managers or []:
            items.append({"kind": "package_manager", "detail": str(manager), "ref": f"dna:{dna.id}"})
        if dna.maturity:
            items.append({"kind": "maturity", "detail": str(dna.maturity), "ref": f"dna:{dna.id}"})
    return items


def _select_security(db: Session, project_id: str) -> list[dict]:
    items: list[dict] = []
    for dna in _project_dna(db, project_id):
        for flag in dna.risk_flags or []:
            items.append({"kind": "risk_flag", "detail": str(flag), "ref": f"dna:{dna.id}"})
    for decision in (
        db.query(Decision)
        .filter(Decision.project_id == project_id)
        .order_by(Decision.created_at.desc(), Decision.id)
        .limit(20)
        .all()
    ):
        text = f"{decision.title} {decision.context or ''}".lower()
        if any(word in text for word in ("security", "auth", "secret", "vuln", "cve", "encrypt")):
            items.append({"kind": "security_decision", "detail": decision.title, "ref": f"decision:{decision.id}"})
    return items


DEFAULT_AGENTS = [
    {
        "name": "research_librarian",
        "agent_type": "research",
        "system_prompt": (
            "You are the Research Librarian. Assess the question strictly from the supplied "
            "evidence (research notes and recorded decisions). Evidence over opinion; do not "
            "invent sources. Return findings you can support and flag gaps as concerns."
        ),
        "evidence_selector": _select_research,
    },
    {
        "name": "architecture_cartographer",
        "agent_type": "architecture",
        "system_prompt": (
            "You are the Architecture Cartographer. Assess system structure from the supplied "
            "architecture nodes, frameworks, and runtime services. Report structural findings; "
            "flag missing or risky structure as concerns."
        ),
        "evidence_selector": _select_architecture,
    },
    {
        "name": "technology_fitness_judge",
        "agent_type": "fitness",
        "system_prompt": (
            "You are the Technology Fitness Judge. Assess technology fitness from the supplied "
            "language mix, frameworks, package managers, and maturity signals. Fitness over "
            "familiarity; flag poor-fit or unsupported technology as concerns."
        ),
        "evidence_selector": _select_fitness,
    },
    {
        "name": "security_agent",
        "agent_type": "security",
        "system_prompt": (
            "You are the Security Agent. Assess security posture from the supplied risk flags and "
            "security-relevant decisions. Any risk flag is a concern until mitigated."
        ),
        "evidence_selector": _select_security,
    },
]


def _build_prompt(agent: dict, question: str, evidence_items: list[dict]) -> str:
    # Evidence is emitted as a single-line JSON array so a deterministic provider
    # can parse it back verbatim; details are short and newline-free.
    return (
        f"Question: {question}\n"
        f"Persona: {agent['name']}\n"
        "Evidence (JSON array):\n"
        f"{json.dumps(evidence_items)}\n"
        "\n"
        "Respond ONLY with a JSON object with keys: "
        "summary (string), findings (array of strings), evidence (array of strings), "
        "concerns (array of strings), confidence (0.0-1.0 number), "
        "status (one of Complete, Needs Evidence, Escalated, Rejected)."
    )


def _coerce_list(value) -> list:
    if isinstance(value, list):
        return value
    if value in (None, ""):
        return []
    return [value]


def _parse_agent_output(text: str) -> dict:
    """Tolerantly parse a provider's text into the agent-output shape.

    Unparseable prose → ``status="Needs Evidence"``, low confidence, raw text in
    ``summary``, empty lists. Both providers flow through this one parser.
    """
    try:
        obj = json.loads(text)
        if not isinstance(obj, dict):
            raise ValueError("not a JSON object")
    except Exception:
        return {
            "summary": text.strip(),
            "findings": [],
            "evidence": [],
            "concerns": [],
            "confidence": 0.05,
            "status": "Needs Evidence",
        }
    try:
        confidence = float(obj.get("confidence", 0.0) or 0.0)
    except (TypeError, ValueError):
        confidence = 0.0
    return {
        "summary": str(obj.get("summary") or ""),
        "findings": _coerce_list(obj.get("findings")),
        "evidence": _coerce_list(obj.get("evidence")),
        "concerns": _coerce_list(obj.get("concerns")),
        "confidence": max(0.0, min(1.0, confidence)),
        "status": str(obj.get("status") or "Complete"),
    }


def _stance(output: CouncilAgentOutput) -> str:
    if not output.evidence or output.status == "Needs Evidence":
        return "uncertain"
    if output.concerns:
        return "unfavorable"
    return "favorable"


def synthesize_verdict(outputs: list[CouncilAgentOutput]) -> dict:
    """Final Judge: deterministic, rule-based synthesis over the agent outputs."""
    total_evidence = sum(len(output.evidence or []) for output in outputs)
    confidences = [output.confidence for output in outputs]
    aggregate_confidence = round(sum(confidences) / len(confidences), 4) if confidences else 0.0

    favorable = [o.agent_name for o in outputs if _stance(o) == "favorable"]
    unfavorable = [o.agent_name for o in outputs if _stance(o) == "unfavorable"]
    uncertain = [o.agent_name for o in outputs if _stance(o) == "uncertain"]

    # Unsupported claims: findings asserted by an agent that offered no evidence.
    unsupported_claims: list[dict] = []
    for output in outputs:
        if output.findings and not output.evidence:
            for finding in output.findings:
                unsupported_claims.append({"agent": output.agent_name, "claim": finding})

    agreements: list[dict] = []
    if len(favorable) >= 2:
        agreements.append({"point": "no blocking concerns", "agents": favorable})
    if len(unfavorable) >= 2:
        agreements.append({"point": "concerns identified", "agents": unfavorable})

    disagreements: list[dict] = []
    if favorable and unfavorable:
        disagreements.append(
            {
                "topic": "overall assessment",
                "favorable": favorable,
                "unfavorable": unfavorable,
            }
        )

    # Abstention floor.
    if total_evidence < MIN_EVIDENCE or aggregate_confidence < ABSTAIN_CONFIDENCE:
        follow_up = [
            "Gather primary evidence for this project (run a repository scan, capture DNA, or record decisions).",
            "Re-run the council once evidence confidence clears the abstention floor.",
        ]
        for output in outputs:
            for concern in output.concerns or []:
                follow_up.append(f"Verify: {concern}")
        return {
            "verdict": "Insufficient evidence",
            "confidence": aggregate_confidence,
            "agreements": agreements,
            "disagreements": disagreements,
            "unsupported_claims": unsupported_claims,
            "follow_up": follow_up,
        }

    if favorable and unfavorable:
        verdict = "Escalate to human"
    elif favorable and not unfavorable:
        verdict = "Accept"
    elif unfavorable and not favorable:
        # Consensus concern with no dissent: warn if partial, reject if unanimous.
        verdict = "Reject" if not uncertain else "Accept with warnings"
    else:
        verdict = "Defer"

    follow_up = []
    for output in outputs:
        for concern in output.concerns or []:
            follow_up.append(f"Address: {concern}")

    return {
        "verdict": verdict,
        "confidence": aggregate_confidence,
        "agreements": agreements,
        "disagreements": disagreements,
        "unsupported_claims": unsupported_claims,
        "follow_up": follow_up,
    }


def run_council(db: Session, *, project_id: str, question: str, provider, agents=DEFAULT_AGENTS) -> CouncilReview:
    """Run the council over a project and persist an auditable review.

    404-guards the project, runs each agent through ``provider``, synthesizes a
    Final Judge verdict, persists the ``CouncilReview`` + ``CouncilAgentOutput``
    rows, commits, and returns the review.
    """
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    outputs: list[CouncilAgentOutput] = []
    provider_name = getattr(provider, "name", type(provider).__name__)
    for agent in agents:
        evidence_items = agent["evidence_selector"](db, project_id)
        prompt = _build_prompt(agent, question, evidence_items)
        result = provider.generate(system=agent["system_prompt"], prompt=prompt)
        provider_name = result.provider or provider_name
        parsed = _parse_agent_output(result.text)
        outputs.append(
            CouncilAgentOutput(
                agent_name=agent["name"],
                agent_type=agent["agent_type"],
                status=parsed["status"],
                summary=parsed["summary"],
                findings=parsed["findings"],
                evidence=parsed["evidence"],
                concerns=parsed["concerns"],
                confidence=parsed["confidence"],
            )
        )

    synthesis = synthesize_verdict(outputs)
    review = CouncilReview(
        project_id=project_id,
        question=question,
        verdict=synthesis["verdict"],
        confidence=synthesis["confidence"],
        agreements=synthesis["agreements"],
        disagreements=synthesis["disagreements"],
        unsupported_claims=synthesis["unsupported_claims"],
        follow_up=synthesis["follow_up"],
        provider=provider_name,
        agent_outputs=outputs,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


__all__ = [
    "ABSTAIN_CONFIDENCE",
    "MIN_EVIDENCE",
    "VERDICTS",
    "DEFAULT_AGENTS",
    "run_council",
    "synthesize_verdict",
]
