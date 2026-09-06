# Backend Architecture

V1's backend is one FastAPI app with six routers, each calling one service function, each making one synchronous call to a single Gemini client. That pattern (thin route → service function → centralized model client) is worth keeping as a *discipline*, but the "one process, one call, no queue, no persistence" shape does not extend to multi-agent workflows, long documents, or concurrent users. V2 decomposes the backend into services connected by both synchronous APIs and an event bus, with long-running work moved off the request/response path entirely.

## Service decomposition

| Service | Exposes | Talks to |
|---|---|---|
| **API Gateway** (FastAPI) | Public REST API, WebSocket endpoints, OpenAPI schema | Auth Service, Orchestration Service, Ingestion Service, Postgres |
| **Auth Service** | Internal auth/session validation | Postgres, Redis |
| **Ingestion Service** | `POST /documents` (internal) | CV Pipeline, NLP Pipeline, MinIO, Redpanda (emits `document.ingested`) |
| **Agent Orchestration Service** | Internal workflow trigger API | Durable-execution engine (DBOS / Hatchet / Temporal — pluggable), Model Router, RAG Service, KG Service, Memory Service |
| **RAG Service** | Internal retrieval API | Vector store (Qdrant / pgvector / LanceDB), graph store (for GraphRAG traversal), BM25 index, self-hosted embed/rerank via the Model Router |
| **Knowledge Graph Service** | Internal graph query/write API, limited GraphQL for the frontend's KG Explorer | Graph store (Memgraph / Neo4j CE / Apache AGE / KùzuDB) |
| **Memory Service** | Internal memory read/write API | Vector store, Postgres, Redis |
| **Model Router** | Internal `generate()` / `embed()` / `rerank()` / `entail()` / `extract_entities()` calls (shipped), `generate_structured()` / `transcribe()` / `synthesize()` reserved, resolved by a declarative policy | `legalai-providers-core` (self-hosted: OpenAI-compat/Ollama/vLLM, TEI, in-process transformers NLI + GLiNER) — always; `legalai-providers-external` (Gemini, …) — optional plugin, absent in on-prem/air-gapped builds |
| **Notification/Webhook Service** | Outbound webhooks, in-app notifications | Redpanda (consumes job-completion events) |

## Provider adapter layer (the Model Router's internals)

`AI_STACK.md` owns the design; the backend-relevant facts:

- Every model backend implements one `ModelProvider` interface. Adapters live only in `services/model_router/providers/`. An **import-linter CI contract** fails the build if any other module imports a model-provider SDK (`google.genai`, `openai`, `anthropic`, `vllm`, …). This is the mechanical guarantee that no service is vendor-coupled.
- Adapters are packaged in two installs: `legalai-providers-core` (self-hosted, always present) and `legalai-providers-external` (commercial, optional, excluded from on-prem/air-gapped builds and verified absent by the SBOM allowlist — `ARCHITECTURE.md`).
- A declarative routing policy (`packages/policies/routing.yaml`, versioned + eval-gated) maps `task × sensitivity × required-capabilities × budget` to a `(provider, model)` binding. The Router is the only place that reads it.
- Every call logs `{task, sensitivity, provider, model, reason, candidates}` — **shipped**: `router.py` at INFO (Class C at WARNING) and, fail-soft via `model_router/telemetry.py`, one row to the `model_calls` table + an OTel span. `eval_runs` (from `app/eval/`) is the join partner for regression attribution.
- **Shipped capabilities beyond generate/embed/rerank** (Phase 6): `entail` — a Class-A local NLI head (`local-nli`, `verify_nli` task) for the Verifier's faithfulness gate; `ner` — GLiNER zero-shot entity extraction (`local-ner`). Both local-only chains (no Class C), both optional (`requirements-local.txt`), both fail-soft to a rule/lexical path.
- **Escalation**: a generate task carries an `escalate_to` in the policy; `generate_content(..., hard=True)` prepends it (a bigger *self-hosted* model, `local-llm-large`), never a Class C target.

## Communication patterns

- **Synchronous (REST/gRPC)** between the API Gateway and services for request/response calls that must complete within the HTTP lifecycle (auth checks, quick lookups, starting a workflow).
- **Asynchronous (Redpanda events)** for anything that fans out or doesn't need to block a client: `document.ingested` → triggers CV/NLP pipeline; `extraction.completed` → triggers KG write + triggers the Agent Orchestration Service; `agent.step.completed` → pushed to the session WebSocket for the frontend.
- **Durable workflows** for the actual multi-agent execution graphs (`AGENTS.md`). This is the direct fix for V1's biggest scalability gap: a route in V1 blocks an HTTP worker thread on a single Gemini call; in V2, starting an analysis returns immediately with a workflow ID, and the client subscribes to progress over WebSocket. A crashed worker resumes the workflow from its last completed step instead of losing the request. The engine is **pluggable** (`MODEL_STACK.md`): **DBOS** (library, Postgres-backed, no extra service) is the default for on-prem/air-gapped and mid-scale; **Hatchet** for larger self-hosted; **Temporal** only where the multi-tenant cloud profile justifies operating a dedicated cluster. Phase 4 runs the graph synchronously in-request (acceptable at seconds-long runtimes); the durable engine lands in Phase 7.

## API versioning and migration

- `/api/v1/*` continues to serve V1's exact six endpoints and response shapes during the transition (`ARCHITECTURE.md`'s migration path), initially proxied to legacy logic, later re-implemented on top of V2 services while preserving the response contract.
- `/api/v2/*` introduces the document-first model: subsequent calls reference a `document_id` instead of re-transmitting full text. **Shipped (Phase 7, `app/routes/v2.py`):** `GET /api/v2/documents/{id}`, `GET/PUT /api/v2/documents/{id}/sensitivity`, and `POST /api/v2/documents/{id}/{analyze,rewrite,map,ask,risk-scan,contextualize,consistency,simulate}` — each loads the org-scoped `Document` (from `/api/upload`) and calls the same service as its V1 counterpart (or, for `consistency`/`simulate`, the Phase 8 baseline services), with an optional `block_id` to target one extracted block. The V1 endpoints are unchanged. Also shipped: `GET/POST /api/review-queue` (`app/routes/review.py`, org-wide not document-scoped) and `GET /api/models/eval-runs` (`app/routes/models.py`). Session objects, a `/negotiate` endpoint, per-org feature-flagging, and the OpenAPI-generated client (beyond `frontend-v2`'s own `npm run codegen`) are still ahead.
- Both API surfaces share the same underlying Pydantic schema package (`packages/schemas`) so V1-compatible responses are provably a projection of V2's richer internal models, not a hand-maintained parallel implementation.

## Data contracts

- **OpenAPI-first**: schemas are defined once in `packages/schemas` (Pydantic v2), and both the OpenAPI spec and the generated TypeScript client (`FRONTEND.md`) derive from them — eliminating the class of bug V1 had where the frontend's endpoint map and request shapes were maintained by hand in `app.js` with no compile-time check against the backend.
- **Agent I/O contracts**: every agent tool (KG query, vector search, statute lookup, calculator) has a typed JSON-schema signature registered with the Model Router's function-calling layer (`AGENTS.md`), so a malformed tool call is a validation error, not a runtime crash deep in a prompt.

## Background workers

- **Embedding/indexing workers** (consuming `extraction.completed` events): generate clause embeddings, write to Qdrant, update the BM25 sparse index.
- **KG construction workers**: run entity resolution and relation extraction (`KNOWLEDGE_GRAPH.md`) and write to Memgraph.
- **Memory consolidation workers**: periodically summarize session memory into episodic/semantic memory (`AGENTS.md`).
- **Eval workers**: run the Ragas/CUAD-based eval suite against a sample of production traffic on a schedule, writing to `eval_runs` (`ARCHITECTURE.md`).

## Rate limiting and quotas

Per-org and per-API-key quotas enforced at the API Gateway (token-bucket in Redis), with separate budgets for **Class B self-hosted** calls (bounded by our own infrastructure — generous default) and **Class C external-provider** calls (metered, hard org-configurable cap, every call itemized in the audit log with the routing reason) — directly addressing V1's complete absence of abuse protection (`docs/v1/FEATURES.md`). In on-prem/air-gapped builds there is no Class C budget because there is no Class C provider.

## Error handling and resilience

- The durable-execution engine retries individual agent steps with backoff on transient model-provider failures, distinguishing (as V1's `genai_client.py` already started doing) between retryable errors (429/timeout) and terminal errors (404/bad config) — that classification logic is preserved and reused inside every provider adapter.
- Circuit breakers around **each provider**. A self-hosted (Class B) model-serving outage degrades to a smaller self-hosted model, then to a Class A approximation with a surfaced confidence warning — the `fallback_chain` is `[B, A]` and **never silently falls through to Class C**. Failing over to an external provider on a Class B outage requires a separate, explicit `emergency_class_c` opt-in per org, and even then only for `Public`/`Internal` documents.
