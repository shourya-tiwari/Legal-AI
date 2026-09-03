# backend/app/services/model_router/__init__.py
"""
Model Router (docs/v2/AI_STACK.md) -- the single point every service calls to
reach a model. Provider-agnostic: services name a *task* and a *sensitivity*,
never a vendor or a model. The router resolves a (provider, model) binding
from a declarative policy (app/policies/routing.yaml), defaulting to
self-hosted providers (Class A/B); a commercial API (Class C) is used only
when explicitly enabled and only for non-sensitive tiers.

Public API:
  generate_content(prompt, *, task=..., sensitivity=..., model=..., hard=..., **cfg) -> str
  embed_content(contents, *, task=..., model=...) -> EmbedResult (.embeddings[i].values)
  rerank(query, documents, *, top_k=...) -> RerankResult
  entailment(pairs, *, task="verify_nli") -> EntailResult  (NLI: (premise, hypothesis) -> label)
  ner_extract(text, labels, *, task="ner_extract") -> NERResult  (zero-shot entity spans)
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
    EntailRequest,
    EntailResult,
    GenerateRequest,
    HostingClass,
    ModelRouterError,
    NERRequest,
    NERResult,
    RerankRequest,
    RerankResult,
    SensitivityTier,
)

__all__ = [
    "generate_content",
    "embed_content",
    "rerank",
    "entailment",
    "ner_extract",
    "is_external_permitted",
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
    "EntailRequest",
    "NERRequest",
]


def is_external_permitted(sensitivity: "str | SensitivityTier | None") -> bool:
    """Would an external (Class C) provider ever be usable for a request at
    this sensitivity tier, given the current settings + routing policy?
    Routes use this to surface `external_providers_permitted` without making
    a call. `confidential`/`privileged` always return False."""
    from app.config import get_settings

    settings = get_settings()
    if not settings.EXTERNAL_PROVIDERS_ENABLED or settings.STRICT_LOCAL_ONLY:
        return False
    tier = SensitivityTier.coerce(sensitivity)
    return tier.value in get_policy().class_c_allowed_tiers


def generate_content(
    prompt: str,
    *,
    model: Optional[str] = None,
    task: str = "generic",
    sensitivity: "str | SensitivityTier | None" = SensitivityTier.INTERNAL,
    hard: bool = False,
    **config_kwargs,
) -> str:
    """Back-compatible text generation. Returns the generated string.
    `hard=True` asks the policy to escalate to a bigger self-hosted model
    (docs/v2/AI_STACK.md) -- callers set it from a task-difficulty signal."""
    temperature = config_kwargs.pop("temperature", None)
    max_output_tokens = config_kwargs.pop("max_output_tokens", None)
    req = GenerateRequest(
        prompt=prompt,
        task=task,
        sensitivity=SensitivityTier.coerce(sensitivity),
        model=model,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        hard=hard,
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


def entailment(
    pairs: Sequence[tuple],
    *,
    task: str = "verify_nli",
    model: Optional[str] = None,
) -> EntailResult:
    """NLI over (premise, hypothesis) pairs. Raises ModelRouterError if no
    entailment provider is available (the caller decides whether to degrade)."""
    req = EntailRequest(pairs=[tuple(p) for p in pairs], task=task, model=model)
    return get_router().entail(req)


def ner_extract(
    text: str,
    labels: Sequence[str],
    *,
    task: str = "ner_extract",
    model: Optional[str] = None,
    threshold: float = 0.5,
) -> NERResult:
    """Zero-shot entity extraction. Raises ModelRouterError if no NER provider
    is available."""
    req = NERRequest(text=text, labels=list(labels), task=task, model=model, threshold=threshold)
    return get_router().extract_entities(req)
