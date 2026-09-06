# backend/app/routes/review.py
"""
Human-in-the-loop review queue (docs/v2/ROADMAP.md Phase 7).

`CaseAnalysis.needs_human_review` (app/routes/agents.py) was computed and
returned in the analyze() HTTP response every time but never persisted --
this is the read side of persisting it: list every analysis that still
needs a human's attention, and let a reviewer resolve it (org-scoped;
resolving requires admin or editor role -- per-key RBAC, app/guard.py --
and the reviewer still identifies themselves with a free-text note, since
there's still no logged-in-user identity to attach to the row, same
pattern as the sensitivity-override "reason" field).
"""
from __future__ import annotations

import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import OrgContext
from app.db import get_db
from app.db_models import CaseAnalysis, Document
from app.guard import api_guard, require_role
from app.models import ReviewQueueItem, ReviewQueueResponse, ReviewResolveRequest

router = APIRouter(tags=["review-queue"])


def _to_item(analysis: CaseAnalysis, filename: str) -> ReviewQueueItem:
    return ReviewQueueItem(
        id=analysis.id,
        document_id=analysis.document_id,
        document_filename=filename,
        analysis_mode=analysis.analysis_mode,
        plan=list(analysis.plan or []),
        summary=analysis.summary,
        faithfulness_ok=analysis.faithfulness_ok,
        faithfulness_method=analysis.faithfulness_method,
        unsupported_claims=list(analysis.unsupported_claims or []),
        invalid_citation_numbers=list(analysis.invalid_citation_numbers or []),
        needs_human_review=analysis.needs_human_review,
        reviewed=analysis.reviewed,
        reviewed_at=analysis.reviewed_at.isoformat() if analysis.reviewed_at else None,
        reviewer_note=analysis.reviewer_note,
        created_at=analysis.created_at.isoformat() if analysis.created_at else None,
    )


@router.get("/review-queue", response_model=ReviewQueueResponse,
            summary="List analyses flagged needs_human_review, unresolved first")
def list_review_queue(
    include_resolved: bool = False,
    org: OrgContext = Depends(api_guard),
    db: Session = Depends(get_db),
) -> ReviewQueueResponse:
    query = (
        db.query(CaseAnalysis, Document.filename)
        .join(Document, Document.id == CaseAnalysis.document_id)
        .filter(CaseAnalysis.org_id == org.id, CaseAnalysis.needs_human_review.is_(True))
    )
    if not include_resolved:
        query = query.filter(CaseAnalysis.reviewed.is_(False))
    rows = query.order_by(CaseAnalysis.reviewed.asc(), CaseAnalysis.created_at.desc()).all()
    return ReviewQueueResponse(items=[_to_item(analysis, filename) for analysis, filename in rows])


@router.post("/review-queue/{analysis_id}/resolve", response_model=ReviewQueueItem,
             summary="Mark a flagged analysis as reviewed")
def resolve_review_item(
    analysis_id: int,
    body: ReviewResolveRequest,
    org: OrgContext = Depends(require_role("admin", "editor")),
    db: Session = Depends(get_db),
) -> ReviewQueueItem:
    analysis = db.query(CaseAnalysis).filter_by(id=analysis_id, org_id=org.id).first()
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")

    analysis.reviewed = True
    analysis.reviewed_at = datetime.datetime.now(datetime.timezone.utc)
    analysis.reviewer_note = body.note
    db.commit()
    db.refresh(analysis)

    document = db.query(Document).filter_by(id=analysis.document_id).first()
    return _to_item(analysis, document.filename if document else "")
