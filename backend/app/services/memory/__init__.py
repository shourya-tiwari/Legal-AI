# backend/app/services/memory/__init__.py
"""
The Memory Service (docs/v2/AGENTS.md's Memory system, Phase 7):

  session.py       -- short-term, TTL-bound, Redis-backed (the last N chat
                       turns, a currently-open document's state).
  episodic.py       -- per-document, across-sessions, backed by the
                       CaseAnalysis table that already exists (not a new
                       table -- that data already IS this tier's structured
                       half).
  consolidation.py -- promotes episodic memory into semantic (cross-
                       document, per-org) memory, with a privacy-tier gate:
                       a `privileged`-tier document's data is never
                       promoted, unconditionally (no opt-in override built).

No scheduler runs consolidation.py automatically -- there's no job-queue/
cron system in this codebase yet (docs/v2/TASKS.md's Postgres-backed event
queue is separately not-yet-built). Callable directly today.
"""
