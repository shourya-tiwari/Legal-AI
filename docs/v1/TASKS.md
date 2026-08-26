# Tasks

Concrete, actionable backlog derived from `ROADMAP.md`. Priority key:
- **P0** — should be done before anything else; bug, security, or correctness issue.
- **P1** — needed for V1; blocks or significantly de-risks later work.
- **P2** — needed for V1 completeness but not blocking.
- **P3** — stretch / post-V1-core.

Each task lists the file(s) most directly involved, so implementation can start without a separate discovery pass.

## P0 — Immediate fixes

| # | Task | Files |
|---|---|---|
| 1 | Rotate/revoke the Gemini API key exposed in `backend/migration_report.md`; scrub the file or replace the example value with a placeholder before it's ever committed | `backend/migration_report.md` |
| 2 | Fix CORS: remove `"*"` from `allow_origins` while `allow_credentials=True` is set, or drop `allow_credentials` if wildcard origins are genuinely needed | `backend/app/main.py` |
| 3 | Fix malformed `<header>` attribute (missing closing quote on `class="hero sect`) | `frontend/index.html` (line 32) |
| 4 | Remove dead `renderRiskList()` function, or replace the duplicated inline risk-rendering logic in the upload handler with a call to it | `frontend/app.js` |
| 5 | Reconcile `GENAI_MODEL` default inconsistency between `genai_client.py` (`gemini-flash-latest`) and `rewriter.py`'s metadata fallback (`gemma-4-26b-a4b-it`) | `backend/app/services/genai_client.py`, `backend/app/services/rewriter.py` |

## P1 — Foundation for V1

### Testing & CI
| # | Task | Files |
|---|---|---|
| 6 | Add `pytest` + `pytest-asyncio` to `requirements.txt` (dev extras) | `backend/requirements.txt` |
| 7 | Write unit tests for `extractor.py` against small sample PDF/DOCX/TXT fixtures (happy path + unsupported-type fallback) | `backend/app/services/extractor.py` |
| 8 | Write unit tests for `risk_radar/rules.py`'s `find_keyword_flags`/`normalize_text` | `backend/app/services/risk_radar/rules.py` |
| 9 | Write route-level tests for all 6 endpoints using FastAPI's `TestClient`, mocking `genai_client.generate_content`/`embed_content` | `backend/app/routes/*.py` |
| 10 | Add a GitHub Actions workflow that installs deps and runs `pytest` on push/PR | new: `.github/workflows/test.yml` |

### Logging & config
| # | Task | Files |
|---|---|---|
| 11 | Replace `print()` calls in `genai_client.py`, `routes/rewrite.py`, `routes/ask.py`, `routes/map.py`, and `contextualizer/rag.py`/`explainer.py` with `logging` calls | listed files |
| 12 | Introduce `pydantic-settings`-based config object (`GOOGLE_API_KEY`, `GENAI_MODEL`, CORS origins, etc.) as the single source of truth, replacing scattered `os.getenv` calls | new: `backend/app/config.py`; update `genai_client.py`, `rewriter.py`, `main.py` |

### Consistency cleanup
| # | Task | Files |
|---|---|---|
| 13 | Move `risk_radar.py`'s inline `ClauseIn` model into `app/models.py` as `RiskScanRequest`; add a proper `RiskScanResponse` model instead of returning a bare dict | `backend/app/routes/risk_radar.py`, `backend/app/models.py` |
| 14 | Decide the fate of `AskResponse.references` (populate it or remove it) | `backend/app/models.py`, `backend/app/services/chatbot.py` |

## P1 — Frontend/backend decoupling

| # | Task | Files |
|---|---|---|
| 15 | Replace hardcoded `baseURL` in `app.js` with a configurable value (e.g., a small `config.js` loaded before `app.js`, or relative paths if co-hosted) | `frontend/app.js`, new: `frontend/config.js`, `frontend/index.html` |
| 16 | Document full local dev setup (backend `.env` + `uvicorn`, frontend config + `npx serve`) in root `README.md` | `README.md` |

## P2 — Persistence & sessions

| # | Task | Files |
|---|---|---|
| 17 | Choose and add a database dependency (SQLite via `sqlmodel` recommended for minimal footprint) | `backend/requirements.txt` |
| 18 | Design and create tables/models for documents, analysis results, and sessions | new: `backend/app/db.py`, `backend/app/db_models.py` |
| 19 | Update `POST /api/upload` to persist the document and return the `session_id` already defined (but unused) in `UploadResponse` | `backend/app/routes/upload.py`, `backend/app/models.py` |
| 20 | Update `rewrite`/`map`/`ask`/`risk`/`contextualize` routes to accept a `session_id`/document reference as an alternative to raw text, looking up persisted text | all `backend/app/routes/*.py` |
| 21 | Persist the Contextualizer's FAISS index + source texts to disk instead of rebuilding on every process start | `backend/app/services/contextualizer/rag.py` |

## P2 — Access control & abuse protection

| # | Task | Files |
|---|---|---|
| 22 | Add API-key-header (or session-based) auth dependency and apply it to all routers | new: `backend/app/auth.py`; update `main.py` router registrations |
| 23 | Add rate limiting (e.g., `slowapi`) per API key/client | `backend/requirements.txt`, `backend/app/main.py` |
| 24 | Add file size / page-count limits to `/api/upload` with a clear 4xx error when exceeded | `backend/app/routes/upload.py`, `backend/app/services/extractor.py` |

## P2 — Close feature/promise gaps

| # | Task | Files |
|---|---|---|
| 25 | Implement the Risk Radar spider/radar chart visualization on the frontend (README already promises this) | `frontend/app.js`, `frontend/index.html`, `frontend/style.css` |
| 26 | Add multi-turn conversational memory to the chat widget (depends on task 18/19 for persisting history per session) | `backend/app/services/chatbot.py`, `backend/app/models.py`, `frontend/app.js` |
| 27 | Wire up the `interests` field in the Contextualizer UI (currently hardcoded `null`) | `frontend/index.html`, `frontend/app.js` |
| 28 | Resolve the `"advanced"` rewrite mode gap: either implement it (`models.py` currently restricts `mode` to `"layman"` only) or update README/UI copy to stop implying it exists | `backend/app/models.py`, `backend/app/services/rewriter.py`, `README.md` |
| 29 | Add export/download (text/JSON/PDF) for rewrite, timeline, and risk results | `frontend/app.js`, possibly new backend export endpoint |

## P3 — AI-layer quality (stretch)

| # | Task | Files |
|---|---|---|
| 30 | Extract one shared, tested chunking utility to replace rewriter's naive char-window split and timeline's hierarchical split | new: `backend/app/services/chunking.py`; update `rewriter.py`, `timeline.py` |
| 31 | Merge timeline's two per-chunk Gemini calls (structure + timeline) into a single combined-schema call | `backend/app/services/timeline.py` |
| 32 | Add retry/repair for malformed JSON responses from Gemini instead of silently returning `[]` | `backend/app/services/timeline.py`, `backend/app/services/risk_radar/detector.py` |
| 33 | Expand the Contextualizer's legal knowledge base with sourced/cited entries, or add an explicit non-authoritative disclaimer in the UI | `backend/app/services/contextualizer/explainer.py`, `frontend/index.html` |
| 34 | Add response caching for repeated identical rewrite/analysis requests | `backend/app/services/rewriter.py` and/or a shared cache layer |

## Suggested execution order

Work top-to-bottom within each priority tier; P0 items are independent and can be done in any order or in parallel. Within P1, testing/CI (6–10) should land before the config/consistency work (11–14) so those changes are covered by tests as they're made. Persistence (17–21) is a prerequisite for both auth-by-session and conversational memory, so it should be scheduled before P2's other two groups where team capacity allows.
