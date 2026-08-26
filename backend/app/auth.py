# backend/app/auth.py
"""
Org-scoped API key auth (docs/v2/ROADMAP.md Phase 1's "Auth Service", scoped
to what's actually needed right now: no login UI exists yet, so per-user
sessions/roles are deferred — an organization's API key is the unit of auth).

Enforcement is gated by Settings.AUTH_REQUIRED (default False): with it off,
every caller resolves to a shared "default" organization so the rest of the
persistence/rate-limiting/audit-log plumbing has a real org to attach to
without requiring anyone to have a key yet.
"""
from __future__ import annotations

import hashlib
import secrets

from fastapi import Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.db_models import ApiKey, Organization

DEFAULT_ORG_NAME = "default"


class OrgContext(BaseModel):
    id: int
    name: str


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def generate_api_key() -> str:
    return f"lai_{secrets.token_urlsafe(32)}"


def get_or_create_default_org(db: Session) -> Organization:
    org = db.query(Organization).filter_by(name=DEFAULT_ORG_NAME).first()
    if org is None:
        org = Organization(name=DEFAULT_ORG_NAME)
        db.add(org)
        db.commit()
        db.refresh(org)
    return org


def create_api_key(db: Session, org: Organization, name: str) -> str:
    """Issues a new API key for an org. Returns the raw key — it is never
    recoverable again once this returns, only its hash is stored."""
    raw_key = generate_api_key()
    db.add(ApiKey(org_id=org.id, name=name, key_hash=hash_api_key(raw_key)))
    db.commit()
    return raw_key


def get_current_org(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> OrgContext:
    settings = get_settings()

    if not settings.AUTH_REQUIRED:
        org = get_or_create_default_org(db)
        return OrgContext(id=org.id, name=org.name)

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing API key. Send 'Authorization: Bearer <key>'.")

    raw_key = authorization.split(" ", 1)[1].strip()
    key_row = (
        db.query(ApiKey)
        .filter_by(key_hash=hash_api_key(raw_key), revoked_at=None)
        .first()
    )
    if key_row is None:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key.")

    return OrgContext(id=key_row.organization.id, name=key_row.organization.name)
