# backend/app/observability.py
"""
OpenTelemetry tracing scaffold (docs/v2/MODEL_STACK.md "Observability",
ROADMAP Phase 5).

Entirely opt-in and fail-soft:
  - does nothing unless Settings.OTEL_ENABLED is true AND
    Settings.OTEL_EXPORTER_OTLP_ENDPOINT is set AND the
    `opentelemetry-*` packages import (requirements-observability.txt).
  - a bad endpoint / missing collector never breaks startup or a request --
    the OTLP exporter buffers and drops, and every hook here is wrapped.

Point OTEL_EXPORTER_OTLP_ENDPOINT at a self-hosted collector: Langfuse
(OTLP ingest), SigNoz (single-binary), or a Grafana Alloy / Tempo pipeline.
A docker-compose.observability.yml bundling one of those is a follow-up.
"""
from __future__ import annotations

import logging

from app.config import get_settings

logger = logging.getLogger("legalai.observability")

_tracer = None
_initialised = False


def init_tracing(app=None) -> None:
    """Called once from app.main's lifespan. Safe to call when disabled."""
    global _tracer, _initialised
    if _initialised:
        return
    _initialised = True

    settings = get_settings()
    if not settings.OTEL_ENABLED:
        return
    if not settings.OTEL_EXPORTER_OTLP_ENDPOINT:
        logger.warning("OTEL_ENABLED but OTEL_EXPORTER_OTLP_ENDPOINT is empty; tracing off.")
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except Exception as e:
        logger.warning("OpenTelemetry packages not installed (%s); tracing off. "
                       "pip install -r requirements-observability.txt", e)
        return

    try:
        provider = TracerProvider(
            resource=Resource.create({"service.name": settings.OTEL_SERVICE_NAME})
        )
        provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT))
        )
        trace.set_tracer_provider(provider)
        _tracer = trace.get_tracer("legalai")

        if app is not None:
            try:
                from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

                FastAPIInstrumentor.instrument_app(app)
            except Exception as e:
                logger.warning("FastAPI auto-instrumentation skipped (%s).", e)

        logger.info("OpenTelemetry tracing enabled -> %s", settings.OTEL_EXPORTER_OTLP_ENDPOINT)
    except Exception as e:
        logger.warning("OpenTelemetry init failed (%s); tracing off.", e)
        _tracer = None


def get_tracer():
    """The tracer, or None when tracing is disabled/unavailable."""
    return _tracer
