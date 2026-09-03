# Model & Infrastructure Stack

The strongest open-source option for each component of V2, with reasoning. This is the reference `AI_STACK.md`, `AGENTS.md`, `NLP.md`, `COMPUTER_VISION.md`, `DEEP_LEARNING.md`, `KNOWLEDGE_GRAPH.md`, and `ARCHITECTURE.md` point at when they say "the recommended model".

**Selection rules applied throughout:**

1. **Permissively licensed and self-hostable.** Apache-2.0 / MIT / clearly-commercial-use-permitted open weights are strongly preferred. Llama-license and Gemma-license models are acceptable but flagged, because a copyleft-ish or acceptable-use-restricted licence complicates air-gapped resale and some enterprise procurement.
2. **Runs on hardware we can actually buy.** Every recommendation names a size that fits a realistic self-hosted budget: a single 24–48 GB GPU for the standard profile, a 6 GB laptop GPU or CPU-only for the constrained/edge profile.
3. **Swappable.** Every recommendation is a default, not a marriage. The Model Router (`AI_STACK.md`) and the eval harness exist precisely so a better model can be dropped in without touching a service.
4. **Recency caveat.** Model releases move faster than this document. Treat specific version numbers as "the current best in this family as of the last revision"; the *family* and the *reasoning* are the durable part. Re-benchmark before adopting.

Sizes are given as **standard profile** (single 24–80 GB GPU or small GPU node) and **constrained profile** (≤ 8 GB VRAM / CPU-only / air-gapped laptop).

---

## Generative & semantic models

### Reasoning LLMs (the primary generation layer)

| Profile | Recommendation | Why |
|---|---|---|
| Standard | **Qwen3-32B** (Apache-2.0) as the default; **Qwen3-235B-A22B** (MoE, ~22 B active) where a GPU node is available and quality matters more than footprint | Qwen3 has the strongest open structured-output and instruction-following behaviour in its class, a hybrid "thinking / non-thinking" mode that maps cleanly onto our "cheap first pass, escalate to reasoning" pattern, genuine multilingual coverage, and a clean Apache licence with no acceptable-use rider. The MoE keeps inference cost near a dense 22 B while giving 235 B-scale quality on hard reasoning. |
| Standard (reasoning-heavy) | **DeepSeek-R1-Distill-Qwen-32B** or **QwQ-32B** for tasks that are genuinely multi-step (cross-document conflict analysis, obligation simulation reasoning traces) | Distilled long-chain-of-thought reasoning at a size that serves on one 48 GB GPU. Use selectively — reasoning models are slower and more expensive per answer, so the Router escalates to them only when a first pass flags the task as hard. |
| Standard (alternative) | **gpt-oss-20b / gpt-oss-120b** (Apache-2.0), **Mistral-Small-3.2-24B** (Apache-2.0), **Gemma-3-27B** (Gemma licence) | gpt-oss is a clean-licence reasoning model with native tool-use formatting. Mistral-Small-3.2 is the best "small dense, no licence friction" option and a strong air-gap-resale choice. Gemma-3 is multimodal out of the box (see VLM row) but carries Google's Gemma terms. |
| Constrained | **Qwen3-4B / Qwen3-8B** (4-bit, via llama.cpp/Ollama), **Gemma-3-4B**, **Phi-4-mini** | Qwen3-4B in Q4 fits ~4 GB and is genuinely usable for rewrite, extraction, and grounded Q&A when the retrieval context does the heavy lifting. This is the model that keeps an air-gapped laptop deployment functional. |

**Legal-domain note:** there is no open general-purpose "legal LLM" worth making the default — the domain-tuned open models (Saul-7B/SaulLM, LawGPT, etc.) trail a current general 32 B model on the tasks we care about, because our grounding comes from RAG + the knowledge graph, not from the model's parametric legal knowledge. We get legal-domain lift instead from (a) fine-tuning a general base on our own curated data (`DEEP_LEARNING.md`), and (b) retrieval. Re-evaluate if a strong, permissively-licensed legal reasoning model appears.

### Coding models (internal use: codegen features, agent tool-writing, dev tooling)

| Profile | Recommendation | Why |
|---|---|---|
| Standard | **Qwen2.5-Coder-32B** (Apache-2.0); watch for Qwen3-Coder | Best open coding model at a self-hostable size; strong fill-in-the-middle and repo-level context handling. Used for: generating structured extraction schemas, drafting deterministic tool code from a spec, and any "explain this contract as a state machine / as code" feature. |
| Standard (alternative) | **DeepSeek-Coder-V2-Lite (16 B MoE)**, **Devstral-Small** (Mistral, Apache-2.0, agent-coding-tuned) | Devstral is specifically tuned for agentic coding workflows (multi-file edits, tool loops) and is the right choice if we build an agent that writes/maintains its own tools. |
| Constrained | **Qwen2.5-Coder-7B / 3B** (4-bit) | Sufficient for schema generation and short deterministic-tool synthesis. |

Coding models are **not** on the contract-analysis critical path — they support developer and agent-authoring workflows. Keep them out of the default serving footprint; load on demand.

### Vision-language models (VLMs) — scanned-document understanding, layout Q&A, figure/exhibit reading

| Profile | Recommendation | Why |
|---|---|---|
| Standard | **Qwen2.5-VL-32B** (or 7B for throughput); watch Qwen3-VL | State-of-the-art open document VLM: reading order, table structure, key-value extraction, and grounded bounding boxes in one model. Handles "read this scanned exhibit and tell me the payment schedule" without a separate OCR+layout+table stack. Apache-2.0. |
| Standard (alternative) | **InternVL3-38B**, **Gemma-3-27B** (multimodal), **Pixtral-12B** (Apache-2.0) | InternVL3 is competitive on doc benchmarks. Pixtral is the clean-licence mid-size option. |
| Constrained | **Qwen2.5-VL-3B/7B (4-bit)**, **MiniCPM-V 2.6 (8B)**, **SmolVLM-2** | MiniCPM-V and SmolVLM are designed for edge/CPU-ish inference and keep the scanned-document path alive on a laptop. |

**How the VLM is used vs. the OCR stack:** the OCR stack (below) is the default for text extraction because it is faster, cheaper, and deterministic. The VLM is the **escalation path** for degraded scans, complex multi-column layouts, and "understand this page as a whole" queries — the same confidence-gated pattern V1 already uses for OCR fallback, now pointed at an open model instead of a commercial Document AI API.

### OCR & document parsing

| Layer | Recommendation | Why |
|---|---|---|
| PDF → structured text/markdown (primary) | **Docling** (IBM, MIT) or **MinerU 2** (AGPL — check licence fit) | Docling is the best-engineered open PDF/DOCX/PPTX → structured-document pipeline: layout, reading order, tables, formulae, and a clean document model that maps onto our `Clause` segmentation. MIT licence, active, designed for exactly this. MinerU is a strong alternative but AGPL, which is a problem for closed-source on-prem resale — prefer Docling unless AGPL is acceptable for the deployment. |
| Layout + reading order + tables (from images) | **Surya** (GPL-ish research licence — check; commercial licence available) or **PaddleOCR-VL / PP-StructureV3** (Apache-2.0) | PaddleOCR is the safe permissive choice for a product: mature, multilingual, layout + table + formula recognition, runs on CPU acceptably. Surya has excellent quality and 90+ language support but verify the licence for commercial/air-gap resale. |
| Raw OCR baseline | **Tesseract 5** (Apache-2.0), kept from V1 | Fine for clean scans; zero licence risk; the floor everything else improves on. |
| Hard-scan / OCR-free understanding | **olmOCR** (AllenAI, Apache-2.0, Qwen2-VL-based) or the standard VLM above | olmOCR is purpose-built for messy real-world PDFs (rotated, handwritten annotations, poor scans) and is Apache-licensed end to end including the training data. Good air-gap story. |
| Commercial fallback | **Optional Class C plugin only** (Google Document AI / Azure Document Intelligence) | Retained as an opt-in connector for the cloud SaaS profile where a customer wants it; **never installed in on-prem/air-gapped builds**, and never the default even in cloud. The open stack above is the product. |

**Recommended default pipeline:** Docling for digital PDFs and DOCX → PaddleOCR for image-only pages that have a usable scan → olmOCR / Qwen2.5-VL for pages both of those flag as low-confidence. Every stage records `extraction_confidence` and which engine ran (`COMPUTER_VISION.md`).

### Embeddings

| Profile | Recommendation | Why |
|---|---|---|
| Standard | **Qwen3-Embedding-8B** (Apache-2.0) or **Qwen3-Embedding-0.6B/4B** for throughput | Top of MTEB among open models, instruction-aware (you can prompt it with the retrieval task), strong multilingual and long-context (32 K) behaviour, clean licence. The 0.6 B model is genuinely competitive and cheap enough to embed every clause of every document on ingest. |
| Standard (alternative) | **BGE-M3** (MIT) | Kept as a documented alternative and the current Phase-3 target. Its distinguishing feature is producing dense + sparse (lexical) + ColBERT-style multi-vector representations from *one* model — useful if we want learned sparse retrieval without running SPLADE separately. Slightly behind Qwen3-Embedding on pure dense quality now. |
| Constrained / on-device | **EmbeddingGemma-300M** (Gemma licence) or **BGE-small / gte-small** | EmbeddingGemma is built for on-device (runs in <200 MB quantized, sub-15 ms on CPU) and keeps semantic retrieval working in the air-gapped-laptop profile. |
| In-house | **Legal Clause Embedding Model** — contrastive fine-tune of BGE-M3 or Qwen3-Embedding on clause-equivalence pairs | The domain-specific objective behind `NOVELTY.md` #3; see `DEEP_LEARNING.md`. This is where legal-domain retrieval lift actually comes from. |

### Rerankers

| Profile | Recommendation | Why |
|---|---|---|
| Standard | **Qwen3-Reranker-4B** (Apache-2.0) | Matches the embedding model's family and training distribution, instruction-aware, current SOTA among open cross-encoders. |
| Standard (alternative) | **bge-reranker-v2-m3** (MIT), **mxbai-rerank-v2** (Apache-2.0), **jina-reranker-v2** | bge-reranker-v2-m3 is the well-worn, lightweight, MIT-licensed default and is the current Phase-3 target; keep it as the fallback. |
| Constrained | **bge-reranker-base** or skip reranking, relying on RRF fusion alone | On a laptop, RRF over dense+sparse without a reranker is an acceptable degradation; the eval harness quantifies the loss. |

### NLP models (non-generative: NER, coref, classification, deontic tagging)

| Task | Recommendation | Why |
|---|---|---|
| Framework / tokenization / sentence split | **spaCy** (MIT) | The integration scaffold; not the intelligence. |
| Zero-shot / configurable NER | **GLiNER** family (Apache-2.0) — `urchade/gliner_multi-v2.1` | One model, arbitrary entity types specified at inference. Covers "party", "governing-law jurisdiction", "monetary amount", "defined term", "statute citation" without a fine-tune. **Shipped (Phase 6)**: `providers/gliner_local.py` (`local-ner` / `ner_extract`), merged with the regex floor in `nlp/entities.py`, fail-soft. |
| NLI faithfulness head (Verifier safety gate) | **DeBERTa-v3 / ModernBERT 3-class NLI**, Class A, in-process | Deterministic, local-only entailment check for the Verifier — never a generation call. **Shipped (Phase 6)**: `providers/nli_local.py` (`local-nli` / `verify_nli`), default `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli`; `verifier.py` labels each summary claim against its sources. |
| Structured extraction from text | **NuExtract 2.0** (small, template-driven extraction model) | Purpose-built for "here's a JSON schema, fill it from this text" — a good fit for clause-field extraction where GLiNER's span model is too coarse. |
| Legal-domain encoder (fine-tune base) | **InLegalBERT**, **Legal-BERT** (Chalkidis et al.), **LexLM** | The base for any fine-tuned token-classification or clause-type head (`DEEP_LEARNING.md`). Pretrained on legal corpora; small enough to serve on CPU at Class A. |
| Coreference resolution | **maverick-coref** (current SOTA-ish, lightweight) with **fastcoref** as the fast fallback | Contracts need long-range coref ("the Company" 40 pages later); maverick handles document-length context better than fastcoref while staying CPU-serveable. LLM-assisted coref via the Router is the escalation path for the hardest cases. |
| Deontic modality tagging | **In-house distilled BERT-family tagger** (`DEEP_LEARNING.md`), bootstrapped by weak supervision | No public model does obligation/permission/prohibition/discretion tagging at the granularity we need. Rule-based Tier-0 (shipped in Phase 2) is the bootstrap and the permanent fast pre-filter. **Scaffolded (Phase 6)** in `backend/training/`, not trained. |
| Clause / contract type classification | **In-house fine-tune** on a DeBERTa-v3 / ModernBERT / Legal-BERT base, evaluated against CUAD/LegalBench | `NLP.md` §8. **Scaffolded (Phase 6)** in `backend/training/` (LoRA, LegalBench + gold + weak-supervision data prep), not trained; the rule base stays the Tier-0 pre-filter until a head beats it on the eval gate. |

### Speech-to-text (ASR) — dictated notes, recorded negotiations, deposition/hearing audio

| Profile | Recommendation | Why |
|---|---|---|
| Standard | **faster-whisper** (CTranslate2 build of Whisper large-v3 / large-v3-turbo, MIT) | The default: strong multilingual accuracy, 4× faster than reference Whisper, runs on modest GPU or CPU. large-v3-turbo trades a little accuracy for a large speed gain and is the right pick for interactive dictation. |
| Standard (English throughput) | **NVIDIA Parakeet-TDT-1.1B** (CC-BY-4.0) | Best-in-class English word error rate and extremely fast, if the deployment is English-only and has an NVIDIA GPU. |
| Diarization + word-level alignment | **WhisperX** (speaker labels + timestamps) with **pyannote** (check licence / gated weights) or **NVIDIA Sortformer** | "Who said what, when" matters for negotiation and hearing audio. pyannote's models are gated on Hugging Face — for air-gap, pre-stage the weights or use an alternative diarizer. |
| Constrained | **whisper.cpp** with base/small, or **Moonshine** (tiny, fast, English) | Keeps transcription available on CPU-only / edge. |

### Text-to-speech (TTS) — accessibility read-aloud, audio summaries, voice UI

| Profile | Recommendation | Why |
|---|---|---|
| Standard | **Kokoro-82M** (Apache-2.0) | Remarkable quality-to-size ratio: an 82 M-param model that produces natural, controllable speech, runs real-time on CPU, and has a fully permissive licence. This is the default for read-aloud and audio summaries. |
| Standard (expressive / cloning) | **XTTS-v2** (Coqui, check licence — CPML, non-commercial by default; commercial licence exists) or **F5-TTS** (research licence — verify) or **Chatterbox** (Resemble, MIT) | Chatterbox is the clean-licence option if we want expressive/voice-styled output. XTTS is higher quality but has licence friction for a commercial product — verify before shipping. |
| Constrained / air-gapped | **Piper** (MIT) | Fast, tiny, fully offline, many pre-built voices, designed for exactly the low-resource / on-device case. The air-gap default. |

---

## Platform & infrastructure

### Agent framework / orchestration

| Concern | Recommendation | Why |
|---|---|---|
| Agent graph runtime | **LangGraph** (MIT), kept from Phase 4 | Explicit state-graph model over free-form agent loops — the right choice for a legal domain where determinism and auditability beat open-ended autonomy. Every node transition and tool call is inspectable and persistable. Already shipped. |
| Alternative to watch | **PydanticAI** (typed, model-agnostic, minimal), **smolagents**, **Google ADK**, **OpenAI Agents SDK** | PydanticAI is the closest philosophical match if LangGraph's abstractions ever feel heavy — it is model-agnostic and Pydantic-native, which fits our schema-first backend. Not a reason to migrate now; a reason to keep the agent layer thin enough that we *could*. |
| Structured-output / tool-call enforcement | **xgrammar** (vLLM's grammar backend) or **Outlines** / **llguidance** | Guaranteed-valid JSON from any served model — removes a whole class of "the model didn't return parseable JSON" retries and makes the typed tool interface (`AGENTS.md`) enforceable at the decoding layer, not just by post-hoc validation. |

### Durable execution / workflow engine

| Profile | Recommendation | Why |
|---|---|---|
| Cloud SaaS at scale | **Temporal** (OSS, MIT) | The mature choice for durable, resumable, retryable multi-agent workflows. Survives worker crashes, retries individual steps, gives a full execution history for free. |
| Standard / on-prem / lean | **Hatchet** (MIT, Postgres-backed) or **DBOS Transact** (library, Postgres-backed) | Temporal is operationally heavy (its own cluster, its own datastore). Hatchet gives most of the durable-workflow value on top of the Postgres we already run. DBOS is a *library* — durable execution with no extra service at all — which is the right answer for the on-prem and air-gapped profiles where "one more cluster to operate" is a real cost. **Recommendation: DBOS/Hatchet as the default, Temporal as an opt-in for the large multi-tenant cloud profile.** |
| Current state | Synchronous in-request (Phase 4) | Acceptable while analyses run in seconds; the abstraction in `app/agents/graph.py` should stay engine-agnostic so any of the above can slot in. |

### Vector database

| Profile | Recommendation | Why |
|---|---|---|
| Standard / cloud | **Qdrant** (Apache-2.0) | Best all-round open vector DB: fast HNSW, native hybrid (dense + sparse) search, payload filtering, quantization, horizontal sharding, per-collection multi-tenancy for org isolation. The default. |
| Small / on-prem-lite | **pgvector + pgvectorscale** (Postgres extensions, permissive) | Collapses the vector store into the Postgres we already operate. pgvectorscale (StreamingDiskANN) closes most of the performance gap for corpora up to tens of millions of vectors. One fewer service to run air-gapped. |
| Embedded / air-gapped laptop / research | **LanceDB** (Apache-2.0) | Serverless, file-based, zero-ops vector store with good ANN and a columnar format that doubles as a dataset format for experiments. The right pick when "run a service" isn't an option. |
| Heavy scale alternative | **Milvus** (Apache-2.0) | If a single-tenant deployment reaches billions of vectors. More operationally complex than Qdrant; only reach for it with a measured need. |

### Knowledge graph store

| Profile | Recommendation | Why |
|---|---|---|
| Standard (interactive agent queries) | **Memgraph** (BSL→ / check current licence; MAGE is Apache) or **Neo4j Community** (GPLv3) | In-memory Cypher engine tuned for the low-latency traversals agent tool calls need. Kept from Phase 3. Verify Memgraph's current licence terms against the deployment model — Neo4j CE (GPLv3) is the documented alternative and both speak Cypher so the query layer is portable. |
| GraphRAG-latency-sensitive | **FalkorDB** (Redis module, permissive) | Purpose-built for GraphRAG: very fast small-graph traversals, sparse-matrix-based, and it colocates with the Redis we already run. Worth benchmarking against Memgraph specifically for the per-query traversal latency inside the retrieval path. |
| Reduced-infra on-prem | **Apache AGE** (Postgres extension, Apache-2.0) | openCypher inside Postgres. Same "one fewer service" argument as pgvector. Acceptable for portfolio sizes typical of a single org; not for multi-tenant cloud scale. |
| Embedded / research | **KùzuDB** (MIT, embedded) | In-process graph DB, columnar, fast analytical graph queries, no server. Excellent for the air-gapped-laptop profile and for research notebooks. *Caveat:* the backing company wound down in 2025; the project is open source and MIT — treat as community-maintained and pin versions. |

### Model serving

| Layer | Recommendation | Why |
|---|---|---|
| LLM/VLM serving (GPU) | **vLLM** (Apache-2.0) primary; **SGLang** (Apache-2.0) where structured output / high concurrency / prefix-cache reuse dominates | vLLM is the throughput default (continuous batching, paged attention, multi-LoRA, broad model coverage). SGLang's RadixAttention gives a real edge on agent workloads that reuse long shared prefixes (system prompts, retrieved context) across many calls — benchmark both on our actual traffic. |
| LLM serving (max NVIDIA perf) | **TensorRT-LLM** | Only when a single-tenant deployment needs the last 30 % of throughput on fixed NVIDIA hardware and can absorb the build complexity. |
| LLM serving (CPU / edge / air-gap laptop) | **llama.cpp** / **Ollama** | Ollama for developer machines and small on-prem (nice model management, OpenAI-compatible endpoint). Raw llama.cpp for the tightest air-gapped footprint. |
| Embeddings / rerankers | **Text Embeddings Inference (TEI)** (Apache-2.0) or **Infinity** (MIT) | Dedicated high-throughput servers for embedding and reranker models. Infinity supports more backends and models; TEI integrates tightly with the HF ecosystem. Either keeps embedding/rerank off the LLM GPU. |
| Serving orchestration (K8s) | **KServe** or **Ray Serve** | Autoscaling, canary rollout, and multi-model management on the GPU node pool. Ray Serve if we also use Ray for training/batch; KServe if we want a thinner, inference-only layer. |
| Provider abstraction (Class C plugins) | **LiteLLM** (MIT) as *one* adapter implementation inside the optional commercial-provider package | LiteLLM already speaks 100+ provider APIs behind one interface. Rather than hand-write a Gemini/OpenAI/Anthropic adapter each, the Class C plugin package can wrap LiteLLM. It does **not** define our provider interface (we own that — see `AI_STACK.md`); it's an implementation convenience for the optional tier. |

### Evaluation

| Concern | Recommendation | Why |
|---|---|---|
| RAG-specific eval | **Ragas** (Apache-2.0) | Faithfulness, answer relevance, context precision/recall. The Phase-2 target. Its judge model is pluggable — point it at a self-hosted model so eval itself has no external dependency. |
| Rigorous / research-grade eval + CI | **Inspect AI** (UK AISI, MIT) | The strongest open eval framework for building real, versioned, reproducible benchmark suites with proper logging — the right backbone for anything headed toward a publication. Use it to house the internal legal gold set and the agent-trajectory evals. |
| Legal-domain benchmarks | **LegalBench**, **LexGLUE**, **CUAD**, **ContractNLI**, **MAUD**, **BillSum** | LegalBench (162 legal-reasoning tasks) is the headline external benchmark to track a self-hosted model against. **Shipped (Phase 6)**: `app/eval/datasets.py` loads LegalBench cuad_*/contract_nli_* subtasks + MNLI; the standalone CUAD-QA/ContractNLI datasets are script-based and dead on `datasets` ≥ 3, so LegalBench's reformatted subtasks are the path. `app/eval/cutover_gate.py` is the "self-hosted must meet/beat the baseline before it becomes default" gate. |
| Prompt/regression testing in CI | **promptfoo** (MIT) or **DeepEval** (Apache-2.0) | Fast, declarative, git-diffable test cases for prompt and model changes — the pre-merge smoke gate that runs on every PR. |
| Broad capability probes | **lm-evaluation-harness** (EleutherAI, MIT) | Standard academic harness; use when evaluating a fine-tune's general capability regression, not just legal tasks. |

### Observability

| Layer | Recommendation | Why |
|---|---|---|
| LLM/agent tracing | **Langfuse** (MIT/self-hostable) primary; **Arize Phoenix** (Elastic-2.0/OSS) alongside for RAG-debugging and eval visualization | Langfuse is the production trace store (every agent step, tool call, prompt version, token count, cost, per session). Phoenix is stronger for interactively debugging *why* a retrieval or a generation went wrong and for running eval experiments — the two complement rather than duplicate. Both self-host. |
| Standard telemetry | **OpenTelemetry** with the GenAI semantic conventions; **OpenLLMetry** (Traceloop SDK) for auto-instrumentation | One tracing standard across every service; GenAI semconv means model/token/cost spans are portable and not locked to one vendor's SDK. |
| Metrics / logs / traces backend | **Grafana LGTM stack** (Loki, Grafana, Tempo, Mimir/Prometheus) — all AGPL/Apache | Fully self-hostable observability backend. Dashboards for latency, cost-per-request by provider, queue depth, eval score over time, per-org usage. **SigNoz** (MIT) is a single-binary alternative for small/on-prem deployments that don't want to run the full LGTM stack. |

### Training

| Concern | Recommendation | Why |
|---|---|---|
| Core framework | **PyTorch** + **Hugging Face Transformers / TRL** | TRL covers SFT, DPO, KTO, ORPO, and GRPO (the RL method behind the reasoning models) with a consistent API. |
| Low-VRAM fine-tuning | **Unsloth** (Apache-2.0) | 2× faster, ~50–70 % less VRAM for LoRA/QLoRA — this is what makes fine-tuning a Legal-BERT / small-LLM head feasible on the RTX-4050-class budget in the constrained profile. The default for our fine-tunes. |
| Config-driven fine-tuning at scale | **Axolotl** (Apache-2.0) or **Llama-Factory** (Apache-2.0) | YAML-configured training recipes, multi-GPU via DeepSpeed/FSDP, reproducible. Use when a training run outgrows a single GPU. |
| Weak-supervision teacher | **Any Class B model via the Router** (e.g. Qwen3-235B), with **distilabel** (Argilla, Apache-2.0) as the pipeline framework | `DEEP_LEARNING.md`'s weak-supervision step is reframed: the "teacher" that labels the seed set is **a self-hosted open model by default**, not a frontier API. distilabel orchestrates the labeling + critique + dedup pipeline. A commercial teacher is an *optional* substitution, used offline/batch only, and never required. |
| Data labeling / review | **Argilla** (Apache-2.0) primary; **Label Studio** (Apache-2.0) for wider modality support | Argilla is Python-native, integrates with distilabel and the HF ecosystem, and is built for the "LLM proposes, human reviews and corrects" loop we need for the legal-expert review step. |
| Data / experiment versioning | **DVC** (Apache-2.0) + **MLflow** (Apache-2.0) | DVC pins every model version to an exact dataset snapshot; MLflow tracks params/metrics/artifacts and is the model registry. **ClearML** (Apache-2.0) is the alternative if we want experiment tracking + orchestration + data management in one tool. |
| Distributed training infra | **Ray Train** or bare **Accelerate / DeepSpeed / FSDP** | Only relevant once we train something bigger than a BERT head or a small-LLM LoRA. |

### Fine-tuning (method, as distinct from tooling above)

| Method | When | Why |
|---|---|---|
| **LoRA / QLoRA / DoRA** (PEFT) | Default for every domain adaptation (clause classifier, deontic tagger, NER head, per-org redline predictor) | Cheap, fast, composable, and servable as hot-swappable adapters via vLLM multi-LoRA / **LoRAX** — one base model, many per-task or per-org adapters, no full copy per fine-tune. |
| **Full fine-tune** | Only the small encoders (Legal-BERT-scale) where LoRA underperforms and the model is small enough that it's cheap anyway | |
| **GRPO / DPO / ORPO** (preference / RL) | The Redline Acceptance Predictor and any "match this org's style" objective; reasoning-trace quality on legal multi-step tasks | Preference optimization from an org's own accepted/rejected redline history (`NOVELTY.md` #4) is a DPO-shaped problem. |
| **Distillation** | Deontic tagger, clause classifier — teacher (big Class B model) → student (fast CPU-serveable model) | The mechanism for getting big-model labeling quality with Class-A production inference cost. |
| **Adapter serving** | vLLM multi-LoRA, **LoRAX** | Per-org models (redline predictor) served as adapters, isolated per tenant, no per-org base-model copy. |

### Deployment

| Concern | Recommendation | Why |
|---|---|---|
| Orchestration | **Kubernetes** (cloud / large on-prem); **k3s** (single-node on-prem / edge); **Docker Compose** bundle (smallest on-prem / local dev) | One set of container images, three packaging targets. k3s is a single binary and the right Kubernetes for a customer's own rack. |
| Packaging | **Helm** + **Kustomize** | Per-service charts, environment overlays (dev/staging/prod/on-prem/air-gap). |
| GitOps | **Argo CD** or **Flux** (both CNCF, open) | Declarative, auditable deploys; the deployed state is a git commit. |
| Infra-as-code | **OpenTofu** (Linux Foundation, MPL-2.0) — **not** Terraform | Terraform's 2023 relicense to BSL is incompatible with the open-source-first commitment and with some customers' procurement. OpenTofu is the drop-in open fork. Use it. |
| Air-gapped delivery | **Zarf** (Apache-2.0) | Packages a whole Kubernetes application — images, charts, manifests, and data — into a single declarative artifact that installs into a disconnected cluster. This is the mechanism that makes the air-gapped profile a supported product rather than a heroics exercise. |
| Private registry | **Harbor** (CNCF, Apache-2.0) | Mirrors all upstream images and model artifacts; the only registry an air-gapped deployment talks to. Scans (Trivy) and signs on push. |
| Model artifact packaging | **KitOps / ModelKit** (OCI artifacts) | Ship model weights + config + eval card as a signed OCI artifact through the same Harbor registry as the code — one supply chain, one signing story, no ad-hoc weight downloads on the target. |
| Minimal / hardened images | **apko + Wolfi** (Chainguard, open) or distroless | Small attack surface, near-zero CVEs, faster to get through enterprise image scanning. |
| Supply chain | **Sigstore/cosign** (signing), **Syft** (SBOM), **Grype/Trivy** (scanning) | Every image and model artifact is signed and has an SBOM. The SBOM allowlist is also the enforcement point for "no commercial-provider SDK in an air-gapped build" (`ARCHITECTURE.md`). |
| GPU on Kubernetes | **NVIDIA GPU Operator** + **KubeRay** (if using Ray) | Standard GPU node-pool management, MIG partitioning, autoscale on queue depth. |

---

## Summary: the default self-hosted stack

| Component | Default |
|---|---|
| Reasoning LLM | Qwen3-32B (Apache-2.0); Qwen3-235B-A22B on a GPU node; DeepSeek-R1-Distill-32B / QwQ-32B for hard reasoning |
| Constrained LLM | Qwen3-4B / Gemma-3-4B (4-bit) |
| VLM | Qwen2.5-VL-32B (7B for throughput) |
| OCR / parsing | Docling → PaddleOCR → olmOCR/Qwen2.5-VL (confidence-gated) |
| Embeddings | Qwen3-Embedding-8B (0.6B constrained); BGE-M3 alternative |
| Reranker | Qwen3-Reranker-4B; bge-reranker-v2-m3 fallback |
| NER / NLP | GLiNER (shipped, `local-ner`) + spaCy; DeBERTa/ModernBERT NLI faithfulness head (shipped, `local-nli`); Legal-BERT/ModernBERT fine-tune bases (scaffolded); maverick-coref (pending) |
| ASR | faster-whisper large-v3-turbo; Parakeet (English); WhisperX (diarization) |
| TTS | Kokoro-82M; Piper (air-gap) |
| Agent framework | LangGraph + xgrammar structured output |
| Durable execution | DBOS / Hatchet default; Temporal for large SaaS |
| Vector DB | Qdrant; pgvector on-prem-lite; LanceDB embedded |
| Graph DB | Memgraph / Neo4j CE; FalkorDB for GraphRAG latency; Apache AGE reduced-infra; KùzuDB embedded |
| Model serving | vLLM + SGLang (GPU); Ollama/llama.cpp (CPU/edge); TEI/Infinity (embeddings) |
| Evaluation | Inspect AI + Ragas + promptfoo; LegalBench / CUAD / ContractNLI corpora |
| Observability | Langfuse + Phoenix + OpenTelemetry + Grafana LGTM (SigNoz small) |
| Training | PyTorch + TRL + Unsloth + Axolotl; distilabel + Argilla; DVC + MLflow |
| Fine-tuning | LoRA/QLoRA/DoRA default; GRPO/DPO for preference; multi-LoRA serving |
| Deployment | Kubernetes/k3s + Helm + Argo CD + OpenTofu + Zarf + Harbor + cosign/Syft |

Every row is self-hostable, and every row has at least one Apache/MIT-licensed option so the air-gapped/on-prem-resale profile has no licence blocker. Where the strongest model in a category carries a non-permissive licence (Gemma terms, Llama AUP, research-only), a permissive alternative is named in the same row.
