from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import redis
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session
from .config import get_settings
from .database import engine, get_db, init_db
from .models import ArchitectureEdge, ArchitectureNode, Artifact, Job, Project, Repository, RepositoryDNA, new_id
from .repository_scanner import safe_repo_path, scan_repository
from .schemas import ArchitectureCorrectionUpdate, ArchitectureEdgeRead, ArchitectureGraphRead, ArchitectureNodeRead, ArtifactCreate, ArtifactRead, JobCreate, JobRead, ProjectCreate, ProjectRead, RepositoryCreate, RepositoryDnaRead, RepositoryRead, RepositoryScanRead

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
    with engine.connect() as connection:
        connection.execute(text("select 1"))
        db_ok = True
    client = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=1, socket_timeout=1)
    redis_ok = bool(client.ping())
    return {"status": "ok", "api": True, "database": db_ok, "redis": redis_ok}


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
    repository = db.get(Repository, repository_id)
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    try:
        repo_path = safe_repo_path(settings.repository_root, repository.local_path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    scan = scan_repository(repo_path)
    repository.last_scanned_at = datetime.now(timezone.utc)

    dna = repository.dna or RepositoryDNA(repository_id=repository.id)
    dna.language_mix = scan["language_mix"]
    dna.package_managers = scan["package_managers"]
    dna.deployment_files = scan["deployment_files"]
    dna.risk_flags = scan["risk_flags"]
    dna.scan_summary = scan
    dna.confidence = 0.65
    dna.evidence = ["read-only repository scanner"]
    dna.status = "draft"
    db.add(dna)

    root_node = (
        db.query(ArchitectureNode)
        .filter(ArchitectureNode.repository_id == repository.id, ArchitectureNode.type == "repository")
        .first()
    )
    if root_node:
        root_node.label = repository.name
        root_node.confidence = 0.9
        root_node.evidence = ["registered repository"]
    else:
        root_node = ArchitectureNode(
            project_id=repository.project_id,
            repository_id=repository.id,
            label=repository.name,
            type="repository",
            confidence=0.9,
            evidence=["registered repository"],
            status="draft",
        )
    db.add(root_node)
    db.flush()
    node_by_label = {repository.name: root_node}
    nodes_out = [{"id": root_node.id, "label": root_node.label, "type": root_node.type, "confidence": root_node.confidence}]

    for item in scan["architecture_nodes"][1:]:
        node = (
            db.query(ArchitectureNode)
            .filter(
                ArchitectureNode.repository_id == repository.id,
                ArchitectureNode.type == "directory",
                ArchitectureNode.label == item["label"],
                ArchitectureNode.parent_id == root_node.id,
            )
            .first()
        )
        if node:
            node.confidence = item["confidence"]
            node.evidence = item["evidence"]
        else:
            node = ArchitectureNode(
                project_id=repository.project_id,
                repository_id=repository.id,
                label=item["label"],
                type=item["type"],
                parent_id=root_node.id,
                confidence=item["confidence"],
                evidence=item["evidence"],
                status="draft",
            )
        db.add(node)
        db.flush()
        node_by_label[item["label"]] = node
        nodes_out.append({"id": node.id, "label": node.label, "type": node.type, "confidence": node.confidence})

    edges_out = []
    for item in scan["architecture_edges"]:
        from_node = node_by_label.get(repository.name)
        to_node = node_by_label.get(item["to"])
        if not from_node or not to_node:
            continue
        edge = (
            db.query(ArchitectureEdge)
            .filter(
                ArchitectureEdge.repository_id == repository.id,
                ArchitectureEdge.from_node_id == from_node.id,
                ArchitectureEdge.to_node_id == to_node.id,
                ArchitectureEdge.type == item["type"],
            )
            .first()
        )
        if edge:
            edge.confidence = item["confidence"]
            edge.evidence = item["evidence"]
        else:
            edge = ArchitectureEdge(
                project_id=repository.project_id,
                repository_id=repository.id,
                from_node_id=from_node.id,
                to_node_id=to_node.id,
                type=item["type"],
                confidence=item["confidence"],
                evidence=item["evidence"],
                status="draft",
            )
        db.add(edge)
        db.flush()
        edges_out.append({"id": edge.id, "from_node_id": edge.from_node_id, "to_node_id": edge.to_node_id, "type": edge.type, "confidence": edge.confidence})

    artifact_body = json.dumps(scan, indent=2, sort_keys=True)
    checksum = hashlib.sha256(artifact_body.encode("utf-8")).hexdigest()
    artifact_id = new_id()
    artifact_name = f"repository-scan-{artifact_id}.json"
    artifact_dir = settings.artifact_root / repository.project_id / repository.id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_dir / artifact_name
    artifact_path.write_text(artifact_body, encoding="utf-8")
    artifact = Artifact(
        id=artifact_id,
        project_id=repository.project_id,
        repository_id=repository.id,
        artifact_type="repository_scan",
        name=artifact_name,
        path=str(artifact_path),
        content_type="application/json",
        checksum=checksum,
        size_bytes=len(artifact_body.encode("utf-8")),
        summary="Read-only repository scan report",
    )
    db.add(artifact)
    db.commit()

    return {
        "repository_id": repository.id,
        "summary": scan,
        "dna": {
            "language_mix": dna.language_mix,
            "package_managers": dna.package_managers,
            "deployment_files": dna.deployment_files,
            "risk_flags": dna.risk_flags,
            "confidence": dna.confidence,
        },
        "architecture_nodes": nodes_out,
        "architecture_edges": edges_out,
        "artifacts": [{"id": artifact.id, "name": artifact.name, "path": artifact.path, "checksum": artifact.checksum}],
    }


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
