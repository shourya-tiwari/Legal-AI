# backend/app/services/chatbot.py
from __future__ import annotations

import re

from .model_router import generate_content
from app.models import AskResponse

# Multi-hop / comparative questions benefit from the bigger self-hosted model
# (docs/v2/AI_STACK.md "Escalation without a bigger vendor"). A cheap heuristic:
# the question compares, counts, or chains conditions.
_MULTIHOP_RE = re.compile(
    r"\b(compare|difference|differ|versus|vs\.?|both|all of|each of|"
    r"how many|which of|conflict|inconsistent|and also|as well as)\b",
    re.IGNORECASE,
)


def _looks_multihop(question: str) -> bool:
    return bool(_MULTIHOP_RE.search(question)) or question.count("?") > 1

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

    answer = generate_content(prompt, task="qa", temperature=temperature,
                              hard=_looks_multihop(question))
    return AskResponse(answer=answer)
