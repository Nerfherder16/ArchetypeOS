"""Decision → Knowledge: render an approved Decision into a repo-vault ADR.

The repo vault is the source of truth (RFC-0002 / RFC-0004): an **approved**
:class:`~aos_core.models.Decision` is rendered into an ADR markdown file under
``knowledge/wiki/decisions/`` (shaped like ``templates/adr.md``) and projected
as a re-syncable :class:`~aos_core.models.KnowledgePage` so it also surfaces on
the Knowledge dashboard. ``sync_knowledge`` can re-derive that page straight
from the vault file, so a DB reset loses nothing.

Export is a **separate, explicit step** from approval (its own endpoint), so a
non-writable vault (the compose stack mounts it ``:ro``) can never make approval
fail: only an ``approved`` decision is exportable, and a read-only vault yields a
graceful **409**, never a 500, and never mutates the approval state. Stdlib-only
rendering; no new dependencies.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models import CouncilReview, Decision, KnowledgePage, now_utc
from .decisions import DECISION_APPROVED

_PAGE_TYPE = "decision"


def _stringify(item: object) -> str:
    """Render a list item (string or structured dict) as one readable line."""
    if isinstance(item, dict):
        for key in ("point", "topic", "claim", "text", "summary", "title", "name"):
            value = item.get(key)
            if value:
                return str(value)
        return ", ".join(f"{key}={value}" for key, value in item.items())
    return str(item)


def _bullets(items: object) -> list[str]:
    lines: list[str] = []
    for item in items or []:
        text = _stringify(item).strip()
        if text:
            lines.append(f"- {text}")
    return lines


def _evidence_lines(decision: Decision, review: CouncilReview | None) -> list[str]:
    lines: list[str] = []
    if review is not None:
        confidence = review.confidence or 0.0
        lines.append(
            f"- Council review `{review.id}` — verdict '{review.verdict}' (confidence {confidence:.2f})."
        )
    for entry in decision.evidence or []:
        if isinstance(entry, dict):
            etype = entry.get("type", "reference")
            ref = entry.get("id") or entry.get("ref") or ""
            line = f"- {etype}: {ref}" if ref else f"- {etype}"
            agent = entry.get("agent")
            if agent:
                line += f" (agent: {agent})"
            lines.append(line)
        else:
            text = str(entry).strip()
            if text:
                lines.append(f"- {text}")
    return lines


def render_adr_markdown(decision: Decision, review: CouncilReview | None = None) -> str:
    """Render a :class:`Decision` into ADR markdown (pure, no I/O).

    Shaped like ``templates/adr.md``: an ``Accepted`` status, the date from
    ``approved_at`` (fallback ``created_at``), and Context/Decision/Alternatives/
    Evidence/Consequences/Acceptance Criteria/Reviewers drawn from the decision.
    When a ``review`` is supplied, its id and verdict are recorded under Evidence.
    """
    title = (decision.title or "Untitled decision").strip()
    when = decision.approved_at or decision.created_at or now_utc()
    date_str = when.date().isoformat()

    meta = decision.meta or {}
    acceptance = meta.get("acceptance_criteria")

    lines: list[str] = [
        f"# ADR — {title}",
        "",
        "## Status",
        "",
        "Accepted",
        "",
        "## Date",
        "",
        date_str,
        "",
        "## Context",
        "",
        (decision.context or "TBD").strip(),
        "",
        "## Decision",
        "",
        (decision.decision or "TBD").strip(),
        "",
        "## Alternatives Considered",
        "",
    ]
    lines.extend(_bullets(decision.alternatives) or ["- None recorded."])
    lines += ["", "## Evidence", ""]
    lines.extend(_evidence_lines(decision, review) or ["- None recorded."])
    lines += ["", "## Consequences", ""]
    lines.extend(_bullets(decision.consequences) or ["- TBD"])
    tradeoffs = _bullets(decision.tradeoffs)
    if tradeoffs:
        lines += ["", "Tradeoffs:"]
        lines.extend(tradeoffs)
    lines += ["", "## Acceptance Criteria", ""]
    if isinstance(acceptance, list):
        acc_lines = _bullets(acceptance)
    elif acceptance:
        acc_lines = [f"- {acceptance}"]
    else:
        acc_lines = []
    lines.extend(acc_lines or ["- TBD"])
    lines += ["", "## Reviewers", ""]
    if decision.approved_by:
        lines.append(f"- Approved by: {decision.approved_by}")
    lines += ["- Research", "- Architecture", "- Security", "- Compliance", "- Final Judge", ""]
    return "\n".join(lines)


def _adr_slug(decision: Decision) -> str:
    """Lowercased, non-alphanumeric-collapsed slug from the decision title."""
    slug = re.sub(r"[^a-z0-9]+", "-", (decision.title or "decision").lower()).strip("-")
    return slug or "decision"


def _adr_filename(decision: Decision) -> str:
    """Stable per-decision filename → idempotent overwrite, unique across titles."""
    return f"ADR-{_adr_slug(decision)}-{decision.id[:8]}.md"


def export_decision_adr(db: Session, *, decision_id: str, knowledge_root: Path | str) -> KnowledgePage:
    """Export an ``approved`` decision to a repo-vault ADR + ``KnowledgePage``.

    404s a missing decision; **409** if the decision is not ``approved`` (approval
    stays a pure DB act). Renders the ADR, writes it under
    ``<knowledge_root>/wiki/decisions/`` (creating dirs) and upserts a single
    ``KnowledgePage`` keyed on ``vault_path`` (``page_type="decision"``). A
    non-writable vault (``:ro`` mount / read-only checkout) raises **409** naming
    the local-first requirement and leaves the decision untouched. Idempotent:
    re-export overwrites the file and updates the one page.
    """
    decision = db.get(Decision, decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    if decision.status != DECISION_APPROVED:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Decision in status '{decision.status}' cannot be exported to an ADR "
                "(only an 'approved' decision is exportable)."
            ),
        )

    review_id = (decision.meta or {}).get("council_review_id")
    review = db.get(CouncilReview, review_id) if review_id else None

    markdown = render_adr_markdown(decision, review)
    filename = _adr_filename(decision)
    vault_path = f"wiki/decisions/{filename}"
    target = Path(knowledge_root) / "wiki" / "decisions" / filename
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(markdown, encoding="utf-8")
    except OSError as exc:
        # Read-only / :ro-mounted vault: fail gracefully (409, not 500) and do
        # NOT mutate the decision's approval state.
        raise HTTPException(
            status_code=409,
            detail=(
                f"Cannot write the ADR to the knowledge vault at '{knowledge_root}': {exc}. "
                "ADR export requires a writable, local-first checkout of the vault "
                "(the compose stack mounts it read-only); run the export from a writable "
                "local vault."
            ),
        ) from exc

    checksum = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    source_refs: list[dict] = [{"type": "decision", "id": decision.id}]
    if review_id:
        source_refs.append({"type": "council_review", "id": review_id})

    page = db.query(KnowledgePage).filter(KnowledgePage.vault_path == vault_path).first()
    if page is None:
        page = KnowledgePage(
            project_id=decision.project_id,
            title=decision.title,
            vault_path=vault_path,
            page_type=_PAGE_TYPE,
            validation_state="approved",
            source_refs=source_refs,
            checksum=checksum,
        )
        db.add(page)
    else:
        page.project_id = decision.project_id
        page.title = decision.title
        page.page_type = _PAGE_TYPE
        page.validation_state = "approved"
        page.source_refs = source_refs
        page.checksum = checksum

    decision.meta = {**(decision.meta or {}), "adr_path": vault_path}
    db.commit()
    db.refresh(page)
    return page


__all__ = ["render_adr_markdown", "export_decision_adr"]
