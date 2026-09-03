# backend/app/agents/verifier.py
"""
Verifier/Critic agent: the mandatory gate before any output is considered
final (docs/v2/AGENTS.md). Three checks, all now real:

1. Citation check -- reuses services/rag/citation_validator.py to catch a [N]
   the summary referenced but was never given.
2. KG consistency -- a cross-document conflict found by the Risk & Compliance
   agent always forces human review; the Verifier enforces it can't be
   silently dropped.
3. Faithfulness check (Phase 6) -- a real NLI (entailment) model via the
   Model Router `verify_nli` task (Class A, local DeBERTa/ModernBERT head,
   app/services/model_router/providers/nli_local.py). Each claim sentence of
   the generated summary is checked against the retrieved sources: does a
   source actually *entail* the claim, or does it just share a topic with it?
   A `contradiction` or an unsupported (`neutral`) claim fails the check and
   lands in `unsupported_claims`.

   If the NLI head isn't installed (`requirements-local.txt` absent) the
   check degrades to `_lexical_overlap_faithfulness` -- a much weaker signal
   -- and `faithfulness_method` is set to `"lexical_fallback"` so the
   weakening is visible, not hidden.
"""
from __future__ import annotations

import logging
import re
from typing import List, Tuple

from app.services.model_router import ModelRouterError, entailment
from app.services.nlp.segmentation import split_sentences
from app.services.rag.citation_validator import find_invalid_citations

from .state import AgentStep, CaseState

logger = logging.getLogger("legalai.agents.verifier")

MIN_OVERLAP_RATIO = 0.15
_WORD_RE = re.compile(r"[a-z]{4,}")  # 4+ letters: crude, cheap stopword skip

# NLI thresholds. A claim is "supported" if some source entails it with
# probability >= _ENTAIL_MIN. A claim is a hard failure if some source
# contradicts it with probability >= _CONTRADICT_MIN.
_ENTAIL_MIN = 0.55
_CONTRADICT_MIN = 0.55
# Tolerate this fraction of merely-unsupported (neutral) claims -- a summary
# often restates document facts not in the retrieved *external* sources.
_MAX_UNSUPPORTED_RATIO = 0.5
_MIN_CLAIM_CHARS = 25  # skip trivially short fragments


def _significant_words(text: str) -> set[str]:
    return set(_WORD_RE.findall(text.lower()))


def _lexical_overlap_faithfulness(summary: str, source_texts: List[str]) -> bool:
    """NOT a real entailment check -- the fallback when the NLI head is absent.
    Returns True if there's nothing to check (no sources) or if the summary
    shares a minimum fraction of its vocabulary with the cited sources."""
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


def _nli_faithfulness(summary: str, source_texts: List[str]) -> Tuple[bool, List[str]]:
    """Real entailment check. Returns (faithfulness_ok, unsupported_claims).
    Raises ModelRouterError if no entailment provider is available."""
    claims = [s for s in split_sentences(summary) if len(s) >= _MIN_CLAIM_CHARS]
    if not claims or not source_texts:
        return True, []

    # One (source, claim) pair per combination; take the best label per claim.
    pairs = [(src, claim) for claim in claims for src in source_texts]
    result = entailment(pairs)  # may raise ModelRouterError

    per_claim = len(source_texts)
    unsupported: List[str] = []
    contradicted = False
    for i, claim in enumerate(claims):
        window = list(zip(result.labels[i * per_claim:(i + 1) * per_claim],
                          result.scores[i * per_claim:(i + 1) * per_claim]))
        entailed = any(l == "entailment" and s >= _ENTAIL_MIN for l, s in window)
        contradicts = any(l == "contradiction" and s >= _CONTRADICT_MIN for l, s in window)
        if contradicts:
            contradicted = True
            unsupported.append(claim)
        elif not entailed:
            unsupported.append(claim)

    unsupported_ratio = len(unsupported) / len(claims)
    faithfulness_ok = (not contradicted) and unsupported_ratio <= _MAX_UNSUPPORTED_RATIO
    return faithfulness_ok, unsupported


def run_verifier(state: CaseState) -> dict:
    invalid_citations = find_invalid_citations(state.summary, num_hints=state.summary_citation_count)

    source_texts = [
        entry["text"]
        for clause_citations in state.research_citations.values()
        for entry in clause_citations
    ]

    unsupported_claims: List[str] = []
    method = "nli"
    try:
        faithfulness_ok, unsupported_claims = _nli_faithfulness(state.summary, source_texts)
    except ModelRouterError as e:
        logger.info("NLI faithfulness head unavailable (%s); using lexical-overlap fallback.", e)
        method = "lexical_fallback"
        faithfulness_ok = _lexical_overlap_faithfulness(state.summary, source_texts)

    needs_human_review = (
        bool(invalid_citations) or bool(state.kg_conflicts) or not faithfulness_ok
    )

    step = AgentStep(
        agent_name="verifier",
        input_summary=f"summary citing up to {state.summary_citation_count} sources",
        output_summary=(
            f"invalid_citations={invalid_citations} faithfulness_ok={faithfulness_ok} "
            f"method={method} unsupported_claims={len(unsupported_claims)} "
            f"needs_human_review={needs_human_review}"
        ),
    )

    return {
        "invalid_citation_numbers": invalid_citations,
        "faithfulness_ok": faithfulness_ok,
        "faithfulness_method": method,
        "unsupported_claims": unsupported_claims,
        "needs_human_review": needs_human_review,
        "trace": state.trace + [step],
    }
