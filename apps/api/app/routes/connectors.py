"""Connector registry + policy routes (AOS-CONNECTOR-001, eval Finding 9).

Governs external connections as first-class assets. ``GET /connectors`` reconciles
the declarative catalog into the registry (so the list is never empty or stale and
``configured`` always reflects current settings) and returns every connector with
its privacy posture and health — disabled/unconfigured connectors included, without
erroring. ``POST /connectors/{name}/health`` records a probe result. See
``docs/CONNECTOR_POLICY.md`` for the governance rules.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from aos_core.config import get_settings
from aos_core.database import get_db
from aos_core.models import Connector
from aos_core.services.connectors import record_health, sync_connectors

from ..schemas import ConnectorHealthUpdate, ConnectorRead

router = APIRouter()

settings = get_settings()


@router.get("/connectors", response_model=list[ConnectorRead])
def list_connectors(db: Session = Depends(get_db)) -> list[Connector]:
    # Reconcile-on-read: the registry is derived from the catalog + current settings,
    # so it self-heals and never drifts from what is actually configured.
    return sync_connectors(db, settings)


@router.get("/connectors/{name}", response_model=ConnectorRead)
def get_connector(name: str, db: Session = Depends(get_db)) -> Connector:
    connector = db.query(Connector).filter(Connector.name == name).first()
    if connector is None:
        raise HTTPException(status_code=404, detail="Connector not found")
    return connector


@router.post("/connectors/{name}/health", response_model=ConnectorRead)
def record_connector_health(
    name: str, payload: ConnectorHealthUpdate, db: Session = Depends(get_db)
) -> Connector:
    connector = record_health(db, name=name, status=payload.status, error=payload.error)
    if connector is None:
        raise HTTPException(status_code=404, detail="Connector not found")
    return connector
