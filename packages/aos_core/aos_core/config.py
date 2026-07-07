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
    # AOS-LLM-LOCAL-001: the "openai_compatible" provider runs ArchetypeOS's
    # reasoned tiers off a local model (Ollama/vLLM/LM Studio — e.g. teevee's
    # RTX 3070 at http://localhost:11434/v1) OR a free hosted API (Groq/Cerebras/
    # OpenRouter from the free-llm-api-resources catalog) with the same code —
    # only these three differ. ``llm_api_key`` is read from the env (LLM_API_KEY),
    # never committed; empty = no auth (the local Ollama case).
    llm_base_url: str = "http://localhost:11434/v1"
    llm_model: str = "qwen2.5-coder:7b"
    llm_api_key: str = ""
    # AOS-LLM-EVAL-001: Tier-2 free hosted provider (non-private tasks only — see
    # the router's privacy tiering). Distinct from the local llm_* above so both
    # tiers can be configured at once. Key from env (LLM_FREE_API_KEY), never committed.
    llm_free_base_url: str = "https://api.groq.com/openai/v1"
    llm_free_model: str = "llama-3.3-70b-versatile"
    llm_free_api_key: str = ""
    # Tier-3 Claude is opt-in (it spends subscription tokens): the router only
    # routes to it when explicitly enabled.
    llm_claude_enabled: bool = False
    # RFC-0010 embedding tier. Default "deterministic" → the hermetic no-op
    # embedder (embed()→None → lexical fallback); the real "fastembed" (ONNX) tier
    # lands in AOS-EMBED-002. ``embedding_model`` names the fastembed model that
    # tier loads (unused by the deterministic embedder). The value is fastembed's
    # supported id for all-MiniLM-L6-v2 (384-dim, drop-in for the pgvector column).
    embedding_provider: str = "deterministic"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    # AOS-USAGE-001: per-tier cost rate table ($ per 1M tokens) for the usage
    # ledger's cost *estimate* — used only when a provider does not report a real
    # cost. Claude Code reports its own ``total_cost_usd`` (preferred, exact); these
    # rates are the documented fallback and any cost derived from them is flagged
    # ``estimated``. Local (self-hosted GPU) and free hosted tiers cost ~$0.
    usage_cost_claude_input_per_mtok: float = 3.0
    usage_cost_claude_output_per_mtok: float = 15.0
    usage_cost_local_per_mtok: float = 0.0
    usage_cost_free_per_mtok: float = 0.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
