# backend/app/services/rag/graph_retrieval.py
"""
GraphRAG leg of hybrid retrieval (docs/v2/AI_STACK.md): given a set of defined
terms, pull the clause texts across the org's portfolio that use those terms
(traversing SAME_AS links too) so they can be fused into hybrid_search
alongside BM25 + dense.

Fail-soft: if Memgraph is unreachable this returns [] and hybrid retrieval
just proceeds with BM25 + dense, exactly as before Phase 5.
"""
from __future__ import annotations

import logging
from typing import Iterable, List

from app.services.kg.client import get_kg_client
from app.services.kg.queries import find_clauses_using_term

logger = logging.getLogger("legalai.rag.graph_retrieval")


def graph_hits_for_terms(org_id: int, terms: Iterable[str], *, limit: int = 5,
                         exclude_texts: Iterable[str] = ()) -> List[str]:
    """Clause texts from the portfolio graph that use any of `terms`.
    De-duplicated, capped at `limit`, with `exclude_texts` filtered out
    (e.g. the clause currently being researched)."""
    client = get_kg_client()
    if not client.available:
        return []

    excluded = {t.strip() for t in exclude_texts}
    seen: set = set()
    hits: List[str] = []
    for term in {t for t in terms if t and t.strip()}:
        try:
            rows = find_clauses_using_term(client, org_id, term)
        except Exception as e:  # fail-soft -- never let a graph error break retrieval
            logger.warning("graph_hits_for_terms: query for term %r failed: %s", term, e)
            continue
        for row in rows:
            text = (row.get("text") or "").strip()
            if not text or text in excluded or text in seen:
                continue
            seen.add(text)
            hits.append(text)
            if len(hits) >= limit:
                return hits
    return hits
