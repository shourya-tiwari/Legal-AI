# backend/app/services/kg/queries.py
"""
Canonical read queries over the graph -- the GraphRAG traversal side of
docs/v2/AI_STACK.md's hybrid retrieval, and the portfolio-level queries from
docs/v2/KNOWLEDGE_GRAPH.md, scoped to what the current graph actually models
(see schema.py's docstring for what's NOT modeled yet).
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import schema
from .builder import normalize_term
from .client import KGClient


def find_clauses_using_term(client: KGClient, org_id: int, term: str) -> List[Dict[str, Any]]:
    """All clauses across the org's portfolio that use a defined term with
    this name, including clauses in documents whose matching term was
    SAME_AS-linked to this one (see builder.link_portfolio_terms).

    Two query variants, picked by `client.backend`: Memgraph/Neo4j allow a
    bound node object (`t`/`linked`) to flow through WITH/UNWIND and be
    reused directly as a MATCH pattern later in the same query. Kuzu's
    binder rejects that ("Cannot bind term as node pattern") -- confirmed
    empirically against a real embedded Kuzu database, not assumed from
    docs -- so the Kuzu variant collects `.id` (a plain string) instead and
    re-MATCHes by id. Every other query in this module runs unchanged
    against both backends; this is the one genuine Cypher-dialect
    difference between them that this codebase's queries hit."""
    if getattr(client, "backend", "memgraph") == "kuzu":
        cypher = (
            f"MATCH (t:{schema.DEFINED_TERM} {{org_id: $org_id}}) "
            f"WHERE toLower(t.term) = $term "
            f"OPTIONAL MATCH (t)-[:{schema.SAME_AS}]-(linked:{schema.DEFINED_TERM}) "
            f"WITH collect(DISTINCT t.id) + coalesce(collect(DISTINCT linked.id), []) AS term_ids "
            f"UNWIND term_ids AS term_id "
            f"WITH DISTINCT term_id WHERE term_id IS NOT NULL "
            f"MATCH (term:{schema.DEFINED_TERM} {{id: term_id}}) "
            f"MATCH (c:{schema.CLAUSE})-[:{schema.USES_TERM}]->(term) "
            f"MATCH (c)-[:{schema.PART_OF}]->(d:{schema.DOCUMENT}) "
            f"RETURN DISTINCT c.id AS clause_id, c.content AS `text`, c.clause_type AS clause_type, "
            f"d.document_id AS document_id"
        )
    else:
        cypher = (
            f"MATCH (t:{schema.DEFINED_TERM} {{org_id: $org_id}}) "
            f"WHERE toLower(t.term) = $term "
            f"OPTIONAL MATCH (t)-[:{schema.SAME_AS}]-(linked:{schema.DEFINED_TERM}) "
            f"WITH collect(DISTINCT t) + collect(DISTINCT linked) AS terms "
            f"UNWIND terms AS term "
            f"WITH term WHERE term IS NOT NULL "
            f"MATCH (c:{schema.CLAUSE})-[:{schema.USES_TERM}]->(term) "
            f"MATCH (c)-[:{schema.PART_OF}]->(d:{schema.DOCUMENT}) "
            # `text` is reserved in Memgraph's Cypher grammar -- needs
            # backticks even as a plain RETURN alias, not just for property access.
            f"RETURN DISTINCT c.id AS clause_id, c.content AS `text`, c.clause_type AS clause_type, "
            f"d.document_id AS document_id"
        )
    return client.run_query(cypher, org_id=org_id, term=normalize_term(term))


def find_potential_conflicts(client: KGClient, org_id: int, term: str) -> List[Dict[str, Any]]:
    """Clauses using the same (or SAME_AS-linked) defined term where one
    clause is an obligation and another, in a DIFFERENT document, is a
    prohibition -- a candidate for review, not a confirmed conflict (actor/
    action aren't resolved yet, see schema.py). This is the scoped-down
    version of docs/v2/KNOWLEDGE_GRAPH.md's portfolio conflict query."""
    clauses = find_clauses_using_term(client, org_id, term)
    if not clauses:
        return []

    detailed = client.run_query(
        f"MATCH (c:{schema.CLAUSE}) WHERE c.id IN $ids "
        f"MATCH (c)-[:{schema.PART_OF}]->(d:{schema.DOCUMENT}) "
        f"RETURN c.id AS clause_id, c.content AS `text`, c.deontic_modalities AS modalities, "
        f"d.document_id AS document_id",
        ids=[c["clause_id"] for c in clauses],
    )

    obligations = [c for c in detailed if "obligation" in (c["modalities"] or [])]
    prohibitions = [c for c in detailed if "prohibition" in (c["modalities"] or [])]

    conflicts = []
    for ob in obligations:
        for pr in prohibitions:
            if ob["document_id"] != pr["document_id"]:
                conflicts.append({"obligation": ob, "prohibition": pr})

    return conflicts


def get_document_graph_summary(client: KGClient, document_id: int) -> Dict[str, Any]:
    from .builder import document_node_id

    doc_id = document_node_id(document_id)
    rows = client.run_query(
        f"MATCH (d:{schema.DOCUMENT} {{id: $doc_id}}) "
        f"OPTIONAL MATCH (c:{schema.CLAUSE})-[:{schema.PART_OF}]->(d) "
        f"OPTIONAL MATCH (d)-[:{schema.DEFINES}]->(t:{schema.DEFINED_TERM}) "
        f"RETURN count(DISTINCT c) AS clause_count, collect(DISTINCT t.term) AS defined_terms",
        doc_id=doc_id,
    )
    if not rows:
        return {"clause_count": 0, "defined_terms": []}
    return rows[0]
