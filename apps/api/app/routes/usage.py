"""LLM usage ledger API (AOS-USAGE-001).

``GET /usage/summary?window=today|7d|30d`` returns the totals + per-tier
(claude/local/free) + per-model breakdown the Operations "Providers & Model
Routing" view (AOS-USAGE-002) renders. Read-only; the ledger is written centrally
by the InstrumentedProvider wrapper, not from this route.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from aos_core.database import get_db
from aos_core.services.usage import summarize_usage

router = APIRouter()

_ALLOWED_WINDOWS = ("today", "7d", "30d")


@router.get("/usage/summary")
def get_usage_summary(
    window: str = Query("7d", description="today | 7d | 30d"),
    db: Session = Depends(get_db),
) -> dict:
    if window not in _ALLOWED_WINDOWS:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown window {window!r} (expected one of {_ALLOWED_WINDOWS}).",
        )
    return summarize_usage(db, window=window)
