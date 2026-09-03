# backend/app/services/model_router/telemetry.py
"""
Routing-decision telemetry (docs/v2/AI_STACK.md "Every routing decision logs
{task, sensitivity, provider, model, policy_version, reason}", docs/v2/
MODEL_STACK.md "Observability").

Two sinks, both entirely fail-soft -- neither may ever break a model call,
exactly like app/rate_limit.py's Redis handling and app/services/kg/client.py's
Memgraph handling:

  1. the `model_calls` table (app/db_models.py) -- the durable record joined to
     the eval delta report and the operator cost/latency view. Gated by
     Settings.MODEL_CALL_LOGGING.
  2. an OpenTelemetry span -- emitted only when app/observability.py has
     successfully initialised a tracer (Settings.OTEL_ENABLED + an OTLP
     endpoint + the packages installed).
"""
from __future__ import annotations

import logging
from typing import Optional

from app.config import get_settings

from .types import RoutingDecision

logger = logging.getLogger("legalai.model_router.telemetry")


def record_call(
    decision: RoutingDecision,
    *,
    latency_ms: int,
    ok: bool,
    error: Optional[str] = None,
) -> None:
    """Persist one routing decision. Swallows every exception."""
    settings = get_settings()
    if settings.MODEL_CALL_LOGGING:
        try:
            _persist(decision, latency_ms=latency_ms, ok=ok, error=error)
        except Exception as e:  # pragma: no cover - defensive, never propagate
            logger.debug("model_calls persistence skipped (%s)", e)
    try:
        _span(decision, latency_ms=latency_ms, ok=ok, error=error)
    except Exception as e:  # pragma: no cover
        logger.debug("model_calls span skipped (%s)", e)


def _persist(decision: RoutingDecision, *, latency_ms: int, ok: bool,
             error: Optional[str]) -> None:
    from app.db import SessionLocal
    from app.db_models import ModelCall

    row = ModelCall(
        task=decision.task,
        capability=decision.capability,
        sensitivity=decision.sensitivity.value,
        provider=decision.provider,
        model=decision.model,
        hosting_class=decision.hosting_class.value,
        reason=decision.reason,
        latency_ms=latency_ms,
        ok=ok,
        error=(error or None) if not ok else None,
    )
    db = SessionLocal()
    try:
        db.add(row)
        db.commit()
    finally:
        db.close()


def _span(decision: RoutingDecision, *, latency_ms: int, ok: bool,
          error: Optional[str]) -> None:
    from app.observability import get_tracer

    tracer = get_tracer()
    if tracer is None:
        return
    with tracer.start_as_current_span("model_router.route") as span:
        for k, v in decision.as_log_dict().items():
            span.set_attribute(f"gen_ai.router.{k}", str(v))
        span.set_attribute("gen_ai.router.latency_ms", latency_ms)
        span.set_attribute("gen_ai.router.ok", ok)
        if error and not ok:
            span.set_attribute("gen_ai.router.error", error[:500])
