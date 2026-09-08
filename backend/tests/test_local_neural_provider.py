"""
The in-process sentence-transformers provider (Class B embed + rerank,
`app/services/model_router/providers/local.py::SentenceTransformerProvider`).

The rest of the suite runs with `LOCAL_NEURAL_ENABLED=false` (conftest) so
embeddings/reranking deterministically resolve to the Class-A hashing/lexical
floor regardless of whether the optional `sentence-transformers` extra is
installed. This module flips it on and exercises the real neural path -- it
self-skips when the extra isn't present (same pattern as
`test_nli_faithfulness.py` for the NLI head).
"""
from __future__ import annotations

import pytest

pytest.importorskip(
    "sentence_transformers",
    reason="sentence-transformers not installed -- the in-process neural provider is optional (requirements-local.txt)",
)

from app.config import get_settings
from app.services.model_router import HostingClass, embed_content, rerank
from app.services.model_router.policy import get_policy
from app.services.model_router.router import get_router
from app.services.model_router.registry import reset_registry_cache


@pytest.fixture(autouse=True)
def _enable_local_neural(monkeypatch):
    monkeypatch.setenv("LOCAL_NEURAL_ENABLED", "true")
    # EMBEDDING_BASE_URL / RERANKER_BASE_URL unset => the router falls through
    # the dedicated-server candidate to the in-process neural one.
    monkeypatch.setenv("EMBEDDING_BASE_URL", "")
    monkeypatch.setenv("RERANKER_BASE_URL", "")
    for cache in (get_settings, get_policy, get_router):
        cache.cache_clear()
    reset_registry_cache()
    yield
    for cache in (get_settings, get_policy, get_router):
        cache.cache_clear()
    reset_registry_cache()


def test_embed_content_prefers_the_in_process_neural_provider_when_enabled():
    result = embed_content(["security deposit refund", "termination notice period"])
    assert len(result.embeddings) == 2
    assert result.hosting_class == HostingClass.B
    assert result.provider == "sentence-transformers"
    # real neural embeddings: unit-normalised, fixed dimensionality
    dim = len(result.embeddings[0].values)
    assert dim > 128
    assert all(len(e.values) == dim for e in result.embeddings)


def test_rerank_prefers_the_in_process_cross_encoder_when_enabled():
    result = rerank(
        "how much notice is required to terminate",
        [
            "The agreement renews automatically each year.",
            "Either party may terminate on 30 days written notice.",
            "Payment is due within 15 days of invoice.",
        ],
    )
    assert result.hosting_class == HostingClass.B
    assert result.provider == "sentence-transformers"
    # the notice-period sentence should rank first
    assert result.ranking[0] == 1


def test_local_neural_disabled_falls_back_to_class_a(monkeypatch):
    monkeypatch.setenv("LOCAL_NEURAL_ENABLED", "false")
    for cache in (get_settings, get_policy, get_router):
        cache.cache_clear()
    reset_registry_cache()

    result = embed_content(["hello world"])
    assert result.hosting_class == HostingClass.A
    assert result.provider == "hashing-embed"
