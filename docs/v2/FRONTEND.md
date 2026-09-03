# Frontend Architecture

V1's frontend is a single static HTML page with vanilla JS and no build step — appropriate for a 6-endpoint demo, insufficient for a system with streaming multi-agent traces, collaborative redlining, and a knowledge-graph explorer. V2 replaces it with a proper SPA while keeping the same "ship something a browser can render with no exotic runtime requirements" spirit.

## Stack

| Layer | Choice | Why |
|---|---|---|
| Framework | **Next.js (React) + TypeScript** | Mature, huge open-source ecosystem, supports both SPA and server-rendered routes for the marketing/about pages carried over from V1 |
| Styling | **Tailwind CSS** | Utility-first, fast to iterate, no CSS-file sprawl like V1's hand-written `style.css` |
| Component primitives | **shadcn/ui** (open source, Radix-based) | Accessible-by-default primitives — extends V1's already-reasonable ARIA usage rather than fighting it |
| Client state | **Zustand** (local UI state) + **TanStack Query** (server state/caching) | Small, unopinionated, avoids Redux-scale boilerplate for what is still a moderately-sized app |
| API client | **Generated from the backend's OpenAPI schema** (`openapi-typescript` + a thin fetch wrapper) | Type-safe by construction; eliminates V1's manual, duplicated endpoint map in `app.js` |
| Real-time | **WebSocket (or SSE) connection per active session** | Streams agent-trace events, extraction progress, and negotiation updates as they happen, instead of V1's single blocking `fetch` per step |
| Document rendering | **PDF.js** (open source) with a custom overlay layer | Renders original PDF pages with clause/entity highlight overlays positioned from CV pipeline bounding boxes (`COMPUTER_VISION.md`) |
| Redline / diff viewer | Custom diff renderer over the clause graph (word-level diff + clause-level change markers) | Needs to diff *structured clauses*, not raw text — off-the-shelf text-diff widgets aren't sufficient once clauses are first-class objects |
| Collaborative editing | **Yjs** (CRDT, open source) | Enables multiple reviewers to redline the same document concurrently without a custom OT implementation |
| Knowledge graph visualization | **Cytoscape.js** (open source) | Interactive exploration of the portfolio graph (`KNOWLEDGE_GRAPH.md`) — contradiction paths, obligation timelines |
| Charts | **Recharts / Observable Plot** (open source) | Risk radar/spider chart (a feature V1 promised in its README but never built — closed in this design) |

No commercial frontend SaaS (analytics, session replay, etc.) is assumed by default; self-hostable equivalents (e.g., Plausible for analytics) are used if needed, to keep the sensitivity-tiering story in `ARCHITECTURE.md` intact end-to-end — a third-party JS analytics snippet on a page displaying `Privileged`-tier contract text would otherwise be a real leak vector.

**Offline / air-gapped build.** The SPA builds with every asset vendored — fonts self-hosted (no Google Fonts CDN), no runtime CDN scripts, no external telemetry — so the same bundle serves the cloud and the air-gapped profile. The build is reproducible and shipped inside the Zarf artifact (`ARCHITECTURE.md`). A strict Content Security Policy with no external origins is the default, not a hardening step.

## Application modules

| Module | Purpose | Key V1 lineage |
|---|---|---|
| **Workspace** | Org/document list, upload, sensitivity tier confirmation | Evolves the "Analyze" section |
| **Document Analyzer** | Simplified/advanced view, clause list with type/deontic tags, inline citations | Evolves "Results" tabs |
| **Timeline** | Interactive obligation/date timeline, now with simulated future events (Novelty: temporal decay simulation) | Evolves "Timeline" section |
| **Risk Dashboard** | Spider/radar chart of risk categories, drill-down to clause-level explanations with counterfactual attribution | Closes the gap flagged in V1's `FEATURES.md` (README promised, never built) |
| **Contextualizer** | Role/tone-personalized explanation, now citing real retrieved sources instead of a static list | Evolves "Contextualizer" section |
| **Negotiation Studio** | Redline suggestions, accept/reject, collaborative multi-reviewer editing, playbook-driven suggestions | New |
| **Agent Trace Viewer** | Step-by-step view of what each agent did, what it retrieved, what it verified, **which provider/model served each step**, and **why the planner chose the agents it ran** (`plan` + `plan_rationale` from `POST /api/v2/documents/{id}/analyze`) — the explainability surface for `AGENTS.md`'s audit trail | New (backend `plan`/trace shipped; the viewer is still to build) |
| **Knowledge Graph Explorer** | Visual traversal of entities/obligations/contradictions across a user's document portfolio | New |
| **Chat** | True multi-turn assistant backed by session memory (`AGENTS.md`), not V1's stateless per-message call | Evolves "Chatbot" widget |
| **Admin/Org Settings** | Sensitivity policy, **routing-policy view + per-task/per-tier Class C toggles**, user/role management, audit log export, **Class C egress log** | New |
| **Provider & Model Admin** | Which self-hosted model serves which task, the eval scores behind the routing policy, and the self-hosted-vs-external delta report (`AI_STACK.md`) — so enabling an external provider for a task is an informed, reversible decision | New |
| **Model Status Panel** | Health, queue depth, and latency of the self-hosted model-serving fleet (vLLM/TEI/…) — the operator's view of their own inference layer | New |

## Real-time architecture

A single **session WebSocket** carries all live events for an active analysis session: extraction progress, per-agent step events (`agent_started`, `tool_call`, `agent_finished`, `verification_result`), and final results. The Agent Trace Viewer and the analysis screens subscribe to the same stream, so a user watching the Risk Dashboard sees the Risk & Compliance Agent's reasoning appear incrementally rather than waiting on one opaque request like V1's `uploadBtn` handler did.

## Security at the frontend layer

- **Content Security Policy** strict by default; no third-party script origins beyond what's explicitly allowlisted (Google Fonts equivalent self-hosted where possible).
- **Sensitivity-aware rendering**: documents tagged `Privileged` render with a persistent visual indicator and disable any client-side control that could trigger a Class C (external-provider) call (mirrors the Model Router's server-side enforcement — defense in depth, not just a UI hint). In on-prem/air-gapped builds these controls are absent entirely, since no external provider exists.
- **Sandboxed document preview**: uploaded file rendering happens through PDF.js in a sandboxed iframe/worker so a malicious PDF cannot execute script in the parent app context.

## What's explicitly *not* changing

- The overall page-section mental model (Analyze → Results → Timeline → Risks → Contextualizer → Chat) carries over — users familiar with V1 shouldn't need to relearn the product, just get a richer version of it.
- Accessibility patterns already present in V1 (skip links, ARIA roles/labels, `aria-live` status regions) are preserved and extended to new components, not reinvented.
