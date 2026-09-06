# backend/app/services/kg/kuzu_client.py
"""
Embedded Knowledge Graph backend (docs/v2/ROADMAP.md Phase 7 "Collapsed
data layer" -- the laptop/single-binary profile: no separate graph-database
server to run at all, Memgraph substituted for an in-process, disk-backed
Kuzu database). Selected via Settings.KG_BACKEND="kuzu"; same public
interface as client.py's KGClient (`available`, `run_query`), so
builder.py/queries.py work against either without knowing which is live --
with one deliberate exception, see find_clauses_using_term's Kuzu variant
in queries.py.

Unlike Memgraph (schema-free property graph, MERGE creates a label on the
fly), Kuzu is statically typed: every node/relationship table and its
columns must be declared up front (`CREATE NODE/REL TABLE`). `_ensure_schema`
does this once per database directory, matching schema.py's node/edge
model exactly -- this is Kuzu's equivalent of Memgraph's uniqueness
constraints (`ensure_constraints`), not an addition to it; `PRIMARY KEY(id)`
at table-creation time already enforces the same uniqueness a Memgraph
`CREATE CONSTRAINT` would, so `ensure_constraints` no-ops for this backend
(see its own docstring).

Fail-soft, matching KGClient: any error opening the database or running a
query logs a warning and returns an empty/unavailable result rather than
raising -- an embedded database can still fail (e.g. a locked directory
from a concurrent process), and the rest of the app must not depend on
this being up, exactly like the Memgraph path.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from . import schema

logger = logging.getLogger("legalai.kg.kuzu_client")

_SCHEMA_DDL = [
    f"CREATE NODE TABLE IF NOT EXISTS {schema.DOCUMENT}"
    f"(id STRING, org_id INT64, document_id INT64, PRIMARY KEY(id))",
    f"CREATE NODE TABLE IF NOT EXISTS {schema.CLAUSE}"
    f"(id STRING, content STRING, clause_type STRING, org_id INT64, "
    f"deontic_modalities STRING[], PRIMARY KEY(id))",
    f"CREATE NODE TABLE IF NOT EXISTS {schema.DEFINED_TERM}"
    f"(id STRING, term STRING, context STRING, org_id INT64, PRIMARY KEY(id))",
    f"CREATE NODE TABLE IF NOT EXISTS {schema.CROSS_REFERENCE_TARGET}"
    f"(id STRING, content STRING, org_id INT64, PRIMARY KEY(id))",
    f"CREATE REL TABLE IF NOT EXISTS {schema.PART_OF}(FROM {schema.CLAUSE} TO {schema.DOCUMENT})",
    f"CREATE REL TABLE IF NOT EXISTS {schema.DEFINES}(FROM {schema.DOCUMENT} TO {schema.DEFINED_TERM})",
    f"CREATE REL TABLE IF NOT EXISTS {schema.USES_TERM}(FROM {schema.CLAUSE} TO {schema.DEFINED_TERM})",
    f"CREATE REL TABLE IF NOT EXISTS {schema.REFERENCES}(FROM {schema.CLAUSE} TO {schema.CROSS_REFERENCE_TARGET})",
    f"CREATE REL TABLE IF NOT EXISTS {schema.SAME_AS}(FROM {schema.DEFINED_TERM} TO {schema.DEFINED_TERM})",
]


class KuzuKGClient:
    backend = "kuzu"

    def __init__(self, db_path: str):
        self._conn = None
        try:
            import kuzu

            db = kuzu.Database(db_path)
            conn = kuzu.Connection(db)
            for statement in _SCHEMA_DDL:
                conn.execute(statement)
            self._conn = conn
            logger.info("Opened embedded Kuzu KG database at %s", db_path)
        except Exception as e:  # pragma: no cover - defensive, mirrors KGClient
            logger.warning("Kuzu KG database unavailable (%s); KG features will no-op.", e)

    @property
    def available(self) -> bool:
        return self._conn is not None

    def run_query(self, cypher: str, **params: Any) -> List[Dict[str, Any]]:
        if self._conn is None:
            return []
        try:
            result = self._conn.execute(cypher, params)
            columns = result.get_column_names()
            rows = []
            while result.has_next():
                rows.append(dict(zip(columns, result.get_next())))
            return rows
        except Exception as e:
            logger.warning("KG query failed (%s): %s", e, cypher[:120])
            return []
