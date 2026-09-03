# backend/app/services/model_router/base.py
"""
The one interface every model backend implements -- self-hosted or commercial.
This is the contract that keeps the rest of the system vendor-agnostic
(docs/v2/AI_STACK.md "The provider interface").

Rules enforced elsewhere:
  - no module outside model_router/providers/ imports a provider SDK
    (tests/test_provider_isolation.py)
  - services call the router by capability + task, never by provider name
"""
from __future__ import annotations

import abc
from typing import List

from .types import (
    EmbedRequest,
    EmbedResult,
    EntailRequest,
    EntailResult,
    GenerateRequest,
    GenerateResult,
    NERRequest,
    NERResult,
    ProviderCard,
    ProviderUnavailable,
    RerankRequest,
    RerankResult,
)


class ModelProvider(abc.ABC):
    """A provider implements the subset of capability methods it supports and
    advertises them via describe(). Unsupported methods raise
    NotImplementedError; an unavailable provider raises ProviderUnavailable
    from is_available()/health checks so the router can skip it."""

    name: str = "unnamed"

    @abc.abstractmethod
    def describe(self) -> ProviderCard: ...

    def is_available(self) -> bool:
        """Cheap, non-throwing readiness check. Default: available.
        Providers that need config/network override this."""
        return True

    # ---- capability methods (override the ones describe() advertises) ----

    def generate(self, req: GenerateRequest) -> GenerateResult:  # pragma: no cover - default
        raise NotImplementedError(f"{self.name} does not support generate")

    def embed(self, req: EmbedRequest) -> EmbedResult:  # pragma: no cover - default
        raise NotImplementedError(f"{self.name} does not support embed")

    def rerank(self, req: RerankRequest) -> RerankResult:  # pragma: no cover - default
        raise NotImplementedError(f"{self.name} does not support rerank")

    def entail(self, req: EntailRequest) -> EntailResult:  # pragma: no cover - default
        raise NotImplementedError(f"{self.name} does not support entail")

    def extract_entities(self, req: NERRequest) -> NERResult:  # pragma: no cover - default
        raise NotImplementedError(f"{self.name} does not support ner")

    # ---- helpers ----

    def supports(self, capability: str) -> bool:
        return capability in self.describe().capabilities

    def require_available(self) -> None:
        if not self.is_available():
            raise ProviderUnavailable(f"provider '{self.name}' is not available")


def capabilities_of(provider: ModelProvider) -> List[str]:
    return list(provider.describe().capabilities)
