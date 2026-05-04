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
            results=[SearchResult(text="Payment escalation evidence", score=0.9, rank=1, chunk_id=5)],
            rag_context="Payment escalation evidence",
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


def test_workflow_ticket_review_and_audit_api(client: TestClient):
    created = client.post("/api/v1/ingestion/text", json={"text": "Payment failed during checkout."}).json()["data"]
    analysis = client.post(f"/api/v1/analysis/feedback-records/{created['feedback_id']}/run")
    assert analysis.status_code == 200

    workflow = client.post(f"/api/v1/workflows/feedback-records/{created['feedback_id']}/create-ticket")

    assert workflow.status_code == 200
    ticket = workflow.json()["data"]["ticket"]
    assert ticket["category"] == "PAYMENT"
    assert ticket["status"] in {"ASSIGNED", "IN_REVIEW", "ESCALATED"}

    listed_tickets = client.get("/api/v1/tickets")
    listed_reviews = client.get("/api/v1/reviews")
    audit_logs = client.get("/api/v1/workflows/audit-logs", params={"entity_type": "ticket", "entity_id": ticket["id"]})

    assert listed_tickets.status_code == 200
    assert listed_tickets.json()["data"]["total"] == 1
    assert listed_reviews.status_code == 200
    assert audit_logs.status_code == 200
    assert audit_logs.json()["data"]["total"] >= 1
