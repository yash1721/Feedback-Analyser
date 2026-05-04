from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db_session
from app.dependencies import get_llm_provider, get_retrieval_service
from app.domain.llm.fake_provider import FakeLLMProvider
from app.domain.retrieval.retrieval_service import RetrievalSearchResult
from app.domain.retrieval.vector_store import SearchResult
from app.main import create_app


class FakeRetrievalService:
    def search_with_options(self, query: str, *, top_k: int, filters=None, persist_trace=False, feedback_record_id=None):
        return RetrievalSearchResult(
            results=[SearchResult(text="Payment evidence", score=0.9, rank=1, chunk_id=5)],
            rag_context="Payment evidence",
            trace_id=10 if persist_trace else None,
        )


@pytest.fixture
def client() -> Iterator[TestClient]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_db_session() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_retrieval_service] = lambda: FakeRetrievalService()
    app.dependency_overrides[get_llm_provider] = lambda: FakeLLMProvider()
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_analysis_run_latest_and_get_run(client: TestClient):
    created = client.post("/api/v1/ingestion/text", json={"text": "Payment failed during checkout."}).json()["data"]

    run_response = client.post(f"/api/v1/analysis/feedback-records/{created['feedback_id']}/run")

    assert run_response.status_code == 200
    run_data = run_response.json()["data"]
    assert run_data["output"]["category"] == "PAYMENT"
    assert run_data["retrieval_trace_id"] == 10

    latest_response = client.get(f"/api/v1/analysis/feedback-records/{created['feedback_id']}/latest")
    get_run_response = client.get(f"/api/v1/analysis/runs/{run_data['analysis_run_id']}")

    assert latest_response.status_code == 200
    assert latest_response.json()["data"]["category"] == "PAYMENT"
    assert get_run_response.status_code == 200
    assert get_run_response.json()["data"]["id"] == run_data["analysis_run_id"]
