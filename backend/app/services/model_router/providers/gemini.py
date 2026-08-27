# backend/app/services/model_router/providers/gemini.py
"""
Gemini provider -- Class C (external, leaves the deployment perimeter).

This is the ONLY module in the codebase that imports the Google GenAI SDK.
It lives in `legalai-providers-external` conceptually (see
requirements-external.txt); on-prem/air-gapped builds do not install
`google-genai`, this import fails, and the registry skips this provider
entirely (docs/v2/AI_STACK.md "Provider packaging").

It carries over V1's diagnostic error classification (404 bad-model,
429 quota, timeout) -- that logic was worth keeping, it just no longer
belongs in a module every service imports.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

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

logger = logging.getLogger("legalai.model_router.gemini")

try:  # the SDK is only present when providers-external is installed
    from google import genai  # type: ignore

    try:
        from google.genai import types as genai_types  # type: ignore
        from google.genai.types import HttpOptions  # type: ignore
    except Exception:  # pragma: no cover
        genai_types = None  # type: ignore[assignment]
        HttpOptions = None  # type: ignore[assignment]
    _SDK_AVAILABLE = True
except Exception:  # pragma: no cover - exercised in air-gapped/no-external builds
    genai = None  # type: ignore[assignment]
    genai_types = None  # type: ignore[assignment]
    HttpOptions = None  # type: ignore[assignment]
    _SDK_AVAILABLE = False


def sdk_available() -> bool:
    return _SDK_AVAILABLE


class GeminiProvider(ModelProvider):
    name = "gemini"
    hosting_class = HostingClass.C

    def __init__(self) -> None:
        self._client: Optional["genai.Client"] = None

    # ---- lifecycle ----

    def describe(self) -> ProviderCard:
        settings = get_settings()
        return ProviderCard(
            name=self.name,
            hosting_class=HostingClass.C,
            capabilities=["generate", "embed"],
            leaves_perimeter=True,
            models=[settings.GENAI_MODEL, "gemini-embedding-001"],
            note="External Google GenAI Developer API. Optional plugin; never required.",
        )

    def is_available(self) -> bool:
        if not _SDK_AVAILABLE:
            return False
        return bool(get_settings().GOOGLE_API_KEY)

    def _get_client(self) -> "genai.Client":
        if self._client is not None:
            return self._client
        if not _SDK_AVAILABLE:
            raise ProviderUnavailable("google-genai SDK is not installed (providers-external)")
        settings = get_settings()
        if not settings.GOOGLE_API_KEY:
            raise ProviderUnavailable("GOOGLE_API_KEY is not set")

        http_kwargs: Dict[str, Any] = {}
        if HttpOptions is not None:
            try:
                http_kwargs["http_options"] = HttpOptions(timeout=30000)
            except Exception as e:  # pragma: no cover
                logger.warning("HttpOptions init warning: %s", e)
        try:
            self._client = genai.Client(api_key=settings.GOOGLE_API_KEY, **http_kwargs)
        except Exception as e:
            raise ProviderUnavailable(f"Failed to initialize Gemini client: {e}") from e
        return self._client

    # ---- capabilities ----

    def generate(self, req: GenerateRequest) -> GenerateResult:
        client = self._get_client()
        settings = get_settings()
        model_name = req.model or settings.GENAI_MODEL

        config = None
        cfg_kwargs: Dict[str, Any] = dict(req.extra)
        if req.temperature is not None:
            cfg_kwargs["temperature"] = req.temperature
        if req.max_output_tokens is not None:
            cfg_kwargs["max_output_tokens"] = req.max_output_tokens
        if genai_types is not None and cfg_kwargs:
            try:
                config = genai_types.GenerateContentConfig(**cfg_kwargs)  # type: ignore[attr-defined]
            except Exception as e:
                logger.warning("GenerateContentConfig warning: %s", e)
                config = None

        start = time.time()
        try:
            resp = client.models.generate_content(model=model_name, contents=req.prompt, config=config)
            text = (getattr(resp, "text", "") or "").strip()
            return GenerateResult(text=text, provider=self.name, model=model_name,
                                  hosting_class=HostingClass.C)
        except Exception as e:
            raise _classify_error(e, model_name, (time.time() - start) * 1000)

    def embed(self, req: EmbedRequest) -> EmbedResult:
        client = self._get_client()
        model_name = req.model or "gemini-embedding-001"
        try:
            res = client.models.embed_content(model=model_name, contents=list(req.inputs))
            vectors = [
                list(getattr(e, "values", e) or [])
                for e in getattr(res, "embeddings", [])
            ]
            return EmbedResult(vectors=vectors, provider=self.name, model=model_name,
                               hosting_class=HostingClass.C)
        except Exception as e:
            raise ProviderUnavailable(f"Gemini embedding failed for '{model_name}': {e}") from e


def _classify_error(e: Exception, model_name: str, elapsed_ms: float) -> RuntimeError:
    err_str = str(e)
    err_type = type(e).__name__
    if "404" in err_str or "NOT_FOUND" in err_str or "not found" in err_str.lower():
        return RuntimeError(
            f"Configured Gemini model '{model_name}' is unavailable or not found (HTTP 404). "
            f"Update GENAI_MODEL to a supported model. Original error: {err_str}"
        )
    if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
        return RuntimeError(
            f"Gemini API rate limit or quota exceeded for model '{model_name}' (HTTP 429). "
            f"Original error: {err_str}"
        )
    if "timeout" in err_str.lower() or "timed out" in err_str.lower() or "Timeout" in err_type:
        return RuntimeError(
            f"Gemini API HTTP request timed out after {elapsed_ms:.1f}ms for model '{model_name}'."
        )
    return RuntimeError(f"Gemini API call failed for model '{model_name}': [{err_type}] {err_str}")
