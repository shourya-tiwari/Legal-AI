from __future__ import annotations

import json
from typing import List, Dict

from app.services.model_router import generate_content
from app.services.risk_radar.rules import RISKY_TERMS, find_keyword_flags

def _call_gemini_for_risk(clause_text: str) -> List[Dict]:
    # Prompt simplified and corrected to actually inject the clause
    prompt_text = (
        "Highlight potential high-risk terms in this clause and return JSON only.\n"
        'Format: {"flags":[{"term":"...","explanation":"..."}]}\n'
        f'Clause: "{clause_text}"'
    )
    try:
        output_text = generate_content(prompt_text, task="risk_analysis") or ""
        try:
            parsed = json.loads(output_text)
            return parsed.get("flags", []) if isinstance(parsed, dict) else []
        except Exception:
            return []
    except Exception:
        return []

def generate_risk_radar_response(clause_text: str) -> Dict:
    keyword_flags = find_keyword_flags(clause_text, RISKY_TERMS)
    contextual_flags = _call_gemini_for_risk(clause_text)
    risk_count = len(keyword_flags) + len(contextual_flags)
    return {
        "flagged_clauses": [
            {
                "clause": clause_text,
                "keyword_flags": keyword_flags,
                "contextual_flags": contextual_flags,
            }
        ],
        "risk_summary": (
            f"{risk_count} high-risk terms detected: "
            f"{len(keyword_flags)} keyword-based, "
            f"{len(contextual_flags)} contextual."
        ),
    }
