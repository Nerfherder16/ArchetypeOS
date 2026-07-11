from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from aos_core.config import get_settings
from aos_core.database import get_db
from aos_core.models import ActionRequest, KnowledgePage, Project, Repository, RepositoryDNA
from aos_core.repository_scanner import safe_repo_path
from aos_core.services.authority_envelope import (
    consume_action,
    is_authorized,
    matches,
    request_action,
)
from aos_core.services.distillation import distill_repository
from aos_core.sensitivity import validate_sensitivity

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
    try:
        validate_sensitivity(payload.sensitivity)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    repository = Repository(
        project_id=project_id,
        name=payload.name,
        local_path=payload.local_path,
        default_branch=payload.default_branch,
        remote_url=payload.remote_url,
        is_read_only=True,
        sensitivity=payload.sensitivity,
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
def distill_repository_endpoint(
    repository_id: str,
    action_request_id: str | None = None,
    db: Session = Depends(get_db),
) -> KnowledgePage:
    # Service 404s a missing repository and 409s a non-writable (:ro-mounted /
    # read-only) vault — never a 500 (local-first write; the distillation is
    # projected as a re-syncable KnowledgePage). RFC-0008. Phase 2 reads a bounded
    # set of source files through verified_generate (routes via settings; deterministic
    # in CI). AOS-USAGE-001: the ledger sink is created inside distill_repository.
    settings_ = get_settings()

    # AOS-AUTHORITY-HARDEN-001: distillation egresses repository content to a model
    # provider — a direct sensitive-egress action. Its sensitivity is derived from the
    # REPOSITORY's persisted policy (not hardcoded public), so a private repo requires
    # approval to egress. Approve-and-resume: an ``action_request_id`` for an already-
    # approved envelope (bound to THIS repository) is validated + consumed on success;
    # otherwise a fresh envelope is created, and if it is not authorized the route 403s
    # with the id to approve — a retry passes that id (no new pending envelope per try).
    repo = db.get(Repository, repository_id)
    if repo is None:
        raise HTTPException(status_code=404, detail="Repository not found")

    if action_request_id is not None:
        action = db.get(ActionRequest, action_request_id)
        if action is None:
            raise HTTPException(status_code=404, detail="ActionRequest not found")
        if not matches(action, action_class="external_network", repository_id=repository_id):
            raise HTTPException(status_code=403, detail="ActionRequest does not authorize this repository")
        if not is_authorized(action):
            raise HTTPException(
                status_code=403,
                detail={"reason": "distillation egress not authorized (pending/expired/used)",
                        "action_request_id": action.id},
            )
    else:
        action = request_action(
            db,
            action_class="external_network",
            actor="operator",
            agent="distillation",
            project_id=repo.project_id,
            repository_id=repository_id,
            target=f"repository:{repository_id}",
            sensitivity=repo.sensitivity,
            requested_capability="distill",
        )
        if not is_authorized(action):
            raise HTTPException(
                status_code=403,
                detail={"reason": "distillation egress requires approval",
                        "action_request_id": action.id},
            )

    page = distill_repository(
        db,
        repository_id=repository_id,
        knowledge_root=settings_.knowledge_root,
    )
    # Consume the envelope EXACTLY once, AFTER the action succeeded (never on failure):
    # a raised distill_repository never reaches here, so the approval stays usable.
    if not consume_action(db, action):
        raise HTTPException(status_code=409, detail="ActionRequest already consumed")
    db.commit()
    return page
