# backend/app/services/kg/graph_export.py
"""
A node/edge-shaped export of one document's knowledge graph neighborhood,
for the Knowledge Graph Explorer frontend (docs/v2/ROADMAP.md Phase 8,
docs/v2/FRONTEND.md: "Knowledge Graph Explorer's visual graph (Cytoscape.js)
-- not built yet"). Every other function in this package (`queries.py`)
answers a specific question ("which clauses use this term"); this one
answers "give me the whole local graph shape so a frontend can draw it."

Deliberately several small, separate queries rather than one clever
WITH/UNWIND traversal -- `queries.py`'s own docstring already documents a
real, empirically-found Kuzu/Memgraph Cypher-dialect divergence around
reusing a bound node object across WITH/UNWIND into a later MATCH; several
simple, independently-portable queries avoid that whole class of risk
rather than requiring a second backend-specific variant here too.
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import schema
from .builder import document_node_id
from .client import KGClient

MAX_LABEL_CHARS = 60


def _truncate(text: str, max_chars: int = MAX_LABEL_CHARS) -> str:
    text = text or ""
    return text if len(text) <= max_chars else text[: max_chars - 1] + "…"


def get_document_graph(client: KGClient, document_id: int) -> Dict[str, Any]:
    """Nodes + edges for `document_id`'s own clauses/defined terms/cross-
    references, plus one hop of SAME_AS-linked defined terms in other
    documents (so the portfolio-linking `builder.link_portfolio_terms`
    already does has something to actually show). Returns
    `{"nodes": [...], "edges": [...], "kg_available": bool}` -- fails soft
    to empty lists, matching every other function in this package."""
    if not client.available:
        return {"nodes": [], "edges": [], "kg_available": False}

    doc_id = document_node_id(document_id)
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    seen_node_ids: set[str] = set()

    def add_node(node_id: str, label: str, node_type: str, **extra: Any) -> None:
        if node_id in seen_node_ids:
            return
        seen_node_ids.add(node_id)
        nodes.append({"id": node_id, "label": label, "type": node_type, **extra})

    doc_rows = client.run_query(
        f"MATCH (d:{schema.DOCUMENT} {{id: $doc_id}}) RETURN d.id AS id, d.document_id AS document_id",
        doc_id=doc_id,
    )
    if not doc_rows:
        return {"nodes": [], "edges": [], "kg_available": True}
    add_node(doc_id, f"Document {document_id}", "Document")

    clause_rows = client.run_query(
        f"MATCH (c:{schema.CLAUSE})-[:{schema.PART_OF}]->(d:{schema.DOCUMENT} {{id: $doc_id}}) "
        f"RETURN c.id AS id, c.content AS `text`, c.clause_type AS clause_type",
        doc_id=doc_id,
    )
    for row in clause_rows:
        add_node(row["id"], _truncate(row["text"]), "Clause", clause_type=row.get("clause_type"))
        edges.append({"source": row["id"], "target": doc_id, "type": schema.PART_OF})

    term_rows = client.run_query(
        f"MATCH (d:{schema.DOCUMENT} {{id: $doc_id}})-[:{schema.DEFINES}]->(t:{schema.DEFINED_TERM}) "
        f"RETURN t.id AS id, t.term AS term",
        doc_id=doc_id,
    )
    for row in term_rows:
        add_node(row["id"], row["term"], "DefinedTerm")
        edges.append({"source": doc_id, "target": row["id"], "type": schema.DEFINES})

    ref_rows = client.run_query(
        f"MATCH (c:{schema.CLAUSE})-[:{schema.PART_OF}]->(d:{schema.DOCUMENT} {{id: $doc_id}}) "
        f"MATCH (c)-[:{schema.REFERENCES}]->(r:{schema.CROSS_REFERENCE_TARGET}) "
        f"RETURN DISTINCT c.id AS clause_id, r.id AS ref_id, r.content AS `text`",
        doc_id=doc_id,
    )
    for row in ref_rows:
        add_node(row["ref_id"], _truncate(row["text"]), "CrossReferenceTarget")
        edges.append({"source": row["clause_id"], "target": row["ref_id"], "type": schema.REFERENCES})

    uses_rows = client.run_query(
        f"MATCH (c:{schema.CLAUSE})-[:{schema.PART_OF}]->(d:{schema.DOCUMENT} {{id: $doc_id}}) "
        f"MATCH (c)-[:{schema.USES_TERM}]->(t:{schema.DEFINED_TERM}) "
        f"RETURN DISTINCT c.id AS clause_id, t.id AS term_id",
        doc_id=doc_id,
    )
    for row in uses_rows:
        edges.append({"source": row["clause_id"], "target": row["term_id"], "type": schema.USES_TERM})

    # One hop of portfolio-linked terms (builder.link_portfolio_terms's
    # SAME_AS edges) -- the actual point of an "explorer": showing that a
    # term in this document is recognized as the same entity elsewhere.
    linked_rows = client.run_query(
        f"MATCH (d:{schema.DOCUMENT} {{id: $doc_id}})-[:{schema.DEFINES}]->(t:{schema.DEFINED_TERM}) "
        f"MATCH (t)-[:{schema.SAME_AS}]-(linked:{schema.DEFINED_TERM}) "
        f"RETURN DISTINCT t.id AS term_id, linked.id AS linked_id, linked.term AS linked_term",
        doc_id=doc_id,
    )
    for row in linked_rows:
        add_node(row["linked_id"], row["linked_term"], "DefinedTerm", portfolio_linked=True)
        edges.append({"source": row["term_id"], "target": row["linked_id"], "type": schema.SAME_AS})

    return {"nodes": nodes, "edges": edges, "kg_available": True}
