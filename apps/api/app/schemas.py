from datetime import datetime
from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str
    slug: str | None = None
    description: str | None = None


class ProjectRead(BaseModel):
    id: str
    name: str
    slug: str
    description: str | None
    status: str
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RepositoryCreate(BaseModel):
    name: str
    local_path: str
    default_branch: str | None = None
    remote_url: str | None = None


class RepositoryRead(BaseModel):
    id: str
    project_id: str
    name: str
    local_path: str
    default_branch: str | None
    remote_url: str | None
    is_read_only: bool
    status: str
    last_scanned_at: datetime | None
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class JobCreate(BaseModel):
    project_id: str | None = None
    repository_id: str | None = None
    job_type: str
    payload: dict = Field(default_factory=dict)
    priority: int = 100


class JobRead(BaseModel):
    id: str
    project_id: str | None
    repository_id: str | None
    job_type: str
    status: str
    priority: int
    payload: dict
    result: dict | None
    error: str | None
    queued_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    attempts: int

    model_config = {"from_attributes": True}


class ArtifactCreate(BaseModel):
    project_id: str
    repository_id: str | None = None
    job_id: str | None = None
    artifact_type: str
    name: str
    path: str
    content_type: str | None = None
    checksum: str | None = None
    size_bytes: int | None = None
    summary: str | None = None


class ArtifactRead(ArtifactCreate):
    id: str
    status: str
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RepositoryScanRead(BaseModel):
    repository_id: str
    summary: dict
    dna: dict
    architecture_nodes: list[dict]
    architecture_edges: list[dict]
    artifacts: list[dict]
