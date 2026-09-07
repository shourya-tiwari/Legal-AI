# backend/app/services/kg/schema.py
"""
Graph schema (docs/v2/KNOWLEDGE_GRAPH.md), scoped down to what Phase 2's
ClauseObject output actually supports today:

Nodes:  Document, Clause, DefinedTerm, CrossReferenceTarget
Edges:  (Clause)-[:PART_OF]->(Document)
        (Document)-[:DEFINES]->(DefinedTerm)
        (Clause)-[:USES_TERM]->(DefinedTerm)
        (Clause)-[:REFERENCES]->(CrossReferenceTarget)
        (DefinedTerm)-[:SAME_AS]->(DefinedTerm)   -- portfolio-linking, see builder.py
        (Document)-[:SUPERSEDES]->(Document)      -- bitemporal versioning, see versioning.py

Deliberately NOT modeled yet: Obligation nodes with resolved actor/action
(docs/v2/KNOWLEDGE_GRAPH.md's full vision) -- Phase 2's deontic tagger
doesn't resolve `actor`, so a real Obligation node graph would be guessing.
Deontic modalities are stored as a property on Clause instead
(`deontic_modalities: [str]`), honest about what's actually known. Also not
modeled: Statute/CaseLaw/Jurisdiction nodes (RAG's citation grounding uses a
separate, non-graph corpus for now -- see services/rag/), Party/Obligation
distinctions.

Bitemporal versioning (Phase 8, `versioning.py`, `LEARNING_LOG.md` #50):
Document and Clause nodes carry `created_at` (transaction time -- when this
graph write happened, stamped in Python at write time, not a Cypher
`timestamp()` call, so it's identical across the Memgraph/Kuzu backends)
and `valid_from`/`valid_to` (valid time -- the real-world period this
version of the document/clause was in effect; `valid_to` is null/absent
while a version is still current). `versioning.mark_document_superseded`
closes the prior version's `valid_to` and opens the new version's
`valid_from` at the same instant, and creates the `SUPERSEDES` edge so a
document's full version history is traversable, not just its current
state. This intentionally applies only at the Document/Clause level --
there is still no Obligation-node concept to version.
"""

DOCUMENT = "Document"
CLAUSE = "Clause"
DEFINED_TERM = "DefinedTerm"
CROSS_REFERENCE_TARGET = "CrossReferenceTarget"

PART_OF = "PART_OF"
DEFINES = "DEFINES"
USES_TERM = "USES_TERM"
REFERENCES = "REFERENCES"
SAME_AS = "SAME_AS"
SUPERSEDES = "SUPERSEDES"


def ensure_constraints(client) -> None:
    """Idempotent uniqueness constraints. Safe to call repeatedly (e.g. on
    every app startup) -- Memgraph no-ops if a constraint already exists.

    No-ops entirely for the Kuzu backend (Settings.KG_BACKEND="kuzu",
    docs/v2/ROADMAP.md Phase 7 "Collapsed data layer"): Kuzu doesn't support
    Memgraph's `CREATE CONSTRAINT ... ASSERT ... IS UNIQUE` syntax at all,
    and doesn't need to -- every Kuzu node table already declares
    `PRIMARY KEY(id)` at creation time (kuzu_client.py's `_SCHEMA_DDL`),
    which enforces the identical uniqueness guarantee up front."""
    if getattr(client, "backend", "memgraph") == "kuzu":
        return
    statements = [
        f"CREATE CONSTRAINT ON (d:{DOCUMENT}) ASSERT d.id IS UNIQUE",
        f"CREATE CONSTRAINT ON (c:{CLAUSE}) ASSERT c.id IS UNIQUE",
        f"CREATE CONSTRAINT ON (t:{DEFINED_TERM}) ASSERT t.id IS UNIQUE",
        f"CREATE CONSTRAINT ON (r:{CROSS_REFERENCE_TARGET}) ASSERT r.id IS UNIQUE",
    ]
    for statement in statements:
        client.run_query(statement)
