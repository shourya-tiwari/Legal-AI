# backend/app/routes/models.py
"""
Model Router status endpoint (docs/v2/AI_STACK.md, ROADMAP Phase 5/7 "Model
status panel").

`GET /api/models/status` -- the operator's view of their own inference layer:
which providers are registered, which are actually reachable right now, what
hosting class each is, and whether any of them leaves the deployment
perimeter. This is also the fastest way to confirm a freshly-bootstrapped
self-hosted stack (Ollama + TEI) is live.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import OrgContext
from app.config import get_settings
from app.db import get_db
from app.db_models import EvalRun, ModelCall, ModelPolicyOverride
from app.guard import api_guard, require_role
from app.models import (
    ClassCOverrideItem,
    ClassCOverridesResponse,
    DeltaReportResponse,
    DeltaReportRow,
    EvalRunsResponse,
    EvalRunSummary,
    ModelProviderStatus,
    ModelsStatusResponse,
    SetClassCOverrideRequest,
)
from app.services.model_router.overrides import clear_class_c_override, set_class_c_override
from app.services.model_router.policy import get_policy
from app.services.model_router.registry import get_registry

_RECENT_LATENCY_SAMPLE = 20

logger = logging.getLogger("legalai.routes.models")

router = APIRouter(tags=["models"])


def _recent_latency(db: Session, provider_own_name: str) -> tuple[Optional[float], int]:
    """Average latency_ms over this provider's most recent successful
    model_calls rows -- the "latency" half of Phase 7's "Model status panel:
    queue depth/latency" line. Queue depth has no backend equivalent (no job
    queue exists in this codebase to have depth); latency was already being
    recorded on every routing decision (model_router/telemetry.py) and
    simply never aggregated for this endpoint.

    Takes the provider's *own* name (`card.name`, e.g. "hashing-embed"), not
    the registry alias (e.g. "local-embed-hash") the rest of this route
    exposes as `ModelProviderStatus.name` -- `model_calls.provider` is
    written from `RoutingDecision.provider`, which is always the provider's
    own name (router.py), so that's the only value that will ever match."""
    rows = (
        db.query(ModelCall.latency_ms)
        .filter(ModelCall.provider == provider_own_name, ModelCall.ok.is_(True))
        .order_by(ModelCall.id.desc())
        .limit(_RECENT_LATENCY_SAMPLE)
        .all()
    )
    if not rows:
        return None, 0
    latencies = [r[0] for r in rows]
    return round(sum(latencies) / len(latencies), 1), len(latencies)


@router.get("/models/status", response_model=ModelsStatusResponse, summary="Model Router status")
def models_status(org: OrgContext = Depends(api_guard), db: Session = Depends(get_db)) -> ModelsStatusResponse:
    settings = get_settings()
    providers = []
    for name, provider in get_registry().items():
        try:
            card = provider.describe()
            available = bool(provider.is_available())
        except Exception as e:  # a provider probe must never 500 this endpoint
            logger.warning("provider %s describe/is_available failed: %s", name, e)
            continue
        avg_latency, sample_count = _recent_latency(db, card.name)
        providers.append(
            ModelProviderStatus(
                # the routing alias (what routing.yaml + the ROUTE logs use),
                # not card.name -- two aliases can share one provider class
                name=name,
                hosting_class=card.hosting_class.value,
                capabilities=list(card.capabilities),
                available=available,
                leaves_perimeter=card.leaves_perimeter,
                models=list(card.models),
                note=card.note,
                recent_avg_latency_ms=avg_latency,
                recent_call_count=sample_count,
            )
        )
    return ModelsStatusResponse(
        providers=providers,
        policy_version=get_policy().version,
        external_providers_enabled=settings.EXTERNAL_PROVIDERS_ENABLED,
        strict_local_only=settings.STRICT_LOCAL_ONLY,
    )


@router.get("/models/eval-runs", response_model=EvalRunsResponse,
            summary="Eval scores behind the routing policy (most recent per task/provider)")
def eval_runs(org: OrgContext = Depends(api_guard), db: Session = Depends(get_db)) -> EvalRunsResponse:
    # eval_runs isn't org-scoped (a system-level eval artifact, not tenant
    # data) -- `org` is only here so this endpoint sits behind api_guard
    # like every other route.
    # created_at can tie within the same commit (SQLite's CURRENT_TIMESTAMP
    # resolution) -- id.desc() as a stable tiebreaker so "most recent" always
    # means "most recently inserted", not an arbitrary tie order.
    rows = db.query(EvalRun).order_by(EvalRun.created_at.desc(), EvalRun.id.desc()).all()
    latest_per_key: dict[tuple[str, str], EvalRun] = {}
    for row in rows:
        key = (row.task, row.provider)
        if key not in latest_per_key:  # rows are already newest-first
            latest_per_key[key] = row
    summaries = [
        EvalRunSummary(
            task=r.task, provider=r.provider, model=r.model, metric=r.metric, score=r.score,
            n_examples=r.n_examples, baseline_score=r.baseline_score, passed=r.passed,
            notes=r.notes, created_at=r.created_at.isoformat() if r.created_at else None,
        )
        for r in latest_per_key.values()
    ]
    summaries.sort(key=lambda s: (s.task, s.provider))
    return EvalRunsResponse(runs=summaries)


@router.get("/models/class-c-overrides", response_model=ClassCOverridesResponse,
            summary="List active per-task Class C overrides")
def list_class_c_overrides(org: OrgContext = Depends(api_guard), db: Session = Depends(get_db)) -> ClassCOverridesResponse:
    rows = db.query(ModelPolicyOverride).order_by(ModelPolicyOverride.task.asc()).all()
    return ClassCOverridesResponse(overrides=[
        ClassCOverrideItem(task=r.task, class_c_disabled=r.class_c_disabled, reason=r.reason,
                           updated_at=r.updated_at.isoformat() if r.updated_at else None)
        for r in rows
    ])


@router.put("/models/class-c-overrides/{task}", response_model=ClassCOverrideItem,
            summary="Set a per-task Class C override (admin only)")
def set_class_c_override_route(
    task: str, body: SetClassCOverrideRequest,
    org: OrgContext = Depends(require_role("admin")), db: Session = Depends(get_db),
) -> ClassCOverrideItem:
    set_class_c_override(task, body.class_c_disabled, body.reason)
    row = db.query(ModelPolicyOverride).filter_by(task=task).first()
    return ClassCOverrideItem(task=row.task, class_c_disabled=row.class_c_disabled, reason=row.reason,
                              updated_at=row.updated_at.isoformat() if row.updated_at else None)


@router.delete("/models/class-c-overrides/{task}", summary="Remove a per-task Class C override (admin only)")
def clear_class_c_override_route(task: str, org: OrgContext = Depends(require_role("admin"))) -> dict:
    existed = clear_class_c_override(task)
    if not existed:
        raise HTTPException(status_code=404, detail=f"No override set for task {task!r}")
    return {"cleared": True, "task": task}


@router.post("/models/delta-report", response_model=DeltaReportResponse,
            summary="Run the self-hosted-vs-external delta report (admin only -- makes real provider calls)")
def run_delta_report(org: OrgContext = Depends(require_role("admin"))) -> DeltaReportResponse:
    # A POST, not a GET: this makes real generation calls against local-llm
    # and gemini for every fixture task (app/eval/delta_report.py) -- an
    # explicit diagnostic action with real latency/cost, not a passive
    # status read like the rest of this file.
    from app.eval.delta_report import build_report

    rows = build_report()
    return DeltaReportResponse(rows=[
        DeltaReportRow(task=r.task, local_ms=r.local_ms, external_ms=r.external_ms,
                       local_len=r.local_len, external_len=r.external_len,
                       agreement_f1=r.agreement_f1, local_error=r.local_error,
                       external_error=r.external_error)
        for r in rows
    ])
