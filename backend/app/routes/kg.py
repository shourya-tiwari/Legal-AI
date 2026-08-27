from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import OrgContext
from app.db import get_db
from app.db_models import Document
from app.guard import api_guard
from app.models import KGConflictsResponse, KGIngestRequest, KGIngestResponse, KGQueryRequest, KGQueryResponse
from app.services.kg.builder import link_portfolio_terms, write_document_graph
from app.services.kg.client import get_kg_client
from app.services.kg.queries import find_clauses_using_term, find_potential_conflicts
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
    clauses = find_clauses_using_term(client, org.id, req.term)
    return KGQueryResponse(term=req.term, clauses=clauses)


@router.post("/kg/conflicts", response_model=KGConflictsResponse, summary="Find Candidate Cross-Document Conflicts")
def query_conflicts(req: KGQueryRequest, org: OrgContext = Depends(api_guard)) -> KGConflictsResponse:
    client = get_kg_client()
    conflicts = find_potential_conflicts(client, org.id, req.term)
    return KGConflictsResponse(term=req.term, conflicts=conflicts)
