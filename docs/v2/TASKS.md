# Tasks

Actionable, checkbox-level backlog for `ROADMAP.md`. Grouped by phase, then by architecture layer. A planning checklist, not a sprint-committed schedule.

**Status legend**: `[x]` done · `[~]` partially done (annotation says what) · `[ ]` not started. Phases 0-4 record what actually shipped (a pragmatic slice — see annotations and `LEARNING_LOG.md`). Phases 5-9 are the forward plan under the revised, self-hosted-first architecture.

**Roadmap renumbering**: the previous "Phase 7 — GPU Upgrade" is now **Phase 6**; the previous "Phase 5 — Portfolio Intelligence" is now **Phase 8**; the previous "Phase 6 — Scale/Hardening" is now **Phase 9**. New **Phase 5** (Provider Abstraction Hardening) and **Phase 7** (Deployment Profiles) are inserted. See `ROADMAP.md`'s mapping table.

---

## Phase 0 — V1 Hardening (prerequisite) — ✅ Complete

- [x] Complete all P0 items in `docs/v1/TASKS.md` (secrets rotation, CORS fix, malformed HTML, dead code, model-default consistency)
- [x] Complete P1 testing/CI items in `docs/v1/TASKS.md` (pytest suite, GitHub Actions, structured logging, config centralization)

## Phase 1 — Foundation Re-platform — ✅ Complete (pragmatic slice)

**Data layer**
- [x] Stand up Postgres with the core schema sketch (`organizations`, `api_keys`, `documents`, `audit_log`; `users`/`sessions` deferred)
- [~] Stand up the polyglot data layer — **Postgres + Redis only**; Qdrant/Memgraph/Redpanda/MinIO deferred to the phases that need them (Memgraph landed in Phase 3)
- [x] Migrate V1's `document_storage` in-memory dict to Postgres-backed document records

**Backend**
- [~] Introduce API Gateway service boundary — not done; still one FastAPI process, cross-cutting concerns centralized via `app/guard.py` (the right amount of separation before a real service split is justified)
- [x] Build Auth Service — **scoped down**: org-scoped API keys only (`app/auth.py`); no per-user login/roles/session tokens (no login UI yet)
- [x] Require authentication on every endpoint — `app/guard.py`'s `api_guard`; **default OFF** (`AUTH_REQUIRED=false`) so the live public frontend keeps working
- [x] Build the Model Router as a generalization of `genai_client.py` — `app/services/model_router.py`. **Re-scoped**: this is the provider-agnostic seam (`AI_STACK.md`), currently with one provider (Gemini). Phase 5 makes it real.
- [~] Re-implement `/api/v1/*` endpoints on the new persistence/auth layer — persistence/auth is live under the existing unversioned `/api/*`; the `/api/v1/*` prefix itself not introduced (nothing needs versioning against yet)

**Observability** — [ ] not started; deferred (structured `logging` from Phase 0 only). OpenTelemetry / Langfuse / Prometheus / Grafana → Phase 5+.

**Developer workflow**
- [ ] Monorepo restructure (`apps/`, `services/*`, `packages/*`, `infra/`) — not done; still `backend/` + `frontend/`
- [ ] OpenTofu + Helm skeletons — not done (still deploying to Render)
- [x] `docker-compose` local-dev profile — **scoped down**: Postgres + Redis (+ Memgraph from Phase 3), not the full data layer or a served model

## Phase 2 — Structured Understanding: CPU Pipeline — ✅ Complete (CPU slice; GPU items → Phase 6)

**Computer vision (`COMPUTER_VISION.md`)**
- [x] Document quality triage — OpenCV Laplacian-variance blur + Hough-line skew (`app/services/cv/quality.py`), not a trained model
- [ ] Layout analysis (Docling / LayoutLMv3 / Qwen2.5-VL) → **Phase 6**
- [ ] OCR-free scan understanding (olmOCR / Qwen2.5-VL) + confidence-gated escalation → **Phase 6**
- [ ] Table extraction (Table Transformer / PP-Structure) → **Phase 6**
- [ ] Signature & stamp detector (YOLOv8-family) → **Phase 6** (also needs labelled data)
- [x] Redaction-region detection — geometric solid-black-rectangle contour heuristic (`app/services/cv/redaction.py`), not a trained model

**NLP (`NLP.md`)**
- [x] Clause/sentence segmentation — paragraph + sentence-boundary regex (`app/services/nlp/segmentation.py`); CV layout hints not used (LayoutLMv3 deferred)
- [x] Defined-term extraction & resolution — regex (`app/services/nlp/defined_terms.py`); doubles as party/entity ID
- [x] Cross-reference resolution — regex (`app/services/nlp/cross_references.py`)
- [ ] Fine-tuned NER (InLegalBERT/ModernBERT base) → **Phase 6**. CPU substitute shipped: parties via defined-term extraction, money/jurisdiction via regex (`app/services/nlp/entities.py`)
- [ ] GLiNER zero-shot entity types → **Phase 6**
- [ ] Real coreference (maverick-coref / fastcoref, LLM fallback) → **Phase 6**. Clearly-labelled heuristic stand-in shipped (`app/services/nlp/coref.py`)
- [x] Deontic modality tagger — **scoped down**: modal-verb regex Tier-0, eval-gated (100% gold-set recall), optional LLM escalation (`app/services/nlp/deontic.py`). The weak-supervise-then-distill *training pipeline* → Phase 6/8
- [x] Temporal expression normalization — `dateparser` for absolute dates; durations left unresolved deliberately (`app/services/nlp/temporal.py`)
- [ ] Fine-tuned clause/contract-type classifier + real CUAD eval → **Phase 6**. CPU substitute shipped: keyword-taxonomy rule base + optional LLM escalation (`app/services/nlp/clause_classifier.py`), eval-gated against a hand-curated gold set
- [x] Ambiguity/vagueness detection — extends V1's vague-term list (`app/services/nlp/ambiguity.py`)
- [x] Canonical `ClauseObject` schema — `app/services/nlp/schema.py` (not a `packages/schemas` package yet)

**Model Router / AI stack (`AI_STACK.md`)**
- [ ] Deploy vLLM serving an open-weight model → **Phase 6**
- [ ] Route rewrite / extraction tasks to self-hosted models → **Phase 6**
- [x] Stand up eval harness — **scoped down**: lightweight custom harness (`app/eval/run_eval.py`) against a 15-example gold set (`app/eval/gold_set.py`); Ragas/Inspect AI/CUAD integration → Phase 5/6
- [x] CI eval-gating for prompt/model/config changes — `tests/test_eval_gate.py` fails the suite on clause-type-accuracy or deontic-recall regression; full provider/policy-aware gating → Phase 5

## Phase 3 — Knowledge Graph & Hybrid RAG — ✅ Complete (pragmatic slice)

**Knowledge graph**
- [x] Deploy Memgraph; implement schema — `docker-compose.yml` + `app/services/kg/schema.py`. Nodes: `Document`/`Clause`/`DefinedTerm`/`CrossReferenceTarget`; edges: `PART_OF`/`DEFINES`/`USES_TERM`/`REFERENCES`/`SAME_AS`. Narrower than the full vision (no `Obligation`/`Statute`/`Jurisdiction` nodes yet) — scoped to what Phase 2's output supports
- [x] Entity resolution pipeline — **scoped down**: `difflib.SequenceMatcher` context-similarity (`should_link_terms` in `builder.py`), not embedding clustering + LLM disambiguation
- [x] Relation extraction pipeline — **scoped down**: derived directly from Phase 2's `ClauseObject` fields, not a separate classifier
- [~] Schema validation + deontic consistency checks — `find_potential_conflicts` flags candidate cross-document obligation/prohibition pairs sharing a term; explicitly "candidate for review", not confirmed (no actor/action resolution yet)
- [x] Portfolio-linking on ingestion — `link_portfolio_terms` in `builder.py`, `POST /api/kg/ingest`
- [ ] Bitemporal versioning (valid time / transaction time) — not done → **Phase 8** (needed for simulation)
- [x] Backfill existing documents into the graph — `POST /api/kg/ingest` is idempotent (MERGE throughout), doubles as backfill

**RAG**
- [ ] Deploy self-hosted embeddings + reranker → **Phase 5** (embeddings, CPU-feasible) / **Phase 6** (GPU-served). Dense retrieval today uses Gemini's embedding API. **Bug fixed during this phase**: `text-embedding-004` was silently 404ing; updated to `gemini-embedding-001`
- [x] Sparse index — **BM25 only** (`app/services/rag/bm25.py`); SPLADE (learned sparse) → Phase 6. BM25 is a legitimate permanent choice, not a placeholder
- [x] GraphRAG traversal tool over Memgraph — `find_clauses_using_term`/`find_potential_conflicts` in `app/services/kg/queries.py`; exposed via `/api/kg/query`, `/api/kg/conflicts`
- [~] RRF fusion across dense/sparse/graph — **dense + sparse only** (`app/services/rag/hybrid.py`, k=60); graph fusion → **Phase 5**
- [x] Ingest & cite a real statute/regulation corpus — **modest and judicious**: `app/services/rag/corpus.py` with a `citation` field populated only where confidently verifiable (Cal. Civ. Code § 1950.5, FLSA § 207, GDPR, CCPA); most entries `citation=None` (general principles) rather than inventing citations
- [x] Migrate Contextualizer to hybrid RAG with citations; remove the hardcoded 28-string list — `explainer.py` now calls `hybrid_search`
- [x] Citation-grounded generation prompt + citation validator — `templates.py` asks for `[N]` citations; `citation_validator.py` flags fabricated citation numbers (does NOT verify entailment — that's the NLI head, Phase 6)

## Phase 4 — Agentic Orchestration MVP — ✅ Complete (backend MVP)

**Agents (`AGENTS.md`)**
- [~] Deploy LangGraph + durable-execution runtime — **LangGraph done** (`app/agents/graph.py`); **durable engine not done**, runs synchronously in-request → **Phase 7**
- [x] Define the shared `CaseState` schema — `app/agents/state.py`, scoped to what the fixed pipeline needs (no `memory_refs`/`sensitivity_tier` yet)
- [ ] Orchestrator/Planner agent — **not implemented as a dynamic agent**; the fixed sequence stands in → **Phase 7**
- [x] Extraction agent — `app/agents/extraction.py`, wraps Phase 2's `build_clause_objects`
- [x] Risk & Compliance agent — `app/agents/risk_compliance.py`: keyword flags (`risk_radar/rules.py`) + KG candidate-conflict lookup. AI risk pass not invoked here (Tier-0 keyword sweep only)
- [x] Clause Research agent — `app/agents/research.py`; only runs on already-flagged clauses
- [~] Verifier/Critic agent — citation check (real, reuses `citation_validator.py`) + KG consistency check (real — a KG conflict forces `needs_human_review`) ship now; **NLI faithfulness check is a lexical-overlap stand-in** (`_lexical_overlap_faithfulness`), honestly labelled → real cross-encoder **Phase 6**
- [ ] Typed tool interfaces (KG query, vector search, statute lookup, date math, clause diff, human-approval) — **not built as a formal typed-tool-calling layer**; agents call services as plain Python functions → **Phase 7** (when a real planner needs to choose tools)
- [x] Persist full agent trace to `agent_traces` — new table in `db_models.py`; one row per step, verified live against Postgres

**Memory (`AGENTS.md`)** → all **Phase 7**
- [ ] Memory Service: session tier (Redis)
- [ ] Episodic tier (Postgres + vector store)
- [ ] Memory consolidation worker (session/episodic → semantic, privacy-tier gated)

**Frontend (`FRONTEND.md`)** → all **Phase 7**
- [ ] Scaffold Next.js + TypeScript; generate API client from OpenAPI
- [ ] Workspace + Document Analyzer modules (V1 parity)
- [ ] Agent Trace Viewer (real-time via session WebSocket)
- [ ] Human-in-the-loop review queue UI
- [ ] Feature-flag `/api/v2` usage per org

**Backend** → **Phase 7**
- [ ] `/api/v2/*` session/document-first endpoints
- [ ] Notification/Webhook Service for async job completion

---

## Phase 5 — Provider Abstraction Hardening — 🟡 In progress (core code slice shipped)

**Scope note**: the code core of this phase shipped — the provider interface, packaging split, policy engine, import-linter contract, and removal of the Gemini embedding dependency, all verified by running the full test suite in a fresh venv with **no `google-genai` installed** (101 pass + 1 skip). The infra pieces (a real TEI/Ollama deployment, the observability stack, Inspect AI) are the honest deferrals — they need services stood up, not code written. See `LEARNING_LOG.md` entry #18.

**Model Router → the real provider interface (`AI_STACK.md`)**
- [x] Define the `ModelProvider` interface + provider-neutral request/response types — `app/services/model_router/{base,types}.py` (`generate`, `embed`, `rerank`, `describe`, `is_available`). `generate_structured`/`transcribe`/`synthesize` reserved in the design, not needed by any current feature
- [x] Split providers into an always-installed core (`local.py` hashing/lexical, `openai_compat.py`) and an optional external adapter (`gemini.py`); `requirements.txt` (core, **no `google-genai`**) / `requirements-external.txt` / `requirements-local.txt`
- [x] **import-linter contract** — `tests/test_provider_isolation.py` (AST scan, CI-gated, zero new deps) + `.importlinter` config; no provider SDK imported outside `app/services/model_router/providers/`
- [x] Declarative routing-policy engine — `app/policies/routing.yaml` + `app/services/model_router/policy.py`: `task × sensitivity × capability` → ordered candidate chain; Class-A/B-only chains; Class C appended only when `EXTERNAL_PROVIDERS_ENABLED` and the tier is in `class_c_allowed_tiers`; `STRICT_LOCAL_ONLY` hard-off switch. `emergency_class_c` per-org opt-in: **not built** (no multi-tenant policy layer yet)
- [x] Log `{task, sensitivity, provider, model, reason, candidates}` on every routing decision (`router.py`); a Class C route logs at WARNING. Join to `eval_runs`: **deferred** (no `eval_runs` table yet)
- [x] Re-express hosting as **Class A / B / C** in config, code, and the policy (retired "Tier 2")
- [x] Move Gemini behind the optional external package + a Class C policy rule; **verified the product runs with `google-genai` uninstalled** (fresh-venv full-suite run) — the phase's acceptance test

**Self-host everything that isn't a large LLM**
- [~] Self-hosted embeddings — the *interface + local default* shipped: `SentenceTransformerProvider` (Class B, optional `requirements-local.txt`) → `OpenAICompatProvider` embed role (TEI/Infinity endpoint) → `HashingEmbeddingProvider` (Class A, zero-dep, offline floor). **Deploying an actual TEI server with EmbeddingGemma/BGE-M3 is Phase 6** (GPU-served) or a follow-up; the code path is ready
- [x] **Removed the Gemini embedding dependency from the RAG path** — `contextualizer/rag.py` no longer hardcodes `gemini-embedding-001`; `embed_content()` routes via the policy (`embed_query`/`embed_corpus` tasks) to a self-hosted provider. This was the single most important deliverable
- [x] Self-hosted reranker + wired into RRF fusion — `rag/hybrid.py` now has a rerank step (`LexicalReranker` Class A default; `SentenceTransformerProvider` cross-encoder when installed), behind `RERANKER_ENABLED`
- [x] Fuse GraphRAG hits into hybrid retrieval — `rag/graph_retrieval.py` + `hybrid_search(..., graph_hits=...)`; wired into the Clause Research agent (`agents/research.py`), fail-soft when Memgraph is down. Contextualizer route wiring: follow-up (needs org context threaded to `explainer`)
- [ ] faster-whisper (ASR) / Kokoro-Piper (TTS) providers → **deferred**: no ASR/TTS feature exists in the product yet; premature to add the providers
- [~] Ollama-served small LLM as the local-dev default — `OpenAICompatProvider` + `LLM_BASE_URL`/`LLM_MODEL` settings ship; adding an `ollama` service to `docker-compose.yml` + a model pull is a follow-up (it downloads a multi-GB model on first `up`)

**Observability & eval** — [ ] all deferred (need services stood up, not code):
- [ ] OpenTelemetry / Langfuse / Arize Phoenix / Prometheus+Grafana
- [ ] Inspect AI backbone + promptfoo; self-hosted eval judge; the self-hosted-vs-external delta report
- [x] Extend the CI eval gate to cover provider/policy — partially: `test_model_router.py` + `test_provider_isolation.py` are CI-gated and fail on a policy/interface regression; the full `eval_runs`-joined gate is future work
- [x] Second CI job (`core-only-smoke`) installs `requirements.txt` alone and proves the product runs with no external SDK

**Exit criteria**: Router is provider-agnostic and passes the import-linter contract ✅; embeddings/rerank self-hosted by default (interface + local providers) ✅, ASR/TTS N/A; the only task routed to a commercial API by default is large-LLM generation ✅ (and only when `EXTERNAL_PROVIDERS_ENABLED`); the product runs end-to-end with no credentials and no `google-genai` ✅ (verified in a fresh venv). Remaining: stand up a real self-hosted embedding server and the observability stack.

## Phase 6 — Self-Hosted LLM Generation: the GPU unlock

**Model serving**
- [ ] Deploy vLLM on the GPU pool; evaluate SGLang for the agent prefix-cache workload
- [ ] Serve Qwen3-32B (AWQ/GPTQ 4-bit) as the default generation model; Qwen3-4B for the constrained profile
- [ ] Serve a reasoning model (DeepSeek-R1-Distill-32B / QwQ-32B) for flagged-hard tasks (multi-hop Q&A, portfolio risk)
- [ ] Serve Qwen2.5-VL-7B/32B for scanned-document understanding
- [ ] Move self-hosted embeddings/reranker to GPU-served (TEI on GPU) for latency
- [ ] Add multi-LoRA serving (vLLM / LoRAX) for per-task and per-org adapters

**Progressive task cutover — each A/B-gated against the Gemini baseline before becoming default**
- [ ] Plain-English rewrite → Qwen3-8B/32B
- [ ] Structure/timeline extraction → Qwen3-32B with grammar-constrained JSON (xgrammar)
- [ ] Q&A / chat → Qwen3-32B + RAG; reasoning model for multi-hop
- [ ] Risk analysis AI pass → Qwen3-32B
- [ ] Contextualizer advisory → Qwen3-32B + RAG
- [ ] Deontic / clause-classifier LLM escalation → self-hosted
- [ ] Remove Gemini from the default routing policy once all of the above pass; keep it only as opt-in Class C for `Public`/`Internal`

**GPU-dependent CV / NLP models**
- [ ] Replace OpenCV quality triage + "tables are text blocks" with Docling + Qwen2.5-VL + Table Transformer / PP-Structure; keep Tesseract + quality-triage as the clean-PDF fast path
- [ ] Add olmOCR / Qwen2.5-VL as the confidence-gated OCR escalation (replaces the planned commercial Document AI fallback as the default; commercial OCR stays an optional Class C plugin only)
- [ ] Fine-tune InLegalBERT/ModernBERT NER (via Unsloth); compare against the regex+defined-term baseline before making it primary
- [ ] Integrate GLiNER (zero-shot entity types) and maverick-coref (real coreference, replacing `app/services/nlp/coref.py`)
- [ ] Run the weak-supervision-then-distill pipeline for the deontic tagger — **teacher is a self-hosted Qwen3-235B/32B via distilabel, not a frontier API**; student is a fast CPU tagger
- [ ] Fine-tune the clause/contract-type classifier; eval against real CUAD; keep the rule base as a Tier-0 pre-filter

**Verifier**
- [ ] Ship the real NLI faithfulness head (local DeBERTa/ModernBERT entailment model, Class A), replacing Phase 4's lexical-overlap stand-in (`app/agents/verifier.py`)

**Eval**
- [ ] Integrate LegalBench / CUAD / ContractNLI / MAUD into the Inspect AI suite; track the self-hosted default continuously
- [ ] Enforce: a self-hosted model becomes default for a task only after meeting or beating the Gemini baseline on that task's eval
- [ ] Explicit re-evaluation step per upgraded component (fine-tuned model vs. the rule-based baseline it replaces) — prove the upgrade, don't assume it

**Exit criteria**: every core task served by a self-hosted model at or above the previous Gemini baseline; Gemini removed from the default routing policy; the product runs end-to-end with no external API call.

## Phase 7 — Deployment Profiles: On-Prem & Air-Gapped

**Build & supply chain**
- [ ] Produce on-prem/air-gapped builds with `legalai-providers-external` excluded; enforce with an SBOM allowlist that fails the build on any commercial-provider SDK (or outbound-calling transitive dependency)
- [ ] Zarf packaging of the full application (images + charts + manifests + model weights + seed corpus) into one installable artifact
- [ ] Model weights as signed KitOps ModelKit OCI artifacts via Harbor; no `pip` / `huggingface-cli` on the target
- [ ] OpenTofu for all IaC (migrate off any Terraform); Helm + Kustomize overlays per profile; k3s single-node target
- [ ] cosign signing + Syft SBOM + Trivy/Grype scanning for every image and model artifact
- [ ] Egress proxy / network policy for the hybrid profile: deny all outbound except configured provider endpoints; log every byte (`audit_log.egress_target`, payload hash, task, policy version, opt-in reference)

**Collapsed data layer**
- [ ] Support pgvector + pgvectorscale as a Qdrant substitute (Helm-value-selected)
- [ ] Support Apache AGE or KùzuDB as a Memgraph substitute
- [ ] Support LanceDB embedded + filesystem object storage + Postgres-backed event queue for the laptop profile
- [ ] Verify the same application code runs against either data-layer profile

**Durable execution & Memory Service**
- [ ] Introduce a durable-execution engine — DBOS (library, Postgres-backed) default; Hatchet mid-scale; Temporal only for large multi-tenant cloud. Keep `app/agents/graph.py` engine-agnostic
- [ ] Memory Service: session tier (Redis), episodic tier (Postgres + vector store), consolidation worker with the privacy-tier gate
- [ ] Dynamic Orchestrator/Planner agent, replacing the fixed Phase 4 sequence
- [ ] Formalize typed tool interfaces (JSON-schema-validated) now that a planner chooses tools

**Frontend SPA**
- [ ] Scaffold Next.js + TypeScript; generate the API client from the OpenAPI schema
- [ ] Workspace + Document Analyzer (V1 parity); Agent Trace Viewer (real-time via session WebSocket); human-in-the-loop review queue UI
- [ ] Provider & Model admin: which models serve which tasks, the eval scores behind the policy, the delta report, per-task/tier Class C toggles
- [ ] Model status panel: self-hosted model health / queue depth / latency
- [ ] Fully self-hosted frontend assets (fonts, Plausible analytics); strict CSP; sandboxed PDF.js preview
- [ ] Sensitivity-aware rendering: `Privileged` documents show a persistent indicator and disable any control that would trigger a Class C call
- [ ] Introduce `/api/v2/*` session/document-first endpoints; feature-flag per org
- [ ] Notification/Webhook Service for async job completion

**Exit criteria**: an air-gapped install (Zarf → disconnected k3s → working product, verified offline) validated with a pilot; a collapsed-data-layer on-prem install validated; the SPA at V1 parity plus the Agent Trace Viewer.

## Phase 8 — Portfolio Intelligence & Research Features

**In-house models (`DEEP_LEARNING.md`)**
- [ ] Curate training data (org corpora with consent + CUAD/ContractNLI)
- [ ] Weak-supervision labelling pass via distilabel with a **self-hosted teacher** (batch/offline)
- [ ] Legal-expert review of weak labels in Argilla
- [ ] Train the Risk Scoring Model (LightGBM, CPU — blocked on labelled data, not hardware); integrate SHAP
- [ ] Finalize the fine-tuned clause/contract-type classifier and NER head; eval-gate promotion
- [ ] Document Sensitivity Classifier — classical (TF-IDF + linear) first; fine-tune a transformer only if that underperforms
- [ ] Legal Clause Embedding Model — contrastive fine-tune (`NOVELTY.md` #3) with hard-negative mining (GPU training step uses Phase 6 infra)
- [ ] Redline Acceptance Predictor — per-org, DPO/classifier over redline history (opt-in, org-scoped, never pooled)
- [ ] MLflow registry + DVC data versioning; eval-gated model promotion in CI/CD
- [ ] Model cards for every trained model (intended use, data provenance, jurisdictions/contract types covered, eval scores, limitations)

**Portfolio agents (`AGENTS.md`, `KNOWLEDGE_GRAPH.md`)**
- [ ] Bitemporal graph versioning (valid time / transaction time) — the Phase 3 gap
- [ ] Cross-Document Consistency agent (embedding-similarity baseline → learned `NOVELTY.md` #1)
- [ ] Simulation agent (deterministic discrete-event baseline → Monte-Carlo `NOVELTY.md` #2)
- [ ] Negotiation/Drafting agent — static org-configured preferences first; learned playbook (`NOVELTY.md` #4) once redline history exists
- [ ] Negotiation Studio frontend (Yjs collaborative editing)
- [ ] Risk Dashboard spider/radar chart (closes the V1 README promise)
- [ ] Knowledge Graph Explorer frontend (Cytoscape.js)

**Research track (`NOVELTY.md`) — each item independently gated**
- [ ] Idea #1 (Deontic GAT conflict detection): literature/patent search + architecture design (CPU); GNN training uses Phase 6 GPU
- [ ] Idea #2 (Temporal obligation simulation): CPU-only — prototype auto-constructed simulation, validate against manually-modelled scenarios
- [ ] Idea #3 (Legal-semantic fingerprinting): hard-negative pair construction (CPU); contrastive training uses Phase 6 GPU
- [ ] Idea #4 (Adaptive negotiation playbook): counterfactual fingerprint-delta attribution (CPU); Redline Acceptance Predictor — classical model first
- [ ] Idea #5 (Deontic-structure-aware ablation): CPU-only — runs against the existing LightGBM risk model
- [ ] For any idea advancing past prototype: commission a formal prior-art search via qualified patent counsel before further investment or disclosure
- [ ] For any idea that validates: target a benchmark contribution and/or a workshop paper (NLLP @ *ACL, JURIX, ICAIL) — see `NOVELTY.md`'s publication strategy

**Exit criteria**: portfolio-level contradiction detection and obligation simulation live (established-technique first, novel-mechanism after its gate); ≥1 in-house model in production at/above its baseline; ≥1 `NOVELTY.md` idea with a validated benchmarked prototype.

## Phase 9 — Scale, Memory Maturity & Enterprise Hardening

- [ ] Semantic memory tier (cross-document, per-org) with privacy-tier gating
- [ ] Procedural memory tier (Redline Acceptance Predictor productionized, per-org isolation)
- [ ] Multi-tenant cloud scale: Qdrant sharding, per-org graph partitioning, GPU autoscale on queue depth, Postgres read replicas
- [ ] Adopt Temporal for the cloud profile if DBOS/Hatchet hit a ceiling
- [ ] Validate hybrid VPC deployment with a pilot customer
- [ ] Validate on-prem and air-gapped deployments with pilot customers (one each)
- [ ] SOC 2 Type II readiness program
- [ ] GDPR data-subject export/delete workflows
- [ ] Full cost/latency review of the routing policy using a quarter of production data; right-size the model fleet; tune quantization / speculative decoding / batching
- [ ] Publish the `/api/v1` deprecation timeline once `/api/v2` has full parity

## Continuous / cross-cutting (all phases)

- [ ] Every prompt/model/provider/routing-policy change passes the eval gate before merge (from Phase 2; policy/provider from Phase 5)
- [ ] The import-linter contract stays green: no vendor SDK outside the provider package (from Phase 5)
- [ ] Every sensitive-tier code-path change gets a security review, with extra scrutiny on Class C egress
- [ ] Model cards maintained for every trained model (`DEEP_LEARNING.md`)
- [ ] Quarterly drift-monitoring review of production eval scores against the gold benchmark
- [ ] Keep flagging, per item, *why* something is deferred: "GPU", "no training data yet", "not needed yet", "separate scope" are four different reasons with four different follow-ups
