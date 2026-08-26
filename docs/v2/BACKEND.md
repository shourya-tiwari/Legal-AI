# Backend Architecture

V1's backend is one FastAPI app with six routers, each calling one service function, each making one synchronous call to a single Gemini client. That pattern (thin route → service function → centralized model client) is worth keeping as a *discipline*, but the "one process, one call, no queue, no persistence" shape does not extend to multi-agent workflows, long documents, or concurrent users. V2 decomposes the backend into services connected by both synchronous APIs and an event bus, with long-running work moved off the request/response path entirely.

## Service decomposition

| Service | Exposes | Talks to |
|---|---|---|
| **API Gateway** (FastAPI) | Public REST API, WebSocket endpoints, OpenAPI schema | Auth Service, Orchestration Service, Ingestion Service, Postgres |
| **Auth Service** | Internal auth/session validation | Postgres, Redis |
| **Ingestion Service** | `POST /documents` (internal) | CV Pipeline, NLP Pipeline, MinIO, Redpanda (emits `document.ingested`) |
| **Agent Orchestration Service** | Internal workflow trigger API | Temporal, Model Router, RAG Service, KG Service, Memory Service |
| **RAG Service** | Internal retrieval API | Qdrant, Memgraph (for GraphRAG traversal), BM25 index |
| **Knowledge Graph Service** | Internal graph query/write API, limited GraphQL for the frontend's KG Explorer | Memgraph |
| **Memory Service** | Internal memory read/write API | Qdrant, Postgres, Redis |
| **Model Router** | Internal `generate()` / `embed()` / `rerank()` calls | vLLM-served open-weight models, commercial frontier APIs (opt-in tier) |
| **Notification/Webhook Service** | Outbound webhooks, in-app notifications | Redpanda (consumes job-completion events) |

## Communication patterns

- **Synchronous (REST/gRPC)** between the API Gateway and services for request/response calls that must complete within the HTTP lifecycle (auth checks, quick lookups, starting a workflow).
- **Asynchronous (Redpanda events)** for anything that fans out or doesn't need to block a client: `document.ingested` → triggers CV/NLP pipeline; `extraction.completed` → triggers KG write + triggers the Agent Orchestration Service; `agent.step.completed` → pushed to the session WebSocket for the frontend.
- **Durable workflows (Temporal)** for the actual multi-agent execution graphs (`AGENTS.md`). This is the direct fix for V1's biggest scalability gap: a route in V1 blocks an HTTP worker thread on a single Gemini call; in V2, starting an analysis returns immediately with a workflow ID, and the client subscribes to progress over WebSocket. A crashed worker resumes the workflow from its last completed step instead of losing the request.

## API versioning and migration

- `/api/v1/*` continues to serve V1's exact six endpoints and response shapes during the transition (`ARCHITECTURE.md`'s migration path), initially proxied to legacy logic, later re-implemented on top of V2 services while preserving the response contract.
- `/api/v2/*` introduces the session/document-first model: `POST /api/v2/documents` returns a `document_id`; all subsequent calls (`/analyze`, `/ask`, `/negotiate`) reference that ID instead of re-transmitting full text, closing the gap already identified in V1 (`UploadResponse.session_id` was defined but never wired up).
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

Per-org and per-API-key quotas enforced at the API Gateway (token-bucket in Redis), with separate budgets for open-weight-tier calls (cheap, generous default) and commercial frontier-tier calls (metered, org-configurable cap) — directly addressing V1's complete absence of abuse protection (`docs/v1/FEATURES.md`).

## Error handling and resilience

- Temporal workflows retry individual agent steps with backoff on transient model-provider failures, distinguishing (as V1's `genai_client.py` already started doing) between retryable errors (429/timeout) and terminal errors (404/bad config) — that classification logic is preserved and reused inside the Model Router.
- Circuit breakers around the commercial frontier tier so a provider outage degrades to the open-weight tier automatically for tasks where that's an acceptable fallback, rather than failing the whole request.
