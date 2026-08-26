# Architecture

## Current architecture

```
┌─────────────────────────┐        HTTPS/JSON        ┌──────────────────────────────────────┐
│  frontend/ (static)      │ ────────────────────────▶ │  FastAPI backend (backend/app)        │
│  index.html + app.js     │ ◀──────────────────────── │  main.py                               │
│  (baseURL hardcoded to   │                            │                                        │
│   Render production URL) │                            │  routers (/api/*) ─▶ service modules   │
└─────────────────────────┘                            │       │                                 │
                                                        │       ▼                                 │
                                                        │  services/genai_client.py               │
                                                        │  (single Gemini Developer API client)   │
                                                        └───────────────┬──────────────────────────┘
                                                                        │ HTTPS
                                                                        ▼
                                                          Google Gemini Developer API
                                                          (generate_content, embed_content)
```

### Request/response flow

`app/main.py` creates the FastAPI app, registers a global `RequestValidationError` handler, and mounts six routers, all under the `/api` prefix:

| Endpoint | Route file | Service | Purpose |
|---|---|---|---|
| `POST /api/upload` | `routes/upload.py` | `services/extractor.py` | Parse an uploaded file to text + paragraph blocks |
| `POST /api/rewrite` | `routes/rewrite.py` | `services/rewriter.py` | Rewrite text into plain English |
| `POST /api/map` | `routes/map.py` | `services/timeline.py` | Extract document structure + timeline events |
| `POST /api/ask` | `routes/ask.py` | `services/chatbot.py` | Single-turn grounded Q&A over supplied contract text |
| `POST /api/risk/scan` | `routes/risk_radar.py` | `services/risk_radar/detector.py` | Keyword + AI risk flagging |
| `POST /api/contextualize/scan` | `routes/contextualize.py` | `services/contextualizer/explainer.py` | Role/context-personalized clause explanation (RAG-assisted) |

Every route is a thin wrapper: validate input (via `app/models.py` Pydantic schemas, except `risk_radar.py` which defines its own inline model), call one service function, return its result. There is no shared middleware layer beyond CORS and the validation-error handler — no auth, no rate limiting, no request logging beyond ad hoc `print()`/`traceback.print_exc()` calls in a couple of routes.

### The "no state" model

- `app/storage.py` defines an in-memory `document_storage: Dict[str, str]`, explicitly commented as dev/hackathon-only, but it is essentially unused — routes don't read/write it.
- Instead, the **client is the source of truth for session state**: the frontend uploads a file once, keeps `full_text` in a JS variable (`LAST_TEXT`), and re-sends it as a request body field (`text` / `contract_text`) on every subsequent call (rewrite, map, risk scan, ask, contextualize).
- This means: no persistence across page reloads, no multi-user isolation guarantees beyond what's implicit in stateless requests, and no way to revisit a past analysis.

### AI call path

All Gemini access is centralized in `services/genai_client.py`:
- `get_client()` — singleton `genai.Client`, reads `GOOGLE_API_KEY` (required) and applies a 30s HTTP timeout.
- `generate_content(prompt, **config_kwargs)` — used by rewriter, timeline, chatbot, risk_radar, contextualizer. Classifies failures into 404 (bad model), 429 (quota), timeout, and generic, always raising a descriptive `RuntimeError`.
- `embed_content(contents, model="text-embedding-004")` — used only by the RAG index in the contextualizer.

Every service module builds its own prompt string inline (no shared prompt-template system, no output schema validation beyond ad hoc JSON parsing with try/except-and-return-`[]`).

### Document ingestion

`services/extractor.py` is fully local/offline:
- PDF → PyMuPDF (`fitz`), with per-page OCR fallback (`pytesseract`) if a page has no extractable text.
- DOCX → `python-docx`.
- TXT → direct decode.
- Images → OCR if `pytesseract`/Pillow are installed, else a placeholder string.
- Output contract (depended on by `routes/upload.py` and the frontend): `{"full_text": str, "blocks": [{"id", "text", "type", "page"}]}`.

### RAG / contextualizer

`services/contextualizer/rag.py` builds a `faiss-cpu` flat-L2 index in-process, once per process lifetime (`_rag_index` module-level singleton), over a **hardcoded** knowledge base (`LEGAL_KNOWLEDGE_BASE` in `explainer.py`, ~28 short legal-fact strings covering lease/employment/contract/financial/SaaS law). It is rebuilt from scratch (re-embedding all 28 strings) on every process start and is never persisted to disk. This is a proof-of-concept RAG implementation, not a scalable knowledge base.

### Frontend

Static site, no framework, no bundler, no package.json:
- `index.html` — single page, anchor-navigated sections (Analyze, Results, Timeline, Risk Radar, Contextualizer, About) plus a floating chat panel.
- `app.js` — vanilla JS, `fetch`-based calls to a **hardcoded production `baseURL`** (`https://plainspeak-ai.onrender.com/api`), DOM manipulation via manual `document.querySelector` wiring, no state management library.
- `style.css` — hand-written CSS.

### Known structural issues (as of this analysis)

1. **CORS misconfiguration**: `main.py` sets `allow_origins=["http://127.0.0.1:5500", "http://localhost:5500", "*"]` with `allow_credentials=True`. Per the CORS spec, browsers reject a wildcard origin when credentials are allowed — this combination doesn't behave as intended and should be fixed explicitly.
2. **Frontend/backend coupling by hardcoded URL**: `app.js`'s `baseURL` points at the deployed Render instance unconditionally; there's no environment-based config, so local frontend development against a local backend requires manually editing a source file.
3. **No environment separation**: one `.env`, one `GENAI_MODEL` default that isn't even consistent across files (`genai_client.py` defaults to `gemini-flash-latest`; `rewriter.py`'s metadata fallback string is `gemma-4-26b-a4b-it`) — this is cosmetic (only used for `meta.model` reporting) but signals no single source of truth for model configuration.
4. **No automated tests**: `test_gemini.py`, `find_best_model.py`, and root `test_script.py` are manual diagnostic/exploration scripts, not a pytest suite. There is no CI.
5. **Malformed HTML**: `frontend/index.html` line 32 has an unclosed attribute (`<header id="home" class="hero sect>`), which likely breaks layout/CSS for the hero section depending on browser error recovery.
6. **Duplicated/dead code paths**: `frontend/app.js` defines `renderRiskList()` but the actual upload-flow risk rendering is done inline in the upload handler instead of calling it — the function is unused dead code.
7. **Secrets hygiene**: `backend/migration_report.md` (untracked) contains what appears to be a real `GOOGLE_API_KEY` value in plaintext example config. `.env` itself is correctly gitignored, but this report file is not, and should be scrubbed/rotated before it's committed or shared.
8. **In-memory-only everything**: no database means no persistence, no multi-instance/horizontal-scaling support (each server instance has its own RAG index and no shared state), and no way to audit or replay past analyses.

## Proposed V1 architecture

The core request→service→Gemini pattern is sound and should be **kept**, not rewritten. V1 should harden and extend it rather than replace it.

```
┌────────────────────┐      ┌──────────────────────────────────────────────┐      ┌────────────────────┐
│  Frontend (SPA)     │─────▶│  API Gateway / FastAPI backend                │─────▶│  Gemini Developer   │
│  - env-based config  │◀────│  - Auth (API key or session-based)            │◀────│  API (existing)     │
│  - typed API client  │      │  - Rate limiting                              │      └────────────────────┘
└────────────────────┘      │  - Structured logging & request IDs           │
                             │  - Existing routers (kept), hardened:         │
                             │    upload / rewrite / map / ask / risk /      │
                             │    contextualize                              │
                             │  - New: sessions, history, export             │
                             └───────────────┬───────────────┬───────────────┘
                                             │               │
                                             ▼               ▼
                                  ┌────────────────┐  ┌───────────────────────┐
                                  │ Persistent DB   │  │ Vector store           │
                                  │ (Postgres/SQLite)│  │ (persisted embeddings, │
                                  │ - documents      │  │  replacing in-memory   │
                                  │ - analysis runs   │  │  FAISS rebuild)        │
                                  │ - users/sessions  │  └───────────────────────┘
                                  └────────────────┘
```

### Key architectural changes for V1

1. **Persistence layer**: introduce a real database (start with SQLite for simplicity, path to Postgres) to store uploaded document metadata, extracted text, and analysis results (rewrite/timeline/risk/contextualize outputs) keyed by a session or document ID. This replaces "re-send full text every request" with "upload once, reference by ID."
2. **Session/document identity**: `UploadResponse` already defines a `session_id` field in `models.py` that the current `upload.py` route doesn't actually return — wire this up so subsequent calls can pass `session_id` instead of raw text.
3. **Auth boundary**: even a minimal API-key-per-client or session-cookie mechanism, since there is currently zero access control on any endpoint (anyone with the URL can burn the Gemini quota).
4. **Config-driven frontend**: replace the hardcoded `baseURL` with a build-time or runtime-configurable value (env var, config.js, or same-origin relative path if frontend and backend are served together).
5. **Persisted vector store**: move the contextualizer's RAG index out of "rebuild in memory on every boot" into a persisted store (even a serialized FAISS index + pickle of texts checked into a data directory, or a proper vector DB) so it can grow beyond the current hardcoded 28-entry knowledge base without a code change.
6. **Centralized prompt/schema management**: introduce a single place (e.g., `services/prompts.py` or per-feature prompt templates with versioning) instead of prompts embedded as string literals in each service file, and validate AI JSON outputs against Pydantic models instead of bare `try: json.loads / except: return []`.
7. **Observability**: replace scattered `print()`/`traceback.print_exc()` calls with structured logging (e.g., Python `logging` + request-id middleware), and add basic metrics (request counts, Gemini latency/error rates) since the app is entirely dependent on a third-party API's availability.
8. **Test suite**: add pytest coverage for the deterministic parts (extractor parsing, risk keyword rules, request validation) and mock the Gemini client for service-level tests, since none of this is currently tested automatically.

This keeps the "FastAPI + centralized Gemini client + local extraction" foundation, which is a reasonable and appropriately-scoped design for this problem, while removing the specific things that make the current implementation feel like a hackathon prototype: no persistence, no auth, no tests, hardcoded config, and inconsistent error/logging discipline.
