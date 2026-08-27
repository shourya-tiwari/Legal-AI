# backend/app/services/model_router/__init__.py
"""
Model Router (docs/v2/AI_STACK.md) -- the single point every service calls to
reach a model. Provider-agnostic: services name a *task* and a *sensitivity*,
never a vendor or a model. The router resolves a (provider, model) binding
from a declarative policy (app/policies/routing.yaml), defaulting to
self-hosted providers (Class A/B); a commercial API (Class C) is used only
when explicitly enabled and only for non-sensitive tiers.

Public API:
  generate_content(prompt, *, task=..., sensitivity=..., model=..., **cfg) -> str
  embed_content(contents, *, task=..., model=...) -> EmbedResult (.embeddings[i].values)
  rerank(query, documents, *, top_k=...) -> RerankResult
  get_router() -> Router  (typed request/response API)

`generate_content` / `embed_content` keep V1's signatures and return shapes so
existing call sites (and their monkeypatched tests) work unchanged. They also
still raise RuntimeError on an unrecoverable model error, same as the old
genai_client, so existing `except RuntimeError` handlers keep working.
"""
from __future__ import annotations

from typing import Optional, Sequence

from .policy import get_policy
from .registry import get_registry, reset_registry_cache
from .router import get_router
from .types import (
    EmbedRequest,
    EmbedResult,
    GenerateRequest,
    HostingClass,
    ModelRouterError,
    RerankRequest,
    RerankResult,
    SensitivityTier,
)

__all__ = [
    "generate_content",
    "embed_content",
    "rerank",
    "get_router",
    "get_policy",
    "get_registry",
    "reset_registry_cache",
    "HostingClass",
    "SensitivityTier",
    "ModelRouterError",
    "GenerateRequest",
    "EmbedRequest",
    "RerankRequest",
]


def generate_content(
    prompt: str,
    *,
    model: Optional[str] = None,
    task: str = "generic",
    sensitivity: "str | SensitivityTier | None" = SensitivityTier.INTERNAL,
    **config_kwargs,
) -> str:
    """Back-compatible text generation. Returns the generated string."""
    temperature = config_kwargs.pop("temperature", None)
    max_output_tokens = config_kwargs.pop("max_output_tokens", None)
    req = GenerateRequest(
        prompt=prompt,
        task=task,
        sensitivity=SensitivityTier.coerce(sensitivity),
        model=model,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        extra=config_kwargs,
    )
    return get_router().generate(req).text


def embed_content(
    contents: Sequence[str],
    *,
    model: Optional[str] = None,
    task: str = "embed_corpus",
) -> EmbedResult:
    """Back-compatible embeddings. Returns an object with
    `.embeddings[i].values` (list[float]), matching the old Gemini shape."""
    if isinstance(contents, str):
        contents = [contents]
    req = EmbedRequest(inputs=list(contents), task=task, model=model)
    return get_router().embed(req)


def rerank(
    query: str,
    documents: Sequence[str],
    *,
    top_k: Optional[int] = None,
    task: str = "rerank",
) -> RerankResult:
    req = RerankRequest(query=query, documents=list(documents), task=task, top_k=top_k)
    return get_router().rerank(req)
