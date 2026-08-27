# backend/app/services/model_router/providers/local.py
"""
Fully local providers that need no server and no network:

  HashingEmbeddingProvider  -- Class A. Deterministic hashed character +
      word n-gram vectors, L2-normalized. This is NOT a neural embedding --
      it's a lexical-overlap signal dressed as a dense vector. It exists so
      the RAG dense leg is structurally present and the whole product runs
      offline with zero dependencies installed. The real self-hosted neural
      embedding (EmbeddingGemma / Qwen3-Embedding / BGE-M3) is
      SentenceTransformerProvider below, or an OpenAI-compatible TEI endpoint.

  SentenceTransformerProvider -- Class B. Real neural embeddings + a
      CrossEncoder reranker, IF `sentence-transformers` is installed
      (requirements-local.txt, opt-in -- it pulls torch). Skipped by the
      registry when the import fails.

  LexicalReranker -- Class A. Token-overlap reranker fallback when no neural
      reranker is available.
"""
from __future__ import annotations

import hashlib
import logging
import math
import re
from functools import lru_cache
from typing import List, Optional, Sequence

from app.config import get_settings

from ..base import ModelProvider
from ..types import (
    EmbedRequest,
    EmbedResult,
    HostingClass,
    ProviderCard,
    ProviderUnavailable,
    RerankRequest,
    RerankResult,
)

logger = logging.getLogger("legalai.model_router.local")

_WORD_RE = re.compile(r"[a-z0-9']+")
_HASH_DIM = 384


def _tokens(text: str) -> List[str]:
    return _WORD_RE.findall(text.lower())


# --------------------------------------------------------------------------
# Class A: hashing embedding
# --------------------------------------------------------------------------

class HashingEmbeddingProvider(ModelProvider):
    name = "hashing-embed"
    hosting_class = HostingClass.A

    def __init__(self, dim: int = _HASH_DIM) -> None:
        self.dim = dim

    def describe(self) -> ProviderCard:
        return ProviderCard(
            name=self.name,
            hosting_class=HostingClass.A,
            capabilities=["embed"],
            leaves_perimeter=False,
            models=[f"hashing-{self.dim}d"],
            note="Deterministic hashed n-gram vectors (lexical signal, not neural). "
                 "Offline floor for the RAG dense leg.",
        )

    def _vector(self, text: str) -> List[float]:
        vec = [0.0] * self.dim
        toks = _tokens(text)
        # unigrams + bigrams + 3/4-char shingles -> captures some morphology
        feats: List[str] = list(toks)
        feats += [f"{a}_{b}" for a, b in zip(toks, toks[1:])]
        low = re.sub(r"\s+", " ", text.lower())
        feats += [low[i:i + 4] for i in range(0, max(0, len(low) - 3))]
        for f in feats:
            h = int.from_bytes(hashlib.md5(f.encode("utf-8")).digest()[:8], "big")
            idx = h % self.dim
            sign = 1.0 if (h >> 8) & 1 else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed(self, req: EmbedRequest) -> EmbedResult:
        vectors = [self._vector(t) for t in req.inputs]
        return EmbedResult(vectors=vectors, provider=self.name, model=f"hashing-{self.dim}d",
                           hosting_class=HostingClass.A)


# --------------------------------------------------------------------------
# Class A: lexical reranker
# --------------------------------------------------------------------------

class LexicalReranker(ModelProvider):
    name = "lexical-rerank"
    hosting_class = HostingClass.A

    def describe(self) -> ProviderCard:
        return ProviderCard(
            name=self.name,
            hosting_class=HostingClass.A,
            capabilities=["rerank"],
            leaves_perimeter=False,
            models=["token-overlap"],
            note="Token-overlap reranker; the fallback when no neural cross-encoder is served.",
        )

    def rerank(self, req: RerankRequest) -> RerankResult:
        q = set(_tokens(req.query))
        scored = []
        for i, doc in enumerate(req.documents):
            d = _tokens(doc)
            if not d:
                scored.append((i, 0.0))
                continue
            overlap = sum(1 for t in d if t in q)
            scored.append((i, overlap / math.sqrt(len(d))))
        scored.sort(key=lambda p: p[1], reverse=True)
        if req.top_k is not None:
            scored = scored[: req.top_k]
        return RerankResult(
            ranking=[i for i, _ in scored],
            scores=[s for _, s in scored],
            provider=self.name,
            hosting_class=HostingClass.A,
        )


# --------------------------------------------------------------------------
# Class B: sentence-transformers (optional dependency)
# --------------------------------------------------------------------------

@lru_cache(maxsize=4)
def _load_st_model(model_name: str):
    from sentence_transformers import SentenceTransformer  # type: ignore

    return SentenceTransformer(model_name)


@lru_cache(maxsize=2)
def _load_cross_encoder(model_name: str):
    from sentence_transformers import CrossEncoder  # type: ignore

    return CrossEncoder(model_name)


def _sentence_transformers_importable() -> bool:
    try:
        import sentence_transformers  # noqa: F401  # type: ignore
        return True
    except Exception:
        return False


class SentenceTransformerProvider(ModelProvider):
    name = "sentence-transformers"
    hosting_class = HostingClass.B

    def __init__(self, embed_model: Optional[str] = None, rerank_model: Optional[str] = None) -> None:
        s = get_settings()
        self._embed_model = embed_model or s.EMBEDDING_MODEL
        self._rerank_model = rerank_model or s.RERANKER_MODEL

    def describe(self) -> ProviderCard:
        return ProviderCard(
            name=self.name,
            hosting_class=HostingClass.B,
            capabilities=["embed", "rerank"],
            leaves_perimeter=False,
            models=[self._embed_model, self._rerank_model],
            note="Self-hosted neural embeddings + cross-encoder reranker "
                 "(requires the optional `sentence-transformers` extra).",
        )

    def is_available(self) -> bool:
        return _sentence_transformers_importable()

    def embed(self, req: EmbedRequest) -> EmbedResult:
        if not self.is_available():
            raise ProviderUnavailable("sentence-transformers is not installed")
        model = _load_st_model(req.model or self._embed_model)
        vecs = model.encode(list(req.inputs), normalize_embeddings=True)
        vectors = [list(map(float, row)) for row in vecs]
        return EmbedResult(vectors=vectors, provider=self.name,
                           model=req.model or self._embed_model, hosting_class=HostingClass.B)

    def rerank(self, req: RerankRequest) -> RerankResult:
        if not self.is_available():
            raise ProviderUnavailable("sentence-transformers is not installed")
        ce = _load_cross_encoder(self._rerank_model)
        pairs = [(req.query, d) for d in req.documents]
        scores = [float(s) for s in ce.predict(pairs)]
        order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        if req.top_k is not None:
            order = order[: req.top_k]
        return RerankResult(ranking=order, scores=[scores[i] for i in order],
                            provider=self.name, hosting_class=HostingClass.B)
