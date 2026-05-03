import numpy as np

from app.core.exceptions import ModelUnavailableError
from app.domain.retrieval.vector_store import SearchResult, VectorStore


class FaissVectorStore(VectorStore):
    def __init__(self) -> None:
        self._index = None
        self._texts: list[str] = []

    def add_texts(self, texts: list[str], embeddings: np.ndarray) -> None:
        if len(texts) != len(embeddings):
            raise ValueError("texts and embeddings must have the same length.")
        faiss = self._faiss()
        vectors = np.asarray(embeddings, dtype="float32")
        self._index = faiss.IndexFlatIP(vectors.shape[1])
        self._index.add(vectors)
        self._texts = list(texts)

    def search(self, query_embedding: np.ndarray, top_k: int) -> list[SearchResult]:
        if self._index is None:
            return []
        query = np.asarray(query_embedding, dtype="float32")
        scores, indices = self._index.search(query, min(top_k, len(self._texts)))
        return [
            SearchResult(text=self._texts[index], score=float(score))
            for score, index in zip(scores[0], indices[0])
            if index != -1
        ]

    def _faiss(self):
        try:
            import faiss
        except ImportError as exc:
            raise ModelUnavailableError("faiss-cpu is not installed.") from exc
        return faiss

