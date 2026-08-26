# Overview

## What this project is

**PlainSpeak AI / LegalAI ("Legal Demystifier")** is a contract-analysis web app that helps non-lawyers understand legal documents. A user uploads a contract (PDF/DOCX/TXT) and the app:

1. Rewrites clauses into plain English.
2. Extracts a structural map and a timeline of key dates/obligations.
3. Scans the text for risky clauses using keyword rules + AI.
4. Answers free-form questions about the contract (single-turn Q&A + a chat widget using the same endpoint).
5. Produces a "contextualized" explanation of a selected clause, personalized by the user's role (tenant/landlord/employee/…), location, contract type, and desired tone.

It originated as a hackathon project (`genx-hackathon25`) and was later migrated off Google Cloud (Document AI, Vertex AI, service-account credentials) onto the plain **Gemini Developer API** (`google-genai` + `GOOGLE_API_KEY`), making the backend cloud-independent and easy to run locally. See `backend/migration_report.md` for the migration history.

## Current state in one paragraph

A single FastAPI backend (`backend/app`) exposes six stateless JSON endpoints under `/api`, each backed by a small service module that formats a prompt and calls a centralized Gemini client. Document parsing is fully local (PyMuPDF/python-docx/optional OCR). There is no database, no auth, and no persistent session state — the frontend (static HTML/CSS/vanilla JS, no build step) re-sends the full contract text with every request. One clause-similarity feature (the "Contextualizer") uses a tiny in-memory FAISS index over a hardcoded legal knowledge base. The app is deployed as a static site + Render-hosted API (`https://plainspeak-ai.onrender.com`).

## Who this documentation is for

This `docs/v1/` set is written for whoever picks up this codebase next — human or AI agent — to:
- Understand what exists today without re-reading every file.
- Know what's solid and should be kept as-is.
- Know what's fragile, hacky, or hackathon-grade and needs rework before a "V1" (real, production-directed) release.
- Have a concrete, prioritized task list to execute against, rather than a vague "make it production ready."

## Document index

| File | Purpose |
|---|---|
| `OVERVIEW.md` | This file — what the project is and how to read the rest of the docs. |
| `ARCHITECTURE.md` | Current system architecture, its weak points, and the proposed V1 architecture. |
| `FEATURES.md` | Feature-by-feature inventory: what exists, its quality, what's missing. |
| `TECH_STACK.md` | Current dependencies/runtime, and proposed additions/changes for V1. |
| `ROADMAP.md` | Phased plan from current state to V1. |
| `TASKS.md` | Concrete, prioritized, actionable task backlog derived from the roadmap. |

## Non-goals of this documentation pass

Per the request that produced it, this pass is **analysis and planning only** — no source code was modified. Nothing in `docs/v1/` has been implemented yet; it is a plan to work from.
