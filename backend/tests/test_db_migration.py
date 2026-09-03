"""
The interim column-migration shim (app/db.py `_ensure_columns`) -- adds
columns introduced after a table's first creation, on an existing DB, without
a migration tool. Idempotent.
"""
from __future__ import annotations

from sqlalchemy import create_engine, inspect, text


def test_ensure_columns_adds_a_missing_column_and_is_idempotent(monkeypatch):
    import app.db as dbmod

    eng = create_engine("sqlite://")  # fresh in-memory, isolated from the app engine
    with eng.begin() as conn:
        # a `documents` table shaped like the pre-sensitivity schema
        conn.execute(text(
            "CREATE TABLE documents (id INTEGER PRIMARY KEY, org_id INTEGER, "
            "filename VARCHAR(512), full_text TEXT)"
        ))
        conn.execute(text("CREATE TABLE audit_log (id INTEGER PRIMARY KEY, org_id INTEGER, action VARCHAR(255))"))

    monkeypatch.setattr(dbmod, "engine", eng)
    dbmod._ensure_columns()
    dbmod._ensure_columns()  # second run must be a no-op, not an error

    cols = {c["name"] for c in inspect(eng).get_columns("documents")}
    assert {"sensitivity_tier", "sensitivity_source", "sensitivity_signals"} <= cols
    assert "detail" in {c["name"] for c in inspect(eng).get_columns("audit_log")}

    # the added NOT NULL columns have a working default
    with eng.begin() as conn:
        conn.execute(text("INSERT INTO documents (org_id, filename, full_text) VALUES (1, 'x', 'y')"))
        row = conn.execute(text("SELECT sensitivity_tier, sensitivity_source FROM documents")).one()
    assert row == ("internal", "auto")
