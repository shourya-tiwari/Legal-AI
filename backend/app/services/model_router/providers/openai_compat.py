# backend/app/services/model_router/providers/openai_compat.py
"""
OpenAI-compatible HTTP provider -- Class B (self-hosted neural).

Talks to any server that exposes the OpenAI REST shape:
  - Ollama            (http://localhost:11434/v1)
  - vLLM / SGLang     (--api-server, OpenAI-compatible)
  - Text Embeddings Inference (TEI) with the OpenAI route
  - LM Studio, llama.cpp server, LocalAI, ...

Configured entirely from Settings (LLM_BASE_URL / LLM_MODEL / LLM_API_KEY,
and EMBEDDING_* for the embedding route). If LLM_BASE_URL is empty the
provider reports itself unavailable and the router moves on -- which is the
normal state on a dev machine or in CI with nothing served locally yet.
"""
from __future__ import annotations

import logging
from typing import List, Optional

import httpx

from app.config import get_settings

from ..base import ModelProvider
from ..types import (
    EmbedRequest,
    EmbedResult,
    GenerateRequest,
    GenerateResult,
    HostingClass,
    ProviderCard,
    ProviderUnavailable,
)

logger = logging.getLogger("legalai.model_router.openai_compat")

_TIMEOUT = httpx.Timeout(60.0, connect=5.0)


class OpenAICompatProvider(ModelProvider):
    """Serves `generate` (chat/completions) and `embed` (embeddings) against a
    self-hosted OpenAI-compatible endpoint."""

    hosting_class = HostingClass.B

    def __init__(self, name: str, *, role: str = "llm") -> None:
        # role: "llm" reads LLM_* settings; "embed" reads EMBEDDING_* settings.
        self.name = name
        self._role = role

    def _cfg(self):
        s = get_settings()
        if self._role == "embed":
            return s.EMBEDDING_BASE_URL, s.EMBEDDING_MODEL, s.EMBEDDING_API_KEY
        return s.LLM_BASE_URL, s.LLM_MODEL, s.LLM_API_KEY

    def describe(self) -> ProviderCard:
        base_url, model, _ = self._cfg()
        caps = ["generate"] if self._role == "llm" else ["embed"]
        return ProviderCard(
            name=self.name,
            hosting_class=HostingClass.B,
            capabilities=caps,
            leaves_perimeter=False,
            models=[model] if model else [],
            note=f"Self-hosted OpenAI-compatible endpoint ({base_url or 'not configured'}).",
        )

    def is_available(self) -> bool:
        base_url, _, _ = self._cfg()
        return bool(base_url)

    def _url(self, path: str) -> str:
        base_url, _, _ = self._cfg()
        return base_url.rstrip("/") + path

    def _headers(self) -> dict:
        _, _, api_key = self._cfg()
        h = {"Content-Type": "application/json"}
        if api_key:
            h["Authorization"] = f"Bearer {api_key}"
        return h

    def generate(self, req: GenerateRequest) -> GenerateResult:
        base_url, default_model, _ = self._cfg()
        if not base_url:
            raise ProviderUnavailable(f"{self.name}: LLM_BASE_URL not configured")
        model = req.model or default_model
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": req.prompt}],
        }
        if req.temperature is not None:
            payload["temperature"] = req.temperature
        if req.max_output_tokens is not None:
            payload["max_tokens"] = req.max_output_tokens
        try:
            resp = httpx.post(self._url("/chat/completions"), json=payload,
                              headers=self._headers(), timeout=_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            text = (data["choices"][0]["message"]["content"] or "").strip()
        except httpx.HTTPError as e:
            raise ProviderUnavailable(f"{self.name}: request to {base_url} failed: {e}") from e
        except (KeyError, IndexError, ValueError) as e:
            raise ProviderUnavailable(f"{self.name}: unexpected response shape: {e}") from e
        return GenerateResult(text=text, provider=self.name, model=model,
                              hosting_class=HostingClass.B)

    def embed(self, req: EmbedRequest) -> EmbedResult:
        base_url, default_model, _ = self._cfg()
        if not base_url:
            raise ProviderUnavailable(f"{self.name}: EMBEDDING_BASE_URL not configured")
        model = req.model or default_model
        try:
            resp = httpx.post(self._url("/embeddings"),
                              json={"model": model, "input": list(req.inputs)},
                              headers=self._headers(), timeout=_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            vectors: List[List[float]] = [item["embedding"] for item in data["data"]]
        except httpx.HTTPError as e:
            raise ProviderUnavailable(f"{self.name}: embedding request to {base_url} failed: {e}") from e
        except (KeyError, IndexError, ValueError) as e:
            raise ProviderUnavailable(f"{self.name}: unexpected embedding response shape: {e}") from e
        return EmbedResult(vectors=vectors, provider=self.name, model=model,
                           hosting_class=HostingClass.B)
