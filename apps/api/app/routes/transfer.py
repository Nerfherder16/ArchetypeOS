from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from aos_core.database import get_db
from aos_core.models import Project
from aos_core.services.transfer import recommend_reuse

from ..schemas import TransferRecommendationRead, TransferRequest

router = APIRouter()


@router.post("/projects/{project_id}/transfer", response_model=list[TransferRecommendationRead])
def recommend_reuse_endpoint(
    project_id: str, payload: TransferRequest, db: Session = Depends(get_db)
) -> list[dict]:
    # 404 the target project; exclude its own repos so the engine only surfaces
    # reusable knowledge from the *rest* of the portfolio (RFC-0009). Advisory,
    # compute-and-return — no persistence.
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return recommend_reuse(db, need=payload.need, exclude_project_id=project_id)
