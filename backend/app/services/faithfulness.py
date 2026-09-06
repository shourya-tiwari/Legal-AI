# backend/app/services/faithfulness.py
"""
Shared faithfulness (hallucination) checking: is a generated claim actually
*entailed* by its source text, or does it just share a topic with it?

Extracted from `app/agents/verifier.py` (where this logic originated, Phase
6) so it has exactly one implementation shared by two consumers:

- `app/agents/verifier.py` -- the mandatory gate on the agent pipeline's
  `agent_summary` output.
- `app/services/chatbot.py` -- the QA path (`POST /api/ask`), which is the
  single most-used feature in the product and, until now, had zero
  faithfulness verification despite this exact capability already existing
  and being tested. A service module depending on an agent module would
  invert this codebase's layering (services sit below agents), which is why
  this lives here rather than `chatbot.py` importing from `agents/verifier.py`.

Two implementations, always the same fallback order:
1. Real NLI (entailment) via the Model Router `verify_nli` task (Class A,
   local DeBERTa/ModernBERT head, `providers/nli_local.py`). Splits the
   candidate text into claim sentences and checks each against the source
   texts.
2. Lexical-overlap fallback (`_lexical_overlap_faithfulness`) when the NLI
   head isn't installed (`requirements-local.txt` absent) -- a much weaker
   signal, always labelled as such via `FaithfulnessResult.method`.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import List, Tuple

from app.services.model_router import ModelRouterError, entailment
from app.services.nlp.segmentation import split_sentences

logger = logging.getLogger("legalai.services.faithfulness")

MIN_OVERLAP_RATIO = 0.15
_WORD_RE = re.compile(r"[a-z]{4,}")  # 4+ letters: crude, cheap stopword skip

# NLI thresholds. A claim is "supported" if some source entails it with
# probability >= _ENTAIL_MIN. A claim is a hard failure if some source
# contradicts it with probability >= _CONTRADICT_MIN.
_ENTAIL_MIN = 0.55
_CONTRADICT_MIN = 0.55
# Tolerate this fraction of merely-unsupported (neutral) claims -- text often
# restates facts not present in the specific sources it's being checked
# against (e.g. connective/framing sentences).
_MAX_UNSUPPORTED_RATIO = 0.5
_MIN_CLAIM_CHARS = 25  # skip trivially short fragments


@dataclass
class FaithfulnessResult:
    ok: bool
    method: str  # "nli" | "lexical_fallback"
    unsupported_claims: List[str] = field(default_factory=list)


def _significant_words(text: str) -> set[str]:
    return set(_WORD_RE.findall(text.lower()))


def _lexical_overlap_faithfulness(text: str, source_texts: List[str]) -> bool:
    """NOT a real entailment check -- the fallback when the NLI head is
    absent. Returns True if there's nothing to check (no sources) or if the
    text shares a minimum fraction of its vocabulary with the sources."""
    if not source_texts:
        return True
    text_words = _significant_words(text)
    if not text_words:
        return True
    source_words: set[str] = set()
    for src in source_texts:
        source_words |= _significant_words(src)
    overlap = text_words & source_words
    return (len(overlap) / len(text_words)) >= MIN_OVERLAP_RATIO


def _nli_faithfulness(text: str, source_texts: List[str]) -> Tuple[bool, List[str]]:
    """Real entailment check. Returns (faithfulness_ok, unsupported_claims).
    Raises ModelRouterError if no entailment provider is available."""
    claims = [s for s in split_sentences(text) if len(s) >= _MIN_CLAIM_CHARS]
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


MAX_SOURCE_SENTENCES = 15


def select_relevant_sources(text: str, corpus: str, *, max_sources: int = MAX_SOURCE_SENTENCES) -> List[str]:
    """Split `corpus` into sentences and keep the `max_sources` most
    vocabulary-relevant to `text` (cheap, deterministic pre-filter, same
    overlap technique as `_lexical_overlap_faithfulness`). Exists so a
    faithfulness check never sends a whole, possibly very long, document to
    the NLI model as one oversized premise (it would just get truncated,
    likely losing the actually-relevant part) and so a check's cost doesn't
    scale with document length. If `corpus` already fits within
    `max_sources` sentences, returns all of them unfiltered."""
    sentences = split_sentences(corpus)
    if len(sentences) <= max_sources:
        return sentences
    text_words = _significant_words(text)
    ranked = sorted(sentences, key=lambda s: -len(text_words & _significant_words(s)))
    return ranked[:max_sources]


def check_faithfulness(text: str, source_texts: List[str]) -> FaithfulnessResult:
    """Public entrypoint: real NLI check, degrading to the lexical-overlap
    fallback when no entailment provider is available. Never raises --
    callers get an honest `method` field instead of an exception either way."""
    try:
        ok, unsupported = _nli_faithfulness(text, source_texts)
        return FaithfulnessResult(ok=ok, method="nli", unsupported_claims=unsupported)
    except ModelRouterError as e:
        logger.info("NLI faithfulness head unavailable (%s); using lexical-overlap fallback.", e)
        ok = _lexical_overlap_faithfulness(text, source_texts)
        return FaithfulnessResult(ok=ok, method="lexical_fallback", unsupported_claims=[])
