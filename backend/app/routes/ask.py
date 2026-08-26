# backend/app/routes/chatbot.py

import logging

from fastapi import APIRouter, HTTPException
from app.models import AskRequest, AskResponse
from app.services.chatbot import answer_question

logger = logging.getLogger("legalai.routes.ask")

# Set the prefix once; include this router in main.py without another prefix
router = APIRouter(tags=["chatbot"])

@router.post("/ask", response_model=AskResponse, summary="Ask Question Endpoint")
def ask_question_endpoint(request: AskRequest) -> AskResponse:
    """
    Accepts {"contract_text": "...", "question": "..."} and returns {"answer": "..."}.
    """
    try:
        # Pass the exact fields: question + contract_text (as context)
        return answer_question(question=request.question, context=request.contract_text)
    except Exception as e:
        logger.exception("Chatbot service error")
        raise HTTPException(status_code=500, detail="Chatbot service error")
