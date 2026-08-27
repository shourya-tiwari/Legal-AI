# backend/app/config.py
"""
Centralized, typed application configuration.

Single source of truth for environment-derived settings, replacing scattered
os.getenv(...) calls (and their inconsistent defaults) across service modules.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    GOOGLE_API_KEY: str = ""
    GENAI_MODEL: str = "gemini-flash-latest"

    # CORS
    CORS_ALLOWED_ORIGINS: list[str] = ["http://127.0.0.1:5500", "http://localhost:5500", "*"]

    # Persistence (Phase 1 re-platform: docs/v2/ARCHITECTURE.md)
    # Defaults to a local SQLite file so the app/tests run with zero external
    # services; docker-compose.yml points this at Postgres for local dev.
    DATABASE_URL: str = "sqlite:///./legalai.db"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Auth (docs/v2/ROADMAP.md Phase 1). Off by default so the existing public
    # frontend keeps working with zero credentials until keys are issued and
    # this is deliberately flipped on.
    AUTH_REQUIRED: bool = False

    # Rate limiting (per org when AUTH_REQUIRED, else per client IP). Fails
    # open (request allowed) if Redis is unreachable.
    RATE_LIMIT_PER_MINUTE: int = 60

    # Knowledge Graph (Phase 3: docs/v2/KNOWLEDGE_GRAPH.md). Memgraph speaks
    # the Bolt protocol, same as Neo4j, hence the neo4j driver. KG features
    # no-op (log + skip) if unreachable -- see app/services/kg/client.py --
    # so the rest of the app doesn't depend on this being up.
    MEMGRAPH_URI: str = "bolt://127.0.0.1:7687"  # IP literal, not "localhost" -- skips a slow dual-stack DNS/connect attempt when Memgraph isn't running
    MEMGRAPH_USER: str = ""
    MEMGRAPH_PASSWORD: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
