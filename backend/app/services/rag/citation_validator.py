# backend/app/services/rag/citation_validator.py
"""
Checks generated text for citation markers ([1], [2], ...) that don't
correspond to an actually-retrieved hint -- a cheap, mechanical guard against
the model inventing a citation number, per docs/v2/AI_STACK.md's citation-
grounded generation requirement. This does NOT verify the generated claim is
actually *entailed* by the cited hint (that's the NLI faithfulness checker
from docs/v2/AGENTS.md -- future work, needs an entailment model); it only
catches "cited something that was never given to it," a real and cheap
failure mode to guard against today.
"""
from __future__ import annotations

import re
from typing import List

_CITATION_RE = re.compile(r"\[(\d+)\]")


def find_invalid_citations(text: str, num_hints: int) -> List[int]:
    """Returns citation numbers referenced in `text` that fall outside
    1..num_hints (the range of hints actually provided) -- non-empty means
    the model referenced a source it wasn't given."""
    cited = {int(m) for m in _CITATION_RE.findall(text)}
    return sorted(n for n in cited if n < 1 or n > num_hints)
