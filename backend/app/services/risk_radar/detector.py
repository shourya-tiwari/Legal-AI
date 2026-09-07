from __future__ import annotations

import json
from typing import List, Dict

from app.services.model_router import generate_content
from app.services.risk_radar.rules import RISK_CATEGORIES, RISK_CATEGORY_NAMES, RISKY_TERMS, find_keyword_flags

def _ai_risk_flags(clause_text: str, sensitivity: str = "internal") -> List[Dict]:
    # The AI risk pass -- routed via the Model Router (not Gemini-specific).
    prompt_text = (
        "Highlight potential high-risk terms in this clause and return JSON only.\n"
        'Format: {"flags":[{"term":"...","explanation":"..."}]}\n'
        f'Clause: "{clause_text}"'
    )
    try:
        output_text = generate_content(prompt_text, task="risk_analysis",
                                       sensitivity=sensitivity) or ""
        try:
            parsed = json.loads(output_text)
            return parsed.get("flags", []) if isinstance(parsed, dict) else []
        except Exception:
            return []
    except Exception:
        return []

def generate_risk_dashboard(clauses: List) -> Dict:
    """Per-category risk-flag counts across every clause in a document, for
    the Risk Dashboard spider/radar chart (docs/v2/ROADMAP.md Phase 8,
    docs/v2/FRONTEND.md's flagged gap). Rule-based only (Tier 0 keyword
    sweep, `find_keyword_flags`) -- the AI risk pass is a per-clause Gemini
    call and isn't invoked here, same posture as `risk_compliance.py`'s
    agent-level sweep.

    `clauses` is a list of ClauseObject (or anything with `.id`/`.text`) --
    typed loosely here rather than importing app.services.nlp.schema, to
    keep this module import-light the way the rest of risk_radar/ already is.

    Every category in RISK_CATEGORY_NAMES is always present in the output
    (zero-filled if nothing was flagged) so the frontend's radar chart has a
    stable, complete set of axes to draw regardless of what a given
    document actually triggers -- a chart with a variable axis count from
    one document to the next would be far harder to read or compare."""
    category_counts: Dict[str, int] = {name: 0 for name in RISK_CATEGORY_NAMES}
    clause_level: List[Dict] = []

    for clause in clauses:
        flags = find_keyword_flags(clause.text, RISKY_TERMS)
        for flag in flags:
            category = RISK_CATEGORIES.get(flag["term"], "Uncategorized")
            category_counts[category] = category_counts.get(category, 0) + 1
            clause_level.append({
                "clause_id": clause.id,
                "category": category,
                "term": flag["term"],
                "explanation": flag["predefined_explanation"],
            })

    return {
        "categories": category_counts,
        "total_flags": sum(category_counts.values()),
        "clause_findings": clause_level,
    }


def generate_risk_radar_response(clause_text: str, *, sensitivity: str = "internal") -> Dict:
    keyword_flags = find_keyword_flags(clause_text, RISKY_TERMS)
    contextual_flags = _ai_risk_flags(clause_text, sensitivity)
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
