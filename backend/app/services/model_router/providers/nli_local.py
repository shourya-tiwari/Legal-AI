# backend/app/services/model_router/providers/nli_local.py
"""
Local NLI (natural-language inference) provider -- Class A.

Phase 6's real faithfulness head for the Verifier agent (docs/v2/AGENTS.md,
docs/v2/AI_STACK.md: "NLI faithfulness (Verifier) | Local DeBERTa/ModernBERT
NLI head (Class A) | This must be local and deterministic -- it is a safety
gate, not a generation task").

It replaces app/agents/verifier.py's lexical-overlap stand-in: given a claim
(hypothesis) and a retrieved source (premise), does the source actually
*entail* the claim, or does it just share vocabulary with it?

The ONLY place `transformers` is imported for this -- kept inside providers/
per the isolation contract (tests/test_provider_isolation.py). Optional
dependency (`requirements-local.txt`); when it's absent the router has no
`entail` provider and the Verifier falls back to lexical overlap, honestly
labelled.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import List, Tuple

from app.config import get_settings

from ..base import ModelProvider
from ..types import (
    EntailRequest,
    EntailResult,
    HostingClass,
    ProviderCard,
    ProviderUnavailable,
)

logger = logging.getLogger("legalai.model_router.nli")

# Canonical 3-class NLI label set. A model whose id2label differs is remapped
# by substring match in _label_order().
_CANONICAL = ("entailment", "neutral", "contradiction")
_MAX_CHARS = 4000  # premise+hypothesis are truncated by the tokenizer anyway; cap the string first


def _torch_and_transformers_available() -> bool:
    try:
        import torch  # noqa: F401
        import transformers  # noqa: F401
        return True
    except Exception:
        return False


@lru_cache(maxsize=2)
def _load(model_name: str):
    import torch
    import transformers
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    transformers.logging.set_verbosity_error()
    tok = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = model.to(device).eval()
    order = _label_order(model.config.id2label)
    logger.info("NLI head loaded: %s on %s (label order %s)", model_name, device, order)
    return tok, model, device, order


def _label_order(id2label: dict) -> List[str]:
    """Map the model's output positions to the canonical labels."""
    out: List[str] = []
    for i in range(len(id2label)):
        raw = str(id2label[i]).lower()
        match = next((c for c in _CANONICAL if c in raw or raw in c), None)
        out.append(match or raw)
    return out


class TransformersNLIProvider(ModelProvider):
    name = "local-nli"
    hosting_class = HostingClass.A

    def __init__(self, model_name: str | None = None) -> None:
        self._model_name = model_name or get_settings().NLI_MODEL

    def describe(self) -> ProviderCard:
        return ProviderCard(
            name=self.name,
            hosting_class=HostingClass.A,
            capabilities=["entail"],
            leaves_perimeter=False,
            models=[self._model_name],
            note="Local DeBERTa/ModernBERT NLI head -- the Verifier's faithfulness "
                 "safety gate. Deterministic, offline. Optional (`requirements-local.txt`).",
        )

    def is_available(self) -> bool:
        return get_settings().NLI_ENABLED and _torch_and_transformers_available()

    def entail(self, req: EntailRequest) -> EntailResult:
        if not self.is_available():
            raise ProviderUnavailable(
                "local-nli: transformers/torch not installed or NLI_ENABLED=false "
                "(pip install -r requirements-local.txt)"
            )
        model_name = req.model or self._model_name
        if not req.pairs:
            return EntailResult(labels=[], scores=[], provider=self.name,
                                model=model_name, hosting_class=HostingClass.A)
        try:
            import torch

            tok, model, device, order = _load(model_name)
            premises = [str(p)[:_MAX_CHARS] for p, _ in req.pairs]
            hypotheses = [str(h)[:_MAX_CHARS] for _, h in req.pairs]
            labels: List[str] = []
            scores: List[float] = []
            batch = 16
            with torch.no_grad():
                for i in range(0, len(premises), batch):
                    enc = tok(
                        premises[i:i + batch], hypotheses[i:i + batch],
                        return_tensors="pt", padding=True, truncation=True, max_length=512,
                    ).to(device)
                    probs = torch.softmax(model(**enc).logits, dim=-1)
                    for row in probs:
                        j = int(row.argmax())
                        labels.append(order[j])
                        scores.append(float(row[j]))
        except ProviderUnavailable:
            raise
        except Exception as e:  # a model/runtime failure -> skip to nothing (no other entail provider)
            raise ProviderUnavailable(f"local-nli: inference failed: {e}") from e
        return EntailResult(labels=labels, scores=scores, provider=self.name,
                            model=model_name, hosting_class=HostingClass.A)
