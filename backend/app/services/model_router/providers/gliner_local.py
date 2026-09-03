# backend/app/services/model_router/providers/gliner_local.py
"""
GLiNER zero-shot NER provider -- Class B.

Phase 6's NER default (docs/v2/MODEL_STACK.md "Zero-shot / configurable NER |
GLiNER family"): one model, entity types specified at inference time. Covers
"party", "governing-law jurisdiction", "monetary amount", "statute citation",
"date/duration" without a fine-tune.

`app/services/nlp/entities.py` keeps its regex money/jurisdiction extraction
as the always-on Class-A floor and MERGES GLiNER's spans when this provider is
available -- so an install without `gliner` still extracts entities, just fewer
types.

The only place `gliner` is imported -- inside providers/ per the isolation
contract. Optional dependency (`requirements-local.txt`).
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import List

from app.config import get_settings

from ..base import ModelProvider
from ..types import (
    HostingClass,
    NERRequest,
    NERResult,
    ProviderCard,
    ProviderUnavailable,
)

logger = logging.getLogger("legalai.model_router.gliner")

_MAX_CHARS = 6000


def _gliner_available() -> bool:
    try:
        import gliner  # noqa: F401
        return True
    except Exception:
        return False


@lru_cache(maxsize=2)
def _load(model_name: str):
    from gliner import GLiNER

    model = GLiNER.from_pretrained(model_name)
    try:
        import torch

        if torch.cuda.is_available():
            model = model.to("cuda")
    except Exception:  # pragma: no cover
        pass
    logger.info("GLiNER model loaded: %s", model_name)
    return model


class GLiNERProvider(ModelProvider):
    name = "local-ner"
    hosting_class = HostingClass.B

    def __init__(self, model_name: str | None = None) -> None:
        self._model_name = model_name or get_settings().NER_MODEL

    def describe(self) -> ProviderCard:
        return ProviderCard(
            name=self.name,
            hosting_class=HostingClass.B,
            capabilities=["ner"],
            leaves_perimeter=False,
            models=[self._model_name],
            note="GLiNER zero-shot NER -- entity types chosen at call time. "
                 "Optional (`requirements-local.txt`); regex extraction is the floor without it.",
        )

    def is_available(self) -> bool:
        return get_settings().NER_ENABLED and _gliner_available()

    def extract_entities(self, req: NERRequest) -> NERResult:
        if not self.is_available():
            raise ProviderUnavailable(
                "local-ner: `gliner` not installed or NER_ENABLED=false "
                "(pip install -r requirements-local.txt)"
            )
        model_name = req.model or self._model_name
        text = (req.text or "")[:_MAX_CHARS]
        if not text.strip() or not req.labels:
            return NERResult(entities=[], provider=self.name, model=model_name,
                             hosting_class=HostingClass.B)
        try:
            model = _load(model_name)
            raw = model.predict_entities(text, list(req.labels), threshold=req.threshold)
        except Exception as e:
            raise ProviderUnavailable(f"local-ner: inference failed: {e}") from e
        entities: List[dict] = [
            {
                "text": e["text"],
                "type": e["label"],
                "score": float(e.get("score", 1.0)),
                "start": int(e.get("start", -1)),
                "end": int(e.get("end", -1)),
            }
            for e in raw
        ]
        return NERResult(entities=entities, provider=self.name, model=model_name,
                         hosting_class=HostingClass.B)
