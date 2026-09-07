from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import OrgContext
from app.db import get_db
from app.db_models import Document
from app.guard import api_guard
from app.models import (
    KGConflictsResponse, KGIngestRequest, KGIngestResponse, KGQueryRequest, KGQueryResponse,
    KGSupersedeRequest, KGSupersedeResponse, KGVersionHistoryResponse,
)
from app.services.kg.builder import link_portfolio_terms, write_document_graph
from app.services.kg.client import get_kg_client
from app.services.kg.queries import find_clauses_using_term, find_potential_conflicts
from app.services.kg.versioning import find_clauses_valid_as_of, find_document_version_history, mark_document_superseded
from app.services.nlp.defined_terms import extract_defined_terms
from app.services.nlp.pipeline import build_clause_objects

router = APIRouter(tags=["knowledge-graph"])


@router.post("/kg/ingest", response_model=KGIngestResponse, summary="Ingest a Document into the Knowledge Graph")
def ingest_document(
    req: KGIngestRequest,
    org: OrgContext = Depends(api_guard),
    db: Session = Depends(get_db),
) -> KGIngestResponse:
    document = db.query(Document).filter_by(id=req.document_id, org_id=org.id).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    clauses = build_clause_objects(document.full_text)
    defined_terms = extract_defined_terms(document.full_text)

    client = get_kg_client()
    summary = write_document_graph(client, org.id, document.id, defined_terms, clauses)
    links_created = link_portfolio_terms(client, org.id, document.id, defined_terms)

    return KGIngestResponse(
        document_id=document.id,
        clauses=summary["clauses"],
        defined_terms=summary["defined_terms"],
        cross_references=summary["cross_references"],
        portfolio_links_created=links_created,
        kg_available=client.available,
    )


@router.post("/kg/query", response_model=KGQueryResponse, summary="Find Clauses Using a Defined Term")
def query_term(req: KGQueryRequest, org: OrgContext = Depends(api_guard)) -> KGQueryResponse:
    client = get_kg_client()
    if req.as_of:
        clauses = find_clauses_valid_as_of(client, org.id, req.term, req.as_of)
    else:
        clauses = find_clauses_using_term(client, org.id, req.term)
    return KGQueryResponse(term=req.term, as_of=req.as_of, clauses=clauses)


@router.post("/kg/conflicts", response_model=KGConflictsResponse, summary="Find Candidate Cross-Document Conflicts")
def query_conflicts(req: KGQueryRequest, org: OrgContext = Depends(api_guard)) -> KGConflictsResponse:
    client = get_kg_client()
    conflicts = find_potential_conflicts(client, org.id, req.term)
    return KGConflictsResponse(term=req.term, conflicts=conflicts)


@router.post(
    "/kg/supersede", response_model=KGSupersedeResponse,
    summary="Mark a Document as Superseded by a Newer Version (Bitemporal Versioning)",
)
def supersede_document(
    req: KGSupersedeRequest,
    org: OrgContext = Depends(api_guard),
    db: Session = Depends(get_db),
) -> KGSupersedeResponse:
    for doc_id in (req.old_document_id, req.new_document_id):
        if db.query(Document).filter_by(id=doc_id, org_id=org.id).first() is None:
            raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")

    client = get_kg_client()
    result = mark_document_superseded(client, org.id, req.old_document_id, req.new_document_id, req.valid_from)
    return KGSupersedeResponse(
        old_document_id=req.old_document_id,
        new_document_id=req.new_document_id,
        valid_from=result.get("valid_from"),
        clauses_closed=result.get("clauses_closed", 0),
        kg_available=result.get("kg_available", False),
    )


@router.get(
    "/kg/documents/{document_id}/versions", response_model=KGVersionHistoryResponse,
    summary="Get a Document's Full Version History (Bitemporal Versioning)",
)
def document_version_history(
    document_id: int,
    org: OrgContext = Depends(api_guard),
    db: Session = Depends(get_db),
) -> KGVersionHistoryResponse:
    if db.query(Document).filter_by(id=document_id, org_id=org.id).first() is None:
        raise HTTPException(status_code=404, detail="Document not found")

    client = get_kg_client()
    versions = find_document_version_history(client, document_id)
    return KGVersionHistoryResponse(document_id=document_id, versions=versions)
