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
from typing import Dict, Optional

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


def record_egress(
    *,
    task: str,
    provider: str,
    model: str,
    sensitivity: str,
    policy_version: int,
    payload: str,
    redacted_categories: Dict[str, int],
) -> None:
    """Persist one `audit_log` row for a Class C (external provider) dispatch
    -- the "log every byte sent" half of ARCHITECTURE.md's egress control
    (item 2), never the payload itself, only its hash. Called once per
    successful Class C generate call (router.py::Router.generate), right
    alongside the PII redaction gate (app/services/redaction.py) it's paired
    with -- `redacted_categories` is that gate's output, so this row also
    proves what was masked before the request left. Fail-soft, matching every
    other model-router persistence path."""
    try:
        _persist_egress(
            task=task, provider=provider, model=model, sensitivity=sensitivity,
            policy_version=policy_version, payload=payload,
            redacted_categories=redacted_categories,
        )
    except Exception as e:  # pragma: no cover - defensive, never propagate
        logger.debug("egress audit log skipped (%s)", e)


def _persist_egress(*, task: str, provider: str, model: str, sensitivity: str,
                    policy_version: int, payload: str, redacted_categories: Dict[str, int]) -> None:
    import hashlib
    import json

    from app.auth import get_or_create_default_org
    from app.db import SessionLocal
    from app.db_models import AuditLog

    detail = json.dumps({
        "model": model,
        "sensitivity": sensitivity,
        "policy_version": policy_version,
        "payload_sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        "redacted_categories": redacted_categories,
    })
    db = SessionLocal()
    try:
        # The router doesn't carry request/org context yet (same documented
        # gap as ModelCall.org_id) -- the default org is the exact org on a
        # single-tenant (AUTH_REQUIRED=false) deployment, and an honest,
        # explicit stand-in on a multi-org one until that's threaded through.
        org = get_or_create_default_org(db)
        db.add(AuditLog(org_id=org.id, action="model_egress", resource=task,
                        egress_target=provider, detail=detail))
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
