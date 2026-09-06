# backend/app/agents/verifier.py
"""
Verifier/Critic agent: the mandatory gate before any output is considered
final (docs/v2/AGENTS.md). Three checks, all now real:

1. Citation check -- reuses services/rag/citation_validator.py to catch a [N]
   the summary referenced but was never given.
2. KG consistency -- a cross-document conflict found by the Risk & Compliance
   agent always forces human review; the Verifier enforces it can't be
   silently dropped.
3. Faithfulness check (Phase 6) -- `app/services/faithfulness.py`'s real NLI
   (entailment) check via the Model Router `verify_nli` task (Class A, local
   DeBERTa/ModernBERT head), degrading to a lexical-overlap fallback when the
   head isn't installed. Extracted to a shared service module so
   `app/services/chatbot.py`'s `/api/ask` path can reuse the exact same
   check (a cross-cutting agent-quality improvement, `LEARNING_LOG.md` #33)
   -- this Verifier used to be the only consumer.
"""
from __future__ import annotations

from app.services.faithfulness import check_faithfulness
from app.services.rag.citation_validator import find_invalid_citations

from .state import AgentStep, CaseState


def run_verifier(state: CaseState) -> dict:
    invalid_citations = find_invalid_citations(state.summary, num_hints=state.summary_citation_count)

    source_texts = [
        entry["text"]
        for clause_citations in state.research_citations.values()
        for entry in clause_citations
    ]

    result = check_faithfulness(state.summary, source_texts)

    needs_human_review = (
        bool(invalid_citations) or bool(state.kg_conflicts) or not result.ok
    )

    step = AgentStep(
        agent_name="verifier",
        input_summary=f"summary citing up to {state.summary_citation_count} sources",
        output_summary=(
            f"invalid_citations={invalid_citations} faithfulness_ok={result.ok} "
            f"method={result.method} unsupported_claims={len(result.unsupported_claims)} "
            f"needs_human_review={needs_human_review}"
        ),
    )

    return {
        "invalid_citation_numbers": invalid_citations,
        "faithfulness_ok": result.ok,
        "faithfulness_method": result.method,
        "unsupported_claims": result.unsupported_claims,
        "needs_human_review": needs_human_review,
        "trace": state.trace + [step],
    }
