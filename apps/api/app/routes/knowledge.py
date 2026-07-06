from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from aos_core.config import get_settings
from aos_core.database import get_db
from aos_core.models import KnowledgePage
from aos_core.services.knowledge import sync_knowledge

from ..schemas import KnowledgePageRead, KnowledgeSyncResult

settings = get_settings()
router = APIRouter()


@router.post("/knowledge/sync", response_model=KnowledgeSyncResult)
def run_knowledge_sync(db: Session = Depends(get_db)) -> dict:
    return sync_knowledge(db, settings.knowledge_root)


@router.get("/knowledge/pages", response_model=list[KnowledgePageRead])
def list_knowledge_pages(
    page_type: str | None = None,
    validation_state: str | None = None,
    db: Session = Depends(get_db),
) -> list[KnowledgePage]:
    query = db.query(KnowledgePage)
    if page_type is not None:
        query = query.filter(KnowledgePage.page_type == page_type)
    if validation_state is not None:
        query = query.filter(KnowledgePage.validation_state == validation_state)
    return query.order_by(KnowledgePage.updated_at.desc(), KnowledgePage.id).limit(100).all()


@router.get("/knowledge/pages/{page_id}", response_model=KnowledgePageRead)
def get_knowledge_page(page_id: str, db: Session = Depends(get_db)) -> KnowledgePage:
    page = db.get(KnowledgePage, page_id)
    if not page:
        raise HTTPException(status_code=404, detail="Knowledge page not found")
    return page
