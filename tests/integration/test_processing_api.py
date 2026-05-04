from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db_session
from app.dependencies import get_feedback_analysis_service, get_processing_queue
from app.domain.feedback.feedback_analysis_service import FeedbackAnalysisResult
from app.domain.processing.queue import EnqueuedProcessingJob
from app.domain.retrieval.vector_store import SearchResult
from app.domain.routing.team_router import RoutingResult
from app.domain.sentiment.sentiment_analyzer import SentimentResult
from app.main import create_app


class FakeQueue:
    def enqueue_feedback_record(self, feedback_id: int) -> EnqueuedProcessingJob:
        return EnqueuedProcessingJob(task_id=f"task-{feedback_id}")


class FakeAnalysisService:
    def analyze(self, text: str, top_k: int) -> FeedbackAnalysisResult:
        return FeedbackAnalysisResult(
            text=text,
            sentiment=SentimentResult(label="NEGATIVE", score=0.9),
            routing=RoutingResult(team="Payment Team", matched_keyword="payment"),
            retrieval_results=[SearchResult(text="Payment context", score=0.8)],
            rag_context="Payment context",
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
    app.dependency_overrides[get_processing_queue] = lambda: FakeQueue()
    app.dependency_overrides[get_feedback_analysis_service] = lambda: FakeAnalysisService()
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_enqueue_endpoint_marks_record_queued(client: TestClient):
    created = client.post("/api/v1/ingestion/text", json={"text": "Payment failed."}).json()["data"]

    response = client.post(f"/api/v1/processing/feedback-records/{created['feedback_id']}/enqueue")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["feedback_id"] == created["feedback_id"]
    assert data["processing_status"] == "QUEUED"
    assert data["task_id"] == f"task-{created['feedback_id']}"
    assert data["enqueued"] is True


def test_enqueue_endpoint_is_idempotent_for_queued_record(client: TestClient):
    created = client.post("/api/v1/ingestion/text", json={"text": "Payment failed."}).json()["data"]

    first = client.post(f"/api/v1/processing/feedback-records/{created['feedback_id']}/enqueue")
    second = client.post(f"/api/v1/processing/feedback-records/{created['feedback_id']}/enqueue")

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["data"]["enqueued"] is False
    assert second.json()["data"]["task_id"] == first.json()["data"]["task_id"]


def test_status_endpoint_returns_processing_metadata(client: TestClient):
    created = client.post("/api/v1/ingestion/text", json={"text": "Payment failed."}).json()["data"]
    client.post(f"/api/v1/processing/feedback-records/{created['feedback_id']}/enqueue")

    response = client.get(f"/api/v1/processing/feedback-records/{created['feedback_id']}/status")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["feedback_id"] == created["feedback_id"]
    assert data["processing_status"] == "QUEUED"
    assert data["task_id"] == f"task-{created['feedback_id']}"
    assert data["error_code"] is None


def test_enqueue_missing_record_returns_404(client: TestClient):
    response = client.post("/api/v1/processing/feedback-records/999/enqueue")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
