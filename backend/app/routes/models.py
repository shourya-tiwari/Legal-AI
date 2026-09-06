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

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import OrgContext
from app.config import get_settings
from app.db import get_db
from app.db_models import EvalRun
from app.guard import api_guard
from app.models import EvalRunsResponse, EvalRunSummary, ModelProviderStatus, ModelsStatusResponse
from app.services.model_router.policy import get_policy
from app.services.model_router.registry import get_registry

logger = logging.getLogger("legalai.routes.models")

router = APIRouter(tags=["models"])


@router.get("/models/status", response_model=ModelsStatusResponse, summary="Model Router status")
def models_status(org: OrgContext = Depends(api_guard)) -> ModelsStatusResponse:
    settings = get_settings()
    providers = []
    for name, provider in get_registry().items():
        try:
            card = provider.describe()
            available = bool(provider.is_available())
        except Exception as e:  # a provider probe must never 500 this endpoint
            logger.warning("provider %s describe/is_available failed: %s", name, e)
            continue
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
