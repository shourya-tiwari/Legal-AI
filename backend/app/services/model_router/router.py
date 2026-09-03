# backend/app/services/model_router/router.py
"""
The Router: the single point every service calls to reach a model. Services
name a *task* and a *sensitivity*; the router resolves that to a
(provider, model) binding via the routing policy, walks the candidate chain
by health, logs the decision, and returns a provider-neutral result.

No service imports a provider. No service names a vendor. (docs/v2/AI_STACK.md)
"""
from __future__ import annotations

import logging
import time
from functools import lru_cache
from typing import List, Optional, Sequence

from . import telemetry
from .base import ModelProvider
from .policy import get_policy
from .registry import get_provider
from .types import (
    EmbedRequest,
    EmbedResult,
    GenerateRequest,
    GenerateResult,
    HostingClass,
    ModelRouterError,
    ProviderUnavailable,
    RerankRequest,
    RerankResult,
    RoutingDecision,
    SensitivityTier,
)

logger = logging.getLogger("legalai.model_router")


class Router:
    def _resolve_chain(self, task: str, capability: str,
                       sensitivity: SensitivityTier) -> List[ModelProvider]:
        policy = get_policy()
        names = policy.candidates(task, sensitivity)
        chain: List[ModelProvider] = []
        for name in names:
            provider = get_provider(name)
            if provider is None:
                continue
            if not provider.supports(capability):
                continue
            chain.append(provider)
        return chain

    def _pick_and_call(self, task: str, capability: str, sensitivity: SensitivityTier,
                       call):
        chain = self._resolve_chain(task, capability, sensitivity)
        if not chain:
            raise ModelRouterError(
                f"No provider available for task '{task}' (capability '{capability}', "
                f"sensitivity '{sensitivity.value}'). "
                f"Configure a self-hosted provider (LLM_BASE_URL / EMBEDDING_BASE_URL / "
                f"the sentence-transformers extra), or enable an external provider."
            )

        considered = [p.name for p in chain]
        errors = []
        for provider in chain:
            if not provider.is_available():
                errors.append(f"{provider.name}: not available")
                continue
            start = time.perf_counter()
            try:
                result, model, hclass = call(provider)
            except (ProviderUnavailable, NotImplementedError) as e:
                errors.append(f"{provider.name}: {e}")
                continue
            latency_ms = int((time.perf_counter() - start) * 1000)

            reason = "primary" if provider is chain[0] else f"fell through from {chain[0].name}"
            decision = RoutingDecision(
                task=task, capability=capability, sensitivity=sensitivity,
                provider=provider.name, model=model, hosting_class=hclass,
                reason=reason, candidates_considered=considered,
            )
            telemetry.record_call(decision, latency_ms=latency_ms, ok=True)
            if hclass.value == "C":
                logger.warning(
                    "ROUTE -> EXTERNAL provider %s for task '%s' (%s). "
                    "This is the Phase 5->6 interim; self-hosted generation becomes the "
                    "default in Phase 6. decision=%s",
                    provider.name, task, reason, decision.as_log_dict(),
                )
            else:
                logger.info("ROUTE %s", decision.as_log_dict())
            return result, decision

        err_msg = f"All providers for task '{task}' failed: {'; '.join(errors)}"
        telemetry.record_call(
            RoutingDecision(
                task=task, capability=capability, sensitivity=sensitivity,
                provider="(none)", model="-", hosting_class=HostingClass.A,
                reason="no candidate served the request",
                candidates_considered=considered,
            ),
            latency_ms=0, ok=False, error=err_msg,
        )
        raise ModelRouterError(err_msg)

    # ---- public API ----

    def generate(self, req: GenerateRequest) -> GenerateResult:
        def _call(p: ModelProvider):
            r = p.generate(req)
            return r, r.model, r.hosting_class

        result, _decision = self._pick_and_call(req.task, "generate", req.sensitivity, _call)
        return result

    def embed(self, req: EmbedRequest) -> EmbedResult:
        def _call(p: ModelProvider):
            r = p.embed(req)
            return r, r.model, r.hosting_class

        result, _decision = self._pick_and_call(req.task, "embed", SensitivityTier.INTERNAL, _call)
        return result

    def rerank(self, req: RerankRequest) -> RerankResult:
        def _call(p: ModelProvider):
            r = p.rerank(req)
            return r, "-", r.hosting_class

        result, _decision = self._pick_and_call(req.task, "rerank", SensitivityTier.INTERNAL, _call)
        return result


@lru_cache
def get_router() -> Router:
    return Router()
