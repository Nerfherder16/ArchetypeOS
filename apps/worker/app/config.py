from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./archetypeos_worker_dev.db"
    redis_url: str = "redis://localhost:6379/0"
    artifact_root: Path = Path("./data/artifacts")
    repository_root: Path = Path("./repositories")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
