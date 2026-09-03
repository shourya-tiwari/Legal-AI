# backend/app/routes/chatbot.py

import logging

from fastapi import APIRouter, Depends, HTTPException
from app.auth import OrgContext
from app.guard import api_guard
from app.models import AskRequest, AskResponse
from app.services.chatbot import answer_question
from app.services.sensitivity import classify_sensitivity

logger = logging.getLogger("legalai.routes.ask")

# Set the prefix once; include this router in main.py without another prefix
router = APIRouter(tags=["chatbot"])

@router.post("/ask", response_model=AskResponse, summary="Ask Question Endpoint")
def ask_question_endpoint(request: AskRequest, org: OrgContext = Depends(api_guard)) -> AskResponse:
    """
    Accepts {"contract_text": "...", "question": "..."} and returns {"answer": "..."}.
    """
    try:
        # Pass the exact fields: question + contract_text (as context)
        return answer_question(question=request.question, context=request.contract_text,
                               sensitivity=classify_sensitivity(request.contract_text).tier)
    except Exception as e:
        logger.exception("Chatbot service error")
        raise HTTPException(status_code=500, detail="Chatbot service error")
