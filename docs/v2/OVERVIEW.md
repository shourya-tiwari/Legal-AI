# LegalAI V2 — Overview

> Status: **design document**. Nothing in `docs/v2/` is implemented. This is a research-grade architecture proposal built on top of the V1 system documented in `docs/v1/`. No application code has been written or modified to produce this design.

## Vision

V1 (`docs/v1/`) proved the core idea: an LLM behind a thin FastAPI service can make contracts legible to non-lawyers. It is a single-model, single-call, stateless pipeline — one Gemini call per feature, no memory, no persistence, no structural understanding of a contract beyond flat text and regex keyword matches.

**V2 reframes the product as a legal *reasoning* system, not a text-transformation API.** Concretely, that means:

- A contract is parsed into a **structured, graph-connected representation** (clauses, obligations, parties, dates, defined terms, cross-references) — not just a text blob re-sent on every request.
- Answers are produced by **specialized agents that collaborate, retrieve evidence, and check their own work** against source text and a knowledge graph — not a single unverified LLM completion.
- Retrieval is **grounded in a real corpus** (the user's documents + statutes/regulations + case law + curated legal knowledge) via hybrid dense+sparse+graph retrieval — not a hardcoded 28-string list.
- The system **remembers**: per-session context, per-document history, and per-organization negotiation patterns — not a stateless request/response cycle.
- Every AI output is **evaluated, traced, and auditable** — not a `print()` statement in a route handler.
- Model choice is **tiered by data sensitivity and task complexity**, defaulting to open-weight models the organization can run itself, escalating to commercial frontier APIs only where they provide a clear, specific advantage.

## Design principles

1. **Open-source-first, commercial-by-exception.** Every component defaults to a self-hostable, open-weight/open-source option. A commercial API (Gemini, or another frontier LLM/OCR provider) is used only where a documented capability gap justifies it — never as the default path for sensitive data.
2. **Structure over strings.** The atomic unit of the system is a `Clause` object with typed annotations (parties, obligations, deontic modality, cross-references), not a raw text chunk. Every downstream feature (RAG, KG, agents, UI) consumes this structure.
3. **Grounded, checked, cited.** No agent output ships without either (a) a source-text citation, (b) a knowledge-graph-backed fact, or (c) an explicit "not found / verify locally" hedge. A dedicated Verifier agent enforces this before any answer reaches a user.
4. **Data sensitivity is a first-class routing dimension.** Every document is classified into a sensitivity tier at ingestion, and that tier — not developer convenience — determines which models, storage, and third parties are allowed to touch it.
5. **Everything is evaluated before it ships.** Prompt changes, model swaps, and fine-tunes are gated behind a regression eval suite (`AI_STACK.md`, `ROADMAP.md`), not shipped on vibes.
6. **Novel research is clearly separated from established engineering.** `NOVELTY.md` is explicit about what is a known technique applied to a new domain versus an original contribution, and states plainly that any patent claim requires independent prior-art search — this document does not constitute legal or patent advice.

## What V2 adds over V1

| Capability | V1 | V2 |
|---|---|---|
| Contract representation | Flat text + paragraph blocks | Structured `Clause` graph with entities, obligations, deontic tags, cross-references |
| Reasoning | One LLM call per feature | Multi-agent orchestration with planning, tool use, and self-verification |
| Retrieval | Hardcoded 28-string list + FAISS | Hybrid dense/sparse/graph retrieval over a real, versioned legal corpus |
| Cross-document awareness | None (single clause at a time) | Portfolio-level knowledge graph; contradiction/conflict detection across contracts |
| Memory | None (client re-sends full text) | Session, episodic, semantic, and procedural memory tiers |
| Model strategy | One hardcoded Gemini model | Sensitivity- and task-aware model router across open-weight and commercial tiers |
| Document understanding | Text-layer extraction + best-effort OCR | Layout-aware CV pipeline (tables, signatures, scan quality, redaction detection) |
| Evaluation | None | Continuous eval harness (RAG faithfulness, agent trace review, human-in-the-loop queue) |
| Auditability | `print()` statements | Full agent decision trace persisted per case, queryable, exportable |
| Deployment | Single Render instance | Multi-tier deployment (cloud / hybrid / on-prem) with GPU-aware model serving |

## Document map

| File | Covers |
|---|---|
| `OVERVIEW.md` | This file. |
| `ARCHITECTURE.md` | Complete system architecture: services, data layer, deployment, security, scalability, developer workflow, evaluation & observability. |
| `FRONTEND.md` | Frontend architecture: stack, modules, real-time agent-trace UI, collaborative redlining. |
| `BACKEND.md` | Backend service decomposition, APIs, workflow orchestration, data contracts. |
| `AI_STACK.md` | Model selection, model router, RAG architecture, prompt/version governance. |
| `AGENTS.md` | Agentic architecture: agent roster, tool interfaces, memory system, verification loop. |
| `NLP.md` | NLP pipeline: segmentation, NER, coreference, deontic modality tagging, clause classification. |
| `DEEP_LEARNING.md` | Training/fine-tuning pipeline for domain-specific models, active learning, model governance. |
| `COMPUTER_VISION.md` | Document layout understanding, OCR, table/signature detection, visual diffing. |
| `KNOWLEDGE_GRAPH.md` | Graph schema, construction pipeline, query patterns, temporal modeling. |
| `NOVELTY.md` | 5 research-grade ideas with potential patent value; established vs. novel components explicitly separated. |
| `ROADMAP.md` | Phased delivery plan from V1's current state to full V2. |
| `TASKS.md` | Actionable, checkbox-level development backlog. |

## Scope and non-goals

- **Not a law firm replacement.** V2 is a decision-support and comprehension tool. Every generated explanation is framed as informational, with jurisdiction-specific claims hedged unless backed by a cited source in the knowledge graph.
- **Not jurisdiction-certified legal advice.** The knowledge graph and RAG corpus improve grounding, but do not make the system authoritative counsel; this must remain explicit in the product UI, not just in system prompts (a gap identified in V1's `FEATURES.md`).
- **Not a single implementation sprint.** This is a multi-quarter architecture; `ROADMAP.md` phases it so V1 keeps running in production while V2 capabilities are built and cut over incrementally.
- **Not vendor-locked.** Every commercial dependency (frontier LLM, commercial OCR fallback) has a documented open-source substitute path, so the platform degrades gracefully rather than breaking if a vendor relationship changes.
