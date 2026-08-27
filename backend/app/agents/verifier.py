# backend/app/agents/verifier.py
"""
Verifier/Critic agent: the mandatory gate before any output is considered
final (docs/v2/AGENTS.md). Three checks, two real and one an honest
stand-in:

1. Citation check (real) -- reuses services/rag/citation_validator.py to
   catch a [N] the summary referenced but was never given.
2. KG consistency (real) -- a cross-document conflict found by the Risk &
   Compliance agent always forces human review; the Verifier doesn't
   re-derive this, it just enforces that it can't be silently dropped.
3. Faithfulness check (STAND-IN, not real) -- docs/v2/AGENTS.md specifies an
   NLI (entailment) model for this: does the summary's claim actually follow
   from the cited source, not just share a topic with it. That needs a
   trained cross-encoder and is deferred to the GPU Upgrade phase
   (docs/v2/ROADMAP.md). What runs here instead is lexical overlap between
   the summary and its cited sources' text -- a much weaker signal (catches
   "cites something with zero shared vocabulary," nothing more) reported
   honestly as `faithfulness_ok`, not dressed up as entailment-checked.
"""
from __future__ import annotations

import re
from typing import List

from app.services.rag.citation_validator import find_invalid_citations

from .state import AgentStep, CaseState

MIN_OVERLAP_RATIO = 0.15
_WORD_RE = re.compile(r"[a-z]{4,}")  # 4+ letters: crude, cheap stopword skip


def _significant_words(text: str) -> set[str]:
    return set(_WORD_RE.findall(text.lower()))


def _lexical_overlap_faithfulness(summary: str, source_texts: List[str]) -> bool:
    """NOT a real entailment check -- see module docstring. Returns True if
    there's nothing to check (no sources cited) or if the summary shares a
    minimum fraction of its vocabulary with the cited sources combined."""
    if not source_texts:
        return True
    summary_words = _significant_words(summary)
    if not summary_words:
        return True
    source_words: set[str] = set()
    for text in source_texts:
        source_words |= _significant_words(text)
    overlap = summary_words & source_words
    return (len(overlap) / len(summary_words)) >= MIN_OVERLAP_RATIO


def run_verifier(state: CaseState) -> dict:
    invalid_citations = find_invalid_citations(state.summary, num_hints=state.summary_citation_count)

    all_source_texts = [
        entry["text"] for clause_citations in state.research_citations.values() for entry in clause_citations
    ]
    faithfulness_ok = _lexical_overlap_faithfulness(state.summary, all_source_texts)

    needs_human_review = bool(invalid_citations) or bool(state.kg_conflicts) or not faithfulness_ok

    step = AgentStep(
        agent_name="verifier",
        input_summary=f"summary citing up to {state.summary_citation_count} sources",
        output_summary=(
            f"invalid_citations={invalid_citations} faithfulness_ok={faithfulness_ok} "
            f"needs_human_review={needs_human_review}"
        ),
    )

    return {
        "invalid_citation_numbers": invalid_citations,
        "faithfulness_ok": faithfulness_ok,
        "needs_human_review": needs_human_review,
        "trace": state.trace + [step],
    }
