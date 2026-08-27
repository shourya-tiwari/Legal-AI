# backend/app/services/model_router/types.py
"""
Provider-neutral request/response types and the hosting-class taxonomy
(docs/v2/AI_STACK.md). No provider-specific fields leak into these -- a
provider adapter translates to/from its native API.

Hosting classes replace the old "Tier 0/1/2" vendor tiers:
  A -- deterministic / CPU (rules, classical ML, hashing embeddings)
  B -- self-hosted neural (vLLM/Ollama/TEI/sentence-transformers on our own hw)
  C -- external provider API (leaves the deployment perimeter; optional plugin)
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any, List, Optional, Sequence


class HostingClass(str, enum.Enum):
    A = "A"  # deterministic / CPU
    B = "B"  # self-hosted neural
    C = "C"  # external provider


class SensitivityTier(str, enum.Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    PRIVILEGED = "privileged"

    @classmethod
    def coerce(cls, value: "str | SensitivityTier | None") -> "SensitivityTier":
        if isinstance(value, SensitivityTier):
            return value
        if not value:
            return cls.INTERNAL
        try:
            return cls(str(value).lower())
        except ValueError:
            return cls.INTERNAL


class ModelRouterError(RuntimeError):
    """Raised when the router cannot satisfy a request (no healthy provider,
    policy forbids the only available option, etc.). Callers that currently
    catch RuntimeError from the old genai_client keep working unchanged."""


class ProviderUnavailable(ModelRouterError):
    """A provider cannot serve requests right now -- missing dependency,
    missing config, or a failed health check. The router skips to the next
    candidate in the task's chain."""


@dataclass
class GenerateRequest:
    prompt: str
    task: str = "generic"
    sensitivity: SensitivityTier = SensitivityTier.INTERNAL
    model: Optional[str] = None          # explicit override; usually None
    temperature: Optional[float] = None
    max_output_tokens: Optional[int] = None
    extra: dict = field(default_factory=dict)   # passthrough config a provider may use


@dataclass
class GenerateResult:
    text: str
    provider: str
    model: str
    hosting_class: HostingClass


@dataclass
class EmbedRequest:
    inputs: Sequence[str]
    task: str = "embed_corpus"
    model: Optional[str] = None


class _Vector:
    """Minimal shape-compatible with the old Gemini embedding response items
    (`.values`) so existing callers -- contextualizer/rag.py -- need no change."""

    __slots__ = ("values",)

    def __init__(self, values: List[float]):
        self.values = values


class EmbedResult:
    """Shape-compatible with the old `embed_content` return value:
    `result.embeddings[i].values`."""

    __slots__ = ("embeddings", "provider", "model", "hosting_class")

    def __init__(self, vectors: Sequence[Sequence[float]], provider: str, model: str,
                 hosting_class: HostingClass):
        self.embeddings = [_Vector(list(v)) for v in vectors]
        self.provider = provider
        self.model = model
        self.hosting_class = hosting_class


@dataclass
class RerankRequest:
    query: str
    documents: Sequence[str]
    task: str = "rerank"
    top_k: Optional[int] = None


@dataclass
class RerankResult:
    # indices into the input `documents`, best first, with scores
    ranking: List[int]
    scores: List[float]
    provider: str
    hosting_class: HostingClass


@dataclass
class ProviderCard:
    name: str
    hosting_class: HostingClass
    capabilities: List[str]              # subset of {"generate","embed","rerank"}
    leaves_perimeter: bool
    models: List[str] = field(default_factory=list)
    note: str = ""


@dataclass
class RoutingDecision:
    task: str
    capability: str
    sensitivity: SensitivityTier
    provider: str
    model: str
    hosting_class: HostingClass
    reason: str
    candidates_considered: List[str] = field(default_factory=list)

    def as_log_dict(self) -> dict:
        return {
            "task": self.task,
            "capability": self.capability,
            "sensitivity": self.sensitivity.value,
            "provider": self.provider,
            "model": self.model,
            "hosting_class": self.hosting_class.value,
            "reason": self.reason,
            "candidates": self.candidates_considered,
        }
