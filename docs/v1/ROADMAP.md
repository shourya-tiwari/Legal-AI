# Roadmap: Current State → V1

This roadmap sequences the work in `FEATURES.md`/`ARCHITECTURE.md`/`TECH_STACK.md` into phases. Each phase is meant to leave the app in a working, deployable state — nothing here requires a big-bang rewrite. See `TASKS.md` for the concrete task backlog behind each phase.

## Phase 0 — Stabilize what exists (hygiene, no new features)
**Goal**: fix known bugs and hygiene issues before building anything new on top of them.

- Scrub/rotate the API key exposed in `backend/migration_report.md` and add it to `.gitignore` handling if the file is kept.
- Fix CORS config (`allow_origins` wildcard + `allow_credentials=True` conflict).
- Fix the malformed HTML attribute in `frontend/index.html`.
- Remove the dead `renderRiskList()` function in `app.js` (or wire it in and remove the duplicated inline logic — pick one).
- Reconcile the `GENAI_MODEL` default string that differs between `genai_client.py` and `rewriter.py`'s metadata fallback.
- Move `routes/risk_radar.py`'s inline `ClauseIn` model into `app/models.py` for consistency with every other route.

**Exit criteria**: no known bugs from `ARCHITECTURE.md`'s "known structural issues" list remain; app behaves identically to today from a user's perspective, just cleaner underneath.

## Phase 1 — Safety net (tests + logging)
**Goal**: make it possible to change things confidently.

- Add `pytest` with unit tests for deterministic logic: `extractor.py` parsing (given sample small PDF/DOCX/TXT fixtures), `risk_radar/rules.py` keyword matching, Pydantic model validation edge cases.
- Add route-level tests using a mocked `genai_client.generate_content`/`embed_content` so tests don't hit the real Gemini API or require a key.
- Replace `print()`/`traceback.print_exc()` calls with `logging` calls at appropriate levels.
- Add a minimal GitHub Actions workflow: install deps, run tests, on push/PR.

**Exit criteria**: `pytest` runs green in CI on every push; a regression in extraction or risk-keyword logic would be caught automatically.

## Phase 2 — Config & environment correctness
**Goal**: decouple frontend/backend and centralize configuration so the app is deployable to more than one fixed environment.

- Introduce `pydantic-settings` (or equivalent) for backend env config, with one authoritative `GENAI_MODEL` default.
- Replace `app.js`'s hardcoded `baseURL` with a configurable value (env-injected `config.js`, or same-origin relative paths if frontend/backend are served together).
- Document local-dev setup end-to-end (backend `.env`, frontend config, running both together) in the root `README.md`.

**Exit criteria**: a new developer can run the full stack locally (frontend talking to local backend) by following the README, with zero source edits.

## Phase 3 — Persistence & sessions
**Goal**: stop re-sending full contract text on every request; give users something that survives a page reload.

- Add a database (start with SQLite) with tables for: documents (raw text, filename, upload timestamp), analysis results (rewrite/timeline/risk/contextualize outputs keyed by document ID), and a lightweight session concept.
- Wire up the `session_id` field already defined in `models.py`'s `UploadResponse` (currently unused) — `POST /api/upload` returns a real session/document ID; other endpoints accept either that ID or raw text (backward compatible).
- Persist the Contextualizer's FAISS index + source texts to disk instead of rebuilding from scratch on every process start.

**Exit criteria**: a user can upload a document, close the tab, and (given the session ID or a login) come back to see prior results without re-uploading.

## Phase 4 — Access control & abuse protection
**Goal**: the API is no longer open to anyone who finds the URL.

- Add a minimal auth layer (API key header to start; session/cookie-based if user accounts are introduced in this phase or deferred to Phase 6).
- Add rate limiting per client/API key to protect Gemini quota.
- Add file size / page count limits on `/api/upload`.

**Exit criteria**: unauthenticated requests are rejected; a single client cannot exhaust the shared Gemini quota through rapid repeated calls.

## Phase 5 — Feature completion (close the promise/implementation gap)
**Goal**: deliver the features the product already claims to have (per the README) or clearly implies via naming, but doesn't yet.

- Implement the actual Risk Radar spider/radar chart visualization on the frontend (README already describes this).
- Add real multi-turn conversational memory to the chat widget (currently stateless single-turn Q&A per message) — likely by persisting a message history per session (depends on Phase 3) and including relevant prior turns in the prompt.
- Populate `AskResponse.references` with actual clause excerpts/citations (field exists, is currently always empty).
- Wire up the `interests` field in the Contextualizer's `UserContext` (currently hardcoded to `null` in the frontend).
- Decide on and implement the advertised-but-missing `"advanced"` rewrite mode (README documents it; `models.py` currently only allows `"layman"`), or update the README/UI to stop implying it exists.
- Add export (download as text/PDF/JSON) for rewrite/timeline/risk results.

**Exit criteria**: no meaningful gap remains between what the product claims/implies (README, endpoint naming, UI copy) and what it actually does.

## Phase 6 — Scale & quality of the AI layer (stretch, post-V1-core)
**Goal**: improve robustness and quality of the AI-dependent features once the above foundation is in place.

- Consolidate rewriter's naive char-window chunking and timeline's hierarchical chunking into one shared, tested chunking utility.
- Combine the timeline endpoint's two separate Gemini calls per chunk (structure + timeline) into one schema-validated call to cut latency/cost.
- Add retry/repair logic for malformed JSON responses from Gemini (currently silently falls back to empty results) with visible error surfacing.
- Grow the Contextualizer's legal knowledge base with actual sourced/cited content (or clearly disclaim it as non-authoritative in the UI, not just in the model prompt).
- Add response caching for repeated rewrite/analysis requests on identical text.

**Exit criteria**: the AI-dependent features are measurably more reliable (fewer silent empty-result failures) and cheaper to run at the same usage volume.

## Sequencing rationale

Phases 0–2 are ordered first because they're cheap, low-risk, and make every subsequent phase easier (you don't want to build persistence on top of a codebase with no tests, or fix bugs under CI you haven't set up yet). Phase 3 (persistence) is a prerequisite for Phase 4's per-user rate limiting and Phase 5's conversational memory, so it's placed before both. Phase 6 is explicitly a "stretch" phase — none of it blocks calling the app "V1," but all of it meaningfully improves quality once the foundation exists.
