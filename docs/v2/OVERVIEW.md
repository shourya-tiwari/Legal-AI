# LegalAI V2 — Overview

> Status: **design document**. Nothing in `docs/v2/` is implemented as described here yet — Phases 1–4 have shipped a pragmatic slice (see `ROADMAP.md`/`TASKS.md` for exactly what is real). This is a research-grade target architecture built on top of the V1 system documented in `docs/v1/`.

## Vision

V1 (`docs/v1/`) proved the core idea: an LLM behind a thin FastAPI service can make contracts legible to non-lawyers. It is a single-model, single-call, stateless pipeline — one Gemini call per feature, no memory, no persistence, no structural understanding of a contract beyond flat text and regex keyword matches.

**V2 reframes the product as a self-hosted legal *reasoning* system, not a text-transformation API wrapped around someone else's model.** Concretely:

- A contract is parsed into a **structured, graph-connected representation** (clauses, obligations, parties, dates, defined terms, cross-references) — not a text blob re-sent on every request.
- Answers are produced by **specialized agents that collaborate, retrieve evidence, and check their own work** against source text and a knowledge graph — not a single unverified completion.
- Retrieval is **grounded in a real corpus** (the user's documents + statutes/regulations + case law + curated legal knowledge) via hybrid dense + sparse + graph retrieval — not a hardcoded 28-string list.
- The system **remembers**: per-session context, per-document history, per-organization negotiation patterns.
- Every AI output is **evaluated, traced, and auditable**.
- **The primary inference layer is open-weight models the organization runs itself.** No feature depends on a commercial API. The entire product — ingestion, extraction, retrieval, reasoning, verification, speech, and training — runs with only open-source components, offline, on the organization's own hardware.

### The open-source-first commitment (this is the load-bearing principle)

Every earlier version of this design treated Gemini as a permanent tier of the architecture. **That is retired.** In V2:

- **Open-weight models are the default and only *required* inference path.** They are not a fallback, a "Tier 0", or a cost-optimization — they are the product's engine.
- **Commercial model APIs (Gemini, OpenAI, Anthropic, Bedrock, …) are optional connector plugins.** They ship in a separate package that an operator chooses to install. They are disabled by default. They are excluded from air-gapped builds by construction. Removing every one of them changes no feature's availability — only, at most, a quality or latency ceiling that the eval harness measures explicitly.
- **No business logic names a vendor.** Services request a *capability* (`generate`, `embed`, `rerank`, `transcribe`, …) from the Model Router; the Router resolves it to a `(provider, model)` binding from a declarative policy. Adding or removing a provider is a policy edit plus one adapter class — never a change to a service.
- **GPU acquisition unlocks local inference as the default path**, it does not "add a model tier". The migration target is a platform where the strongest available model for every task is one we host.

See `AI_STACK.md` for the Model Router design and `MODEL_STACK.md` for the recommended open-source model and infrastructure choices, component by component, with reasoning.

## Design principles

1. **Self-hosted-first, external-by-exception-and-by-plugin.** Every component defaults to a self-hostable, open-weight/open-source option that runs with no outbound network calls. An external commercial API is an opt-in plugin, never the default path, and never a hard dependency of any feature.
2. **No vendor in the business logic.** Every provider — self-hosted or commercial — implements one interface. The Model Router is the only component that knows providers exist. Swapping, adding, or dropping a provider is a configuration change.
3. **Structure over strings.** The atomic unit of the system is a `Clause` object with typed annotations (parties, obligations, deontic modality, cross-references), not a raw text chunk. Every downstream feature consumes this structure.
4. **Grounded, checked, cited.** No agent output ships without (a) a source-text citation, (b) a knowledge-graph-backed fact, or (c) an explicit "not found / verify locally" hedge. A dedicated Verifier agent enforces this.
5. **Data sensitivity is a first-class routing dimension.** Every document is classified into a sensitivity tier at ingestion; that tier — not developer convenience — determines which providers, storage, and third parties may touch it. A `Privileged` document never leaves the deployment perimeter, and the Router enforces this server-side.
6. **Everything is evaluated before it ships.** Prompt changes, model swaps, provider changes, and fine-tunes are gated behind a regression eval suite, not shipped on vibes. The eval harness is what decides whether a self-hosted model is good enough for a task — never preference, and never a vendor's marketing.
7. **Reproducible by construction.** Every output records the prompt version, model version, provider, retrieval set, and eval score that produced it. Every trained model traces to an exact dataset snapshot. This is required for the audit trail, for research publications, and for any patent filing.
8. **Novel research is clearly separated from established engineering.** `NOVELTY.md` is explicit about what is a known technique applied to a new domain versus an original contribution, and states plainly that any patent claim requires independent prior-art search.

## What V2 adds over V1

| Capability | V1 | V2 |
|---|---|---|
| Contract representation | Flat text + paragraph blocks | Structured `Clause` graph with entities, obligations, deontic tags, cross-references |
| Reasoning | One LLM call per feature | Multi-agent orchestration with planning, tool use, and self-verification |
| Retrieval | Hardcoded 28-string list + in-memory FAISS | Hybrid dense/sparse/graph retrieval over a real, versioned legal corpus |
| Cross-document awareness | None | Portfolio-level knowledge graph; contradiction/conflict detection across contracts |
| Memory | None (client re-sends full text) | Session, episodic, semantic, procedural memory tiers |
| Model strategy | One hardcoded Gemini model | **Provider-agnostic Model Router over self-hosted open-weight models; commercial APIs are optional plugins** |
| Inference location | Vendor cloud, always | **Organization's own hardware by default; air-gap-capable end to end** |
| Document understanding | Text-layer extraction + best-effort OCR | Layout-aware CV pipeline (tables, signatures, scan quality, redaction detection) |
| Evaluation | None | Continuous eval harness (RAG faithfulness, agent-trace review, legal benchmarks, human-in-the-loop queue) |
| Auditability | `print()` statements | Full agent decision trace persisted per case, queryable, exportable |
| Deployment | Single Render instance | Multi-profile: cloud SaaS / single-tenant VPC / on-prem / air-gapped, all from one codebase |
| Custom models | None | In-house fine-tuning pipeline (LoRA/QLoRA/GRPO) with a model registry and eval-gated promotion |

## Document map

| File | Covers |
|---|---|
| `OVERVIEW.md` | This file. |
| `ARCHITECTURE.md` | System architecture: services, data layer, deployment profiles (cloud → air-gapped), security, scalability, developer workflow, evaluation & observability. |
| `FRONTEND.md` | Frontend architecture: stack, modules, real-time agent-trace UI, provider/model admin, offline build. |
| `BACKEND.md` | Backend service decomposition, APIs, workflow orchestration, provider adapter layer, egress policy. |
| `AI_STACK.md` | The Model Router: provider interface, inference classes, routing-policy engine, RAG architecture, prompt/version governance. |
| `MODEL_STACK.md` | Recommended open-source stack, component by component (reasoning LLMs, VLMs, OCR, embeddings, rerankers, NLP, speech, TTS, agent framework, vector DB, graph DB, orchestration, serving, eval, observability, training, fine-tuning, deployment), each with reasoning and alternatives. |
| `AGENTS.md` | Agentic architecture: agent roster, tool interfaces, memory system, verification loop, durable execution. |
| `NLP.md` | NLP pipeline: segmentation, NER, coreference, deontic modality tagging, clause classification. |
| `DEEP_LEARNING.md` | Training/fine-tuning pipeline for domain-specific models, weak supervision with a pluggable teacher, active learning, model governance. |
| `COMPUTER_VISION.md` | Document layout understanding, OCR, table/signature detection, visual diffing. |
| `KNOWLEDGE_GRAPH.md` | Graph schema, construction pipeline, query patterns, temporal modeling, embedded vs. server graph stores. |
| `NOVELTY.md` | 5 research-grade ideas with potential patent value; established vs. novel components separated; publication and open-source-contribution strategy. |
| `ROADMAP.md` | Phased delivery plan from V1's current state to a fully self-hosted platform. |
| `TASKS.md` | Actionable, checkbox-level development backlog. |

## Scope and non-goals

- **Not a law firm replacement.** V2 is a decision-support and comprehension tool. Every generated explanation is framed as informational, with jurisdiction-specific claims hedged unless backed by a cited source in the knowledge graph.
- **Not jurisdiction-certified legal advice.** The knowledge graph and RAG corpus improve grounding but do not make the system authoritative counsel; this must be explicit in the product UI, not just in system prompts.
- **Not a single implementation sprint.** This is a multi-quarter architecture; `ROADMAP.md` phases it so V1 keeps running in production while V2 capabilities are built and cut over incrementally.
- **Not vendor-locked, and not vendor-dependent.** Every commercial dependency is an optional plugin with a self-hosted default already in the primary path. The platform does not degrade when a vendor relationship changes — because the vendor was never in the critical path.
