from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class SearchResult:
    text: str
    score: float


class VectorStore(ABC):
    @abstractmethod
    def add_texts(self, texts: list[str], embeddings: np.ndarray) -> None:
        raise NotImplementedError

    @abstractmethod
    def search(self, query_embedding: np.ndarray, top_k: int) -> list[SearchResult]:
        raise NotImplementedError

