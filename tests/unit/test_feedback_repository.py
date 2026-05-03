from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.domain.feedback.models import FeedbackProcessingStatus, FeedbackRecord, FeedbackSourceType
from app.domain.feedback.repository import FeedbackRepository


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with session_factory() as session:
        yield session


def test_repository_create_and_get_by_id(session: Session):
    repository = FeedbackRepository(session)

    record = repository.create(
        source_type=FeedbackSourceType.TEXT,
        raw_text="Checkout failed.",
        extracted_text="Checkout failed.",
        normalized_text="Checkout failed.",
    )
    session.commit()

    found = repository.get_by_id(record.id)

    assert found is not None
    assert found.raw_text == "Checkout failed."
    assert found.processing_status == FeedbackProcessingStatus.PENDING


def test_repository_lists_with_filters_and_total(session: Session):
    repository = FeedbackRepository(session)
    first = repository.create(
        source_type=FeedbackSourceType.TEXT,
        raw_text="Payment failed.",
        processing_status=FeedbackProcessingStatus.PENDING,
    )
    second = repository.create(
        source_type=FeedbackSourceType.TEXT,
        raw_text="Shipping delayed.",
        processing_status=FeedbackProcessingStatus.PENDING,
    )
    repository.update_analysis_result(
        first,
        sentiment_label="NEGATIVE",
        sentiment_score=0.9,
        routed_team="Payment Team",
        matched_keyword="payment",
    )
    repository.update_analysis_result(
        second,
        sentiment_label="NEGATIVE",
        sentiment_score=0.7,
        routed_team="Logistics Team",
        matched_keyword="shipping",
    )
    session.commit()

    records, total = repository.list(limit=20, offset=0, routed_team="Payment Team")

    assert total == 1
    assert records[0].routed_team == "Payment Team"


def test_repository_updates_status(session: Session):
    repository = FeedbackRepository(session)
    record = repository.create(source_type=FeedbackSourceType.TEXT, raw_text="Bad upload.")

    updated = repository.update_status(
        record,
        processing_status=FeedbackProcessingStatus.FAILED,
        error_code="ocr_error",
        error_message="OCR failed.",
    )
    session.commit()

    assert updated.processing_status == FeedbackProcessingStatus.FAILED
    assert session.get(FeedbackRecord, record.id).error_code == "ocr_error"
