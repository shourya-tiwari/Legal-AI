# backend/app/routes/audit.py
"""
Egress audit log (docs/v2/ARCHITECTURE.md Security architecture item 2 "log
every byte sent" + item 9 "audit trail").

`app/services/model_router/telemetry.py::record_egress` has been writing one
`audit_log` row per Class C dispatch since it shipped; nothing read it back
until this endpoint. Same "persist, then actually surface it" shape as the
review queue (`routes/review.py`) and the eval-runs endpoint (`routes/
models.py`) -- a capability was real in the database and invisible to every
caller of the API.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import OrgContext
from app.db import get_db
from app.db_models import AuditLog
from app.guard import api_guard
from app.models import EgressLogEntry, EgressLogResponse

router = APIRouter(tags=["audit"])


def _to_entry(row: AuditLog) -> EgressLogEntry:
    detail = json.loads(row.detail) if row.detail else {}
    return EgressLogEntry(
        id=row.id,
        task=row.resource or "",
        provider=row.egress_target or "",
        model=detail.get("model"),
        sensitivity=detail.get("sensitivity"),
        policy_version=detail.get("policy_version"),
        payload_sha256=detail.get("payload_sha256"),
        redacted_categories=detail.get("redacted_categories", {}),
        created_at=row.created_at.isoformat() if row.created_at else None,
    )


@router.get("/audit/egress", response_model=EgressLogResponse,
            summary="Every request that left the perimeter to a Class C provider")
def list_egress_log(
    limit: int = 100,
    org: OrgContext = Depends(api_guard),
    db: Session = Depends(get_db),
) -> EgressLogResponse:
    # Not org-scoped: the Model Router doesn't carry request/org context yet
    # (the same documented gap as ModelCall.org_id) -- every egress row is
    # currently written under the default org regardless of which org's
    # document triggered it. `org` is only here to sit behind api_guard like
    # every other route, matching GET /api/models/eval-runs's precedent.
    rows = (
        db.query(AuditLog)
        .filter(AuditLog.action == "model_egress")
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(min(limit, 500))
        .all()
    )
    return EgressLogResponse(entries=[_to_entry(row) for row in rows])
