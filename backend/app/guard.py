# backend/app/guard.py
"""
Single dependency every route uses for the three cross-cutting concerns
Phase 1 introduces: auth resolution, rate limiting, and audit logging.
Kept as one dependency (rather than three separate Depends()) to keep route
signatures uncluttered while the app is still a single FastAPI process.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.auth import OrgContext, get_current_org
from app.config import get_settings
from app.db import get_db
from app.db_models import AuditLog
from app.rate_limit import RateLimitExceeded, check_rate_limit


def api_guard(
    request: Request,
    org: OrgContext = Depends(get_current_org),
    db: Session = Depends(get_db),
) -> OrgContext:
    settings = get_settings()

    rate_limit_key = f"org:{org.id}" if settings.AUTH_REQUIRED else f"ip:{request.client.host if request.client else 'unknown'}"
    try:
        check_rate_limit(rate_limit_key)
    except RateLimitExceeded as e:
        raise HTTPException(status_code=429, detail=str(e))

    db.add(AuditLog(org_id=org.id, actor_id=org.api_key_id,
                    action=request.method, resource=request.url.path))
    db.commit()

    return org


def require_role(*allowed_roles: str):
    """Dependency factory gating a route on the caller's role (per-key RBAC,
    docs/v2/ARCHITECTURE.md security item 5) -- use in place of
    `Depends(api_guard)` on a route that's a privileged action, not any org
    caller. Composes with api_guard rather than duplicating it: FastAPI
    resolves a given dependency once per request, so this doesn't double the
    rate-limit check or the audit-log row."""
    def _check(org: OrgContext = Depends(api_guard)) -> OrgContext:
        if org.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"This action requires one of roles {allowed_roles!r}; caller has '{org.role}'.",
            )
        return org
    return _check
