"""Authority action policy (AOS-AUTHORITY-001, eval Finding 10).

Review-first is enforced infrastructure here, not convention. Every high-impact
operation maps to an ``ActionClass`` (ordered by escalating risk), and a single
central evaluator, ``requires_approval(action_type, target, sensitivity, capability)``,
decides whether human approval is needed. The policy is a pure, total function so
it is trivially testable and cannot be silently bypassed: write and destructive
classes ALWAYS require approval, regardless of sensitivity or claimed capability.

See ``docs/AUTHORITY_POLICY.md`` for the governing rules.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from ..models import ApprovalRecord

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.orm import Session


class ActionClass(str, Enum):
    """High-impact operation classes, ordered by escalating risk (see LEVELS)."""

    CAPTURE_ONLY = "capture_only"
    READ_ONLY = "read_only"
    DRAFT_ARTIFACT = "draft_artifact"
    EXTERNAL_NETWORK = "external_network"
    REPO_WRITE = "repo_write"
    GIT_COMMIT = "git_commit"
    DEPLOY = "deploy"
    DELETE_DESTRUCTIVE = "delete_destructive"


# Risk level per class (index into the escalation ladder). Higher = more dangerous.
LEVELS: dict[ActionClass, int] = {ac: i for i, ac in enumerate(ActionClass)}

# Write/destructive classes: these ALWAYS require approval. This set is the
# enforcement backbone — a write path cannot opt out of it.
_ALWAYS_APPROVE: frozenset[ActionClass] = frozenset(
    {
        ActionClass.REPO_WRITE,
        ActionClass.GIT_COMMIT,
        ActionClass.DEPLOY,
        ActionClass.DELETE_DESTRUCTIVE,
    }
)

# Sensitivity values that must not leave the local network without approval. Public
# data may egress freely; anything private/internal-or-higher needs a human.
_SENSITIVE: frozenset[str] = frozenset({"private", "internal", "confidential", "restricted", "secret"})


@dataclass(frozen=True)
class ActionClassInfo:
    name: str
    level: int
    always_requires_approval: bool
    description: str


_DESCRIPTIONS: dict[ActionClass, str] = {
    ActionClass.CAPTURE_ONLY: "Capture input for later review (voice/command turns). Performs nothing.",
    ActionClass.READ_ONLY: "Read data or run analysis with no side effects.",
    ActionClass.DRAFT_ARTIFACT: "Produce a draft artifact awaiting review (never executes it).",
    ActionClass.EXTERNAL_NETWORK: "Send data to an external network; gated when the data is sensitive.",
    ActionClass.REPO_WRITE: "Write to a repository working tree.",
    ActionClass.GIT_COMMIT: "Commit/push to version control.",
    ActionClass.DEPLOY: "Deploy or restart a running service.",
    ActionClass.DELETE_DESTRUCTIVE: "Delete data or perform an irreversible operation.",
}


def action_class_catalog() -> list[ActionClassInfo]:
    """The full, ordered action-class catalog for the dashboard/clients."""
    return [
        ActionClassInfo(
            name=ac.value,
            level=LEVELS[ac],
            always_requires_approval=ac in _ALWAYS_APPROVE,
            description=_DESCRIPTIONS[ac],
        )
        for ac in ActionClass
    ]


def requires_approval(
    action_type: str,
    *,
    target: str | None = None,
    sensitivity: str = "public",
    capability: str | None = None,
) -> bool:
    """Central policy: does this action need human approval? Raises on unknown class."""
    action = ActionClass(action_type)  # ValueError if unknown — no silent pass
    if action in _ALWAYS_APPROVE:
        return True
    if action is ActionClass.EXTERNAL_NETWORK:
        return sensitivity.lower() in _SENSITIVE
    return False


def evaluate(
    action_type: str,
    *,
    target: str | None = None,
    sensitivity: str = "public",
    capability: str | None = None,
) -> dict:
    """A reasoned decision: requires_approval plus the level and a human-readable reason."""
    action = ActionClass(action_type)
    needed = requires_approval(action_type, target=target, sensitivity=sensitivity, capability=capability)
    if action in _ALWAYS_APPROVE:
        reason = f"{action.value} is a write/destructive action and always requires approval."
    elif action is ActionClass.EXTERNAL_NETWORK and needed:
        reason = f"external network egress of {sensitivity!r} data requires approval."
    elif action is ActionClass.EXTERNAL_NETWORK:
        reason = "external network egress of public data is allowed without approval."
    else:
        reason = f"{action.value} has no side effects that require approval."
    return {
        "action_type": action.value,
        "action_level": LEVELS[action],
        "requires_approval": needed,
        "sensitivity": sensitivity,
        "reason": reason,
    }


def list_pending_actions(db: "Session") -> list[ApprovalRecord]:
    """Every ApprovalRecord still awaiting a human decision (dashboard queue)."""
    return (
        db.query(ApprovalRecord)
        .filter(ApprovalRecord.approval_status == "pending")
        .order_by(ApprovalRecord.created_at.desc(), ApprovalRecord.id)
        .all()
    )
