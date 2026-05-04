from collections.abc import Iterator

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db_session
from app.dependencies import get_embedding_model, get_vector_store
from app.domain.retrieval.embedding_model import EmbeddingModel
from app.domain.retrieval.vector_store import SearchResult, UpsertedVector, VectorChunk, VectorStore
from app.main import create_app


class FakeEmbeddingModel(EmbeddingModel):
    def embed(self, texts: list[str]) -> np.ndarray:
        return np.array([[float(len(text)), 1.0, 0.0] for text in texts], dtype="float32")


class FakeVectorStore(VectorStore):
    def __init__(self) -> None:
        self.chunks: list[VectorChunk] = []

    def add_texts(self, texts: list[str], embeddings: np.ndarray) -> None:
        self.chunks = [
            VectorChunk(id=index + 1, text=text, metadata={"text": text})
            for index, text in enumerate(texts)
        ]

    def upsert_chunks(self, chunks: list[VectorChunk], embeddings: np.ndarray) -> list[UpsertedVector]:
        self.chunks = list(chunks)
        return [UpsertedVector(chunk_id=chunk.id, point_id=f"point-{chunk.id}") for chunk in chunks]

    def search(self, query_embedding: np.ndarray, top_k: int) -> list[SearchResult]:
        return self.search_with_filters(query_embedding, top_k=top_k)

    def search_with_filters(self, query_embedding: np.ndarray, *, top_k: int, filters: dict | None = None) -> list[SearchResult]:
        chunks = self.chunks
        if filters:
            chunks = [
                chunk
                for chunk in chunks
                if all(chunk.metadata.get(key) == value for key, value in filters.items())
            ]
        return [
            SearchResult(
                text=chunk.text,
                score=1.0 - (index * 0.1),
                rank=index + 1,
                point_id=f"point-{chunk.id}",
                chunk_id=chunk.id,
                metadata=chunk.metadata,
            )
            for index, chunk in enumerate(chunks[:top_k])
        ]


@pytest.fixture
def client() -> Iterator[TestClient]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    fake_store = FakeVectorStore()

    def override_db_session() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_embedding_model] = lambda: FakeEmbeddingModel()
    app.dependency_overrides[get_vector_store] = lambda: fake_store
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_create_get_and_index_knowledge_document(client: TestClient):
    created = client.post(
        "/api/v1/knowledge/documents",
        json={
            "title": "Payment handbook",
            "text": "Payment failures should be routed to the Payment Team.",
            "source_type": "manual",
            "source_name": "runbook",
            "metadata": {"team": "Payment Team"},
        },
    )

    assert created.status_code == 200
    document_id = created.json()["data"]["id"]

    indexed = client.post(f"/api/v1/knowledge/documents/{document_id}/index")
    detail = client.get(f"/api/v1/knowledge/documents/{document_id}")

    assert indexed.status_code == 200
    assert indexed.json()["data"]["indexed_chunks"] == 1
    assert detail.status_code == 200
    assert detail.json()["data"]["chunks"][0]["qdrant_point_id"].startswith("point-")


def test_retrieval_search_with_trace_uses_indexed_knowledge(client: TestClient):
    created = client.post(
        "/api/v1/knowledge/documents",
        json={
            "title": "Payment handbook",
            "text": "Payment failures should be routed to the Payment Team.",
            "metadata": {"team": "Payment Team"},
        },
    ).json()["data"]
    client.post(f"/api/v1/knowledge/documents/{created['id']}/index")

    response = client.post(
        "/api/v1/retrieval/search",
        json={
            "query": "payment failed",
            "top_k": 1,
            "filters": {"team": "Payment Team"},
            "persist_trace": True,
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["trace_id"] is not None
    assert data["results"][0]["metadata"]["team"] == "Payment Team"
    assert "Payment failures" in data["rag_context"]
