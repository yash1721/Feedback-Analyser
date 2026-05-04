from typing import Any
from uuid import uuid5, NAMESPACE_URL

import numpy as np

from app.core.exceptions import ModelUnavailableError
from app.domain.retrieval.vector_store import SearchResult, UpsertedVector, VectorChunk, VectorStore


class QdrantVectorStore(VectorStore):
    def __init__(
        self,
        *,
        url: str,
        collection_name: str,
        vector_size: int,
        distance: str = "cosine",
    ) -> None:
        self.url = url
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.distance = distance
        self._client = None

    @property
    def client(self):
        if self._client is None:
            try:
                from qdrant_client import QdrantClient
            except ImportError as exc:
                raise ModelUnavailableError("qdrant-client is not installed.") from exc
            self._client = QdrantClient(url=self.url)
        return self._client

    def ensure_collection(self) -> None:
        try:
            from qdrant_client.http import models
        except ImportError as exc:
            raise ModelUnavailableError("qdrant-client is not installed.") from exc
        existing = {collection.name for collection in self.client.get_collections().collections}
        if self.collection_name in existing:
            return
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(
                size=self.vector_size,
                distance=self._distance_model(models),
            ),
        )

    def add_texts(self, texts: list[str], embeddings: np.ndarray) -> None:
        chunks = [
            VectorChunk(id=index + 1, text=text, metadata={"text": text}, point_id=str(index + 1))
            for index, text in enumerate(texts)
        ]
        self.upsert_chunks(chunks, embeddings)

    def upsert_chunks(self, chunks: list[VectorChunk], embeddings: np.ndarray) -> list[UpsertedVector]:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have the same length.")
        try:
            from qdrant_client.http import models
        except ImportError as exc:
            raise ModelUnavailableError("qdrant-client is not installed.") from exc
        self.ensure_collection()
        points = []
        upserted: list[UpsertedVector] = []
        vectors = np.asarray(embeddings, dtype="float32")
        for chunk, vector in zip(chunks, vectors):
            point_id = chunk.point_id or str(uuid5(NAMESPACE_URL, f"feedbackiq:chunk:{chunk.id}"))
            payload = {
                **chunk.metadata,
                "chunk_id": chunk.id,
                "text": chunk.text,
            }
            points.append(
                models.PointStruct(
                    id=point_id,
                    vector=vector.tolist(),
                    payload=payload,
                )
            )
            upserted.append(UpsertedVector(chunk_id=chunk.id, point_id=point_id))
        self.client.upsert(collection_name=self.collection_name, points=points)
        return upserted

    def search(self, query_embedding: np.ndarray, top_k: int) -> list[SearchResult]:
        return self.search_with_filters(query_embedding, top_k=top_k)

    def search_with_filters(
        self,
        query_embedding: np.ndarray,
        *,
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        self.ensure_collection()
        query = np.asarray(query_embedding, dtype="float32")[0].tolist()
        response = self.client.query_points(
            collection_name=self.collection_name,
            query=query,
            limit=top_k,
            query_filter=self._build_filter(filters),
            with_payload=True,
        )
        search_results: list[SearchResult] = []
        for rank, item in enumerate(response.points, start=1):
            payload = dict(item.payload or {})
            search_results.append(
                SearchResult(
                    text=str(payload.get("text", "")),
                    score=float(item.score),
                    rank=rank,
                    point_id=str(item.id),
                    chunk_id=payload.get("chunk_id"),
                    metadata=payload,
                )
            )
        return search_results

    def _build_filter(self, filters: dict[str, Any] | None):
        if not filters:
            return None
        try:
            from qdrant_client.http import models
        except ImportError as exc:
            raise ModelUnavailableError("qdrant-client is not installed.") from exc
        conditions = []
        for key, value in filters.items():
            if value is None:
                continue
            if isinstance(value, list):
                conditions.append(models.FieldCondition(key=key, match=models.MatchAny(any=value)))
            else:
                conditions.append(models.FieldCondition(key=key, match=models.MatchValue(value=value)))
        if not conditions:
            return None
        return models.Filter(must=conditions)

    def _distance_model(self, models):
        normalized = self.distance.lower()
        if normalized == "dot":
            return models.Distance.DOT
        if normalized == "euclidean":
            return models.Distance.EUCLID
        return models.Distance.COSINE
