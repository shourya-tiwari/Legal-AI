from fastapi import APIRouter, Depends
from app.auth import OrgContext
from app.guard import api_guard
from app.services.contextualizer.explainer import generate_contextualized_explanation
from app.services.sensitivity import classify_sensitivity
from app.models import ContextualizerRequest, ContextualizerResponse

router = APIRouter()

@router.post("/contextualize/scan", response_model=ContextualizerResponse)
def explain_clause(body: ContextualizerRequest, org: OrgContext = Depends(api_guard)) -> ContextualizerResponse:
    result = generate_contextualized_explanation(
        body.text, body.context, sensitivity=classify_sensitivity(body.text).tier)
    return ContextualizerResponse(**result)
