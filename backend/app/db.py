# backend/app/db.py
"""
SQLAlchemy engine/session setup.

Backed by Postgres in docker-compose (local dev) and production, and by a
local SQLite file (or in-memory DB in tests) with zero external services
required — see app/config.py's DATABASE_URL default.
"""
from __future__ import annotations

import logging
from typing import Iterator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings

logger = logging.getLogger("legalai.db")


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


# New columns added to *existing* tables after they were first created.
# `create_all` only creates missing tables, never alters columns, and there
# is no migration tool yet (deliberate for this stage). This list is the
# interim mechanism: `_ensure_columns()` adds each one if it's missing, on
# both SQLite (dev/tests) and Postgres. Remove an entry once Alembic owns it.
_ADDED_COLUMNS: list[tuple[str, str, str]] = [
    # (table, column, column DDL incl. type + default)
    ("documents", "sensitivity_tier", "VARCHAR(16) NOT NULL DEFAULT 'internal'"),
    ("documents", "sensitivity_source", "VARCHAR(16) NOT NULL DEFAULT 'auto'"),
    ("documents", "sensitivity_signals", "JSON"),
    ("documents", "quality", "JSON"),
    ("audit_log", "detail", "TEXT"),
    ("audit_log", "egress_target", "VARCHAR(64)"),
    ("audit_log", "actor_id", "INTEGER"),
    ("audit_log", "actor_type", "VARCHAR(16)"),
    ("api_keys", "role", "VARCHAR(16) NOT NULL DEFAULT 'admin'"),
]


def _ensure_columns() -> None:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    with engine.begin() as conn:
        for table, column, ddl in _ADDED_COLUMNS:
            if table not in existing_tables:
                continue  # create_all just made it with the column already
            cols = {c["name"] for c in inspector.get_columns(table)}
            if column in cols:
                continue
            try:
                conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {column} {ddl}'))
                logger.info("schema: added %s.%s", table, column)
            except Exception as e:  # pragma: no cover - defensive
                logger.warning("schema: could not add %s.%s (%s)", table, column, e)


def init_db() -> None:
    """Create missing tables, then add any columns that were introduced after
    a table's first creation (`_ensure_columns` -- the interim before Alembic
    owns migrations). Idempotent."""
    from app import db_models  # noqa: F401  (ensure models are registered)
    Base.metadata.create_all(bind=engine)
    _ensure_columns()


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
