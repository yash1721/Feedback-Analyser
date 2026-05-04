from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class SearchResult:
    text: str
    score: float
    rank: int | None = None
    point_id: str | None = None
    chunk_id: int | None = None
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class VectorChunk:
    id: int
    text: str
    metadata: dict[str, Any]
    point_id: str | None = None


@dataclass(frozen=True)
class UpsertedVector:
    chunk_id: int
    point_id: str


class VectorStore(ABC):
    @abstractmethod
    def add_texts(self, texts: list[str], embeddings: np.ndarray) -> None:
        raise NotImplementedError

    @abstractmethod
    def search(self, query_embedding: np.ndarray, top_k: int) -> list[SearchResult]:
        raise NotImplementedError

    def upsert_chunks(self, chunks: list[VectorChunk], embeddings: np.ndarray) -> list[UpsertedVector]:
        self.add_texts([chunk.text for chunk in chunks], embeddings)
        return [
            UpsertedVector(chunk_id=chunk.id, point_id=chunk.point_id or str(chunk.id))
            for chunk in chunks
        ]

    def search_with_filters(
        self,
        query_embedding: np.ndarray,
        *,
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        return self.search(query_embedding, top_k)

    def ensure_collection(self) -> None:
        return None
