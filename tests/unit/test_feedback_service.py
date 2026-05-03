from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.exceptions import BadRequestError, NotFoundError
from app.db.base import Base
from app.domain.feedback.models import FeedbackProcessingStatus, FeedbackSourceType
from app.domain.feedback.repository import FeedbackRepository
from app.domain.feedback.service import FeedbackService
from app.domain.routing.team_router import RoutingResult
from app.domain.sentiment.sentiment_analyzer import SentimentResult


@pytest.fixture
def service() -> Iterator[FeedbackService]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with session_factory() as session:
        yield FeedbackService(FeedbackRepository(session))


def test_service_creates_text_feedback(service: FeedbackService):
    record = service.create_text_feedback(text="  Checkout   failed.  ")

    assert record.id is not None
    assert record.source_type == FeedbackSourceType.TEXT
    assert record.normalized_text == "Checkout failed."
    assert record.processing_status == FeedbackProcessingStatus.PENDING


def test_service_rejects_non_text_create(service: FeedbackService):
    with pytest.raises(BadRequestError):
        service.create_text_feedback(text="file content", source_type=FeedbackSourceType.IMAGE)


def test_service_updates_analysis_result(service: FeedbackService):
    record = service.create_text_feedback(text="Payment failed.")

    updated = service.attach_analysis_result(
        record.id,
        sentiment=SentimentResult(label="NEGATIVE", score=0.95),
        routing=RoutingResult(team="Payment Team", matched_keyword="payment"),
    )

    assert updated.processing_status == FeedbackProcessingStatus.COMPLETED
    assert updated.sentiment_label == "NEGATIVE"
    assert updated.routed_team == "Payment Team"


def test_service_raises_for_missing_record(service: FeedbackService):
    with pytest.raises(NotFoundError):
        service.get_feedback_record(404)
