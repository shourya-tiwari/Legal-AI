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

from app.auth import OrgContext
from app.config import get_settings
from app.guard import api_guard
from app.models import ModelProviderStatus, ModelsStatusResponse
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
