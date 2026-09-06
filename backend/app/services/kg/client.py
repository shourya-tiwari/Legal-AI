# backend/app/services/kg/client.py
"""
Memgraph client, fail-soft by design: if Memgraph is unreachable (not
running, wrong URI), KG operations log a warning and return empty results
rather than crashing the request -- the same philosophy as
app/rate_limit.py's fail-open Redis handling. The rest of the app must not
depend on this being up.

Memgraph speaks the Bolt protocol, the same one Neo4j uses, so the official
`neo4j` Python driver works against it unmodified.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any, Dict, List

from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError, ServiceUnavailable

from app.config import get_settings

logger = logging.getLogger("legalai.kg.client")


class KGClient:
    # docs/v2/ROADMAP.md Phase 7 "Collapsed data layer" -- `KuzuKGClient`
    # (kuzu_client.py) is the embedded substitute selected by
    # Settings.KG_BACKEND="kuzu"; both expose the same `run_query`/
    # `available` interface, and `backend` is how queries.py tells them
    # apart for the one query whose Cypher genuinely differs between engines
    # (see find_clauses_using_term's docstring).
    backend = "memgraph"

    def __init__(self, uri: str, user: str, password: str):
        self._driver = None
        driver = None
        try:
            auth = (user, password) if user else None
            driver = GraphDatabase.driver(uri, auth=auth, connection_timeout=0.5)
            driver.verify_connectivity()
            self._driver = driver
            logger.info("Connected to Memgraph at %s", uri)
        except Exception as e:
            logger.warning("Memgraph unavailable (%s); KG features will no-op.", e)
            if driver is not None:
                driver.close()  # avoid relying on GC/destructor to release the connection

    @property
    def available(self) -> bool:
        return self._driver is not None

    def run_query(self, cypher: str, **params: Any) -> List[Dict[str, Any]]:
        if self._driver is None:
            return []
        try:
            with self._driver.session() as session:
                result = session.run(cypher, **params)
                return [record.data() for record in result]
        except (ServiceUnavailable, Neo4jError) as e:
            logger.warning("KG query failed (%s): %s", e, cypher[:120])
            return []


@lru_cache
def get_kg_client():
    settings = get_settings()
    if settings.KG_BACKEND == "kuzu":
        from .kuzu_client import KuzuKGClient

        return KuzuKGClient(settings.KUZU_DB_PATH)
    return KGClient(settings.MEMGRAPH_URI, settings.MEMGRAPH_USER, settings.MEMGRAPH_PASSWORD)
