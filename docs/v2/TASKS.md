# Tasks

Actionable, checkbox-level backlog for `ROADMAP.md`. Grouped by phase, then by architecture layer. This is a planning checklist, not a sprint-committed schedule — sizing and sequencing within a phase is left to the team executing it.

## Phase 0 — V1 Hardening (prerequisite)

- [ ] Complete all P0 items in `docs/v1/TASKS.md` (secrets rotation, CORS fix, malformed HTML, dead code, model-default consistency)
- [ ] Complete P1 testing/CI items in `docs/v1/TASKS.md` (pytest suite, GitHub Actions, structured logging, config centralization)

## Phase 1 — Foundation Re-platform

**Data layer**
- [ ] Stand up Postgres with the core schema sketch in `ARCHITECTURE.md` (organizations, users, documents, sessions, audit_log)
- [ ] Stand up Qdrant, Memgraph, Redis, MinIO, Redpanda (docker-compose for local dev, Helm charts for cloud)
- [ ] Migrate V1's `document_storage` in-memory dict usage to Postgres-backed document records

**Backend**
- [ ] Introduce API Gateway service boundary; move routing/auth concerns out of the monolithic `main.py` pattern
- [ ] Build Auth Service (users, orgs, roles, API keys, session tokens)
- [ ] Require authentication on every endpoint (close V1's open-access gap)
- [ ] Build the Model Router as a generalization of `genai_client.py`; route 100% of traffic to Gemini initially (no behavior change)
- [ ] Re-implement `/api/v1/*` endpoints on top of the new persistence/auth layer, preserving exact V1 response contracts

**Observability**
- [ ] Wire OpenTelemetry tracing into every new service
- [ ] Deploy Langfuse for LLM-call tracing
- [ ] Deploy Prometheus + Grafana dashboards (latency, error rate, cost)

**Developer workflow**
- [ ] Set up monorepo structure (`apps/frontend`, `services/*`, `packages/schemas`, `packages/prompts`, `infra/`)
- [ ] Terraform + Helm skeletons for dev/staging/prod environments
- [ ] `docker-compose` local-dev profile bringing up the full data layer + a small open-weight model

## Phase 2 — Core AI Pipeline Buildout

**Computer vision (`COMPUTER_VISION.md`)**
- [ ] Document quality triage (blur/skew/resolution scoring)
- [ ] Integrate LayoutLMv3 for layout analysis
- [ ] Integrate Donut for OCR-free scan understanding; wire confidence-gated commercial OCR fallback
- [ ] Integrate Table Transformer for table extraction
- [ ] Train/integrate signature & stamp detector (YOLOv8-family)
- [ ] Redaction-region detection

**NLP (`NLP.md`)**
- [ ] Clause/sentence segmentation using CV layout hints
- [ ] Defined-term extraction & resolution
- [ ] Cross-reference resolution
- [ ] Fine-tune NER model (InLegalBERT/LegalBERT base) for parties/dates/money/jurisdictions
- [ ] Integrate GLiNER for zero-shot entity types
- [ ] Integrate coreference resolution (fastcoref, with LLM fallback)
- [ ] Weak-supervise + distill the deontic modality tagger
- [ ] Temporal expression normalization
- [ ] Fine-tune clause/contract type classifier (eval against CUAD)
- [ ] Ambiguity/vagueness detection scoring
- [ ] Define and ship the canonical `ClauseObject` schema (`packages/schemas`)

**Model Router / AI stack (`AI_STACK.md`)**
- [ ] Deploy vLLM serving for at least one open-weight model (Llama 3.1 8B to start)
- [ ] Route plain-English rewrite task to open-weight Tier 1 model; A/B against Gemini baseline
- [ ] Route structure/timeline extraction to Qwen2.5-72B-Instruct; validate JSON-schema adherence rate
- [ ] Stand up eval harness: Ragas integration + CUAD/ContractNLI-based gold set
- [ ] Wire CI eval-gating for any prompt/model/config change

## Phase 3 — Knowledge Graph & GraphRAG

**Knowledge graph (`KNOWLEDGE_GRAPH.md`)**
- [ ] Deploy Memgraph; implement schema (node/edge types)
- [ ] Build entity resolution pipeline (embedding clustering + LLM-assisted disambiguation)
- [ ] Build relation extraction pipeline (classifier + LLM-assisted low-confidence fallback)
- [ ] Implement schema validation + deontic consistency checks on graph write
- [ ] Implement portfolio-linking on ingestion
- [ ] Implement bitemporal versioning (valid time / transaction time)
- [ ] Backfill: re-process existing documents into the graph

**RAG (`AI_STACK.md`)**
- [ ] Deploy BGE-M3 for dense embeddings; deploy bge-reranker-v2-m3
- [ ] Build BM25/SPLADE sparse index
- [ ] Implement GraphRAG traversal tool over Memgraph
- [ ] Implement reciprocal rank fusion across dense/sparse/graph retrievers
- [ ] Ingest and cite a real statute/regulation corpus (start with jurisdictions V1 already hinted at)
- [ ] Migrate Contextualizer feature to real hybrid RAG with citations; remove the hardcoded 28-string list
- [ ] Implement citation-grounded generation prompt contract + citation validator

## Phase 4 — Agentic Orchestration MVP

**Agents (`AGENTS.md`)**
- [ ] Deploy LangGraph + Temporal orchestration runtime
- [ ] Define the shared `CaseState` schema
- [ ] Implement Orchestrator/Planner agent
- [ ] Implement Extraction agent (wraps CV/NLP pipeline outputs)
- [ ] Implement Risk & Compliance agent
- [ ] Implement Clause Research agent (hybrid RAG)
- [ ] Implement Verifier/Critic agent (citation check + NLI faithfulness check + KG consistency check)
- [ ] Implement typed tool interfaces (KG query, vector search, statute lookup, date math, clause diff, human-approval request)
- [ ] Persist full agent trace to `agent_traces`

**Memory (`AGENTS.md`)**
- [ ] Implement Memory Service: session tier (Redis)
- [ ] Implement episodic tier (Postgres + Qdrant)
- [ ] Implement memory consolidation worker (session/episodic → semantic, with privacy-tier gating)

**Frontend (`FRONTEND.md`)**
- [ ] Scaffold Next.js + TypeScript app; generate API client from OpenAPI schema
- [ ] Build Workspace and Document Analyzer modules (V1 parity)
- [ ] Build Agent Trace Viewer (real-time via session WebSocket)
- [ ] Build human-in-the-loop review queue UI
- [ ] Feature-flag `/api/v2` usage per org for staged rollout

**Backend**
- [ ] Introduce `/api/v2/*` session/document-first endpoints
- [ ] Implement Notification/Webhook Service for async job completion

## Phase 5 — Portfolio Intelligence & Research Features

**Deep learning (`DEEP_LEARNING.md`)**
- [ ] Curate training data (org corpora with consent + CUAD/ContractNLI)
- [ ] Weak-supervision labeling pass (batch, offline frontier-model use)
- [ ] Human legal-expert review of weak labels
- [ ] Train Risk Scoring Model (LightGBM); integrate SHAP explainability
- [ ] Train/finalize Clause/Contract Type Classifier
- [ ] Train Document Sensitivity Classifier
- [ ] Set up MLflow model registry + DVC data versioning
- [ ] Wire eval-gated model promotion into CI/CD

**Portfolio agents (`AGENTS.md`, `KNOWLEDGE_GRAPH.md`)**
- [ ] Implement Cross-Document Consistency agent (rule-based/embedding-similarity baseline first)
- [ ] Implement Simulation agent (deterministic discrete-event baseline first)
- [ ] Implement Negotiation/Drafting agent with static, org-configured preferences (no learned playbook yet)
- [ ] Ship Negotiation Studio frontend module with Yjs-based collaborative editing
- [ ] Ship Risk Dashboard spider/radar chart (closes the V1 README promise gap)

**Research track (`NOVELTY.md`) — each item independently gated**
- [ ] Idea #1 (Deontic GAT conflict detection): literature/patent search → prototype → benchmark vs. rule-based baseline
- [ ] Idea #2 (Temporal obligation simulation): prototype auto-constructed simulation from extracted conditional logic → validate against manually-modeled scenarios
- [ ] Idea #3 (Legal-semantic fingerprinting): construct hard-negative training set → train contrastive model → benchmark contradiction-detection precision/recall vs. generic embeddings
- [ ] Idea #4 (Adaptive negotiation playbook): prototype counterfactual fingerprint-delta attribution → validate against a held-out redline history set
- [ ] Idea #5 (Deontic-structure-aware ablation): implement deontic-parse-based perturbation → compare attribution quality vs. token-level SHAP baseline (human evaluation of "meaningfulness")
- [ ] For any idea advancing past prototype: commission formal prior-art search via qualified patent counsel before further investment or disclosure

## Phase 6 — Scale, Memory Maturity & Enterprise Hardening

- [ ] Implement semantic memory tier (cross-document, per-org) with privacy-tier gating
- [ ] Implement procedural memory tier (Redline Acceptance Predictor productionized)
- [ ] Validate hybrid VPC deployment profile with a pilot customer
- [ ] Validate on-prem/air-gapped deployment profile with a pilot customer
- [ ] Begin SOC 2 Type II readiness program
- [ ] Implement GDPR data-subject export/delete workflows
- [ ] Full cost/latency review of Model Router tier allocation using a quarter of production data
- [ ] Publish `/api/v1` deprecation timeline

## Continuous / cross-cutting (all phases)

- [ ] Every prompt/model/config change passes the eval gate before merge (from Phase 2 onward)
- [ ] Every sensitive-tier code path change gets a security review before merge
- [ ] Model cards maintained for every trained model (`DEEP_LEARNING.md`)
- [ ] Quarterly drift-monitoring review of production eval scores against the gold benchmark
