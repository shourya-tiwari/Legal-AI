# backend/app/services/kg/builder.py
"""
Converts Phase 2's ClauseObject output (app/services/nlp/) into graph writes.
Deliberately does NOT auto-merge same-named defined terms across different
documents by node identity -- "the Company" in one contract and "the
Company" in an unrelated one are not the same entity just because they share
an alias. Every DefinedTerm/CrossReferenceTarget node is scoped to its own
document; cross-document links are a separate, evidence-based step
(`link_portfolio_terms`) that only connects terms when both the alias text
AND the surrounding defining context are actually similar -- see
`should_link_terms`'s docstring.
"""
from __future__ import annotations

import difflib
import re
from typing import Dict, List

from app.services.nlp.schema import ClauseObject

from . import schema
from .client import KGClient

CONTEXT_SIMILARITY_THRESHOLD = 0.6


def normalize_term(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def document_node_id(document_id: int) -> str:
    return f"doc:{document_id}"


def clause_node_id(document_id: int, ordinal: int) -> str:
    return f"doc:{document_id}:clause:{ordinal}"


def term_node_id(document_id: int, term: str) -> str:
    return f"doc:{document_id}:term:{normalize_term(term)}"


def cross_ref_node_id(document_id: int, ref_text: str) -> str:
    return f"doc:{document_id}:ref:{normalize_term(ref_text)}"


def should_link_terms(term_a: str, context_a: str, term_b: str, context_b: str) -> bool:
    """Two defined terms (from different documents) are linked only when
    their alias text matches AND their defining context is similar enough --
    catching "the same counterparty, named consistently, across contracts"
    without conflating two different parties who happen to both be called
    "the Company" in their own agreements."""
    if normalize_term(term_a) != normalize_term(term_b):
        return False
    similarity = difflib.SequenceMatcher(None, context_a, context_b).ratio()
    return similarity >= CONTEXT_SIMILARITY_THRESHOLD


def write_document_graph(
    client: KGClient,
    org_id: int,
    document_id: int,
    defined_terms: Dict[str, str],
    clauses: List[ClauseObject],
) -> Dict[str, int]:
    """Writes Document/Clause/DefinedTerm/CrossReferenceTarget nodes and
    their edges for one document. Idempotent (safe to re-run on re-analysis
    of the same document -- MERGE, not CREATE, throughout)."""
    if not client.available:
        return {"clauses": 0, "defined_terms": 0, "cross_references": 0}

    doc_id = document_node_id(document_id)
    client.run_query(
        f"MERGE (d:{schema.DOCUMENT} {{id: $id}}) SET d.org_id = $org_id, d.document_id = $document_id",
        id=doc_id, org_id=org_id, document_id=document_id,
    )

    for term, context in defined_terms.items():
        t_id = term_node_id(document_id, term)
        client.run_query(
            f"MERGE (t:{schema.DEFINED_TERM} {{id: $id}}) SET t.term = $term, t.context = $context, t.org_id = $org_id",
            id=t_id, term=term, context=context, org_id=org_id,
        )
        client.run_query(
            f"MATCH (d:{schema.DOCUMENT} {{id: $doc_id}}), (t:{schema.DEFINED_TERM} {{id: $term_id}}) "
            f"MERGE (d)-[:{schema.DEFINES}]->(t)",
            doc_id=doc_id, term_id=t_id,
        )

    cross_ref_count = 0
    for clause in clauses:
        c_id = clause_node_id(document_id, clause.id)
        client.run_query(
            # `text` is a reserved word in Memgraph's Cypher dialect and can't
            # be used as a bare property key (c.text fails to parse) -- the
            # property is called `content` here for that reason.
            f"MERGE (c:{schema.CLAUSE} {{id: $id}}) "
            f"SET c.content = $content, c.clause_type = $clause_type, c.org_id = $org_id, "
            f"c.deontic_modalities = $modalities",
            id=c_id, content=clause.text, clause_type=clause.clause_type, org_id=org_id,
            modalities=[t.modality for t in clause.deontic_tags],
        )
        client.run_query(
            f"MATCH (c:{schema.CLAUSE} {{id: $c_id}}), (d:{schema.DOCUMENT} {{id: $doc_id}}) "
            f"MERGE (c)-[:{schema.PART_OF}]->(d)",
            c_id=c_id, doc_id=doc_id,
        )

        for term in clause.defined_terms_used:
            t_id = term_node_id(document_id, term)
            client.run_query(
                f"MATCH (c:{schema.CLAUSE} {{id: $c_id}}), (t:{schema.DEFINED_TERM} {{id: $term_id}}) "
                f"MERGE (c)-[:{schema.USES_TERM}]->(t)",
                c_id=c_id, term_id=t_id,
            )

        for ref in clause.cross_references:
            r_id = cross_ref_node_id(document_id, ref.text)
            client.run_query(
                f"MERGE (r:{schema.CROSS_REFERENCE_TARGET} {{id: $id}}) SET r.content = $content, r.org_id = $org_id",
                id=r_id, content=ref.text, org_id=org_id,
            )
            client.run_query(
                f"MATCH (c:{schema.CLAUSE} {{id: $c_id}}), (r:{schema.CROSS_REFERENCE_TARGET} {{id: $r_id}}) "
                f"MERGE (c)-[:{schema.REFERENCES}]->(r)",
                c_id=c_id, r_id=r_id,
            )
            cross_ref_count += 1

    return {"clauses": len(clauses), "defined_terms": len(defined_terms), "cross_references": cross_ref_count}


def link_portfolio_terms(client: KGClient, org_id: int, document_id: int, defined_terms: Dict[str, str]) -> int:
    """Compares this document's defined terms against every other
    DefinedTerm in the org, creating a SAME_AS edge wherever
    `should_link_terms` says they're plausibly the same entity. Returns the
    number of links created."""
    if not client.available:
        return 0

    doc_id = document_node_id(document_id)
    others = client.run_query(
        f"MATCH (t:{schema.DEFINED_TERM})<-[:{schema.DEFINES}]-(otherDoc:{schema.DOCUMENT} {{org_id: $org_id}}) "
        f"WHERE otherDoc.id <> $doc_id "
        f"RETURN t.id AS id, t.term AS term, t.context AS context",
        org_id=org_id, doc_id=doc_id,
    )

    links_created = 0
    for term, context in defined_terms.items():
        this_id = term_node_id(document_id, term)
        for other in others:
            if should_link_terms(term, context, other["term"], other["context"]):
                client.run_query(
                    f"MATCH (a:{schema.DEFINED_TERM} {{id: $a_id}}), (b:{schema.DEFINED_TERM} {{id: $b_id}}) "
                    f"MERGE (a)-[:{schema.SAME_AS}]->(b)",
                    a_id=this_id, b_id=other["id"],
                )
                links_created += 1

    return links_created
