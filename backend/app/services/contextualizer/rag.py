from __future__ import annotations
import logging
from typing import List, Tuple, Optional
import numpy as np

try:
    import faiss  # pip install faiss-cpu
except Exception:  # pragma: no cover
    faiss = None

from app.services.model_router import embed_content

logger = logging.getLogger("legalai.contextualizer.rag")

# Phase 5: no hardcoded embedding model any more. embed_content() routes
# through the Model Router, whose default for the `embed_query` task is a
# self-hosted provider (Class A/B) -- the Gemini embedding API is no longer
# on this path. See app/policies/routing.yaml and docs/v2/AI_STACK.md.

def embed_texts(texts: List[str], *, task: str = "embed_query") -> np.ndarray:
    """
    Returns an array of shape (n, d) from the Model Router's embedding provider.
    """
    try:
        res = embed_content(contents=texts, task=task)
        vecs = [
            np.array(e.values, dtype="float32") if hasattr(e, "values") else np.array(e, dtype="float32")
            for e in getattr(res, "embeddings", [])
        ]
        return np.vstack(vecs) if vecs else np.zeros((0, 768), dtype="float32")
    except Exception as e:
        logger.warning("Embedding failed (%s), returning empty vector set.", e)
        return np.zeros((0, 768), dtype="float32")

class SimpleFaissIndex:
    def __init__(self, dim: int, items: List[str], vecs: np.ndarray):
        self.items = items
        self.vecs = vecs.astype("float32")
        if faiss is None or self.vecs.shape[0] == 0:
            self.index = None
        else:
            self.index = faiss.IndexFlatL2(dim)
            self.index.add(self.vecs)

    @classmethod
    def from_texts(cls, texts: List[str]) -> "SimpleFaissIndex":
        vecs = embed_texts(texts, task="embed_corpus")
        dim = vecs.shape[1] if vecs.size else 768
        return cls(dim, texts, vecs)

    def search(self, query: str, k: int = 3) -> List[Tuple[str, float]]:
        if self.index is None:
            return []
        q = embed_texts([query])
        if q.size == 0 or q.shape[0] == 0:
            return []
        D, I = self.index.search(q.astype("float32"), k)
        hits = []
        for idx, dist in zip(I[0], D[0]):
            if 0 <= idx < len(self.items):
                hits.append((self.items[idx], float(dist)))
        return hits
