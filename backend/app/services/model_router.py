# backend/app/services/model_router.py
"""
Model Router (docs/v2/AI_STACK.md): the single point every service calls to
reach a model — no service instantiates a model client directly.

Phase 1 scope: this is a drop-in wrapper around genai_client that routes
100% of traffic to Gemini, with no behavior change from before its
introduction. It exists now so the call sites (rewriter, timeline, chatbot,
risk_radar, contextualizer) depend on a routing abstraction instead of a
specific provider client — real tiered routing (open-weight vs. commercial,
by task/sensitivity) lands in a later phase per docs/v2/AI_STACK.md, at which
point only this module needs to change, not its callers.
"""
from __future__ import annotations

from typing import Any, Optional

from . import genai_client


def generate_content(prompt: str, *, model: Optional[str] = None, **config_kwargs) -> str:
    return genai_client.generate_content(prompt, model=model, **config_kwargs)


def embed_content(contents: Any, *, model: str = "gemini-embedding-001") -> Any:
    return genai_client.embed_content(contents, model=model)
