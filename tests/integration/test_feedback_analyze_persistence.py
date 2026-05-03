from collections.abc import Iterator
from contextlib import contextmanager

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.dependencies import get_feedback_analysis_service, get_feedback_service_scope_provider
from app.domain.feedback.feedback_analysis_service import FeedbackAnalysisResult
from app.domain.feedback.models import FeedbackProcessingStatus, FeedbackRecord
from app.domain.feedback.repository import FeedbackRepository
from app.domain.feedback.service import FeedbackService
from app.domain.retrieval.vector_store import SearchResult
from app.domain.routing.team_router import RoutingResult
from app.domain.sentiment.sentiment_analyzer import SentimentResult
from app.main import create_app


class FakeFeedbackAnalysisService:
    def analyze(self, text: str, top_k: int) -> FeedbackAnalysisResult:
        return FeedbackAnalysisResult(
            text=text,
            sentiment=SentimentResult(label="NEGATIVE", score=0.91),
            routing=RoutingResult(team="Payment Team", matched_keyword="payment"),
            retrieval_results=[SearchResult(text="Payment context", score=0.8)],
            rag_context="Query: payment failed",
        )


def test_feedback_analyze_without_persist_keeps_existing_response_shape():
    app = create_app()
    app.dependency_overrides[get_feedback_analysis_service] = lambda: FakeFeedbackAnalysisService()
    app.dependency_overrides[get_feedback_service_scope_provider] = lambda: _raise_if_called
    client = TestClient(app)

    response = client.post("/api/v1/feedback/analyze", json={"text": "Payment failed."})

    assert response.status_code == 200
    data = response.json()["data"]
    assert "record_id" not in data
    assert data["routing"]["team"] == "Payment Team"


def test_feedback_analyze_with_persist_creates_completed_record():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    @contextmanager
    def service_scope() -> Iterator[FeedbackService]:
        with session_factory() as session:
            yield FeedbackService(FeedbackRepository(session))

    app = create_app()
    app.dependency_overrides[get_feedback_analysis_service] = lambda: FakeFeedbackAnalysisService()
    app.dependency_overrides[get_feedback_service_scope_provider] = lambda: service_scope
    client = TestClient(app)

    response = client.post("/api/v1/feedback/analyze", json={"text": "Payment failed.", "persist": True})

    assert response.status_code == 200
    record_id = response.json()["data"]["record_id"]
    with session_factory() as session:
        record = session.scalar(select(FeedbackRecord).where(FeedbackRecord.id == record_id))
    assert record is not None
    assert record.processing_status == FeedbackProcessingStatus.COMPLETED
    assert record.sentiment_label == "NEGATIVE"
    assert record.routed_team == "Payment Team"


@contextmanager
def _raise_if_called() -> Iterator[FeedbackService]:
    raise AssertionError("Persistence scope should not be opened when persist is false.")
