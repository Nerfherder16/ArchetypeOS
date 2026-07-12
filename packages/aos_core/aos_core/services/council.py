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

from ..llm import InstrumentedProvider
from .llm_router import Sensitivity, routed_provider
from ..models import (
    ArchitectureEdge,
    ArchitectureNode,
    CouncilAgentOutput,
    CouncilReview,
    Decision,
    KnowledgePage,
    Project,
    RepositoryDNA,
    ResearchNote,
    Repository,
)
from .llm_pool import free_pool_provider

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


def _select_distillation(db: Session, project_id: str) -> list[dict]:
    """Repository distillation pages (RFC-0008) surfaced as research evidence.

    Content-extraction pages (``page_type="repository"``) let a content-rich but
    structurally-thin repo produce substance instead of a fingerprint abstention.
    Tolerant: no distillation → no items.
    """
    items: list[dict] = []
    for page in (
        db.query(KnowledgePage)
        .filter(KnowledgePage.project_id == project_id, KnowledgePage.page_type == "repository")
        .order_by(KnowledgePage.updated_at.desc(), KnowledgePage.id)
        .limit(10)
        .all()
    ):
        items.append({"kind": "repo_distillation", "detail": page.title, "ref": page.vault_path})
    return items


def _select_research_librarian(db: Session, project_id: str) -> list[dict]:
    """Research evidence + repository distillations for the Research Librarian."""
    return _select_research(db, project_id) + _select_distillation(db, project_id)


def _select_architecture(db: Session, project_id: str) -> list[dict]:
    # AOS-ARCH-STUDIO-001 (Finding 7): the Council reasons over the operator's
    # CORRECTED architecture, not just the raw scanner output. Every corrected node
    # is always included (corrections are the operator's explicit signal) alongside
    # the most recent nodes, and the correction text is surfaced in the detail so a
    # persona can cite it. Corrected edges are cited too.
    items: list[dict] = []
    recent_nodes = (
        db.query(ArchitectureNode)
        .filter(ArchitectureNode.project_id == project_id)
        .order_by(ArchitectureNode.created_at.desc(), ArchitectureNode.id)
        .limit(20)
        .all()
    )
    corrected_nodes = (
        db.query(ArchitectureNode)
        .filter(ArchitectureNode.project_id == project_id, ArchitectureNode.manual_correction.isnot(None))
        .order_by(ArchitectureNode.id)
        .all()
    )
    seen: set[str] = set()
    for node in [*corrected_nodes, *recent_nodes]:
        if node.id in seen:
            continue
        seen.add(node.id)
        detail = f"{node.type}: {node.label}"
        item = {"kind": "architecture_node", "detail": detail, "ref": f"node:{node.id}"}
        if node.manual_correction:
            item["detail"] = f"{detail} (operator correction: {node.manual_correction})"
            item["corrected"] = True
        items.append(item)

    node_labels = {node.id: node.label for node in [*corrected_nodes, *recent_nodes]}

    def _label(node_id: str) -> str:
        if node_id in node_labels:
            return node_labels[node_id]
        node = db.get(ArchitectureNode, node_id)
        return node.label if node else node_id

    for edge in (
        db.query(ArchitectureEdge)
        .filter(ArchitectureEdge.project_id == project_id, ArchitectureEdge.manual_correction.isnot(None))
        .order_by(ArchitectureEdge.id)
        .all()
    ):
        src, dst = _label(edge.from_node_id), _label(edge.to_node_id)
        items.append(
            {
                "kind": "architecture_edge",
                "detail": f"{src} -> {dst} ({edge.type}) - operator correction: {edge.manual_correction}",
                "ref": f"edge:{edge.id}",
                "corrected": True,
            }
        )

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
        "evidence_selector": _select_research_librarian,
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
        "summary (string), "
        "findings (array of typed items: {'kind': string, 'detail': string, 'ref': string or null} "
        "— kind labels the item, e.g. 'finding'/'structural'/'risk'; detail is a short single-line "
        "claim; ref optionally cites a supplied evidence item's own 'ref'), "
        "evidence (array of the same typed-item shape — one per supplied evidence item you relied "
        "on, citing its 'ref' where possible), "
        "concerns (array of the same typed-item shape), "
        "confidence (0.0-1.0 number), "
        "status (one of Complete, Needs Evidence, Escalated, Rejected). "
        "A plain string is also accepted anywhere a typed item is expected and is treated as that "
        "item's 'detail' with no ref."
    )


def _coerce_list(value) -> list:
    if isinstance(value, list):
        return value
    if value in (None, ""):
        return []
    return [value]


def _coerce_finding_item(item, default_kind: str) -> dict:
    """Coerce one findings/evidence/concerns entry into a typed ``{kind, detail, ref}`` item.

    RFC-0016 §11 (AOS-COUNCIL-TYPED-001): the evidence selectors and the
    deterministic provider already speak typed items; a real-model agent (or
    old stored data) may still hand back a plain string. Both are accepted and
    normalized to the same shape — never raises on an unexpected input.
    """
    if isinstance(item, dict):
        detail = item.get("detail")
        if detail in (None, ""):
            detail = item.get("text") or item.get("summary") or ""
        ref = item.get("ref")
        return {
            "kind": str(item.get("kind") or default_kind),
            "detail": str(detail),
            "ref": str(ref) if ref not in (None, "") else None,
        }
    return {"kind": default_kind, "detail": str(item), "ref": None}


def _coerce_items(value, default_kind: str) -> list[dict]:
    """Coerce a findings/evidence/concerns list into typed ``{kind, detail, ref}`` items."""
    return [_coerce_finding_item(item, default_kind) for item in _coerce_list(value) if item not in (None, "")]


def _item_text(item) -> str:
    """Human-readable text for one findings/evidence/concerns entry.

    Tolerant of both shapes: a typed ``{kind, detail, ref}`` object (post
    RFC-0016 §11) and a plain string (pre-existing rows, or an agent that
    ignored the typed contract). Never raises.
    """
    if isinstance(item, dict):
        detail = item.get("detail")
        return str(detail) if detail is not None else str(item)
    return str(item)


def _loads_tolerant(text: str):
    """Best-effort parse of provider text into a JSON object.

    Real Claude output (``claude -p --output-format json`` → ``.result``) often
    wraps the structured answer in a Markdown code fence (```` ```json … ``` ````)
    or prefixes it with prose, which defeats a bare ``json.loads``. Layered
    recovery (LES-018, self-found on the first real Council run over pydantic-ai):

    1. parse as-is,
    2. strip a leading/trailing Markdown code fence and re-parse,
    3. slice from the first ``{`` to the last ``}`` and re-parse.

    Returns the decoded ``dict`` or ``None`` if no layer yields a JSON object.
    """

    def _try(candidate: str):
        try:
            obj = json.loads(candidate)
        except Exception:
            return None
        return obj if isinstance(obj, dict) else None

    stripped = text.strip()
    for candidate in (stripped, _strip_code_fence(stripped)):
        obj = _try(candidate)
        if obj is not None:
            return obj

    fenceless = _strip_code_fence(stripped)
    start, end = fenceless.find("{"), fenceless.rfind("}")
    if start != -1 and end > start:
        obj = _try(fenceless[start : end + 1])
        if obj is not None:
            return obj
    return None


def _strip_code_fence(text: str) -> str:
    """Remove a single leading/trailing Markdown code fence, if present."""
    s = text.strip()
    if not s.startswith("```"):
        return s
    lines = s.splitlines()
    lines = lines[1:]  # drop the opening ```/```json line
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]  # drop the closing fence
    return "\n".join(lines).strip()


def _parse_agent_output(text: str) -> dict:
    """Tolerantly parse a provider's text into the agent-output shape.

    Unparseable prose → ``status="Needs Evidence"``, low confidence, raw text in
    ``summary``, empty lists. Both providers flow through this one parser.
    """
    obj = _loads_tolerant(text)
    if obj is None:
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
        "findings": _coerce_items(obj.get("findings"), "finding"),
        "evidence": _coerce_items(obj.get("evidence"), "evidence"),
        "concerns": _coerce_items(obj.get("concerns"), "concern"),
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
                follow_up.append(f"Verify: {_item_text(concern)}")
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
            follow_up.append(f"Address: {_item_text(concern)}")

    return {
        "verdict": verdict,
        "confidence": aggregate_confidence,
        "agreements": agreements,
        "disagreements": disagreements,
        "unsupported_claims": unsupported_claims,
        "follow_up": follow_up,
    }


def council_provider(settings, sink=None):
    """Pick the council's provider.

    When multi-model is enabled (``council_multi_model``) and the free pool has
    >=2 members, return the rotation pool — each agent then draws a DIFFERENT
    model from it (genuine diversity; RFC-0005) with per-member failover. Claude
    stays the Final Judge (the deterministic synthesis here; a real-model Final
    Judge is opt-in via ``llm_provider``/``llm_claude_enabled``). Otherwise fall
    back to the single configured provider. The privacy guardrail lives in the
    router; the council must only be invoked with non-private evidence when the
    pool is in use.

    When a usage ``sink`` is supplied (AOS-USAGE-001) the chosen provider is
    instrumented so each agent call records a usage event: the single-provider
    path defers to ``routed_provider`` (cheap-first tier selection), and the
    multi-model pool is wrapped here in :class:`InstrumentedProvider`.
    """
    if getattr(settings, "council_multi_model", False):
        pool = free_pool_provider()
        if pool is not None and len(pool) >= 2:
            return InstrumentedProvider(pool, sink) if sink is not None else pool
    return routed_provider("council_agent", Sensitivity.PUBLIC, settings, sink=sink)


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
                # The model that produced THIS agent's output — a multi-model
                # council (a rotating pool) records a different model per agent.
                agent_model=getattr(result, "model", None),
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
    "council_provider",
    "run_council",
    "synthesize_verdict",
]
