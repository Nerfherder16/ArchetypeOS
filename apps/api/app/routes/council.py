import redis
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from aos_core.config import get_settings
from aos_core.database import get_db
from aos_core.models import CouncilReview, Job, Project
from aos_core.services.jobs import enqueue_job

from ..schemas import CouncilReviewCreate, CouncilReviewRead, JobRead

settings = get_settings()
router = APIRouter()


@router.post("/projects/{project_id}/council-reviews", response_model=JobRead)
def create_council_review(project_id: str, payload: CouncilReviewCreate, db: Session = Depends(get_db)) -> Job:
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return enqueue_job(
        db,
        redis.Redis.from_url(settings.redis_url),
        job_type="council_review",
        project_id=project_id,
        payload={"question": payload.question},
    )


@router.get("/projects/{project_id}/council-reviews", response_model=list[CouncilReviewRead])
def list_council_reviews(project_id: str, db: Session = Depends(get_db)) -> list[CouncilReview]:
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return (
        db.query(CouncilReview)
        .filter(CouncilReview.project_id == project_id)
        .order_by(CouncilReview.created_at.desc(), CouncilReview.id)
        .limit(50)
        .all()
    )


@router.get("/council-reviews/{review_id}", response_model=CouncilReviewRead)
def get_council_review(review_id: str, db: Session = Depends(get_db)) -> CouncilReview:
    review = db.get(CouncilReview, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Council review not found")
    return review
