import numpy as np

from app.core.exceptions import ModelUnavailableError
from app.domain.retrieval.embedding_model import EmbeddingModel


class SentenceTransformerEmbeddingModel(EmbeddingModel):
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._model = None

    @property
    def model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise ModelUnavailableError("sentence-transformers is not installed.") from exc
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed(self, texts: list[str]) -> np.ndarray:
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return np.asarray(embeddings, dtype="float32")

