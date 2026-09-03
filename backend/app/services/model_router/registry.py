# backend/app/services/model_router/registry.py
"""
Provider registry: instantiates the provider objects named in the routing
policy. A provider whose SDK/dependency is missing (e.g. `google-genai` not
installed in an on-prem build) is simply absent from the registry -- the
router then skips any policy candidate that resolves to nothing.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Dict, Optional

from .base import ModelProvider
from .providers import (
    HashingEmbeddingProvider,
    LexicalReranker,
    OpenAICompatProvider,
    SentenceTransformerProvider,
    load_gemini_provider,
)

logger = logging.getLogger("legalai.model_router.registry")


def _build() -> Dict[str, ModelProvider]:
    providers: Dict[str, ModelProvider] = {
        "local-llm": OpenAICompatProvider("local-llm", role="llm"),
        "local-embed-remote": OpenAICompatProvider("local-embed-remote", role="embed"),
        "local-rerank-remote": OpenAICompatProvider("local-rerank-remote", role="rerank"),
        "local-embed-neural": SentenceTransformerProvider(),
        "local-rerank-neural": SentenceTransformerProvider(),
        "local-embed-hash": HashingEmbeddingProvider(),
        "local-rerank-lexical": LexicalReranker(),
    }

    gemini = load_gemini_provider()
    if gemini is not None:
        providers["gemini"] = gemini
        logger.info("Gemini provider registered (providers-external present).")
    else:
        logger.info("Gemini provider NOT registered (providers-external not installed) -- "
                    "the product runs on self-hosted providers only.")

    return providers


@lru_cache
def get_registry() -> Dict[str, ModelProvider]:
    return _build()


def get_provider(name: str) -> Optional[ModelProvider]:
    return get_registry().get(name)


def reset_registry_cache() -> None:
    """Test helper -- lets a test flip settings and rebuild the registry."""
    get_registry.cache_clear()
