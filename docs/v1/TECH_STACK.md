# Tech Stack

## Current stack

### Backend (`backend/`)
| Component | Choice | Notes |
|---|---|---|
| Language | Python 3.13 | inferred from `__pycache__/*.cpython-313.pyc` |
| Web framework | FastAPI 0.116.1 | `backend/app/main.py` |
| ASGI server | Uvicorn 0.35.0 | run via `uvicorn app.main:app --reload` |
| Validation | Pydantic 2.11.7 | schemas in `app/models.py` |
| Env config | python-dotenv 1.1.1 | loads `backend/.env` |
| AI provider | `google-genai` 1.32.0 | Gemini Developer API (not Vertex AI) |
| PDF parsing | PyMuPDF (`fitz`) 1.28.0 | text + block extraction, per-page OCR fallback |
| DOCX parsing | python-docx 1.2.0 | paragraph-level extraction |
| OCR (optional) | pytesseract + Pillow | soft dependency, not in `requirements.txt` — must be installed separately, plus the Tesseract binary itself |
| Vector search | faiss-cpu 1.12.0 | in-memory flat L2 index for the Contextualizer RAG |
| Numerics | numpy 2.3.2 | embedding vector handling |
| HTTP clients | requests 2.32.5, httpx 0.28.1 | used by diagnostics / dependency of other libs |
| File uploads | python-multipart 0.0.20 | required by FastAPI's `UploadFile` |
| Persistence | **none** | `app/storage.py` in-memory dict, effectively unused |
| Auth | **none** | |
| Testing | **none** (pytest not a dependency) | manual scripts only |

### Frontend (`frontend/`)
| Component | Choice | Notes |
|---|---|---|
| Markup/style | Static HTML + hand-written CSS | `index.html`, `style.css` |
| Scripting | Vanilla JavaScript (ES6+) | `app.js`, no framework |
| Build tooling | **none** | no `package.json`, no bundler; served via `npx serve .` or opened directly |
| HTTP | native `fetch` | hardcoded `baseURL` pointing at the deployed Render backend |

### Deployment (inferred from README/code)
- Backend: Render (`https://plainspeak-ai.onrender.com`).
- Frontend: static hosting, URL referenced in root `README.md` (`https://plainspeakai.onrender.com/`).
- No containerization (no `Dockerfile`/`docker-compose.yml` present).
- No infrastructure-as-code.

### Ad hoc / diagnostic scripts (not part of the app runtime)
- `backend/test_gemini.py` — 7-step network/auth/SDK diagnostic for the Gemini API.
- `backend/find_best_model.py` — lists models available to the configured API key.
- `test_script.py` (repo root, 3 lines) — trivial scratch script.
- `backend/migration_report.md` — historical record of the GCP → Gemini Developer API migration (contains an example API key value that should be scrubbed — see `ARCHITECTURE.md`).

## Proposed V1 stack changes

The guiding principle: **add only what closes a concrete gap identified in `FEATURES.md`/`ARCHITECTURE.md`**, keep the stack as small as the current one where possible, and avoid introducing a second AI provider or a heavyweight frontend framework unless the roadmap explicitly calls for it.

### Backend additions
| Need | Proposed addition | Why |
|---|---|---|
| Persistence | SQLite via `sqlmodel` or plain `sqlite3`, with a path to Postgres later | Lightweight, no new infra required to start; matches the project's current "runs locally with one `.env`" simplicity |
| Auth | Simple API-key header check (FastAPI dependency) or session cookie, not a full OAuth stack initially | Matches current scope — this is not a multi-tenant SaaS yet |
| Rate limiting | `slowapi` (Starlette/FastAPI-compatible) or a hand-rolled token bucket dependency | Protects Gemini quota from abuse now that auth exists |
| Testing | `pytest` + `pytest-asyncio` + `httpx`'s `TestClient`/`ASGITransport` for route tests; mock `genai_client.generate_content` for service tests | Zero automated coverage today is the single biggest risk in the repo |
| Logging | Python stdlib `logging` configured once in `main.py`, replacing scattered `print()`/`traceback.print_exc()` | Needed for any real debugging/observability once deployed beyond a demo |
| Config validation | `pydantic-settings` for typed env var loading (currently raw `os.getenv` calls scattered across `genai_client.py`, `rewriter.py`, etc. with inconsistent defaults) | Fixes the `GENAI_MODEL` default-inconsistency issue noted in `ARCHITECTURE.md` |
| Vector persistence | Serialize the FAISS index + texts to disk (or migrate to a lightweight persisted vector store) instead of rebuilding in memory on every boot | Needed once the knowledge base grows beyond the current 28 hardcoded strings |

### Frontend additions
| Need | Proposed addition | Why |
|---|---|---|
| Config | A small `config.js` (or build-time env substitution) replacing the hardcoded `baseURL` | Unblocks local frontend development against a local backend without editing source |
| Charting | A lightweight charting lib (e.g., Chart.js) *only if* the Risk Radar spider-chart visualization is implemented (see `ROADMAP.md`) | The README already promises this visualization; currently unimplemented |
| Framework | **Not recommended yet.** The current vanilla JS is small (~330 lines) and functional; introducing React/Vue is only justified once multi-turn chat state, session/history views, and auth flows meaningfully increase UI complexity | Avoid premature complexity |

### Things deliberately not changed
- **AI provider**: stay on `google-genai` / Gemini Developer API — the migration to this was intentional and recent (see `migration_report.md`); no reason to reintroduce Vertex AI or add a second provider without a concrete driver.
- **Document parsing libs**: PyMuPDF/python-docx are appropriate, standard choices for this use case — keep them.
- **No ORM lock-in yet**: start with the lightest persistence option (SQLite) rather than committing to a specific cloud database before usage patterns are known.
