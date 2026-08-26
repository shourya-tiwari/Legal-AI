# Features

Legend: ✅ Keep as-is · 🔧 Keep, needs refactor · ⚠️ Fragile/hackathon-grade · ❌ Missing

## Current features

### 1. Document upload & extraction — 🔧
**Endpoint**: `POST /api/upload` · **Service**: `services/extractor.py`

Accepts PDF, DOCX, TXT, and (best-effort) image files. Fully local parsing — no cloud OCR dependency. PDF extraction has a page-level OCR fallback via `pytesseract` when a page yields no text layer.

- **Keep**: the local-parsing approach (PyMuPDF/python-docx), the fallback chain, the normalized `{full_text, blocks}` output contract.
- **Refactor**: `models.py` defines `UploadResponse` with a `session_id` field, but `routes/upload.py` doesn't use that model at all — it returns an ad hoc dict (`filename`, `content_type`, `full_text`, `clauses`, `count`) with no session ID. This is the seam where document persistence should be wired in for V1 (see `ARCHITECTURE.md`).
- **Fragile**: OCR dependencies (`pytesseract`, Pillow) are optional/soft-imported; if missing, image uploads silently degrade to a placeholder string rather than a clear error to the user. File size limits are not enforced anywhere — a very large PDF will be processed in full in-memory with no guardrail.

### 2. Plain-English rewrite ("Simplify") — 🔧
**Endpoint**: `POST /api/rewrite` · **Service**: `services/rewriter.py`

Chunks input text (8000-char windows with 200-char overlap) and rewrites each chunk via Gemini with a fixed system prompt, then joins the outputs.

- **Keep**: the core transform and its guardrail-style system prompt ("preserve exact legal meaning," "don't add information").
- **Refactor**: naive char-window chunking can split mid-sentence/mid-clause, which risks incoherent output at chunk boundaries; `timeline.py` already uses a smarter hierarchical (paragraph→sentence→whitespace) splitter — the two should converge on one shared chunking utility. `mode` is currently constrained by `models.py` to the single literal `"layman"` (`pattern="^(layman)$"`) even though the README documents an `"advanced"` mode — that mode does not exist in the implementation today.
- **Fragile**: no caching — re-rewriting the same document twice re-spends the full Gemini quota/latency.

### 3. Document map & timeline — 🔧
**Endpoint**: `POST /api/map` · **Service**: `services/timeline.py`

Two AI calls per text chunk (structure extraction + timeline extraction), each expecting raw JSON back from Gemini, parsed defensively (strips code fences, falls back to `[]` on parse failure) and deduplicated.

- **Keep**: the hierarchical chunking splitter (better than rewriter's), the dedup logic, the structured Pydantic response models (`DocumentSection`, `TimelineEvent`).
- **Refactor**: JSON-from-LLM parsing has no retry/repair step and no logging when parsing fails silently — a malformed model response just produces an empty structure/timeline with no visible error to the caller. Doubling the number of Gemini calls per chunk (one for structure, one for timeline) is the most latency/cost-expensive part of the whole app for large documents; consider a single combined-schema prompt.

### 4. Risk Radar (keyword + AI risk scan) — 🔧
**Endpoint**: `POST /api/risk/scan` · **Service**: `services/risk_radar/`

Combines a deterministic keyword scan (`rules.py`, ~55 predefined risky legal terms with static explanations) with an AI call that asks Gemini to flag additional risky terms as JSON.

- **Keep**: the hybrid approach (fast, free, deterministic keyword pass + AI pass for anything the static list misses) is a good design and should be preserved.
- **Refactor**: `routes/risk_radar.py` defines its own inline `ClauseIn` Pydantic model instead of using `app/models.py` like every other route — should be moved into `models.py` for consistency, and given a proper `RiskScanResponse` model instead of returning a bare dict. The README's "Risk Radar (spider chart)" framing implies a visual radar/spider chart on the frontend — **this visualization does not exist**; the frontend currently just renders a flat `<ul>` list of flagged terms.
- **Fragile**: the AI risk prompt has no length/chunking strategy at all (unlike rewrite/map), so very long clauses passed to `/api/risk/scan` risk exceeding prompt limits.

### 5. Contract Q&A (single-turn + chat widget) — 🔧
**Endpoint**: `POST /api/ask` · **Service**: `services/chatbot.py`

Single Gemini call per question, grounded on the full contract text passed in the request body, with a system instruction to answer only from the given text or return a fixed "not found" string.

- **Keep**: the "answer only from provided context" grounding instruction — this is the right approach for reducing hallucination on this kind of task.
- **Refactor**: despite the frontend framing this as a "chat" with a message history UI (`chatPanel`/`chatMessages`), the backend is stateless single-turn Q&A — there is no conversation memory, so follow-up questions ("what about the second one?") will not resolve correctly. This is a naming/expectation mismatch between the UI and the actual capability. `AskResponse.references` is defined in `models.py` but `chatbot.py` never populates it — always returns an empty list.
- **Fragile**: no chunking or retrieval for long contracts — the entire `contract_text` is stuffed into the prompt every time, which will hit prompt/context limits on long documents and re-costs a full context on every single question.

### 6. Contextualizer (role-personalized clause explanation) — 🔧
**Endpoint**: `POST /api/contextualize/scan` · **Service**: `services/contextualizer/`

The most sophisticated feature: builds a role/location/contract-type/tone-aware prompt (`templates.py`), enriches it with up to 3 relevant facts retrieved via a FAISS similarity search (`rag.py`) over a hardcoded 28-entry legal knowledge base (`explainer.py`), with explicit anti-hallucination guardrails in the prompt (don't invent jurisdiction-specific numbers, etc.).

- **Keep**: the guardrail-heavy prompt design, the role/tone/context modeling (`UserContext` dataclass), the RAG-with-fallback pattern (falls back to static per-contract-type hints if retrieval fails).
- **Refactor**: the knowledge base is hardcoded Python data with no update mechanism, sourced from no cited authority (comments like "AB 12," "AB 1482" are asserted, not linked to a source) — needs either a real citation/source field or a clear "informational, not legal advice, verify locally" disclaimer surfaced to the end user (the prompt tells the *model* to hedge, but the UI doesn't independently disclose this limitation). The RAG index rebuilds (re-embeds all 28 strings) on every process cold start, which is wasteful and will not scale if the knowledge base grows.
- **Fragile**: `interests` in `UserContext` is modeled but the frontend hardcodes it to `null` with a comment "Could be expanded later" — half-wired feature.

### 7. Frontend UI — 🔧
Single static page (`frontend/index.html` + `app.js` + `style.css`), no build tooling, accessible markup (ARIA roles/labels used reasonably throughout), responsive nav.

- **Keep**: the overall page structure/section layout, accessibility attributes already present.
- **Refactor**: hardcoded production `baseURL` in `app.js` (see `ARCHITECTURE.md`); dead code (`renderRiskList()` defined but never called — risk list rendering is duplicated inline in the upload handler instead); a malformed HTML attribute on the hero header (`class="hero sect>`, missing closing quote) at `index.html:32`.
- **Missing**: no loading/error state for individual analysis steps beyond a single top-level status string — if `map` succeeds but `risk/scan` fails, the user sees a generic error with no indication that rewrite/timeline results are still valid and displayed.

## Missing features (not present at all today)

- ❌ **Authentication / authorization** — every endpoint is open; anyone with the URL can call it and consume Gemini quota.
- ❌ **Persistence** — no database; nothing survives a page refresh or server restart. No history of past analyses.
- ❌ **Multi-turn conversational memory** for the "chat" widget (currently stateless single-turn Q&A per message).
- ❌ **Risk radar visualization** — despite the feature's name and the README's description ("visualizes them in a risk radar (spider chart)"), there is no chart; results are a plain list.
- ❌ **Export/download** of results (simplified text, timeline, risk report) — everything is view-only in the browser.
- ❌ **Rate limiting / abuse protection** on any endpoint.
- ❌ **File size / page count limits** on upload.
- ❌ **Automated tests** (unit or integration) — only manual diagnostic scripts exist.
- ❌ **CI/CD pipeline** — no GitHub Actions or equivalent visible in the repo.
- ❌ **Structured logging / observability** — only scattered `print()` statements.
- ❌ **Multi-document comparison** or side-by-side clause comparison across contracts.
- ❌ **User accounts / saved preferences** (e.g., remembering a user's role/location/tone choice for the Contextualizer across sessions).
- ❌ **Real legal knowledge base with sourcing** — current knowledge base is a static, uncited, hardcoded list of ~28 strings.
