"""Connector registry + policy routes (AOS-CONNECTOR-001; AOS-CONNECTOR-RUNTIME-001).

Governs external connections as first-class assets. ``GET /connectors`` is now a
READ-ONLY view derived from the catalog + current settings + persisted health (it
no longer writes on a read — finding P0-4); ``POST /connectors/reconcile`` is the
explicit write path. ``POST /connectors/{name}/probe`` runs an active reachability
probe and records the result. ``POST /connectors/{name}/health`` records a posted
probe result (create-on-demand for a catalogued connector).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from aos_core.config import get_settings
from aos_core.database import get_db
from aos_core.models import Connector
from aos_core.services.connectors import (
    connector_views,
    probe_and_record,
    record_health,
    sync_connectors,
)

from ..schemas import ConnectorHealthUpdate, ConnectorRead

router = APIRouter()

settings = get_settings()


@router.get("/connectors", response_model=list[ConnectorRead])
def list_connectors(db: Session = Depends(get_db)) -> list[ConnectorRead]:
    # Read-only: computed from the catalog + settings + persisted health; no write.
    return [ConnectorRead(**view) for view in connector_views(db, settings)]


@router.post("/connectors/reconcile", response_model=list[ConnectorRead])
def reconcile_connectors(db: Session = Depends(get_db)) -> list[Connector]:
    # The explicit reconciliation (write) path — replaces reconcile-on-read.
    return sync_connectors(db, settings)


@router.get("/connectors/{name}", response_model=ConnectorRead)
def get_connector(name: str, db: Session = Depends(get_db)) -> ConnectorRead:
    for view in connector_views(db, settings):
        if view["name"] == name:
            return ConnectorRead(**view)
    raise HTTPException(status_code=404, detail="Connector not found")


@router.post("/connectors/{name}/probe", response_model=ConnectorRead)
def probe_connector(name: str, db: Session = Depends(get_db)) -> Connector:
    connector = probe_and_record(db, name=name, settings=settings)
    if connector is None:
        raise HTTPException(status_code=404, detail="Connector not found")
    return connector


@router.post("/connectors/{name}/health", response_model=ConnectorRead)
def record_connector_health(
    name: str, payload: ConnectorHealthUpdate, db: Session = Depends(get_db)
) -> Connector:
    connector = record_health(db, name=name, status=payload.status, error=payload.error, settings=settings)
    if connector is None:
        raise HTTPException(status_code=404, detail="Connector not found")
    return connector
