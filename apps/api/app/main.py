import redis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from aos_core.config import get_settings
from aos_core.database import engine, init_db

from .routes import architecture, artifacts, council, decisions, digests, jobs, knowledge, nodes, projects, repositories, research, scans, schedules, transfer, usage, voice

settings = get_settings()
app = FastAPI(title="ArchetypeOS API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


# Include order mirrors the previous top-to-bottom @app definition order so
# route registration (and any overlapping-path resolution) is byte-identical.
for _module in (projects, repositories, scans, architecture, jobs, schedules, artifacts, decisions, digests, council, research, knowledge, transfer, usage, voice, nodes):
    app.include_router(_module.router)
