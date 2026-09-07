# backend/app/services/durable/__init__.py
"""
Durable execution (docs/v2/ROADMAP.md Phase 7 "Durable execution & Memory
Service"). Empty on purpose: importing this package must not require
`dbos` or a Postgres connection -- only `dbos_engine` (imported lazily by
callers, gated on `Settings.DURABLE_EXECUTION_ENABLED`) does.
"""
