# backend/app/services/chatbot.py
from __future__ import annotations

from .genai_client import generate_content
from app.models import AskResponse

SYSTEM_INSTRUCTIONS = (
    "You are a helpful legal assistant. Answer ONLY using the provided contract text. "
    "If the answer is not in the text, reply exactly: 'The answer is not found in the document.' "
    "After the answer, include 1 to 3 short quotes from the text that support it. "
    "Return a single concise sentence; do not repeat lines or include quoted echoes."
)

def answer_question(question: str, context: str, temperature: float = 0.2) -> AskResponse:
    """
    Single-turn QA grounded on the given contract context.
    """
    prompt = f"""{SYSTEM_INSTRUCTIONS}

Contract Text:
---
{context}
---

Question: {question}

Answer:
""".strip()

    answer = generate_content(prompt, temperature=temperature)
    return AskResponse(answer=answer)
