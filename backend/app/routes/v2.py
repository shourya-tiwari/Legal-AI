# backend/app/routes/v2.py
"""
`/api/v2/*` -- document-first API surface (docs/v2/BACKEND.md).

Every task endpoint takes a persisted `document_id` (from `/api/upload`)
instead of a raw `contract_text` blob re-sent on each call. The V1 endpoints
are unchanged; this is additive.

Each endpoint loads the org-scoped `Document` and calls the *same* service
function as its V1 counterpart -- no service logic changes here.
"""
from __future__ import annotations

import datetime
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.auth import OrgContext
from app.db import get_db
from app.db_models import AuditLog, Document
from app.guard import actor_of, require_feature, require_role
from app.models import (
    AgentAnalyzeResponse,
    AskResponse,
    ConsistencyResponse,
    ContextualizerResponse,
    MapResponse,
    RewriteResponse,
    RiskDashboardResponse,
    RiskScanResponse,
    SensitivityOverrideRequest,
    SensitivityResponse,
    SimulationRequest,
    SimulationResponse,
    V2AnalyzeRequest,
    V2AskRequest,
    V2ContextualizeRequest,
    V2DocumentResponse,
    V2RewriteRequest,
    V2RiskScanRequest,
)
from app.routes.agents import run_and_persist_analysis
from app.services.chatbot import answer_question
from app.services.consistency import MAX_OTHER_DOCUMENTS, find_cross_document_consistency
from app.services.contextualizer.explainer import generate_contextualized_explanation
from app.services.file_store import load_bytes
from app.services.model_router import is_external_permitted
from app.services.nlp.pipeline import build_clause_objects
from app.services.risk_radar.detector import generate_risk_dashboard, generate_risk_radar_response
from app.services.rewriter import rewrite_text
from app.services.sensitivity import classify_sensitivity
from app.services.simulation import simulate_obligation_timeline
from app.services.timeline import generate_map

logger = logging.getLogger("legalai.routes.v2")

router = APIRouter(prefix="/v2", tags=["v2"])


def _load_doc(document_id: int, org: OrgContext, db: Session) -> Document:
    doc = db.query(Document).filter_by(id=document_id, org_id=org.id).first()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


def _block_text(doc: Document, block_id) -> str:
    """Whole document by default; one block's text when `block_id` is given."""
    if block_id is None:
        return doc.full_text
    for block in doc.blocks or []:
        if str(block.get("id")) == str(block_id):
            return block.get("text", "")
    raise HTTPException(status_code=404, detail=f"Block '{block_id}' not found in document {doc.id}")


@router.get("/documents/{document_id}", response_model=V2DocumentResponse, summary="Get a stored document")
def get_document(
    document_id: int,
    org: OrgContext = Depends(require_feature("api_v2_enabled")),
    db: Session = Depends(get_db),
) -> V2DocumentResponse:
    doc = _load_doc(document_id, org, db)
    return V2DocumentResponse(
        document_id=doc.id,
        filename=doc.filename,
        content_type=doc.content_type,
        full_text=doc.full_text,
        blocks=doc.blocks or [],
        created_at=doc.created_at.isoformat() if doc.created_at else None,
        sensitivity_tier=doc.sensitivity_tier,
        sensitivity_source=doc.sensitivity_source,
        quality=doc.quality,
        original_available=bool(doc.original_sha256),
        original_size=doc.original_size,
    )


@router.get("/documents/{document_id}/original", summary="Download the original uploaded file")
def get_original_file(
    document_id: int,
    org: OrgContext = Depends(require_feature("api_v2_enabled")),
    db: Session = Depends(get_db),
) -> Response:
    """Stream back the exact bytes that were uploaded (Phase 7,
    services/file_store.py). 404 if this document predates blob storage or
    its upload's storage write failed (`original_sha256` is null), or if the
    blob is somehow missing from the store."""
    doc = _load_doc(document_id, org, db)
    if not doc.original_sha256:
        raise HTTPException(status_code=404, detail="Original file was not stored for this document")
    data = load_bytes(doc.original_sha256)
    if data is None:
        raise HTTPException(status_code=404, detail="Original file blob is missing from the store")
    filename = (doc.filename or "document").replace('"', "")
    return Response(
        content=data,
        media_type=doc.content_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/documents/{document_id}/sensitivity", response_model=SensitivityResponse,
            summary="Get a document's sensitivity tier and why")
def get_sensitivity(
    document_id: int,
    org: OrgContext = Depends(require_feature("api_v2_enabled")),
    db: Session = Depends(get_db),
) -> SensitivityResponse:
    doc = _load_doc(document_id, org, db)
    return SensitivityResponse(
        document_id=doc.id,
        tier=doc.sensitivity_tier,
        source=doc.sensitivity_source,
        signals=list(doc.sensitivity_signals or []),
        rationale=classify_sensitivity(doc.full_text, filename=doc.filename).rationale
        if doc.sensitivity_source == "auto" else "set by org-admin override",
        external_providers_permitted=is_external_permitted(doc.sensitivity_tier),
    )


@router.put("/documents/{document_id}/sensitivity", response_model=SensitivityResponse,
            summary="Override a document's sensitivity tier (org-admin)")
def override_sensitivity(
    document_id: int,
    body: SensitivityOverrideRequest,
    request: Request,
    org: OrgContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> SensitivityResponse:
    doc = _load_doc(document_id, org, db)
    old = doc.sensitivity_tier
    doc.sensitivity_tier = body.tier
    doc.sensitivity_source = "override"
    doc.sensitivity_signals = ([{"tier": body.tier, "phrase": body.reason, "category": "override"}]
                               + list(doc.sensitivity_signals or []))
    actor_id, actor_type = actor_of(org)
    db.add(AuditLog(
        org_id=org.id, actor_id=actor_id, actor_type=actor_type,
        action="PUT", resource=str(request.url.path),
        detail=f"sensitivity {old} -> {body.tier}: {body.reason}",
    ))
    db.commit()
    db.refresh(doc)
    return SensitivityResponse(
        document_id=doc.id,
        tier=doc.sensitivity_tier,
        source=doc.sensitivity_source,
        signals=list(doc.sensitivity_signals or []),
        rationale=f"overridden from {old} by org-admin: {body.reason}",
        external_providers_permitted=is_external_permitted(doc.sensitivity_tier),
    )


@router.post("/documents/{document_id}/analyze", response_model=AgentAnalyzeResponse,
             summary="Run the planner-driven agent analysis")
def analyze(
    document_id: int,
    background_tasks: BackgroundTasks,
    body: V2AnalyzeRequest = V2AnalyzeRequest(),
    org: OrgContext = Depends(require_feature("api_v2_enabled")),
    db: Session = Depends(get_db),
) -> AgentAnalyzeResponse:
    doc = _load_doc(document_id, org, db)
    return run_and_persist_analysis(
        doc, org, db,
        analysis_mode=body.analysis_mode,
        use_ai_planner=body.use_ai_planner,
        background_tasks=background_tasks,
    )


@router.post("/documents/{document_id}/rewrite", response_model=RewriteResponse,
             summary="Plain-English rewrite of the document or one block")
def rewrite(
    document_id: int,
    body: V2RewriteRequest = V2RewriteRequest(),
    org: OrgContext = Depends(require_feature("api_v2_enabled")),
    db: Session = Depends(get_db),
) -> RewriteResponse:
    doc = _load_doc(document_id, org, db)
    out, meta = rewrite_text(_block_text(doc, body.block_id), body.mode,
                             sensitivity=doc.sensitivity_tier)
    return RewriteResponse(rewritten_text=out, meta=meta)


@router.post("/documents/{document_id}/map", response_model=MapResponse,
             summary="Structure + timeline for the document")
def contract_map(
    document_id: int,
    org: OrgContext = Depends(require_feature("api_v2_enabled")),
    db: Session = Depends(get_db),
) -> MapResponse:
    doc = _load_doc(document_id, org, db)
    return generate_map(doc.full_text, sensitivity=doc.sensitivity_tier)


@router.post("/documents/{document_id}/ask", response_model=AskResponse,
             summary="Ask a question grounded on the document")
def ask(
    document_id: int,
    body: V2AskRequest,
    org: OrgContext = Depends(require_feature("api_v2_enabled")),
    db: Session = Depends(get_db),
) -> AskResponse:
    doc = _load_doc(document_id, org, db)
    return answer_question(question=body.question, context=doc.full_text,
                           sensitivity=doc.sensitivity_tier)


@router.post("/documents/{document_id}/risk-scan", response_model=RiskScanResponse,
             summary="Rule + AI risk scan of the document or one block")
def risk_scan(
    document_id: int,
    body: V2RiskScanRequest = V2RiskScanRequest(),
    org: OrgContext = Depends(require_feature("api_v2_enabled")),
    db: Session = Depends(get_db),
) -> RiskScanResponse:
    doc = _load_doc(document_id, org, db)
    return generate_risk_radar_response(_block_text(doc, body.block_id),
                                        sensitivity=doc.sensitivity_tier)


@router.post("/documents/{document_id}/risk-dashboard", response_model=RiskDashboardResponse,
             summary="Per-category risk-flag counts for the Risk Dashboard spider/radar chart")
def risk_dashboard(
    document_id: int,
    org: OrgContext = Depends(require_feature("api_v2_enabled")),
    db: Session = Depends(get_db),
) -> RiskDashboardResponse:
    doc = _load_doc(document_id, org, db)
    clauses = build_clause_objects(doc.full_text, sensitivity=doc.sensitivity_tier)
    return generate_risk_dashboard(clauses)


@router.post("/documents/{document_id}/contextualize", response_model=ContextualizerResponse,
             summary="Explain one block's clause for a user's context")
def contextualize(
    document_id: int,
    body: V2ContextualizeRequest,
    org: OrgContext = Depends(require_feature("api_v2_enabled")),
    db: Session = Depends(get_db),
) -> ContextualizerResponse:
    doc = _load_doc(document_id, org, db)
    result = generate_contextualized_explanation(_block_text(doc, body.block_id), body.context,
                                                 sensitivity=doc.sensitivity_tier)
    return ContextualizerResponse(**result)


@router.post("/documents/{document_id}/consistency", response_model=ConsistencyResponse,
             summary="Cross-document consistency check (embedding-similarity baseline)")
def consistency(
    document_id: int,
    org: OrgContext = Depends(require_feature("api_v2_enabled")),
    db: Session = Depends(get_db),
) -> ConsistencyResponse:
    doc = _load_doc(document_id, org, db)
    # The service only compares against the newest MAX_OTHER_DOCUMENTS anyway;
    # cap the query rather than loading the whole org's document rows.
    other_docs = (
        db.query(Document)
        .filter(Document.org_id == org.id, Document.id != doc.id)
        .order_by(Document.created_at.desc())
        .limit(MAX_OTHER_DOCUMENTS)
        .all()
    )
    findings = find_cross_document_consistency(doc, other_docs, sensitivity=doc.sensitivity_tier)
    return ConsistencyResponse(
        document_id=doc.id,
        other_documents_checked=len(other_docs),
        findings=findings,
    )


@router.post("/documents/{document_id}/simulate", response_model=SimulationResponse,
             summary="Obligation timeline simulation (deterministic discrete-event baseline)")
def simulate(
    document_id: int,
    body: SimulationRequest = SimulationRequest(),
    org: OrgContext = Depends(require_feature("api_v2_enabled")),
    db: Session = Depends(get_db),
) -> SimulationResponse:
    doc = _load_doc(document_id, org, db)
    reference_date = (
        datetime.date.fromisoformat(body.reference_date) if body.reference_date else datetime.date.today()
    )
    events = simulate_obligation_timeline(
        doc, reference_date=reference_date, warning_window_days=body.warning_window_days,
        sensitivity=doc.sensitivity_tier,
    )
    return SimulationResponse(
        document_id=doc.id,
        reference_date=reference_date.isoformat(),
        warning_window_days=body.warning_window_days,
        events=events,
    )
