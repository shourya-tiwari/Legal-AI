# backend/app/routes/auth.py
"""
Per-user identity (docs/v2/ARCHITECTURE.md security item 5, `LEARNING_LOG.md`
#37) -- the remaining half of Phase 7's RBAC work. `ApiKey.role` (Phase 7,
`LEARNING_LOG.md` #36) made a *credential* the unit of RBAC; this makes a
*person* one, so two people sharing an org no longer have to share one
key's role and are individually attributable in `audit_log`.

Login/logout only matter once `Settings.AUTH_REQUIRED=true` -- with it off
every caller is the shared default org already (see app/auth.py). There is
still no self-serve signup: an org's first user has to be created by
whoever provisions the org (`scripts/create_api_key.py`'s sibling for users
is the `POST /users` endpoint here, callable by an existing admin, or
directly via a script for the very first user -- same bootstrapping shape
`create_api_key.py` already has for keys).
"""
from __future__ import annotations

import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.auth import OrgContext, authenticate_user, create_session, create_user, revoke_session
from app.config import get_settings
from app.db import get_db
from app.db_models import Organization, User
from app.guard import api_guard, require_role
from app.models import (
    CreateUserRequest,
    LoginRequest,
    LoginResponse,
    UserSummary,
    UsersListResponse,
)
from app.rate_limit import RateLimitExceeded, check_rate_limit

router = APIRouter(tags=["auth"])


def _to_summary(user: User) -> UserSummary:
    return UserSummary(
        id=user.id, email=user.email, role=user.role,
        created_at=user.created_at.isoformat() if user.created_at else None,
        revoked_at=user.revoked_at.isoformat() if user.revoked_at else None,
    )


@router.post("/auth/login", response_model=LoginResponse, summary="Log in with email + password")
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)) -> LoginResponse:
    # No credential exists yet at this point in the request -- rate-limit by
    # IP the same way api_guard does for the unauthenticated default-org
    # posture, so a login endpoint isn't a brute-force-able exception to the
    # rate limiter every other route gets for free.
    try:
        check_rate_limit(f"ip:{request.client.host if request.client else 'unknown'}:login")
    except RateLimitExceeded as e:
        raise HTTPException(status_code=429, detail=str(e))

    user = authenticate_user(db, body.email, body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = create_session(db, user)
    expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        hours=get_settings().SESSION_TTL_HOURS
    )
    return LoginResponse(
        token=token, org_id=user.organization.id, org_name=user.organization.name,
        role=user.role, expires_at=expires_at.isoformat(),
    )


@router.post("/auth/logout", summary="Revoke the session token used to authenticate this request")
def logout(
    authorization: str | None = Header(default=None),
    org: OrgContext = Depends(api_guard),
    db: Session = Depends(get_db),
) -> dict:
    if org.user_id is None:
        raise HTTPException(status_code=400, detail="Logout applies to a user session, not an API key.")
    raw_token = authorization.split(" ", 1)[1].strip() if authorization else ""
    revoked = revoke_session(db, raw_token)
    return {"revoked": revoked}


@router.post("/auth/users", response_model=UserSummary, summary="Create a user in the caller's org (admin only)")
def create_org_user(
    body: CreateUserRequest,
    org: OrgContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> UserSummary:
    organization = db.query(Organization).filter_by(id=org.id).first()
    try:
        user = create_user(db, organization, body.email, body.password, role=body.role)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return _to_summary(user)


@router.get("/auth/users", response_model=UsersListResponse, summary="List users in the caller's org (admin only)")
def list_org_users(
    org: OrgContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> UsersListResponse:
    users = db.query(User).filter_by(org_id=org.id).order_by(User.created_at.asc()).all()
    return UsersListResponse(users=[_to_summary(u) for u in users])


@router.post("/auth/users/{user_id}/revoke", response_model=UserSummary,
            summary="Revoke a user in the caller's org (admin only)")
def revoke_org_user(
    user_id: int,
    org: OrgContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> UserSummary:
    user = db.query(User).filter_by(id=user_id, org_id=org.id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.revoked_at = datetime.datetime.now(datetime.timezone.utc)
    db.commit()
    db.refresh(user)
    return _to_summary(user)
