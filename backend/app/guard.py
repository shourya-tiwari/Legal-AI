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

    db.add(AuditLog(org_id=org.id, action=request.method, resource=request.url.path))
    db.commit()

    return org
