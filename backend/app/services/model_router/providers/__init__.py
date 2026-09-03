# backend/app/services/model_router/providers/__init__.py
"""
Provider adapters -- the ONLY place in the codebase allowed to import a
model backend's SDK (google.genai, openai, anthropic, sentence_transformers,
vllm, ...). Enforced by tests/test_provider_isolation.py.

Conceptually two packages (docs/v2/AI_STACK.md "Provider packaging"):
  legalai-providers-core     -- openai_compat, local           (always installed)
  legalai-providers-external -- gemini (+ future openai/claude) (optional plugin,
                                absent in on-prem/air-gapped builds)
"""
from .gliner_local import GLiNERProvider
from .local import (
    HashingEmbeddingProvider,
    LexicalReranker,
    SentenceTransformerProvider,
)
from .nli_local import TransformersNLIProvider
from .openai_compat import OpenAICompatProvider

__all__ = [
    "HashingEmbeddingProvider",
    "LexicalReranker",
    "SentenceTransformerProvider",
    "OpenAICompatProvider",
    "TransformersNLIProvider",
    "GLiNERProvider",
    "load_gemini_provider",
]


def load_gemini_provider():
    """Import the external Gemini provider lazily. Returns a GeminiProvider
    instance, or None if `google-genai` is not installed (the normal state
    in an on-prem / air-gapped build)."""
    try:
        from .gemini import GeminiProvider, sdk_available

        if not sdk_available():
            return None
        return GeminiProvider()
    except Exception:
        return None
