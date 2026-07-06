from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Shared embedding dimensionality (RFC-0010). 384 = the all-MiniLM-L6-v2 output
# width the real tier (AOS-EMBED-002, fastembed/ONNX) produces; the pgvector column
# + the deterministic seam agree on it here so the store and the real embedder are
# dimension-compatible. Single source of truth.
EMBEDDING_DIM = 384


class Settings(BaseSettings):
    database_url: str = "sqlite:///./archetypeos_dev.db"
    redis_url: str = "redis://localhost:6379/0"
    artifact_root: Path = Path("./data/artifacts")
    repository_root: Path = Path("./repositories")
    knowledge_root: Path = Path("./knowledge")
    cors_origins: str = "http://localhost:5173"
    llm_provider: str = "deterministic"
    # RFC-0010 embedding tier. Default "deterministic" → the hermetic no-op
    # embedder (embed()→None → lexical fallback); the real "fastembed" (ONNX) tier
    # lands in AOS-EMBED-002. ``embedding_model`` names the fastembed model that
    # tier loads (unused by the deterministic embedder). The value is fastembed's
    # supported id for all-MiniLM-L6-v2 (384-dim, drop-in for the pgvector column).
    embedding_provider: str = "deterministic"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
