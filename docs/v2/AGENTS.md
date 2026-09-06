# Agentic AI Architecture

V1 has no agency: each route makes exactly one LLM call and returns whatever comes back, unverified. V2's central architectural bet is that legal reasoning tasks — cross-referencing clauses, checking a claim against a knowledge graph, deciding whether a risk flag is grounded — are better handled by a small set of specialized agents that plan, use tools, and check each other's work than by one large prompt asking a single model to do everything at once.

## Orchestration framework

**LangGraph** (MIT) implements each workflow as an explicit state graph rather than a free-form agent loop — a deliberate choice for a legal domain where **determinism and auditability matter more than open-ended autonomy**. Every node transition, tool call, and intermediate state is recorded. Shipped in Phase 4 as a fixed pipeline; **Phase 7** made it **planner-driven** — a `planner` node runs after extraction and sets `state.plan` (the ordered node ids to execute), and the graph dispatches by it, so a document with no risk/ambiguity signal runs `extraction → planner → verifier` and skips the middle agents entirely (`app/agents/{planner,registry,graph}.py`).

Long-running graphs execute on a **durable-execution engine** (`BACKEND.md`, `MODEL_STACK.md`) so a multi-step analysis survives process restarts and individual step failures retry without re-running the whole graph. The engine is **pluggable and not a vendor commitment**: **DBOS** (a library, Postgres-backed — no extra service) is the default for on-prem/air-gapped and mid-scale; **Hatchet** for larger self-hosted; **Temporal** only where the multi-tenant cloud profile's scale justifies operating it. The `app/agents/graph.py` abstraction stays engine-agnostic. Phase 4 runs synchronously in-request; the durable engine lands in Phase 7.

Every model call an agent makes goes through the **provider-agnostic Model Router** (`AI_STACK.md`) — agents name a *task*, never a model or vendor. In the on-prem and air-gapped profiles every agent runs entirely on self-hosted models (Class A/B); no agent has a hard dependency on a commercial API.

All agents read and write a shared **Case State** object (the LangGraph state), which is the structured successor to V1's pattern of re-sending raw text on every call:

```
CaseState {
  document_ids: [...]
  clauses: [ClauseObject, ...]        # from NLP.md
  kg_refs: [...]                       # node IDs in the Knowledge Graph
  sensitivity_tier: enum
  findings: { risk: [...], structure: [...], contradictions: [...] }
  citations: [...]
  verification_status: { claim_id -> verified|unverified|contradicted }
  memory_refs: [...]                   # pointers into the Memory Service
  trace: [AgentStep, ...]              # full audit trail, persisted to agent_traces
}
```

## Agent roster

| Agent | Role | Key tools | Escalates to |
|---|---|---|---|
| **Orchestrator/Planner** | Decides which specialist agents run for a document — **shipped (Phase 7)** as `app/agents/planner.py`: rule-based by default (heuristics over the extracted clauses), optional LLM planning (`task="agent_plan"`, falls back to rules offline), plus `analysis_mode` presets (`full`/`quick`/`risk_only`/`extract_only`). The *full* vision — decomposing an arbitrary user request into a task graph and choosing tools dynamically — is still ahead. | Case-state read/write, agent registry (`registry.py`) | — |
| **Ingestion & Triage** | Classifies document type and sensitivity tier, routes to the right pipeline configuration. **Sensitivity half shipped (Phase 7)** as a service — `app/services/sensitivity/classify_sensitivity()` runs at upload, persists `documents.sensitivity_tier`, and every downstream generate call is routed against it (`AI_STACK.md`). A LangGraph triage *node* + document-type classification are still ahead. | CV/NLP pipeline triggers, sensitivity classifier | Human review / org-admin override (`PUT /api/v2/documents/{id}/sensitivity`) |
| **Extraction** | Wraps the NLP/CV pipelines' output into structured clauses, entities, and timeline events | NLP pipeline, CV pipeline, date/calendar tool | Verifier |
| **Risk & Compliance** | Runs keyword + learned risk scoring (`DEEP_LEARNING.md`), checks flags against KG-known statutory rules | Risk scorer, KG query tool, statute lookup tool | Verifier |
| **Clause Research** | Hybrid RAG retrieval (`AI_STACK.md`) to answer questions and ground explanations in cited sources | Vector search tool, BM25 tool, GraphRAG traversal tool | Verifier |
| **Contextualizer/Advisory** | Produces role/tone-personalized explanations (V1 feature, evolved) | Clause Research agent's output, tone/role prompt templates | Verifier |
| **Negotiation/Drafting** | Suggests redlines, informed by procedural memory of the org's negotiation history | Clause diff tool, procedural memory read, KG query tool | Human approval gate (always, for any suggested edit sent externally) |
| **Cross-Document Consistency** | Portfolio-level contradiction/conflict detection across a user's document set. **Embedding-similarity baseline shipped (Phase 8)**: `app/services/consistency.py` embeds every deontic-tagged clause in a document and every other org document, flags pairs above a similarity threshold whose modality actively conflicts — catches same-concept-different-wording pairs the KG's exact-term match can't. Not yet a standalone agent-graph node (a direct service call via `POST /api/v2/documents/{id}/consistency`); the learned legal-semantic fingerprint matcher (`NOVELTY.md` #3) is still ahead. | KG traversal, legal-semantic fingerprint matcher (`NOVELTY.md` #3) | Verifier |
| **Simulation** | Projects the obligation graph forward in time to surface emergent risks (renewal traps, notice-period collisions). **Deterministic single-document baseline shipped (Phase 8)**: `app/services/simulation.py` classifies every clause with a resolved absolute date as past/upcoming/future against a reference date. Portfolio-scope emergent-risk detection over `TRIGGERED_BY` graph edges + Monte Carlo sampling (`NOVELTY.md` #2) is still ahead — needs `Obligation`/`TRIGGERED_BY` KG nodes that don't exist yet (`KNOWLEDGE_GRAPH.md`). | Temporal obligation simulator (`NOVELTY.md` #2), calendar tool | Verifier |
| **Verifier/Critic** | Checks every other agent's output against source text and the KG before release; the single mandatory gate before any answer reaches a user | NLI faithfulness checker, KG fact-check tool, citation validator | Human review queue on failure |

### Adversarial stress-testing (optional, high-stakes documents)

For high-value/high-risk documents, an optional **Red Agent / Blue Agent** pair runs a bounded adversarial debate: the Red Agent is prompted to find exploitable loopholes or unfavorable interpretations in a clause; the Blue Agent defends/patches. This is a genuinely useful robustness-testing pattern for contract review and is described further, alongside its novelty assessment, in `NOVELTY.md`.

## Tool interface

Every tool is a typed, JSON-schema-validated function — agents cannot execute arbitrary code or make unbounded network calls (`ARCHITECTURE.md` prompt-injection defense). Structured tool calls are enforced at the decoding layer via grammar-constrained generation (xgrammar / Outlines — `MODEL_STACK.md`), so a malformed tool call is impossible, not merely caught. Agents still call the backing services as plain Python functions; the Phase 7 planner chooses *agents* (from `app/agents/registry.py`), not arbitrary tools — the formal typed-tool layer is still ahead. Representative tools:

| Tool | Signature (conceptual) | Backing service |
|---|---|---|
| `kg_query(cypher_template, params)` | Constrained to a set of pre-approved query templates, not free Cypher | Knowledge Graph Service |
| `vector_search(query, corpus, k)` | Dense/sparse hybrid search | RAG Service |
| `statute_lookup(jurisdiction, topic)` | Cited statute/regulation retrieval | RAG Service |
| `date_math(expression, reference_date)` | Deterministic date/deadline arithmetic (no LLM — plain code) | Utility function |
| `clause_diff(clause_a, clause_b)` | Structured word- and clause-level diff | Utility function |
| `request_human_approval(payload, reason)` | Blocks the workflow pending human sign-off | Frontend approval queue |

## Verification loop (hallucination mitigation)

Every agent output that will reach a user passes through the Verifier before release:

1. **Citation check** — every factual claim must reference a retrieved chunk or KG fact; unreferenced claims are rejected or flagged.
2. **NLI faithfulness check** — a **local, self-hosted entailment model** (DeBERTa/ModernBERT NLI head, Class A — `MODEL_STACK.md`) checks that the claim is actually entailed by its cited source, not just topically related. This is a safety gate, so it must be deterministic and run inside the perimeter — it is never a generation call and never a commercial API. **Shipped in Phase 6** (`app/services/model_router/providers/nli_local.py`, `verify_nli` task, in-process DeBERTa-v3-MNLI): `app/agents/verifier.py` splits the summary into claim sentences and labels each against the retrieved sources; a `contradiction` or unsupported claim fails the check and is listed in `unsupported_claims`. The Phase 4 lexical-overlap heuristic remains only as the labelled fallback (`faithfulness_method="lexical_fallback"`) when the head isn't installed.
3. **KG consistency check** — claims about obligations/dates are cross-checked against the structured KG representation of the same document, catching a category of error pure text generation is prone to (e.g., misstating a deadline that's already been extracted with higher precision elsewhere).
4. **Confidence-gated human review** — anything failing 1-3, or falling below a calibrated confidence threshold, or touching a `Privileged`-tier document, sets `needs_human_review`, which is a strict improvement over V1's pattern of returning an LLM's output as-is regardless of confidence. **Shipped in Phase 7**: this outcome used to be computed and returned in the analyze() HTTP response but never persisted, so nothing could actually list flagged runs; a `CaseAnalysis` table now stores it and `GET/POST /api/review-queue` (+ a `/review` page in `frontend-v2`) is the real human review queue, not just a documented intention.

## Memory system

Four memory tiers, all backed by the Memory Service (`BACKEND.md`):

| Tier | Scope | Storage | Example |
|---|---|---|---|
| **Short-term (session)** | Current analysis session | Redis, TTL-bound | The last N chat turns, currently-open document's clause state |
| **Episodic** | Per-document, across sessions | Postgres (structured) + the vector store (embedded summaries) | "Last time this document was analyzed, these 3 risks were flagged and dismissed by the user" |
| **Semantic (long-term)** | Per-org, cross-document | Vector store + Knowledge Graph | Facts and patterns the org has established as reliably true for their context (e.g., "this org's leases are always California-governed") |
| **Procedural** | Per-org, learned behavior | A trained preference/policy representation (`DEEP_LEARNING.md`, `NOVELTY.md` #4) | "This org typically negotiates indemnification caps down to 12 months; suggest that stance by default" |

**Consolidation**: a scheduled background worker (`BACKEND.md`) summarizes short-term/episodic memory into semantic memory, with an explicit **privacy-tier gate** — content from `Privileged`-tier documents is never promoted into cross-document semantic memory without explicit org opt-in, since semantic memory is, by definition, information that could surface in a *different* document's analysis.

**Retrieval-augmented recall**: agents query memory the same way they query the RAG corpus (a memory hit is just another retrieval source with its own citation type: "from your prior session," "from your org's negotiation history").

## Auditability

Every agent step — input, tool calls, output, verification result, and any human override — is persisted to `agent_traces` (`ARCHITECTURE.md`) and rendered in the frontend's Agent Trace Viewer (`FRONTEND.md`). This is a hard requirement, not a nice-to-have: a legal-domain AI system that cannot explain *why* it flagged (or didn't flag) something is not defensible to the professionals who will ultimately rely on it, and it is the direct fix for V1's complete absence of logging beyond ad hoc `print()` statements.
