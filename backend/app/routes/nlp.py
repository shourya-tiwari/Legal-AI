from fastapi import APIRouter, Depends

from app.auth import OrgContext
from app.guard import api_guard
from app.models import NlpAnalyzeRequest, NlpAnalyzeResponse
from app.services.nlp.pipeline import build_clause_objects

router = APIRouter(tags=["nlp"])


@router.post("/nlp/analyze", response_model=NlpAnalyzeResponse, summary="Structured Clause Analysis")
def analyze_contract(req: NlpAnalyzeRequest, org: OrgContext = Depends(api_guard)) -> NlpAnalyzeResponse:
    clauses = build_clause_objects(req.contract_text, use_ai_escalation=req.use_ai_escalation)
    return NlpAnalyzeResponse(clauses=clauses)
