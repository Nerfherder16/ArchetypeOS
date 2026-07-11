import secrets

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from aos_core.config import get_settings
from aos_core.database import get_db
from aos_core.models import AuditHeartbeat
from aos_core.services.audit_heartbeat import HEARTBEAT_STATUSES, list_heartbeats, record_heartbeat

from ..schemas import AuditHeartbeatCreate, AuditHeartbeatRead

settings = get_settings()
router = APIRouter()


# AOS-SELFHEAL observability: a nightly self-learn probe posts a heartbeat on every
# run so a missed run is visible (a clean night looks different from silence). The
# store is a live status board — one row per routine, upserted.
@router.post("/audits/heartbeat", response_model=AuditHeartbeatRead, status_code=201)
def post_heartbeat(
    payload: AuditHeartbeatCreate,
    db: Session = Depends(get_db),
    x_telemetry_token: str | None = Header(default=None),
) -> AuditHeartbeat:
    # When a token is configured, require it (constant-time) — mirrors the audit-
    # routine collector pattern. Empty token (the local/tailnet default) means no auth.
    _token = settings.audit_heartbeat_token
    if _token and (not x_telemetry_token or not secrets.compare_digest(x_telemetry_token, _token)):
        raise HTTPException(status_code=401, detail="Invalid telemetry token")
    routine = payload.routine.strip()
    if not routine:
        raise HTTPException(status_code=422, detail="routine must not be empty")
    if payload.status not in HEARTBEAT_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"status must be one of {sorted(HEARTBEAT_STATUSES)}",
        )
    return record_heartbeat(
        db,
        routine=routine,
        status=payload.status,
        day=payload.day,
        pr_url=payload.pr_url,
        detail=payload.detail,
        project_id=payload.project_id,
    )


@router.get("/audits/heartbeats", response_model=list[AuditHeartbeatRead])
def get_heartbeats(db: Session = Depends(get_db)) -> list[AuditHeartbeat]:
    return list_heartbeats(db)
