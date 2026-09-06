# backend/app/db_models.py
"""
SQLAlchemy models for the Phase 1 persistence layer (docs/v2/ARCHITECTURE.md's
core relational schema, scoped down to what Phase 1 actually needs — full
per-user login/session tokens and RBAC roles are deferred to a later phase;
auth for now is org-scoped API keys).
"""
from __future__ import annotations

import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    api_keys: Mapped[list["ApiKey"]] = relationship(back_populates="organization")


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    name: Mapped[str] = mapped_column(String(255))
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    # Per-user RBAC (docs/v2/ARCHITECTURE.md security item 5), scoped to what
    # actually exists: no login/session system, so a key -- not a logged-in
    # user -- is the unit of identity, and its role is the caller's role.
    # "admin" default keeps every key issued before this column existed at
    # full access -- non-breaking. One of "admin" | "editor" | "viewer",
    # validated in app.auth.create_api_key, not enforced at the DB level.
    role: Mapped[str] = mapped_column(String(16), default="admin", server_default="admin")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    revoked_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    organization: Mapped["Organization"] = relationship(back_populates="api_keys")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    filename: Mapped[str] = mapped_column(String(512))
    content_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_text: Mapped[str] = mapped_column(Text)
    blocks: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # ---- sensitivity tiering (app/services/sensitivity/) ----
    # `sensitivity_tier` (public|internal|confidential|privileged) is what the
    # Model Router's Class-C gate keys on -- confidential/privileged documents
    # never reach an external provider. `sensitivity_source` is "auto" (the
    # rule classifier) or "override" (an org-admin set it via
    # PUT /api/v2/documents/{id}/sensitivity).
    sensitivity_tier: Mapped[str] = mapped_column(String(16), default="internal", server_default="internal")
    sensitivity_source: Mapped[str] = mapped_column(String(16), default="auto", server_default="auto")
    sensitivity_signals: Mapped[list] = mapped_column(JSON, default=list)

    # CV quality triage (services/cv/quality.py) -- only set for PDFs with
    # scanned pages (see extractor.py); null otherwise. Previously computed
    # at upload time and returned in that one response only, never persisted.
    quality: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    action: Mapped[str] = mapped_column(String(255))
    resource: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # free-text context for actions that need it (e.g. a sensitivity override
    # reason). Nullable -- most audit rows are just method+path from guard.py.
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Populated only for a Class C (external provider) dispatch -- the "log
    # every byte sent" half of ARCHITECTURE.md's egress control (item 2),
    # written by model_router/telemetry.py::record_egress. The provider name
    # a request actually left the perimeter to; null for every other action.
    egress_target: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Which specific API key performed this action, when known -- the
    # `actor_id` ARCHITECTURE.md's schema sketch always named but the model
    # never had. Null under the default (AUTH_REQUIRED=false) org, where
    # there's no key to attribute to.
    actor_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ModelCall(Base):
    """One row per Model Router routing decision (docs/v2/AI_STACK.md "Every
    routing decision logs ...", docs/v2/MODEL_STACK.md "Observability").

    This is the join key between a served request and the eval harness's
    delta report, and the operator's cost/latency-by-hosting-class view. The
    write is fail-soft (app/services/model_router/telemetry.py) -- a DB error
    never breaks a model call. `org_id` is nullable because the router isn't
    yet threaded with request/org context (a Phase 7 follow-up)."""
    __tablename__ = "model_calls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    org_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    task: Mapped[str] = mapped_column(String(64), index=True)
    capability: Mapped[str] = mapped_column(String(32))
    sensitivity: Mapped[str] = mapped_column(String(32))
    provider: Mapped[str] = mapped_column(String(64), index=True)
    model: Mapped[str] = mapped_column(String(128))
    hosting_class: Mapped[str] = mapped_column(String(4), index=True)
    reason: Mapped[str] = mapped_column(String(255))
    latency_ms: Mapped[int] = mapped_column(Integer)
    ok: Mapped[bool] = mapped_column(default=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EvalRun(Base):
    """One row per graded eval run (docs/v2/AI_STACK.md "join to eval_runs";
    ROADMAP Phase 6). Written by app/eval/ -- the cutover gate, the task CLI.
    The join partner for `model_calls`: a routing-policy change is defensible
    only if the eval_runs for the affected tasks didn't regress."""
    __tablename__ = "eval_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task: Mapped[str] = mapped_column(String(64), index=True)
    dataset: Mapped[str] = mapped_column(String(128))
    provider: Mapped[str] = mapped_column(String(64), index=True)
    model: Mapped[str] = mapped_column(String(128))
    metric: Mapped[str] = mapped_column(String(32))
    score: Mapped[float] = mapped_column()
    n_examples: Mapped[int] = mapped_column(Integer)
    baseline_score: Mapped[float | None] = mapped_column(nullable=True)
    passed: Mapped[bool | None] = mapped_column(nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AgentTrace(Base):
    """One row per agent step in a Phase 4 case-analysis run
    (app/agents/graph.py) -- the audit trail docs/v2/AGENTS.md requires
    before any agent output can be considered defensible."""
    __tablename__ = "agent_traces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"))
    agent_name: Mapped[str] = mapped_column(String(100))
    step_no: Mapped[int] = mapped_column(Integer)
    input_summary: Mapped[str] = mapped_column(Text)
    output_summary: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CaseAnalysis(Base):
    """One row per `run_and_persist_analysis()` call -- the run-level outcome
    (`AgentTrace` above is per-step). Phase 7's human-in-the-loop review
    queue needs this: `needs_human_review` was computed and returned in the
    HTTP response every time but never persisted anywhere, so nothing could
    ever list "which analyses still need a human to look at them" -- the
    exact same computed-then-discarded shape as `Document.quality` before it
    was persisted (see CLAUDE.md's sensitivity-tiering section for the
    pattern this follows)."""
    __tablename__ = "case_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"))
    analysis_mode: Mapped[str] = mapped_column(String(32))
    plan: Mapped[list] = mapped_column(JSON, default=list)
    summary: Mapped[str] = mapped_column(Text)
    faithfulness_ok: Mapped[bool] = mapped_column(Boolean, default=True)
    faithfulness_method: Mapped[str] = mapped_column(String(32), default="lexical_fallback")
    unsupported_claims: Mapped[list] = mapped_column(JSON, default=list)
    invalid_citation_numbers: Mapped[list] = mapped_column(JSON, default=list)
    needs_human_review: Mapped[bool] = mapped_column(Boolean, default=False)
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    reviewed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewer_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
