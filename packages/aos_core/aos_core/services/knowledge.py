"""Knowledge read path (RFC-0002 / RFC-0004).

The repo vault (``knowledge/wiki/lessons/index.md``) stays the source of
truth; this module parses it and upserts derived ``KnowledgePage`` rows so
lessons gain an API/DB read surface. A DB reset loses nothing — re-run the
sync from the repo tree. Stdlib-only, no new dependencies.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from sqlalchemy.orm import Session

from ..models import KnowledgePage

# ID cell looks like ``[[LES-007]]`` — only rows whose first cell matches are data rows.
_LESSON_ID_RE = re.compile(r"\[\[\s*(LES-\d+)\s*\]\]")

# Column order of the lessons index table.
_FIELDS = ("lesson_id", "date", "category", "short", "source", "status", "consumed_by")


def _split_row(line: str) -> list[str] | None:
    """Split a markdown table row into stripped cells, or None if not a row."""
    stripped = line.strip()
    if not stripped.startswith("|"):
        return None
    # Drop the leading/trailing pipe artifacts, then split on the remaining pipes.
    body = stripped.strip("|")
    return [cell.strip() for cell in body.split("|")]


def parse_lessons_index(text: str) -> list[dict]:
    """Parse the lessons-index markdown table into a list of lesson rows.

    Tolerant: non-data / malformed lines and an absent table yield ``[]`` and
    never raise. Only rows whose first cell contains ``[[LES-<n>]]`` are kept.
    """
    rows: list[dict] = []
    for line in text.splitlines():
        cells = _split_row(line)
        if not cells:
            continue
        match = _LESSON_ID_RE.search(cells[0])
        if not match:
            continue
        # Pad/truncate to the expected column count so short rows don't raise.
        padded = (cells + [""] * len(_FIELDS))[: len(_FIELDS)]
        row = dict(zip(_FIELDS, padded))
        row["lesson_id"] = match.group(1)
        rows.append(row)
    return rows


def _row_checksum(row: dict) -> str:
    payload = "\x1f".join(row.get(field, "") or "" for field in _FIELDS)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def sync_knowledge(db: Session, knowledge_root: Path) -> dict:
    """Upsert lesson ``KnowledgePage`` rows from the vault lessons index.

    Idempotent: keyed by ``vault_path`` (``wiki/lessons/<LES-id>.md``); existing
    rows are updated in place, new ones created. A missing vault dir/file returns
    all-zero counts rather than raising.
    """
    index_path = Path(knowledge_root) / "wiki" / "lessons" / "index.md"
    if not index_path.is_file():
        return {"synced": 0, "created": 0, "updated": 0, "open_lessons": 0}

    text = index_path.read_text(encoding="utf-8")
    lessons = parse_lessons_index(text)

    created = 0
    updated = 0
    open_lessons = 0
    for row in lessons:
        lesson_id = row["lesson_id"]
        vault_path = f"wiki/lessons/{lesson_id}.md"
        status = row.get("status") or "raw"
        if status == "open":
            open_lessons += 1

        page = db.query(KnowledgePage).filter(KnowledgePage.vault_path == vault_path).first()
        source = row.get("source") or ""
        checksum = _row_checksum(row)
        if page is None:
            page = KnowledgePage(
                project_id=None,
                title=row.get("short") or lesson_id,
                vault_path=vault_path,
                page_type="lesson",
                validation_state=status,
                source_refs=[{"type": "pr_or_run", "ref": source}],
                checksum=checksum,
            )
            db.add(page)
            created += 1
        else:
            page.project_id = None
            page.title = row.get("short") or lesson_id
            page.page_type = "lesson"
            page.validation_state = status
            page.source_refs = [{"type": "pr_or_run", "ref": source}]
            page.checksum = checksum
            updated += 1

    db.commit()
    return {
        "synced": len(lessons),
        "created": created,
        "updated": updated,
        "open_lessons": open_lessons,
    }
