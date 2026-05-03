from abc import ABC, abstractmethod

import numpy as np


class EmbeddingModel(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> np.ndarray:
        raise NotImplementedError


class FakeEmbeddingModel(EmbeddingModel):
    def embed(self, texts: list[str]) -> np.ndarray:
        vectors = []
        for text in texts:
            value = float(sum(ord(char) for char in text) % 1000)
            vectors.append([value, float(len(text)), 1.0])
        return np.array(vectors, dtype="float32")

