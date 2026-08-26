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


@lru_cache
def get_settings() -> Settings:
    return Settings()
