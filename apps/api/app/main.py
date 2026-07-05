import json
from pathlib import Path
import re
import redis
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session
from aos_core.config import get_settings
from aos_core.database import engine, get_db, init_db
from aos_core.models import ArchitectureEdge, ArchitectureNode, Artifact, Decision, Job, NightlyDigest, Project, Recommendation, Repository, RepositoryDNA, ResearchNote
from aos_core.repository_scanner import safe_repo_path
from aos_core.services.scan import run_scan
from aos_core.services.digest import build_digest
from .schemas import ArchitectureCorrectionUpdate, ArchitectureEdgeRead, ArchitectureGraphRead, ArchitectureNodeRead, ArtifactCreate, ArtifactRead, DecisionCreate, DecisionRead, JobCreate, JobRead, NightlyDigestRead, ProjectCreate, ProjectRead, RecommendationCreate, RecommendationRead, RepositoryCreate, RepositoryDnaRead, RepositoryRead, RepositoryScanRead, ResearchNoteCreate, ResearchNoteRead

settings = get_settings()
app = FastAPI(title="ArchetypeOS API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "project"


@app.on_event("startup")
def on_startup() -> None:
    settings.artifact_root.mkdir(parents=True, exist_ok=True)
    init_db()


@app.get("/health")
def health() -> dict:
    db_ok = False
    redis_ok = False
    try:
        with engine.connect() as connection:
            connection.execute(text("select 1"))
            db_ok = True
    except Exception:
        db_ok = False
    try:
        client = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=1, socket_timeout=1)
        redis_ok = bool(client.ping())
    except Exception:
        redis_ok = False
    return {"status": "ok" if (db_ok and redis_ok) else "degraded", "api": True, "database": db_ok, "redis": redis_ok}


@app.post("/projects", response_model=ProjectRead)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)) -> Project:
    slug = payload.slug or slugify(payload.name)
    project = Project(name=payload.name, slug=slug, description=payload.description)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@app.get("/projects", response_model=list[ProjectRead])
def list_projects(db: Session = Depends(get_db)) -> list[Project]:
    return db.query(Project).order_by(Project.created_at.desc()).all()


@app.get("/projects/{project_id}", response_model=ProjectRead)
def get_project(project_id: str, db: Session = Depends(get_db)) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@app.post("/projects/{project_id}/repositories", response_model=RepositoryRead)
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


@app.get("/projects/{project_id}/repositories", response_model=list[RepositoryRead])
def list_repositories(project_id: str, db: Session = Depends(get_db)) -> list[Repository]:
    return db.query(Repository).filter(Repository.project_id == project_id).order_by(Repository.created_at.desc()).all()


@app.post("/repositories/{repository_id}/scan", response_model=RepositoryScanRead)
def scan_registered_repository(repository_id: str, db: Session = Depends(get_db)) -> dict:
    return run_scan(repository_id, db)


@app.get("/repositories/{repository_id}/scans", response_model=list[ArtifactRead])
def list_repository_scans(repository_id: str, db: Session = Depends(get_db)) -> list[Artifact]:
    if not db.get(Repository, repository_id):
        raise HTTPException(status_code=404, detail="Repository not found")
    return (
        db.query(Artifact)
        .filter(Artifact.repository_id == repository_id, Artifact.artifact_type == "repository_scan")
        .order_by(Artifact.created_at.desc(), Artifact.id)
        .all()
    )


@app.get("/repositories/{repository_id}/scans/{artifact_id}", response_model=dict)
def get_repository_scan(repository_id: str, artifact_id: str, db: Session = Depends(get_db)) -> dict:
    if not db.get(Repository, repository_id):
        raise HTTPException(status_code=404, detail="Repository not found")
    artifact = db.get(Artifact, artifact_id)
    if not artifact or artifact.repository_id != repository_id or artifact.artifact_type != "repository_scan":
        raise HTTPException(status_code=404, detail="Scan artifact not found")
    artifact_path = Path(artifact.path)
    if not artifact_path.exists():
        raise HTTPException(status_code=404, detail="Scan artifact file missing")
    return json.loads(artifact_path.read_text(encoding="utf-8"))


@app.get("/repositories/{repository_id}/dna", response_model=RepositoryDnaRead)
def get_repository_dna(repository_id: str, db: Session = Depends(get_db)) -> RepositoryDNA:
    repository = db.get(Repository, repository_id)
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    if repository.dna is None:
        raise HTTPException(status_code=404, detail="Repository has not been scanned")
    return repository.dna


@app.get("/projects/{project_id}/architecture", response_model=ArchitectureGraphRead)
def get_project_architecture(project_id: str, repository_id: str | None = None, db: Session = Depends(get_db)) -> dict:
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    node_query = db.query(ArchitectureNode).filter(ArchitectureNode.project_id == project_id)
    edge_query = db.query(ArchitectureEdge).filter(ArchitectureEdge.project_id == project_id)
    if repository_id is not None:
        node_query = node_query.filter(ArchitectureNode.repository_id == repository_id)
        edge_query = edge_query.filter(ArchitectureEdge.repository_id == repository_id)
    nodes = node_query.order_by(ArchitectureNode.label, ArchitectureNode.id).all()
    edges = edge_query.order_by(ArchitectureEdge.type, ArchitectureEdge.id).all()
    return {"nodes": nodes, "edges": edges}


@app.patch("/architecture/nodes/{node_id}", response_model=ArchitectureNodeRead)
def correct_architecture_node(node_id: str, payload: ArchitectureCorrectionUpdate, db: Session = Depends(get_db)) -> ArchitectureNode:
    node = db.get(ArchitectureNode, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Architecture node not found")
    node.manual_correction = payload.manual_correction
    db.add(node)
    db.commit()
    db.refresh(node)
    return node


@app.patch("/architecture/edges/{edge_id}", response_model=ArchitectureEdgeRead)
def correct_architecture_edge(edge_id: str, payload: ArchitectureCorrectionUpdate, db: Session = Depends(get_db)) -> ArchitectureEdge:
    edge = db.get(ArchitectureEdge, edge_id)
    if not edge:
        raise HTTPException(status_code=404, detail="Architecture edge not found")
    edge.manual_correction = payload.manual_correction
    db.add(edge)
    db.commit()
    db.refresh(edge)
    return edge


@app.post("/jobs", response_model=JobRead)
def create_job(payload: JobCreate, db: Session = Depends(get_db)) -> Job:
    job = Job(
        project_id=payload.project_id,
        repository_id=payload.repository_id,
        job_type=payload.job_type,
        payload=payload.payload,
        priority=payload.priority,
        status="queued",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    client = redis.Redis.from_url(settings.redis_url)
    client.lpush("archetypeos:jobs", job.id)
    return job


@app.get("/jobs/{job_id}", response_model=JobRead)
def get_job(job_id: str, db: Session = Depends(get_db)) -> Job:
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.post("/artifacts", response_model=ArtifactRead)
def create_artifact(payload: ArtifactCreate, db: Session = Depends(get_db)) -> Artifact:
    artifact = Artifact(**payload.model_dump())
    db.add(artifact)
    db.commit()
    db.refresh(artifact)
    return artifact


@app.get("/projects/{project_id}/artifacts", response_model=list[ArtifactRead])
def list_artifacts(project_id: str, db: Session = Depends(get_db)) -> list[Artifact]:
    return db.query(Artifact).filter(Artifact.project_id == project_id).order_by(Artifact.created_at.desc()).all()


@app.post("/projects/{project_id}/decisions", response_model=DecisionRead)
def create_decision(project_id: str, payload: DecisionCreate, db: Session = Depends(get_db)) -> Decision:
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    for note_id in payload.research_note_ids:
        note = db.get(ResearchNote, note_id)
        if not note or note.project_id != project_id:
            raise HTTPException(status_code=404, detail="Research note not found")
    evidence = list(payload.evidence) + [{"type": "research_note", "id": nid} for nid in payload.research_note_ids]
    decision = Decision(
        project_id=project_id,
        title=payload.title,
        context=payload.context,
        decision=payload.decision,
        alternatives=payload.alternatives,
        tradeoffs=payload.tradeoffs,
        consequences=payload.consequences,
        evidence=evidence,
        confidence=payload.confidence,
    )
    db.add(decision)
    db.commit()
    db.refresh(decision)
    return decision


@app.get("/projects/{project_id}/decisions", response_model=list[DecisionRead])
def list_decisions(project_id: str, db: Session = Depends(get_db)) -> list[Decision]:
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return db.query(Decision).filter(Decision.project_id == project_id).order_by(Decision.created_at.desc()).all()


@app.get("/decisions/{decision_id}", response_model=DecisionRead)
def get_decision(decision_id: str, db: Session = Depends(get_db)) -> Decision:
    decision = db.get(Decision, decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    return decision


@app.post("/projects/{project_id}/research-notes", response_model=ResearchNoteRead)
def create_research_note(project_id: str, payload: ResearchNoteCreate, db: Session = Depends(get_db)) -> ResearchNote:
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    note = ResearchNote(
        project_id=project_id,
        title=payload.title,
        question=payload.question,
        summary=payload.summary,
        sources=payload.sources,
        findings=payload.findings,
        freshness=payload.freshness,
        confidence=payload.confidence,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@app.get("/projects/{project_id}/research-notes", response_model=list[ResearchNoteRead])
def list_research_notes(project_id: str, db: Session = Depends(get_db)) -> list[ResearchNote]:
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return db.query(ResearchNote).filter(ResearchNote.project_id == project_id).order_by(ResearchNote.created_at.desc()).all()


@app.get("/research-notes/{note_id}", response_model=ResearchNoteRead)
def get_research_note(note_id: str, db: Session = Depends(get_db)) -> ResearchNote:
    note = db.get(ResearchNote, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Research note not found")
    return note


@app.post("/projects/{project_id}/recommendations", response_model=RecommendationRead)
def create_recommendation(project_id: str, payload: RecommendationCreate, db: Session = Depends(get_db)) -> Recommendation:
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    recommendation = Recommendation(
        project_id=project_id,
        title=payload.title,
        recommendation=payload.recommendation,
        rationale=payload.rationale,
        alternatives=payload.alternatives,
        pros=payload.pros,
        cons=payload.cons,
        risk=payload.risk,
        effort=payload.effort,
        dependencies=payload.dependencies,
        acceptance_criteria=payload.acceptance_criteria,
        evidence=payload.evidence,
        confidence=payload.confidence,
    )
    db.add(recommendation)
    db.commit()
    db.refresh(recommendation)
    return recommendation


@app.get("/projects/{project_id}/recommendations", response_model=list[RecommendationRead])
def list_recommendations(project_id: str, db: Session = Depends(get_db)) -> list[Recommendation]:
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return db.query(Recommendation).filter(Recommendation.project_id == project_id).order_by(Recommendation.created_at.desc()).all()


@app.get("/recommendations/{recommendation_id}", response_model=RecommendationRead)
def get_recommendation(recommendation_id: str, db: Session = Depends(get_db)) -> Recommendation:
    recommendation = db.get(Recommendation, recommendation_id)
    if not recommendation:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return recommendation


@app.post("/projects/{project_id}/digests", response_model=NightlyDigestRead)
def run_digest(project_id: str, db: Session = Depends(get_db)) -> NightlyDigest:
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    digest = build_digest(project_id, db)
    db.add(digest)
    db.commit()
    db.refresh(digest)
    return digest


@app.get("/projects/{project_id}/digests", response_model=list[NightlyDigestRead])
def list_digests(project_id: str, db: Session = Depends(get_db)) -> list[NightlyDigest]:
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return (
        db.query(NightlyDigest)
        .filter(NightlyDigest.project_id == project_id)
        .order_by(NightlyDigest.created_at.desc(), NightlyDigest.id)
        .all()
    )


@app.get("/digests/{digest_id}", response_model=NightlyDigestRead)
def get_digest(digest_id: str, db: Session = Depends(get_db)) -> NightlyDigest:
    digest = db.get(NightlyDigest, digest_id)
    if not digest:
        raise HTTPException(status_code=404, detail="Digest not found")
    return digest
