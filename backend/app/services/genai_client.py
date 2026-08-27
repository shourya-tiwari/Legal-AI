# backend/app/services/genai_client.py
from __future__ import annotations

import logging
import time
from typing import Optional, Dict, Any

from google import genai

from app.config import get_settings

try:
    from google.genai import types as genai_types  # type: ignore
    from google.genai.types import HttpOptions      # type: ignore
except Exception:  # pragma: no cover
    genai_types = None  # type: ignore[assignment]
    HttpOptions = None  # type: ignore[assignment]

logger = logging.getLogger("legalai.genai_client")

_client: Optional[genai.Client] = None

def get_client() -> genai.Client:
    """
    Returns a configured Google Gen AI Developer API client using GOOGLE_API_KEY.
    Cloud-independent, pure Google GenAI Developer API.
    """
    global _client
    if _client is not None:
        return _client

    logger.info("Initializing GenAI Client...")
    settings = get_settings()

    if not settings.GOOGLE_API_KEY:
        logger.error("Missing GOOGLE_API_KEY in environment!")
        raise RuntimeError("Missing GOOGLE_API_KEY. Please set GOOGLE_API_KEY in your .env file.")

    http_kwargs: Dict[str, Any] = {}
    if HttpOptions is not None:
        try:
            # Configure 30-second HTTP timeout to prevent hanging requests
            http_kwargs["http_options"] = HttpOptions(timeout=30000)
            logger.info("Configured HttpOptions with 30.0s timeout")
        except Exception as e:
            logger.warning("HttpOptions initialization warning: %s", e)

    try:
        _client = genai.Client(api_key=settings.GOOGLE_API_KEY, **http_kwargs)
        logger.info("GenAI client initialized successfully.")
        return _client
    except Exception as e:
        logger.error("Client creation failed: %s", e)
        raise RuntimeError(f"Failed to initialize Gemini Client: {e}") from e

def generate_content(prompt: str, *, model: Optional[str] = None, **config_kwargs) -> str:
    """
    Centralized generation helper called by all AI features.
    Calls client.models.generate_content(...) with diagnostic logging and detailed error handling.
    """
    client = get_client()
    settings = get_settings()
    model_name = model or settings.GENAI_MODEL

    config = None
    if genai_types is not None and config_kwargs:
        try:
            config = genai_types.GenerateContentConfig(**config_kwargs)  # type: ignore[attr-defined]
        except Exception as e:
            logger.warning("GenerateContentConfig warning: %s", e)
            config = None

    logger.info("HTTP request start -> Model: '%s' | Prompt length: %d chars", model_name, len(prompt))
    start_time = time.time()

    try:
        resp = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=config,
        )
        elapsed = (time.time() - start_time) * 1000
        logger.info("HTTP request end -> Completed in %.1fms", elapsed)
        text = getattr(resp, "text", "") or ""
        return text.strip()

    except Exception as e:
        elapsed = (time.time() - start_time) * 1000
        err_str = str(e)
        err_type = type(e).__name__

        # 1. Handle 404 / Model Not Found errors
        if "404" in err_str or "NOT_FOUND" in err_str or "not found" in err_str.lower():
            msg = (
                f"Configured Gemini model '{model_name}' is unavailable or not found (HTTP 404). "
                f"Please update GENAI_MODEL in .env to a supported model (e.g., 'gemini-flash-latest'). "
                f"Original error: {err_str}"
            )
            logger.error(msg)
            raise RuntimeError(msg) from e

        # 2. Handle 429 / Quota / Rate Limit errors
        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
            msg = (
                f"Gemini API rate limit or quota exceeded for model '{model_name}' (HTTP 429). "
                f"Please retry in a moment or check project limits. Original error: {err_str}"
            )
            logger.error(msg)
            raise RuntimeError(msg) from e

        # 3. Handle Timeouts
        if "timeout" in err_str.lower() or "timed out" in err_str.lower() or "Timeout" in err_type:
            msg = (
                f"Gemini API HTTP request timed out after {elapsed:.1f}ms for model '{model_name}' "
                f"at endpoint 'generativelanguage.googleapis.com'."
            )
            logger.error(msg)
            raise RuntimeError(msg) from e

        # 4. General API errors
        msg = f"Gemini API call failed for model '{model_name}': [{err_type}] {err_str}"
        logger.error(msg)
        raise RuntimeError(msg) from e

def embed_content(contents: Any, *, model: str = "gemini-embedding-001") -> Any:
    """
    Centralized embedding helper using Gemini API.
    """
    client = get_client()
    logger.info("Embedding request start -> Model: '%s'", model)
    try:
        res = client.models.embed_content(model=model, contents=contents)
        logger.info("Embedding request completed.")
        return res
    except Exception as e:
        logger.error("Embedding request failed: %s: %s", type(e).__name__, e)
        raise RuntimeError(f"Gemini embedding failed for model '{model}': {e}") from e
