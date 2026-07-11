"""Decision → Plan (RFC-0015 Design §1, AOS-BUILD-PLAN-001).

An approved :class:`~aos_core.models.Decision` becomes a governed, **draft-only**
:class:`~aos_core.models.ImplementationPlan` that a named human then approves —
the right-of-decision half of the Build Intelligence loop opened without
introducing any code execution (that is AOS-BUILD-EXEC-001).

``plan_from_decision`` requires ``decision.status == "approved"`` (else 409,
mirroring ``services.decisions.approve_decision``'s status gate) and drafts the
plan's objective/tasks/acceptance criteria by running the routed
:class:`~aos_core.llm.Provider` over the decision's ``context``/``decision``/
``consequences``/``evidence``, then tolerantly parsing the result (reusing
``services.council._loads_tolerant``, the same tolerant-JSON parser
``distillation.py`` and ``verifier.py`` already share). When the provider
output does not parse into a usable plan shape — always true for the
hermetic ``DeterministicProvider`` CI runs on, whose generic council-shaped
JSON carries no ``objective``/``tasks`` key — a **deterministic fallback**
derives a minimal plan directly from the decision's own fields, so CI stays
hermetic and a malformed real-provider reply never yields an empty plan.

Idempotent via ``meta["decision_id"]`` (mirrors
``services.decisions.draft_decision_from_review``'s ``meta["council_review_id"]``
pattern): a second call for the same decision returns the existing plan rather
than drafting a duplicate.

``approve_plan`` transitions a ``draft`` plan to ``approved`` (else 409) and
writes an :class:`~aos_core.models.ApprovalRecord` (``requested_capability=
"plan.approve"``), mirroring ``approve_decision``.
"""

from __future__ import annotations

import json

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import ApprovalRecord, Decision, ImplementationPlan, now_utc
from .council import _loads_tolerant
from .llm_router import Sensitivity, routed_provider

# Status vocabulary (via AuditMixin.status — no new column), mirroring Decision.
PLAN_DRAFT = "draft"
PLAN_APPROVED = "approved"
PLAN_REJECTED = "rejected"
PLAN_SUPERSEDED = "superseded"

_TITLE_MAX = 255

_PLAN_SYSTEM_PROMPT = (
    "You are a build-planning agent. Reason ONLY from the supplied decision "
    "context, decision, consequences, and evidence — do not invent scope beyond "
    "it. Produce a concrete, verifiable implementation plan."
)


def _title_for(decision: Decision) -> str:
    base = (decision.title or "").strip() or "Untitled decision"
    title = f"Plan: {base}"
    if len(title) <= _TITLE_MAX:
        return title
    return title[: _TITLE_MAX - 1].rstrip() + "…"


def _existing_plan(db: Session, decision_id: str) -> ImplementationPlan | None:
    """Return a plan already drafted from this decision, if any (idempotency)."""
    for plan in (
        db.query(ImplementationPlan)
        .filter(ImplementationPlan.decision_id == decision_id)
        .order_by(ImplementationPlan.created_at, ImplementationPlan.id)
        .all()
    ):
        meta = plan.meta or {}
        if meta.get("decision_id") == decision_id:
            return plan
    return None


def _deterministic_plan(decision: Decision) -> dict:
    """A minimal plan derived directly from the decision's own fields (no model).

    One task per recorded consequence (or a single task from the decision text
    when there are none), each with a matching acceptance criterion; risk is
    summarized from the decision's tradeoffs. This is the CI-hermetic floor —
    always correct, never fabricated.
    """
    objective = (decision.decision or decision.title or "").strip() or "Implement the approved decision."
    consequences = [str(c).strip() for c in (decision.consequences or []) if str(c).strip()]
    if consequences:
        tasks = [
            {
                "id": f"task-{i + 1}",
                "description": text,
                "acceptance": f"Verify: {text}",
                "target_paths": [],
            }
            for i, text in enumerate(consequences)
        ]
    else:
        tasks = [
            {
                "id": "task-1",
                "description": objective,
                "acceptance": "Implementation matches the approved decision.",
                "target_paths": [],
            }
        ]
    acceptance_criteria = [task["acceptance"] for task in tasks]
    verification_requirements = [
        "Run the existing test suite.",
        "Manual review against the decision's recorded evidence.",
    ]
    tradeoffs = [str(t).strip() for t in (decision.tradeoffs or []) if str(t).strip()]
    risk = "; ".join(tradeoffs) or None
    return {
        "objective": objective,
        "tasks": tasks,
        "acceptance_criteria": acceptance_criteria,
        "verification_requirements": verification_requirements,
        "risk": risk,
        "effort": None,
    }


def _build_prompt(decision: Decision) -> str:
    payload = {
        "context": decision.context,
        "decision": decision.decision,
        "consequences": decision.consequences,
        "evidence": decision.evidence,
    }
    return (
        "Draft an implementation plan for the following approved decision.\n"
        f"Decision (JSON):\n{json.dumps(payload)}\n\n"
        "Respond ONLY with a JSON object with keys: "
        "objective (string), "
        "tasks (array of objects, each with id, description, acceptance, target_paths), "
        "acceptance_criteria (array of strings), "
        "verification_requirements (array of strings), "
        "risk (string or null), "
        "effort (string or null)."
    )


def _coerce_tasks(value) -> list[dict]:
    tasks: list[dict] = []
    if not isinstance(value, list):
        return tasks
    for i, item in enumerate(value):
        if isinstance(item, dict):
            description = str(item.get("description") or "").strip()
            if not description:
                continue
            tasks.append(
                {
                    "id": str(item.get("id") or f"task-{i + 1}"),
                    "description": description,
                    "acceptance": str(item.get("acceptance") or ""),
                    "target_paths": [str(p) for p in (item.get("target_paths") or [])],
                }
            )
        else:
            text = str(item).strip()
            if text:
                tasks.append({"id": f"task-{i + 1}", "description": text, "acceptance": "", "target_paths": []})
    return tasks


def _coerce_str_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value if str(v).strip()]
    if value in (None, ""):
        return []
    return [str(value)]


def _draft_plan_fields(decision: Decision, settings) -> dict:
    """Draft objective/tasks/acceptance criteria via the Provider, tolerantly.

    Falls back to :func:`_deterministic_plan` whenever the provider's reply
    does not parse into a usable plan (missing/empty ``objective`` or
    ``tasks``, or any exception raised by routing/generation) — this is the
    hermetic path CI always takes.
    """
    fallback = _deterministic_plan(decision)
    try:
        provider = routed_provider("build_plan", Sensitivity.PUBLIC, settings)
        result = provider.generate(system=_PLAN_SYSTEM_PROMPT, prompt=_build_prompt(decision))
        obj = _loads_tolerant(result.text or "")
    except Exception:
        return fallback

    if not obj:
        return fallback
    objective = str(obj.get("objective") or "").strip()
    tasks = _coerce_tasks(obj.get("tasks"))
    if not objective or not tasks:
        return fallback

    return {
        "objective": objective,
        "tasks": tasks,
        "acceptance_criteria": _coerce_str_list(obj.get("acceptance_criteria")) or fallback["acceptance_criteria"],
        "verification_requirements": (
            _coerce_str_list(obj.get("verification_requirements")) or fallback["verification_requirements"]
        ),
        "risk": str(obj.get("risk")).strip() if obj.get("risk") else fallback["risk"],
        "effort": str(obj.get("effort")).strip() if obj.get("effort") else fallback["effort"],
    }


def plan_from_decision(db: Session, *, decision_id: str) -> ImplementationPlan:
    """Draft a governed :class:`ImplementationPlan` from an approved :class:`Decision`.

    404s a missing decision. **Idempotent**: if a plan already references this
    decision (``ImplementationPlan.meta["decision_id"]``), it is returned
    unchanged rather than drafting a second. Otherwise requires
    ``decision.status == "approved"`` (else **409**) before drafting.
    """
    decision = db.get(Decision, decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    existing = _existing_plan(db, decision_id)
    if existing is not None:
        return existing

    if decision.status != "approved":
        raise HTTPException(
            status_code=409,
            detail=(
                f"Decision in status '{decision.status}' is not approved; "
                "only an approved decision can be planned."
            ),
        )

    fields = _draft_plan_fields(decision, get_settings())

    plan = ImplementationPlan(
        decision_id=decision.id,
        project_id=decision.project_id,
        title=_title_for(decision),
        objective=fields["objective"],
        tasks=fields["tasks"],
        acceptance_criteria=fields["acceptance_criteria"],
        verification_requirements=fields["verification_requirements"],
        risk=fields["risk"],
        effort=fields["effort"],
        evidence=[{"type": "decision", "id": decision.id}],
        status=PLAN_DRAFT,
        meta={"decision_id": decision.id},
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def approve_plan(db: Session, *, plan_id: str, approver: str, rationale: str | None = None) -> ImplementationPlan:
    """Approve a ``draft`` plan on behalf of a named human.

    404s a missing plan. Only a ``draft`` plan is approvable — an already
    ``approved``/``rejected``/``superseded`` plan raises **409**. On success
    sets ``approved_by``/``approved_at``/``status=approved`` and writes an
    ``ApprovalRecord``.
    """
    plan = db.get(ImplementationPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Implementation plan not found")

    if plan.status != PLAN_DRAFT:
        raise HTTPException(
            status_code=409,
            detail=f"Plan in status '{plan.status}' cannot be approved (only 'draft' is approvable).",
        )

    plan.status = PLAN_APPROVED
    plan.approved_by = approver
    plan.approved_at = now_utc()
    plan.updated_by = approver
    db.add(
        ApprovalRecord(
            project_id=plan.project_id,
            actor=approver,
            reason=rationale,
            requested_capability="plan.approve",
            target=plan_id,
            approval_status="approved",
        )
    )
    db.commit()
    db.refresh(plan)
    return plan


__all__ = [
    "PLAN_DRAFT",
    "PLAN_APPROVED",
    "PLAN_REJECTED",
    "PLAN_SUPERSEDED",
    "plan_from_decision",
    "approve_plan",
]
