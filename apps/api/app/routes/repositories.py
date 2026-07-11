from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from aos_core.config import get_settings
from aos_core.database import get_db
from aos_core.models import KnowledgePage, Project, Repository, RepositoryDNA
from aos_core.repository_scanner import safe_repo_path
from aos_core.services.authority_envelope import is_authorized, mark_executed, request_action
from aos_core.services.distillation import distill_repository

from ..schemas import KnowledgePageRead, RepositoryCreate, RepositoryDnaRead, RepositoryRead

settings = get_settings()
router = APIRouter()


@router.post("/projects/{project_id}/repositories", response_model=RepositoryRead)
def register_repository(project_id: str, payload: RepositoryCreate, db: Session = Depends(get_db)) -> Repository:
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        safe_repo_path(settings.repository_root, payload.local_path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    repository = Repository(
        project_id=project_id,
        name=payload.name,
        local_path=payload.local_path,
        default_branch=payload.default_branch,
        remote_url=payload.remote_url,
        is_read_only=True,
    )
    db.add(repository)
    db.commit()
    db.refresh(repository)
    return repository


@router.get("/projects/{project_id}/repositories", response_model=list[RepositoryRead])
def list_repositories(project_id: str, db: Session = Depends(get_db)) -> list[Repository]:
    return db.query(Repository).filter(Repository.project_id == project_id).order_by(Repository.created_at.desc()).all()


@router.get("/repositories/{repository_id}/dna", response_model=RepositoryDnaRead)
def get_repository_dna(repository_id: str, db: Session = Depends(get_db)) -> RepositoryDNA:
    repository = db.get(Repository, repository_id)
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    if repository.dna is None:
        raise HTTPException(status_code=404, detail="Repository has not been scanned")
    return repository.dna


@router.post("/repositories/{repository_id}/distill", response_model=KnowledgePageRead)
def distill_repository_endpoint(repository_id: str, db: Session = Depends(get_db)) -> KnowledgePage:
    # Service 404s a missing repository and 409s a non-writable (:ro-mounted /
    # read-only) vault — never a 500 (local-first write; the distillation is
    # projected as a re-syncable KnowledgePage). RFC-0008. Phase 2 reads a bounded
    # set of source files through verified_generate (routes via settings; deterministic
    # in CI). AOS-USAGE-001: the ledger sink is created inside distill_repository.
    settings_ = get_settings()
    # AOS-REVIEW-002 follow-up (P0-6): distillation egresses repository content to a
    # model provider, so it is a direct sensitive-egress action — it must pass through
    # the same authority envelope that gates job origination, not just jobs. Public
    # egress auto-authorizes (unchanged behaviour); a policy that requires approval
    # for egress makes this return 403 with the pending ActionRequest to approve.
    action = request_action(
        db,
        action_class="external_network",
        actor="operator",
        agent="distillation",
        target=f"repository:{repository_id}",
        sensitivity="public",
        requested_capability="distill",
    )
    if not is_authorized(action):
        raise HTTPException(
            status_code=403,
            detail={
                "reason": "distillation egress requires approval",
                "action_request_id": action.id,
            },
        )
    page = distill_repository(
        db,
        repository_id=repository_id,
        knowledge_root=settings_.knowledge_root,
    )
    mark_executed(db, action)
    db.commit()
    return page
