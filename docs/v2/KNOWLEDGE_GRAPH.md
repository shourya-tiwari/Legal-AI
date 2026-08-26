# Knowledge Graph

V1 has no cross-document memory of any kind — every clause is analyzed in isolation, and even within one document there's no structural link between, say, a defined term and every clause that uses it. The Knowledge Graph is V2's answer: a persistent, queryable graph of entities and relationships spanning a single document, an entire contract portfolio, and the external legal knowledge (statutes, regulations) those contracts are governed by.

## Storage

**Memgraph** (open source, in-memory, Cypher-compatible) is the primary graph database, chosen for query latency suited to interactive agent tool calls; **Neo4j Community Edition** is a documented alternative for deployments that prefer its tooling ecosystem. Both speak Cypher, so the query layer is portable between them.

## Schema

### Node types

| Node | Key properties |
|---|---|
| `Document` | id, org_id, title, sensitivity_tier, version |
| `Party` | id, name (resolved), role (tenant/landlord/employer/...) |
| `Clause` | id (= `ClauseObject.id` from `NLP.md`), clause_type, deontic_summary |
| `Obligation` | id, actor, action, condition, deadline (normalized) |
| `DefinedTerm` | id, term, definition_text |
| `DateEvent` | id, normalized_date_or_rule (e.g., recurring, conditional) |
| `Jurisdiction` | id, name |
| `Statute` | id, citation, text_excerpt, source_url |
| `CaseLaw` | id, citation, summary, source_url (where licensed) |
| `ContractType` | id, name (lease, employment, SaaS, ...) |
| `RiskFlag` | id, category, severity, source (keyword\|learned\|ai) |

### Edge types

| Edge | Meaning |
|---|---|
| `OBLIGATES(Party, Obligation)` | This party bears this obligation |
| `DEFINES(Clause, DefinedTerm)` | This clause is where a term is defined |
| `USES_TERM(Clause, DefinedTerm)` | This clause references a previously defined term |
| `REFERENCES(Clause, Clause)` | Explicit cross-reference between clauses |
| `AMENDS(Document, Document)` | One document amends another |
| `SUPERSEDES(Document, Document)` | One document supersedes another |
| `CONFLICTS_WITH(Clause, Clause)` | Detected contradiction (`NOVELTY.md` #1/#3) |
| `CITES(Clause, Statute\|CaseLaw)` | Grounding for RAG generation (`AI_STACK.md`) |
| `GOVERNED_BY(Document, Jurisdiction)` | Governing law |
| `PART_OF(Clause, Document)` | Structural membership |
| `TRIGGERED_BY(Obligation, DateEvent)` | Temporal trigger condition |

## Construction pipeline

```
NLP pipeline output (ClauseObject) + CV pipeline output
  → 1. Entity resolution        — cluster mentions of the same real-world entity across clauses/documents
  → 2. Relation extraction      — classify relationships between resolved entities
  → 3. Graph write              — upsert nodes/edges into Memgraph
  → 4. Schema validation        — enforce node/edge type constraints, flag deontic-logic inconsistencies
  → 5. Portfolio linking        — connect newly ingested document to related documents in the org's graph
```

1. **Entity resolution**: combines embedding-based clustering (using the Legal Clause Embedding Model, `DEEP_LEARNING.md`) with LLM-assisted disambiguation (Model Router Tier 0/1) for ambiguous cases — e.g., recognizing "ABC Corp," "the Company," and "ABC Corporation" as the same `Party` node across a document and across a portfolio.
2. **Relation extraction**: a fine-tuned relation classifier (extending the deontic tagger's output, `NLP.md`) handles common patterns (`OBLIGATES`, `DEFINES`, `USES_TERM`, `REFERENCES`) directly from structural cues; an LLM-assisted pass handles lower-confidence or novel relation types, with results logged for eventual distillation into the classifier (`DEEP_LEARNING.md`'s active learning loop).
3. **Graph write**: idempotent upserts, versioned by `document_versions.id` so re-analyzing an amended document doesn't silently overwrite the graph state of the prior version — both are retained (see temporal modeling below).
4. **Schema validation**: structural constraints (an `Obligation` must have an `actor`; a `CONFLICTS_WITH` edge must connect two `Clause` nodes with overlapping subject matter) plus **deontic logic consistency checks** — e.g., flagging a `Party` that is both obligated and prohibited from the same action under the same condition, a direct, mechanical use of the deontic tags from `NLP.md`.
5. **Portfolio linking**: new documents are checked against the org's existing graph for shared parties, defined terms, and referenced documents, building the cross-document connectivity that portfolio-level analysis depends on.

## Query patterns

- **GraphRAG traversal** (`AI_STACK.md`): starting from entities mentioned in a user's question, traverse `REFERENCES`/`USES_TERM`/`CITES` edges outward to assemble a grounded context set beyond what pure vector similarity would retrieve.
- **Portfolio conflict queries**: find all `Clause` pairs connected by (or inferable as) `CONFLICTS_WITH` across a party's full document set — the query backbone of `NOVELTY.md` #1.
- **Obligation timeline queries**: traverse `TRIGGERED_BY` edges to build a chronological or conditional view of everything a party must do, across every document that obligates them — feeds the Timeline UI module (`FRONTEND.md`) and the Simulation Agent (`NOVELTY.md` #2).
- **Dependency queries**: "what else changes if this clause is amended" — traverse `REFERENCES`/`DEFINES`/`USES_TERM` edges to find everything structurally dependent on a clause before a redline is suggested.

## Graph algorithms

- **Community detection** (e.g., Louvain) to automatically cluster related documents (e.g., a master service agreement and all its amendments/order forms) without relying on manual tagging.
- **Centrality measures** to identify "load-bearing" clauses/defined terms a large part of a portfolio structurally depends on — useful for prioritizing what a Risk & Compliance Agent should scrutinize most carefully before any change is approved.
- **Path-finding** between `Obligation` nodes to detect indirect conflicts (A obligates B obligates C in a way that circles back to contradict A) that a pairwise-only comparison would miss.

## Temporal modeling

The graph is **bitemporal**: every node/edge carries both a *valid time* (when the underlying contractual fact is/was legally effective) and a *transaction time* (when the platform recorded it). This distinction is what allows:
- Querying "what did the obligation graph look like as of last year" (valid-time query) independent of when the analysis was actually run.
- Full audit reproducibility — re-running a query against the graph as it existed at a specific transaction time reproduces exactly what an agent saw when it made a past decision (directly supporting the auditability requirement in `AGENTS.md`).
- The forward-looking simulation in `NOVELTY.md` #2, which needs to reason about valid-time states that haven't occurred yet.

## Storage and performance

- Per-org graph partitioning for multi-tenant isolation and independent scaling (`ARCHITECTURE.md`).
- Periodic snapshotting of the in-memory Memgraph state to object storage (MinIO) for durability and disaster recovery, since Memgraph's primary storage model is in-memory.
- Query templates used by agent tools (`AGENTS.md`) are pre-approved and parameterized, not free-form Cypher generated by an LLM — bounding both performance (no runaway queries) and security (no injection via a generated query string).
