# Roadmap

Phased delivery plan from V1's current production state to a **fully self-hosted legal-AI platform**. Each phase leaves the system deployable — V1's endpoints keep serving throughout (`ARCHITECTURE.md`'s migration path), so this is an incremental cutover, not a rewrite-and-replace. Durations are rough sizing (in sprints, small dedicated team), not commitments.

## The through-line

Every phase moves inference *toward* the organization's own hardware and *away* from any external dependency:

```
V1:        100% Gemini, no fallback
Phase 1-4: Gemini for generation; local rules/classical-ML for structure
Phase 5:   Provider-agnostic Router; embeddings/rerank self-hosted (TEI); Ollama
           (Qwen3-8B) serving config'd; Gemini an optional plugin
Phase 6:   Self-hosted generation = Qwen3-8B/14B (one 16 GB card is the ceiling);   ← WE ARE HERE
           cut over per task where it beats the Gemini baseline, Gemini kept for the rest
Phase 7:   On-prem + air-gapped builds; commercial-provider package excludable entirely
Phase 8+:  Portfolio intelligence, in-house trained heads (CPU-served), research track
```

The old roadmap put "GPU Upgrade" *last*, as a quality top-up on a Gemini product. **That is inverted here** — self-hosting is the spine. But the "GPU unlock" is now **bounded**: the project has one RTX A4000 (16 GB), often borrowed, and no plan to buy or rent a bigger card. So Phase 6 targets **Qwen3-8B/14B**, and the domain quality comes from RAG + KG + fine-tuned heads, not model scale (which the design always argued anyway — `MODEL_STACK.md`).

## GPU requirement by phase

**Hardware reality: one RTX A4000 (16 GB), often borrowed; the owner's own machine is CPU-only (Core i5 + 4 GB integrated). No 24 GB+ card, owned or rented, is planned.** Nothing in the plan *requires* a GPU to run (Class-A fallbacks keep every path working); a GPU improves generation and trains the small heads.

| Phase | GPU on *our* side? | Notes |
|---|---|---|
| **0–5** | **No** | CPU rules / classical ML / hashing embeddings; generation via Gemini or a small served model. The `gpu` compose profile (Ollama Qwen3-8B + TEI) is configured; run it on the A4000 when available. |
| **6 — Self-hosted generation (16 GB ceiling)** | **The A4000 helps; not required** | Target = **Qwen3-8B** (+ 14B-AWQ escalation) via Ollama/vLLM, fits 16 GB alongside bge-m3 + bge-reranker + the NLI head. The A4000 also trains every small head in the plan (Legal-BERT / ModernBERT LoRA — minutes) which then serve on **CPU**. **Deferred to future scope**: Qwen3-32B / 235B, reasoning models, 7B VLM — all need 24 GB+. Cut over per-task: self-hosted where the gate says it beats Gemini, Gemini (tier-permitting) / human review otherwise. |
| **7 — On-prem / air-gapped deployment** | **No** | Packaging, collapsed data layer, durable execution, Memory Service, frontend SPA — all CPU/infra. A *customer* supplies their own GPU or accepts the 8-14 B / CPU small-model quality. |
| **8 — Portfolio intelligence & research** | **A4000 for one-off training; CPU for everything else** | CPU: Risk Scoring (LightGBM), Document Sensitivity (classical), Cross-Document Consistency + Simulation agents (similarity / discrete-event baselines), bitemporal graph, `NOVELTY.md` #2 / #5. A4000 (or a one-off cloud rental): the fine-tuned clause classifier, the Legal Clause Embedding contrastive fine-tune, `NOVELTY.md` #1 / #3 training — then served on CPU. |
| **9 — Scale & enterprise hardening** | **No** | SOC 2, GDPR workflows, cost/latency tuning, multi-tenant scale. |

## Phase mapping from the previous roadmap

| Previous phase | This roadmap |
|---|---|
| Phase 0 — V1 Hardening | Phase 0 (unchanged) |
| Phase 1 — Foundation Re-platform | Phase 1 (unchanged; Model Router re-scoped as the provider-agnostic seam) |
| Phase 2 — Core AI Pipeline Buildout | Phase 2 (unchanged) |
| Phase 3 — Knowledge Graph & GraphRAG | Phase 3 (unchanged) |
| Phase 4 — Agentic Orchestration MVP | Phase 4 (unchanged) |
| Phase 5 — Portfolio Intelligence & Research | **Phase 8** (moved later — it depends on self-hosted training infra) |
| Phase 6 — Scale, Memory, Enterprise Hardening | **Phase 9** |
| Phase 7 — GPU Upgrade | **Phase 6** (moved *earlier* and made the spine) |
| *(new)* | **Phase 5** — Provider Abstraction Hardening |
| *(new)* | **Phase 7** — Deployment Profiles: On-Prem & Air-Gapped |

Code docstrings and `LEARNING_LOG.md` entries that reference "Phase 7 (GPU Upgrade)" now correspond to **Phase 6** here. `LEARNING_LOG.md` is an append-only journal and is not rewritten; this table is the reconciliation.

---

## Phase 0 — V1 Hardening (prerequisite, ~2-4 sprints) — ✅ Complete

Complete the hardening scoped in `docs/v1/ROADMAP.md`/`TASKS.md` (tests, CORS fix, secrets hygiene, config correctness) before layering V2 on top.

**Exit criteria**: V1's P0/P1 tasks complete — CI running, CORS fixed, secrets rotated, config centralized. — **met.**

## Phase 1 — Foundation Re-platform (~4-6 sprints) — ✅ Complete (pragmatic slice)

Stand up the V2 data layer and service skeleton without changing user-facing behaviour. **Delivered**: Postgres + Redis (not the full 6-store polyglot stack — the rest deferred to when RAG/KG need them), org-scoped API-key auth default-off, **a Model Router pass-through wrapper** (`app/services/model_router.py`), and document persistence replacing the in-memory dict. **Not delivered**: OpenTelemetry/Langfuse/Prometheus, Kubernetes/OpenTofu/Helm, the monorepo restructure, an actual API Gateway service boundary — deliberately deferred.

**Re-scope note (this revision):** the Model Router shipped here is now understood as the **provider-agnostic seam** described in `AI_STACK.md`, not a "route everything to Gemini" shim. It currently has one provider (Gemini). Phase 5 turns it into the real thing. Nothing built here needs to be undone.

**Exit criteria**: V1 feature parity on the V2 data/service foundation, authenticated (off by default), observable via structured logging, zero in-memory-only state. — **met at reduced scope.**

## Phase 2 — Structured Understanding: CPU Pipeline (~6-10 sprints) — ✅ Complete (CPU slice; GPU items → Phase 6)

Build the pipelines that turn flat text into structured `Clause` objects. Re-planned mid-phase once hardware reality was checked — the dev machine has no discrete GPU, ruling out vLLM/VLMs/fine-tuning. Every stage was implemented as a genuine, tested, CPU-only equivalent; the GPU-dependent versions moved to Phase 6.

- **CV pipeline** (`COMPUTER_VISION.md`): OpenCV quality triage (blur/skew) and geometric redaction detection. Layout/table/signature analysis → Phase 6.
- **NLP pipeline** (`NLP.md`): segmentation, defined-term extraction (doubling as party/entity ID), cross-references, regex money/jurisdiction entities, rule-based deontic tagging with optional LLM escalation, `dateparser` temporal normalization, keyword-taxonomy clause classification, ambiguity detection, heuristic coref stand-in — all producing the canonical `ClauseObject`. Fine-tuned NER/classifier/deontic models and real coref → Phase 6.
- **Model Router**: no self-hosted model yet (needs Phase 5/6); generation still routes to Gemini.
- **Eval harness**: lightweight custom harness (not yet Ragas/Inspect AI) against a 15-example hand-curated gold set, wired as a CI gate.

**Exit criteria**: every uploaded document produces a structured `ClauseObject` graph, not just flat text — **met.** "At least one production task fully served by a self-hosted model" — **deferred to Phase 6.**

## Phase 3 — Knowledge Graph & Hybrid RAG (~6-8 sprints) — ✅ Complete (pragmatic slice)

Memgraph needs no GPU, so this phase's infrastructure is real. Scoped down: entity resolution via string similarity rather than embedding clustering; relation extraction derived from Phase 2's structured output rather than a separate model; dense embeddings via **Gemini's API** rather than self-hosted (self-hosting the embedding model → **Phase 5**).

- Knowledge Graph Service + Memgraph deployed; entity resolution (`difflib` context-similarity) and relation extraction running via idempotent `POST /api/kg/ingest`.
- Hybrid RAG (dense + sparse, RRF fusion) replaces V1's hardcoded 28-string knowledge base; a real cited statute/regulation corpus ingested, citations only where confidently verifiable.
- Contextualizer migrated onto hybrid RAG with `[N]`-style inline citations + a fabricated-citation validator.
- **Live bug fixed**: V1's `text-embedding-004` default had been silently 404ing against the current Gemini API; updated to `gemini-embedding-001`. Dense retrieval had effectively been BM25-only until this was caught.
- **Not yet done**: GraphRAG hits not fused into the Contextualizer's retrieval alongside BM25/dense; bitemporal graph versioning; self-hosted embeddings/reranker.

**Exit criteria**: Contextualizer answers cite real, retrievable sources — **met, verified live.** GraphRAG "what else references this term" query — **met** via `POST /api/kg/query`.

## Phase 4 — Agentic Orchestration MVP (~8-12 sprints) — ✅ Complete (backend MVP)

A fixed LangGraph pipeline wiring Phases 0-3 into one verified agent workflow.

- LangGraph orchestration deployed: Extraction → Risk & Compliance → Clause Research → Summary → Verifier as a fixed sequence. **Since made planner-driven in Phase 7** (`app/agents/planner.py` chooses which middle agents run). **Still not done**: a durable-execution engine (runs synchronously in-request — acceptable at current runtimes, revisit in Phase 7).
- Verifier ships citation check + KG consistency check (both real); the NLI faithfulness check is an honestly-labelled lexical-overlap stand-in — real local NLI head → **Phase 6**.
- Memory Service — **not started** → Phase 7.
- Frontend Agent Trace Viewer — **not started**; the whole project is backend-only through Phase 4 → Phase 7.
- `agent_traces` persistence — **done**, one row per step, verified live.

**Exit criteria**: a full single-document analysis runs as an auditable agent workflow with every claim citation-checked before reaching the UI — **met at the backend level** (no UI yet — Phase 7).

---

## Phase 5 — Provider Abstraction Hardening (~4-6 sprints) — 🟢 Complete in code (serving stack is an ops step away)

**This phase makes the architecture genuinely provider-agnostic and removes every external dependency *except* large-LLM generation quality.** The code core came first (no GPU needed); the serving layer landed once a GPU (RTX A4000, 16 GB) became available.

**Shipped (code):** the `ModelProvider` interface, the `providers-core` / `providers-external` packaging split (`google-genai` removed from `requirements.txt`), the import-linter contract (CI-gated), the declarative routing-policy engine (`app/policies/routing.yaml`) with Class A/B/C and Class-C gating, per-call routing-decision logging, and **removal of the Gemini embedding dependency from the RAG path**. Verified in a fresh venv with no `google-genai` (`LEARNING_LOG.md` #18).

**Shipped (serving + observability, `LEARNING_LOG.md` #19):** a `gpu` docker-compose profile + `scripts/bootstrap_selfhosted.sh` running **Ollama (Qwen3-8B)** for generation and **TEI on GPU** for **bge-m3** embeddings and **bge-reranker-v2-m3** reranking; a `local-rerank-remote` provider (`OpenAICompatProvider` rerank role) for TEI's `/rerank`; `GET /api/models/status`; `model_calls` routing-decision persistence + an OpenTelemetry scaffold (`app/observability.py`); and the eval seed — Inspect-AI suite (`app/eval/inspect_tasks.py`), CUAD / ContractNLI loaders, and the self-hosted-vs-external **delta report**. Full suite 110 pass + 1 skip, green with nothing served.

**Still open:** an actual observability collector wired to the OTel scaffold (a `docker-compose.observability.yml` — Langfuse / SigNoz / Grafana LGTM); promptfoo; ASR/TTS providers (deferred until a feature needs them).

**Model Router → the real provider interface** (`AI_STACK.md`)
- [x] Define the `ModelProvider` protocol (`generate`, `embed`, `rerank`, `describe`, `is_available`) and provider-neutral request/response schemas. `generate_structured`/`transcribe`/`synthesize`/`health` reserved, not yet needed.
- [x] Split providers into core (self-hosted adapters) / external (commercial); `-external` is an optional install (`requirements-external.txt`).
- [x] Add the **import-linter CI contract**: nothing outside the provider package may import a model SDK (`tests/test_provider_isolation.py` + `.importlinter`).
- [x] Build the **declarative routing-policy engine** (`app/policies/routing.yaml`): task × sensitivity × capability → ordered chain, self-hosted-only fallback chains, conditional Class C. `emergency_class_c` per-org opt-in: not built (no multi-tenant policy layer yet).
- [x] Log `{task, sensitivity, provider, model, reason, candidates}` on every routing decision (`router.py` + `model_router/telemetry.py` → `model_calls`). Join to `eval_runs`: deferred (no `eval_runs` table yet).
- [x] Re-express hosting as **Class A / B / C**, not vendor tiers, throughout config and code.

**Self-host everything that isn't a large LLM** (all CPU- or small-GPU-feasible)
- [x] Deploy **TEI** serving a self-hosted embedding model (**BGE-M3** on the GPU, `gpu` compose profile). **Gemini embedding dependency removed from the RAG path** — the phase's key deliverable.
- [x] Deploy a self-hosted reranker (**bge-reranker-v2-m3** on TEI) and wire it into RRF fusion (`local-rerank-remote` provider).
- [~] Fuse GraphRAG hits into hybrid retrieval — done for the Clause Research agent; the Contextualizer route wiring is a follow-up (needs org context threaded to `explainer`).
- [ ] Add **faster-whisper** (ASR) and **Kokoro/Piper** (TTS) providers — deferred until an audio feature exists.
- [x] Ship an **Ollama**-served small LLM (**Qwen3-8B**) as the local default (`scripts/bootstrap_selfhosted.sh`, `.env.example`).

**Eval harness upgrade**
- [~] Adopt **Inspect AI** as the suite backbone — seed task shipped (`app/eval/inspect_tasks.py`); keep the hand-curated gold set as the fast pre-merge check; **promptfoo** not yet added.
- [~] Point every eval judge at a self-hosted model — the delta report can use `local-llm`; a dedicated judge harness is future work.
- [x] Add the **self-hosted-vs-external delta report** (`app/eval/delta_report.py`): per task, measure what Class C would add. Gates future Class C decisions.

**Exit criteria**: the Model Router is provider-agnostic and passes the import-linter contract ✅; embeddings and reranking are self-hosted on a real TEI/GPU deployment ✅; ASR/TTS N/A; the *only* task routed to a commercial API by default is large-LLM text generation ✅; a contributor can run the entire product locally with zero credentials ✅. Remaining: an observability collector wired to the OTel scaffold; promptfoo.

**Can the product run with no GPU and no external API?** Yes — end to end, at a quality caveat. Structure/RAG/KG/agents/sensitivity are CPU-fine (Phases 2–7); embeddings/rerank run CPU-served (bge-small) or on the A4000 (bge-m3 via TEI); the NLI verifier runs on CPU (slow) or the A4000. LLM generation is the weak point without a GPU: a CPU-served 3B model is usable for dev only. So the running modes are (a) **cloud/hybrid** — Gemini for generation quality on `public`/`internal` docs; (b) **A4000 available** — Qwen3-8B/14B served locally; (c) **disconnected, no GPU** — a CPU 3B model, dev-grade. Nothing is *blocked*; generation quality tracks the hardware.

## Phase 6 — Self-Hosted Generation on one 16 GB card (~6-10 sprints)

**Bounded, not "the unlock".** The project's GPU is one RTX A4000 (16 GB), often borrowed, with **no plan to buy or rent a bigger card**. So the self-hosted generation target is **Qwen3-8B** (default) + **Qwen3-14B-AWQ** (the `hard=` escalation) — fits 16 GB alongside bge-m3 + bge-reranker + the NLI head. Qwen3-32B, reasoning models, and the 7B VLM are **moved to future scope** (they need 24 GB+). The domain quality comes from RAG + KG + fine-tuned heads + the verifier — the design always said so.

**Model serving (fits the 16 GB card)**
- [~] Serve **Qwen3-8B** via Ollama (configured, not yet run — Docker/Ollama is an ops step). Evaluate **vLLM** with Qwen3-8B/14B-AWQ for throughput + grammar-constrained JSON.
- [x] Self-hosted embeddings/reranker via **TEI** (bge-m3, bge-reranker-v2-m3) — configured in the Phase 5 bootstrap.
- **Future scope** (need 24 GB+, revisit only if a bigger/rented GPU appears): Qwen3-32B / 235B as the default; a reasoning model for multi-hop; Qwen2.5-VL for scanned docs; multi-LoRA serving.

**Progressive task cutover — each A/B-gated against the Gemini baseline before it becomes default**
- [x] The **gate mechanism** — `app/eval/cutover_gate.py`: runs a task's graded eval bound to the Gemini baseline vs the self-hosted candidate, `passed = cand ≥ base × ratio`, writes `eval_runs`. `qa` (`legalbench_qa`), `clause_rewrite` (`rewrite_retention` — fact-retention + jargon-removal), `timeline_extract` (`timeline_extraction` — per-event token-F1), and `risk_analysis` (`risk_flag_recall`) all have curated gold sets and graded `Candidate`s now (`app/eval/gold_set.py`: `REWRITE_GOLD`/`TIMELINE_GOLD`/`RISK_GOLD`). `contextualize`/`agent_summary` still have no gold set (open-ended generation with citations has no clean automatic reference; `delta_report.py` covers them qualitatively).
- [x] The **escalation ladder** — `hard=True` on a generate call prepends `local-llm-large` (`LLM_LARGE_MODEL`, e.g. Qwen3-14B) via the policy's `escalate_to`; `services/rewriter.py` sets it for long input, `services/chatbot.py` for multi-hop-looking questions.
- [ ] Actually cut each task over once its gate passes — blocked on a served `local-llm` (Ollama/vLLM up). **Expected**: Qwen3-8B/14B passes on rewrite, structure/timeline extraction (grammar-constrained), simple grounded Q&A; loses to Gemini on multi-hop reasoning and nuanced risk. Resulting policy: self-hosted default where it passes, Gemini (tier-permitting) / human review otherwise — with the per-task delta documented, not glossed over.
- [ ] Structure/timeline extraction → grammar-constrained JSON (xgrammar) once on vLLM.

**CV/NLP models — trainable on the A4000, then CPU-served**
- [x] Integrate **GLiNER** for zero-shot entity types — `providers/gliner_local.py` (`local-ner` / `ner_extract`), merged with the regex floor.
- [ ] **Run the fine-tunes** (`backend/training/`): the clause/contract-type classifier and the **weak-supervision-then-distill** deontic tagger — QLoRA on ModernBERT/Legal-BERT, **minutes each on the A4000**, then the small head serves on CPU. Highest-value GPU task; do it while the card is available. Blocked only on data curation.
- [ ] Fine-tune an **InLegalBERT/ModernBERT NER** head (same story).
- [ ] **maverick-coref** — still blocked by a *software* issue, not GPU, but the issue moved: the original transformers-5/torch-<2.6 CVE guard is resolved on a current stack (torch 2.14 + a safetensors checkpoint load fine), but `fastcoref`'s own model-loading code is unmaintained and breaks against transformers ≥ 5's `PreTrainedModel` internals (`AttributeError: 'FCorefModel' object has no attribute 'all_tied_weights_keys'`). Needs a maintained coref library/checkpoint, or pinning transformers to an older 4.x line specifically for this one dependency (untested).
- [ ] Layout/table extraction (**Docling** / **PaddleOCR PP-Structure**) — mostly CPU; the clean-PDF fast path (Tesseract + quality triage) stays. **olmOCR / Qwen2.5-VL** OCR escalation → future scope (VLM needs more VRAM).

**Verifier**
- [x] Ship the real **NLI faithfulness head** — `providers/nli_local.py` (`local-nli` / `verify_nli`, Class A, in-process DeBERTa-v3-MNLI, 0.91 acc on MNLI, 8/8 on `FAITHFULNESS_GOLD` vs lexical's 6/8). `app/agents/verifier.py` checks each summary claim by entailment; `faithfulness_method` surfaces `nli` vs `lexical_fallback`.

**Eval**
- [x] Integrate **LegalBench** (cuad_* / contract_nli_* subtasks) + **MNLI** into a graded harness — `app/eval/{datasets,metrics,tasks,cutover_gate}.py` + Inspect-AI wrappers + the `eval_runs` table. (The script-based CUAD/ContractNLI/MAUD datasets are dead on `datasets`≥3; LegalBench is the maintained path.)
- [x] For every cutover: the self-hosted model must meet or beat the Gemini baseline on the task's eval — enforced by `cutover_gate.py` (reports "cannot evaluate", never a false PASS, when a provider is missing).

**Exit criteria (revised for the 16 GB ceiling)**: Qwen3-8B/14B is served and cut over for every task where the gate shows parity-or-better vs Gemini; for the rest, the policy documents the delta and routes to Gemini (tier-permitting) or human review. The **air-gapped profile** runs end-to-end with no external call at the 8-14 B quality level. The fine-tuned clause/deontic heads are trained and eval-gate-promoted.

**Progress:** verify is done (real Class-A NLI head); NER gained a GLiNER layer; the **cutover gate + escalation ladder + graded eval harness** are built and tested, and every generate task with a clean automatic reference (`qa`/`clause_rewrite`/`timeline_extract`/`risk_analysis`) now has a curated gold set behind it. What's left: install Ollama/vLLM on the A4000 and run the cutovers (a served `local-llm`, not more hardware); train the clause/deontic heads (minutes on the A4000, blocked on data curation). The 32B/reasoning/VLM ambitions are retired to future scope.

## Phase 7 — Deployment Profiles: On-Prem & Air-Gapped (~10-14 sprints) — 🟡 started (the CPU-only agent/API bits)

With generation self-hosted (Phase 6), the product can now ship disconnected. This phase makes on-prem and air-gapped *supported profiles*, not heroics.

**Done ahead of the deployment work** (they didn't need it):
- the **dynamic Orchestrator/Planner** (`app/agents/planner.py` — rule-based, LLM-optional, `analysis_mode` presets) replacing the fixed Phase 4 sequence;
- the first slice of the **document-first `/api/v2/*` API** (`app/routes/v2.py`);
- **document sensitivity tiering, enforced end to end** (`app/services/sensitivity/` classifies on upload → `documents.sensitivity_tier` → every model call → `policy.candidates()` drops Class C for `confidential`/`privileged`, and `router._pick_and_call` fails closed as a last line). This is the enforcement half of the egress boundary: the Model Router's "Privileged never leaves the perimeter" guarantee was architecture-on-paper (every call site passed `sensitivity="internal"`); it now protects real documents. Org-admin override via `PUT /api/v2/documents/{id}/sensitivity` (audit-logged).

The rest of the phase — packaging, collapsed data layer, durable execution, Memory Service, frontend SPA, per-user RBAC, the PII redaction gate — is genuinely deferred.

**Build & supply chain**
- [ ] Produce on-prem/air-gapped builds with `legalai-providers-external` **excluded**; enforce with an **SBOM allowlist** that fails the build if a commercial-provider SDK is present.
- [ ] **Zarf** packaging of the full application (images + charts + manifests + model weights + seed corpus) into one installable artifact.
- [ ] Model weights as signed **KitOps ModelKit** OCI artifacts through **Harbor**; no `pip`/`huggingface-cli` on the target.
- [ ] **OpenTofu** (not Terraform) for all IaC; Helm + Kustomize overlays per profile; **k3s** single-node target for smaller on-prem racks.
- [ ] cosign signing + Syft SBOM + Trivy/Grype scanning for every image and model artifact.
- [ ] Egress proxy / network policy for the hybrid profile: deny all outbound except configured provider endpoints; log every byte (`audit_log.egress_target`).

**Collapsed data layer** (the "one fewer service to operate" profile)
- [ ] Support **pgvector + pgvectorscale** as a Qdrant substitute; **Apache AGE** or **KùzuDB** as a Memgraph substitute; **LanceDB** embedded for the laptop profile; filesystem object storage; Postgres-backed event queue.
- [ ] Profile-select the data layer via Helm values; the same application code runs against either.

**Durable execution & Memory Service** (deferred from Phase 4)
- [ ] Introduce a durable-execution engine — **DBOS** (library, Postgres-backed) as the default so no new cluster is needed; **Hatchet** for mid-scale; **Temporal** only for the large multi-tenant cloud profile. The `app/agents/graph.py` abstraction stays engine-agnostic.
- [ ] Build the Memory Service: session tier (Redis), episodic tier (Postgres + vector store), consolidation worker (session/episodic → semantic) with the privacy-tier gate.
- [x] Dynamic Orchestrator/Planner agent replacing the fixed Phase 4 sequence — `app/agents/{planner,registry,graph}.py`: `extraction → planner → dispatch-by-plan → verifier`. Rule-based planning (heuristics over the extracted clauses) is the default; `use_ai_planner=True` routes to `task="agent_plan"` and falls back to rules offline. `analysis_mode` presets: `full` / `quick` / `risk_only` / `extract_only`. Done without a durable engine — a per-document analysis still runs in seconds; the engine-agnostic abstraction stays.

**Frontend SPA** (deferred from Phase 4 — a large workstream) — 🟡 two slices shipped, `LEARNING_LOG.md` #27–#28
- [x] Scaffold Next.js + TypeScript; generate the API client from the OpenAPI schema — `frontend-v2/` (App Router, TS, Tailwind, TanStack Query for server state); `npm run codegen` dumps `app.main.app.openapi()` with the backend's own venv (no server needed) and runs `openapi-typescript` over it into the committed `src/lib/api-types.ts`. shadcn/ui and Zustand from `FRONTEND.md`'s full target stack are deliberately not adopted yet — no cross-page shared state or complex primitives this slice needs them for.
- [x] Workspace + Document Analyzer (V1 parity) — upload (`POST /api/upload`, still V1's endpoint) redirects into `/documents/[id]`: a left-panel clause list with **per-clause** rewrite/risk-scan/contextualize via `block_id` (something V1's whole-blob UI structurally could not offer), whole-document rewrite/timeline/risk-scan/ask for V1 parity, and a "run full agent analysis" panel surfacing the planner's `plan`/`plan_rationale`, risk findings, KG conflicts, and faithfulness result. V1's `frontend/` is untouched and keeps serving.
- [x] **Second slice — the NLP/CV/KG/Model-Router backend-vs-frontend gap closed**: after auditing what was built vs. what the UI showed, three more real, already-tested backend capabilities got their first UI ever: a **Structured NLP analysis** panel (`POST /api/nlp/analyze` — per-clause type, deontic modality, entities, defined terms, cross-references, ambiguity flags), a **Knowledge Graph** panel (`POST /api/kg/{ingest,query,conflicts}` — ingest a document, search a defined term for cross-document usage and candidate conflicts; fail-soft "Memgraph unreachable" state surfaced honestly, not hidden), and a standalone `/models` page (`GET /api/models/status` — every registered provider's hosting class, capabilities, availability). A small paired backend change: `Document.quality` (the CV blur/skew triage) was computed at upload but never persisted — added as a real column (`app/db.py`'s `_ensure_columns()` pattern) so it survives past the initial upload response and now shows as a low-quality-page warning banner in the workspace.
- [~] **Agent Trace Viewer** — the post-hoc version is shipped: `AgentAnalyzeResponse.trace` already returned every step in one response and had nowhere to render, so `AgentTraceViewer` renders it as a collapsible timeline (agent name, input/output summary, in order) inside the analysis panel. The *real-time* version (live updates as each agent runs, via a session WebSocket) is still not started — needs session infrastructure this phase's Memory Service section also hasn't built. Human-in-the-loop review queue UI — still not started.
- [ ] **Provider & Model admin**: an org admin sees which models serve which tasks, the eval scores behind the routing policy, and the delta report; toggles Class C per task/tier (where the build includes it). The plain `/models` status table above is a step toward this, not the same thing — no eval scores, no delta report, no toggles yet.
- [~] **Model status panel**: the `/models` page shows hosting class, capabilities, and live `is_available()` per provider — the backend doesn't track queue depth or latency anywhere yet, so that half is still open.
- [ ] Fully self-hosted frontend assets (fonts, analytics via Plausible) so a `Privileged` page has no third-party origin. `frontend-v2` currently uses `next/font/google` (Geist) — fine for local dev, would need vendoring for the air-gapped build profile.
- [x] Sensitivity-aware rendering — a persistent `SensitivityBadge` sourced from the real `GET /api/v2/documents/{id}/sensitivity` response (not a client-side tier guess), shown on every document. No Class-C toggle exists in the UI to disable yet, so that half of the security note has nothing to enforce against.
- [~] Introduce `/api/v2/*` document-first endpoints — **first slice shipped** (`app/routes/v2.py`: `GET /api/v2/documents/{id}` + `POST .../{analyze,rewrite,map,ask,risk-scan,contextualize}`, reusing the V1 services, `block_id` to target one block); **now consumed by a real client** (`frontend-v2`). Session objects, `/negotiate`, per-org feature-flagging are still to do.

**Verification**: `npm run build` + `npm run lint` clean on both slices; every endpoint exercised live via `curl` against the real backend with the exact request/response shapes the TypeScript client sends/expects, including the new `/api/nlp/analyze`, `/api/models/status`, `/api/kg/*` calls and the persisted `quality` column (confirmed `null` for a `.txt` upload, migration confirmed applying on an existing SQLite file: `schema: added documents.quality`). Full backend suite re-run after the schema change: 193 pass, 1 skip, no regressions. **Not yet done**: an actual in-browser click-through — no `claude-in-chrome` extension was connected either session, so the UI has been server-rendered and API-verified but not visually exercised by a human-equivalent agent.

**What's still backend-only with no UI at all**: the fine-tuning scaffold's outputs (nothing trained yet, so nothing to show); the eval harness / cutover gate results (`app/eval/`, `eval_runs` table — a Provider & Model admin concern, not built); `NOVELTY.md`'s five research ideas (Phase 8, not started, prototypes don't exist yet to have a UI for).

**Exit criteria**: a genuine air-gapped install (Zarf artifact → disconnected k3s cluster → working product, verified with no network) validated with a pilot customer; a collapsed-data-layer on-prem install validated; the frontend SPA at V1 feature parity plus the Agent Trace Viewer.

## Phase 8 — Portfolio Intelligence & Research Features (~10-14 sprints, research-gated)

The in-house models are the main lever on quality now that the served LLM is capped at 8-14 B. Training runs are minutes-to-hours on the A4000 (or a one-off cloud rental); the resulting BERT-scale heads and the LightGBM risk model serve on **CPU**. The `distilabel` weak-supervision *teacher* is a served self-hosted model (Qwen3-8B here, not the 235B the doc assumes) or, for a batch offline pass, a one-off rented larger model.

**In-house models** (`DEEP_LEARNING.md`)
- [ ] Curate training data (org corpora with consent + CUAD/ContractNLI); **distilabel** weak-supervision pass with a **self-hosted teacher**; legal-expert review in **Argilla**.
- [ ] Train the **Risk Scoring Model** (LightGBM, CPU — blocked on labelled data, not hardware); integrate SHAP explainability.
- [ ] Finalize the fine-tuned **clause/contract-type classifier** and **NER head**; eval-gate promotion.
- [ ] **Document Sensitivity Classifier** — try classical (TF-IDF + linear) first; only fine-tune a transformer if that underperforms.
- [ ] **Legal Clause Embedding Model** — contrastive fine-tune (`NOVELTY.md` #3) with hard-negative mining.
- [ ] **MLflow** registry + **DVC** data versioning; eval-gated model promotion wired into CI/CD; **model cards** for every trained model.

**Portfolio agents** (`AGENTS.md`, `KNOWLEDGE_GRAPH.md`)
- [ ] **Cross-Document Consistency** agent (embedding-similarity baseline → learned `NOVELTY.md` #1).
- [ ] **Simulation** agent (deterministic discrete-event baseline → Monte-Carlo `NOVELTY.md` #2).
- [ ] **Negotiation/Drafting** agent — static org-configured preferences first; the learned playbook (`NOVELTY.md` #4) once redline history exists.
- [ ] **Bitemporal** graph versioning (valid time / transaction time) — the Phase 3 gap; needed for simulation.
- [ ] Negotiation Studio frontend (Yjs collaborative editing); Risk Dashboard spider chart (closes the V1 README promise).

**Research track** (`NOVELTY.md`) — each idea independently gated; prototype + benchmark + (if pursued) formal prior-art search
- [ ] Ideas #1–#5: literature review, architecture design, and CPU-only components proceed anytime; GPU training steps (GAT #1, contrastive embedding #3) use the Phase 6 infra.
- [ ] Target a benchmark contribution and/or a workshop paper (NLLP @ *ACL, JURIX, ICAIL) for any idea that validates — see `NOVELTY.md`'s publication strategy.

**Exit criteria**: portfolio-level contradiction detection and obligation-timeline simulation are live (established-technique versions first; novel-mechanism versions only after their research gate); at least one in-house trained model in production at or above its rule-based baseline; at least one `NOVELTY.md` idea has a validated prototype with benchmark results.

## Phase 9 — Scale, Memory Maturity & Enterprise Hardening (~ongoing)

- [ ] Semantic and procedural memory tiers completed; consolidation jobs live with privacy-tier gating enforced.
- [ ] Multi-tenant cloud scale: Qdrant sharding, per-org graph partitioning, GPU autoscale on queue depth, Postgres read replicas; **Temporal** adopted for the cloud profile if DBOS/Hatchet hit a ceiling.
- [ ] **SOC 2 Type II** readiness and **GDPR** data-subject workflows (export/delete per org) as a formal compliance program; air-gapped profile positioned for customers with data-residency / classified-handling mandates.
- [ ] Full cost/latency optimization pass across the routing policy using a quarter of production eval + cost data; right-size the self-hosted model fleet; quantization / speculative-decoding / batching tuning.
- [ ] V1's `/api/v1/*` deprecation timeline finalized once `/api/v2/*` has full parity plus the new capabilities.
- [ ] Quarterly drift-monitoring review of production eval scores against the gold benchmark.

**Exit criteria**: at least one production customer per deployment profile (cloud / hybrid / on-prem / air-gapped); compliance program formally underway; V1 API sunset scheduled; the routing policy is cost/latency-optimized on real data.

## Cross-cutting, all phases

- **Nothing merges without the eval gate** (from Phase 2 onward) — and, from Phase 5, that includes routing-policy and provider changes.
- **Every sensitive-tier code path change gets a security review**, with special attention to anything touching Class C egress. The tier itself is now enforced (`app/services/sensitivity/` + the Model Router fail-closed guard, Phase 7).
- **Every phase preserves V1's live traffic** — this is an additive migration.
- **The import-linter contract** (from Phase 5) is a permanent CI gate: no vendor SDK outside the provider package, ever.
