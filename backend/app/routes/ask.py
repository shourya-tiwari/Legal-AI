# backend/app/routes/ask.py

from fastapi import APIRouter, Depends

from app.auth import OrgContext
from app.guard import api_guard
from app.models import AskRequest, AskResponse
from app.services.chatbot import answer_question
from app.services.sensitivity import classify_sensitivity

router = APIRouter(tags=["chatbot"])


@router.post("/ask", response_model=AskResponse, summary="Ask Question Endpoint")
def ask_question_endpoint(request: AskRequest, org: OrgContext = Depends(api_guard)) -> AskResponse:
    """Accepts {"contract_text": "...", "question": "..."} and returns an answer
    grounded on the contract text (+ a faithfulness check -- see AskResponse)."""
    return answer_question(
        question=request.question,
        context=request.contract_text,
        sensitivity=classify_sensitivity(request.contract_text).tier,
    )
