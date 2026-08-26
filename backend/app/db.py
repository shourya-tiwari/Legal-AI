# backend/app/db.py
"""
SQLAlchemy engine/session setup.

Backed by Postgres in docker-compose (local dev) and production, and by a
local SQLite file (or in-memory DB in tests) with zero external services
required — see app/config.py's DATABASE_URL default.
"""
from __future__ import annotations

from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def _make_engine():
    url = get_settings().DATABASE_URL
    connect_args = {}
    kwargs = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        if ":memory:" in url:
            # A single shared in-memory DB across connections/threads (tests).
            kwargs["poolclass"] = StaticPool
    return create_engine(url, connect_args=connect_args, **kwargs)


engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    """Create tables that don't exist yet. Simple create_all for now;
    revisit with a real migration tool (e.g. Alembic) once the schema
    stabilizes past this early phase."""
    from app import db_models  # noqa: F401  (ensure models are registered)
    Base.metadata.create_all(bind=engine)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
