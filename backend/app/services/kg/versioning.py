# backend/app/services/kg/versioning.py
"""
Bitemporal graph versioning (docs/v2/ROADMAP.md Phase 8 "Bitemporal graph
versioning (valid time / transaction time) -- the Phase 3 gap").

Applies only at the Document/Clause level -- there is still no Obligation
node concept to version (see schema.py). The model:

  - `created_at` (transaction time): when this node was first written to
    the graph, stamped once and never changed by re-ingestion or
    supersession (builder.py's `coalesce(x.created_at, $now)`).
  - `valid_from` / `valid_to` (valid time): the real-world period this
    version of the document/clause was actually in effect. `valid_to` is
    absent (null) while a version is still current.

`mark_document_superseded` is the one write in this module: given an org
already has both documents ingested (`write_document_graph` for each),
it closes the old document's clauses' `valid_to` and creates a
`(new)-[:SUPERSEDES]->(old)` edge, so a document's full version history is
a graph traversal, not just its current snapshot. It does NOT re-open or
change the new document's `valid_from` unless one is explicitly given --
by default the new document's clauses keep the `valid_from` they already
got at ingestion time (when they were written), which is the honest
default when no real-world effective date is known.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from . import schema
from .builder import document_node_id
from .client import KGClient


def mark_document_superseded(
    client: KGClient,
    org_id: int,
    old_document_id: int,
    new_document_id: int,
    valid_from: Optional[str] = None,
) -> Dict[str, Any]:
    """Closes `old_document_id`'s clauses' valid-time interval at
    `valid_from` (defaults to now) and links
    `(new)-[:SUPERSEDES {valid_from}]->(old)`. Both documents must already
    be ingested (`write_document_graph`) -- this only versions, it doesn't
    create graph nodes for a document that was never analyzed."""
    if not client.available:
        return {"kg_available": False, "clauses_closed": 0}

    effective = valid_from or datetime.now(timezone.utc).isoformat()
    old_id = document_node_id(old_document_id)
    new_id = document_node_id(new_document_id)

    client.run_query(
        f"MATCH (old:{schema.DOCUMENT} {{id: $old_id}}), (new:{schema.DOCUMENT} {{id: $new_id}}) "
        f"MERGE (new)-[r:{schema.SUPERSEDES}]->(old) "
        f"SET r.valid_from = $effective",
        old_id=old_id, new_id=new_id, effective=effective,
    )

    result = client.run_query(
        f"MATCH (c:{schema.CLAUSE})-[:{schema.PART_OF}]->(d:{schema.DOCUMENT} {{id: $old_id}}) "
        f"SET c.valid_to = $effective "
        f"RETURN count(c) AS n",
        old_id=old_id, effective=effective,
    )
    clauses_closed = result[0]["n"] if result else 0

    return {"kg_available": True, "valid_from": effective, "clauses_closed": clauses_closed}


def find_document_version_history(client: KGClient, document_id: int) -> List[Dict[str, Any]]:
    """Walks the SUPERSEDES chain in both directions from `document_id`,
    returning every version with its valid-time window -- oldest first."""
    if not client.available:
        return []

    doc_id = document_node_id(document_id)
    rows = client.run_query(
        f"MATCH (d:{schema.DOCUMENT} {{id: $doc_id}}) "
        f"OPTIONAL MATCH (d)-[:{schema.SUPERSEDES}*0..]->(older:{schema.DOCUMENT}) "
        f"OPTIONAL MATCH (newer:{schema.DOCUMENT})-[:{schema.SUPERSEDES}*0..]->(d) "
        f"WITH collect(DISTINCT older) + collect(DISTINCT newer) AS versions "
        f"UNWIND versions AS v "
        f"WITH DISTINCT v WHERE v IS NOT NULL "
        f"RETURN v.document_id AS document_id, v.created_at AS created_at, "
        f"v.valid_from AS valid_from ORDER BY v.valid_from",
        doc_id=doc_id,
    )
    return rows


def find_clauses_valid_as_of(client: KGClient, org_id: int, term: str, as_of: str) -> List[Dict[str, Any]]:
    """Same shape as queries.find_clauses_using_term, filtered to clauses
    whose valid-time window actually covers `as_of` (an ISO date/datetime
    string) -- "what did the portfolio say about this term as of this
    date," not just "what does it say now." A clause with no `valid_to`
    is still open (current) and matches any `as_of` on/after its
    `valid_from`."""
    from .builder import normalize_term

    if not client.available:
        return []

    cypher = (
        f"MATCH (t:{schema.DEFINED_TERM} {{org_id: $org_id}}) "
        f"WHERE toLower(t.term) = $term "
        f"MATCH (c:{schema.CLAUSE})-[:{schema.USES_TERM}]->(t) "
        f"MATCH (c)-[:{schema.PART_OF}]->(d:{schema.DOCUMENT}) "
        f"WHERE c.valid_from <= $as_of AND (c.valid_to IS NULL OR c.valid_to > $as_of) "
        f"RETURN DISTINCT c.id AS clause_id, c.content AS `text`, c.clause_type AS clause_type, "
        f"d.document_id AS document_id, c.valid_from AS valid_from, c.valid_to AS valid_to"
    )
    return client.run_query(cypher, org_id=org_id, term=normalize_term(term), as_of=as_of)
