# backend/app/routes/org_settings.py
"""
Per-org feature flags + webhook registration (docs/v2/ROADMAP.md Phase 7
"per-org feature-flagging" + "Notification/Webhook Service"). Read is open
to any authenticated caller in the org (so a non-admin integration can at
least see what's configured); writing either setting is admin-only, same
posture as the sensitivity override and user-management routes.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import OrgContext
from app.db import get_db
from app.db_models import Organization
from app.guard import api_guard, require_role
from app.models import OrgSettingsResponse, UpdateOrgSettingsRequest

router = APIRouter(tags=["org-settings"])


def _to_response(organization: Organization) -> OrgSettingsResponse:
    return OrgSettingsResponse(
        org_id=organization.id,
        feature_flags=dict(organization.feature_flags or {}),
        webhook_url=organization.webhook_url,
        negotiation_preferences=dict(organization.negotiation_preferences or {}),
    )


@router.get("/org/settings", response_model=OrgSettingsResponse, summary="Read the caller's org settings")
def get_org_settings(org: OrgContext = Depends(api_guard), db: Session = Depends(get_db)) -> OrgSettingsResponse:
    organization = db.query(Organization).filter_by(id=org.id).first()
    return _to_response(organization)


@router.put("/org/settings", response_model=OrgSettingsResponse, summary="Update the caller's org settings (admin only)")
def update_org_settings(
    body: UpdateOrgSettingsRequest,
    org: OrgContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> OrgSettingsResponse:
    organization = db.query(Organization).filter_by(id=org.id).first()
    if body.feature_flags is not None:
        merged = dict(organization.feature_flags or {})
        merged.update(body.feature_flags)
        organization.feature_flags = merged
    if body.webhook_url is not None:
        organization.webhook_url = body.webhook_url or None
    if body.negotiation_preferences is not None:
        merged_prefs = dict(organization.negotiation_preferences or {})
        merged_prefs.update(body.negotiation_preferences)
        organization.negotiation_preferences = merged_prefs
    db.commit()
    db.refresh(organization)
    return _to_response(organization)
