# backend/app/services/org_settings.py
"""
Per-org feature flags (docs/v2/ROADMAP.md Phase 7 "Introduce /api/v2/*
document-first endpoints ... per-org feature-flagging still to do") and the
Notification/Webhook Service (docs/v2/ROADMAP.md Phase 7 "Notification/
Webhook Service for async job completion").

Both live on `Organization` directly (`feature_flags` JSON, `webhook_url`)
rather than a separate settings table -- there's exactly one row of
settings per org, so a second table would just be a 1:1 join for no
benefit, the same reasoning `documents.sensitivity_tier` living directly on
`Document` already follows.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

import requests

from app.db_models import Organization

logger = logging.getLogger("legalai.org_settings")

# Every flag this codebase actually checks, with its default -- a flag not
# in an org's `feature_flags` dict (e.g. an org created before the flag
# existed) falls back to this, never to a KeyError.
_FLAG_DEFAULTS: Dict[str, bool] = {
    "api_v2_enabled": True,
}

_WEBHOOK_TIMEOUT_SECONDS = 5


def is_feature_enabled(org: Organization, flag_name: str) -> bool:
    default = _FLAG_DEFAULTS.get(flag_name, True)
    return bool((org.feature_flags or {}).get(flag_name, default))


def send_webhook_notification(webhook_url: str, event: str, payload: Dict[str, Any]) -> bool:
    """Fire-and-forget POST to an org's registered webhook. Fail-soft: any
    failure (unreachable host, timeout, non-2xx) is logged and swallowed --
    a notification failing must never fail the request that triggered it.
    Returns whether the POST was actually accepted (2xx), for callers that
    want to know without having it raise."""
    try:
        resp = requests.post(webhook_url, json={"event": event, "data": payload},
                             timeout=_WEBHOOK_TIMEOUT_SECONDS)
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.warning("Webhook notification to %s failed (%s); event=%s not delivered.",
                       webhook_url, e, event)
        return False


def notify_org(org: Organization, event: str, payload: Dict[str, Any]) -> None:
    """No-ops silently if the org has no webhook configured -- this is the
    call site every job-completion path should use, not
    send_webhook_notification directly, so "no webhook set" and "webhook
    failed" are both handled the same fail-soft way without every caller
    re-checking `org.webhook_url`."""
    if not org.webhook_url:
        return
    send_webhook_notification(org.webhook_url, event, payload)
