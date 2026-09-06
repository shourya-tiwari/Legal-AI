# backend/app/auth.py
"""
Auth (docs/v2/ROADMAP.md Phase 1's "Auth Service" + Phase 7's per-user
identity, `LEARNING_LOG.md` #36/#37). Two credential kinds resolve to the
same `OrgContext`:

  - an org-scoped API key (`ApiKey`) -- the original Phase 1 unit of auth,
    still the right fit for machine-to-machine callers (a service integration
    doesn't have a "person" to log in as);
  - a logged-in user (`User` + `Session`) -- Phase 7's addition, for the case
    an API key structurally can't cover: two people sharing one org need to
    be individually attributed and individually revocable, not just handed
    the same shared secret with the same role.

Enforcement is gated by Settings.AUTH_REQUIRED (default False): with it off,
every caller resolves to a shared "default" organization (role="admin", no
credential of either kind) so the rest of the persistence/rate-limiting/
audit-log plumbing has a real org to attach to without requiring anyone to
have a key or an account yet.
"""
from __future__ import annotations

import datetime
import hashlib
import hmac
import secrets

from fastapi import Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as DbSession

from app.config import get_settings
from app.db import get_db
from app.db_models import ApiKey, Organization, Session as SessionRow, User

DEFAULT_ORG_NAME = "default"

# Per-key AND per-user RBAC (docs/v2/ARCHITECTURE.md security item 5) share
# this one role vocabulary.
VALID_ROLES = ("admin", "editor", "viewer")

# Bearer-token prefixes distinguish which table to resolve against without
# a second header or a DB round-trip against both tables on every request.
API_KEY_PREFIX = "lai_"
SESSION_TOKEN_PREFIX = "sess_"

_PBKDF2_ALGO = "sha256"
_PBKDF2_ITERATIONS = 260_000  # OWASP's current PBKDF2-HMAC-SHA256 minimum


class OrgContext(BaseModel):
    id: int
    name: str
    # "admin" for the default (AUTH_REQUIRED=false) org and for every
    # credential issued before roles existed -- fully permissive, matching
    # this app's "off by default so the public frontend keeps working"
    # posture. Real restriction only kicks in for a lower-role credential.
    role: str = "admin"
    # Exactly one of these is set when a real credential authenticated the
    # request (never both); both None under the default org. Used for audit
    # attribution (`AuditLog.actor_id`/`actor_type`) and by require_role.
    api_key_id: int | None = None
    user_id: int | None = None
    user_email: str | None = None


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def generate_api_key() -> str:
    return f"{API_KEY_PREFIX}{secrets.token_urlsafe(32)}"


def hash_password(raw_password: str) -> str:
    """PBKDF2-HMAC-SHA256, stdlib only (no new dependency) -- OWASP's current
    minimum iteration count for this algorithm. Format: algo$iterations$salt$hash,
    all hex/plain except the algo tag, so a future iteration-count bump doesn't
    break verifying passwords hashed under the old count."""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(_PBKDF2_ALGO, raw_password.encode("utf-8"),
                                 bytes.fromhex(salt), _PBKDF2_ITERATIONS)
    return f"pbkdf2_{_PBKDF2_ALGO}${_PBKDF2_ITERATIONS}${salt}${digest.hex()}"


def verify_password(raw_password: str, stored_hash: str) -> bool:
    try:
        algo_tag, iterations_str, salt, expected_hex = stored_hash.split("$")
        algo = algo_tag.removeprefix("pbkdf2_")
        iterations = int(iterations_str)
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac(algo, raw_password.encode("utf-8"), bytes.fromhex(salt), iterations)
    return hmac.compare_digest(digest.hex(), expected_hex)


def generate_session_token() -> str:
    return f"{SESSION_TOKEN_PREFIX}{secrets.token_urlsafe(32)}"


def hash_session_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def get_or_create_default_org(db: DbSession) -> Organization:
    org = db.query(Organization).filter_by(name=DEFAULT_ORG_NAME).first()
    if org is None:
        org = Organization(name=DEFAULT_ORG_NAME)
        db.add(org)
        db.commit()
        db.refresh(org)
    return org


def create_api_key(db: DbSession, org: Organization, name: str, role: str = "admin") -> str:
    """Issues a new API key for an org. Returns the raw key — it is never
    recoverable again once this returns, only its hash is stored."""
    if role not in VALID_ROLES:
        raise ValueError(f"role must be one of {VALID_ROLES}, got {role!r}")
    raw_key = generate_api_key()
    db.add(ApiKey(org_id=org.id, name=name, key_hash=hash_api_key(raw_key), role=role))
    db.commit()
    return raw_key


def create_user(db: DbSession, org: Organization, email: str, password: str, role: str = "admin") -> User:
    """Creates a logged-in-capable user for an org. Raises ValueError on an
    invalid role or a duplicate email (case-sensitive -- `users.email` is a
    plain unique column, no normalization yet)."""
    if role not in VALID_ROLES:
        raise ValueError(f"role must be one of {VALID_ROLES}, got {role!r}")
    if db.query(User).filter_by(email=email).first() is not None:
        raise ValueError(f"a user with email {email!r} already exists")
    user = User(org_id=org.id, email=email, password_hash=hash_password(password), role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: DbSession, email: str, password: str) -> User | None:
    """Returns the User on a correct, non-revoked email+password match, else
    None. Deliberately returns the same None for "no such user" and "wrong
    password" -- distinguishing them in the response would let a caller
    enumerate registered emails."""
    user = db.query(User).filter_by(email=email, revoked_at=None).first()
    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def create_session(db: DbSession, user: User) -> str:
    """Issues a session token for a user. Returns the raw token — it is
    never recoverable again once this returns, only its hash is stored."""
    raw_token = generate_session_token()
    ttl = datetime.timedelta(hours=get_settings().SESSION_TTL_HOURS)
    expires_at = datetime.datetime.now(datetime.timezone.utc) + ttl
    db.add(SessionRow(user_id=user.id, token_hash=hash_session_token(raw_token), expires_at=expires_at))
    db.commit()
    return raw_token


def revoke_session(db: DbSession, raw_token: str) -> bool:
    """Revokes the session matching this raw token. Returns whether a live
    (non-revoked, non-expired) session was actually found and revoked."""
    row = db.query(SessionRow).filter_by(token_hash=hash_session_token(raw_token), revoked_at=None).first()
    if row is None:
        return False
    row.revoked_at = datetime.datetime.now(datetime.timezone.utc)
    db.commit()
    return True


def _resolve_api_key(db: DbSession, raw_key: str) -> OrgContext | None:
    key_row = db.query(ApiKey).filter_by(key_hash=hash_api_key(raw_key), revoked_at=None).first()
    if key_row is None:
        return None
    return OrgContext(id=key_row.organization.id, name=key_row.organization.name,
                      role=key_row.role, api_key_id=key_row.id)


def _resolve_session(db: DbSession, raw_token: str) -> OrgContext | None:
    session_row = db.query(SessionRow).filter_by(token_hash=hash_session_token(raw_token), revoked_at=None).first()
    if session_row is None:
        return None
    now = datetime.datetime.now(datetime.timezone.utc)
    expires_at = session_row.expires_at
    if expires_at.tzinfo is None:  # SQLite round-trips naive datetimes
        expires_at = expires_at.replace(tzinfo=datetime.timezone.utc)
    if expires_at < now:
        return None
    user = session_row.user
    if user.revoked_at is not None:
        return None
    return OrgContext(id=user.organization.id, name=user.organization.name,
                      role=user.role, user_id=user.id, user_email=user.email)


def get_current_org(
    authorization: str | None = Header(default=None),
    db: DbSession = Depends(get_db),
) -> OrgContext:
    settings = get_settings()

    if not settings.AUTH_REQUIRED:
        org = get_or_create_default_org(db)
        return OrgContext(id=org.id, name=org.name, role="admin")

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing credential. Send 'Authorization: Bearer <key-or-token>'.")

    raw_token = authorization.split(" ", 1)[1].strip()

    if raw_token.startswith(SESSION_TOKEN_PREFIX):
        ctx = _resolve_session(db, raw_token)
        if ctx is None:
            raise HTTPException(status_code=401, detail="Invalid, expired, or revoked session.")
        return ctx

    ctx = _resolve_api_key(db, raw_token)
    if ctx is None:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key.")
    return ctx
