import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.core.exceptions import BadRequestError, ModelUnavailableError
from app.db.base import Base
from app.domain.analysis.schemas import AnalysisResponse, AnalysisCategory, SentimentLabel, Severity, StructuredAnalysisOutput, ValidationStatus
from app.domain.feedback.feedback_analysis_service import FeedbackAnalysisResult
from app.domain.feedback.models import FeedbackProcessingStatus, FeedbackRecord, FeedbackSourceType
from app.domain.feedback.repository import FeedbackRepository
from app.domain.feedback.service import FeedbackService
from app.domain.processing.queue import EnqueuedProcessingJob
from app.domain.processing.service import ProcessingService, TransientProcessingError
from app.domain.retrieval.vector_store import SearchResult
from app.domain.routing.team_router import RoutingResult
from app.domain.sentiment.sentiment_analyzer import SentimentResult


class FakeQueue:
    def __init__(self) -> None:
        self.enqueued_feedback_ids: list[int] = []

    def enqueue_feedback_record(self, feedback_id: int) -> EnqueuedProcessingJob:
        self.enqueued_feedback_ids.append(feedback_id)
        return EnqueuedProcessingJob(task_id=f"task-{feedback_id}")


class FakeAnalysisService:
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail

    def analyze(self, text: str, top_k: int) -> FeedbackAnalysisResult:
        if self.should_fail:
            raise ModelUnavailableError("Model is unavailable in test.")
        return FeedbackAnalysisResult(
            text=text,
            sentiment=SentimentResult(label="NEGATIVE", score=0.9),
            routing=RoutingResult(team="Payment Team", matched_keyword="payment"),
            retrieval_results=[SearchResult(text="Payment failed context", score=0.7)],
            rag_context="Payment context",
        )


class FakeStructuredAnalysisService:
    def __init__(self, feedback_service: FeedbackService) -> None:
        self.feedback_service = feedback_service

    def run_feedback_analysis(self, feedback_id: int) -> AnalysisResponse:
        output = StructuredAnalysisOutput(
            sentiment_label=SentimentLabel.NEGATIVE,
            sentiment_score=0.91,
            category=AnalysisCategory.PAYMENT,
            severity=Severity.P1,
            routed_team="Payment Team",
            summary="Payment failed.",
            recommended_action="Investigate checkout payments.",
            confidence_score=0.88,
            reasoning_summary="Payment evidence was used.",
            evidence_chunk_ids=[1],
        )
        self.feedback_service.attach_structured_analysis_result(
            feedback_id,
            analysis_run_id=123,
            output=output,
        )
        return AnalysisResponse(
            feedback_id=feedback_id,
            analysis_run_id=123,
            retrieval_trace_id=456,
            validation_status=ValidationStatus.VALID,
            output=output,
            provider="fake",
            model_name="fake",
            prompt_version="test",
        )


@pytest.fixture
def session_factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def test_enqueue_feedback_record_marks_queued_and_stores_task_id(session_factory: sessionmaker[Session]):
    with session_factory() as session:
        feedback_service = FeedbackService(FeedbackRepository(session))
        record = feedback_service.create_ingested_feedback(
            source_type=FeedbackSourceType.TEXT,
            raw_text="Payment failed.",
            extracted_text="Payment failed.",
            processing_status=FeedbackProcessingStatus.EXTRACTED,
        )
        queue = FakeQueue()
        service = ProcessingService(
            feedback_service=feedback_service,
            analysis_service=FakeAnalysisService(),
            queue=queue,
            settings=Settings(),
        )

        result = service.enqueue_feedback_record(record.id)

        assert result.enqueued is True
        assert result.task_id == f"task-{record.id}"
        assert result.record.processing_status == FeedbackProcessingStatus.QUEUED
        assert result.record.processing_task_id == f"task-{record.id}"
        assert queue.enqueued_feedback_ids == [record.id]


def test_enqueue_feedback_record_is_idempotent_for_active_record(session_factory: sessionmaker[Session]):
    with session_factory() as session:
        feedback_service = FeedbackService(FeedbackRepository(session))
        record = feedback_service.create_ingested_feedback(
            source_type=FeedbackSourceType.TEXT,
            raw_text="Payment failed.",
            extracted_text="Payment failed.",
            processing_status=FeedbackProcessingStatus.EXTRACTED,
        )
        queue = FakeQueue()
        service = ProcessingService(
            feedback_service=feedback_service,
            analysis_service=FakeAnalysisService(),
            queue=queue,
            settings=Settings(),
        )

        first = service.enqueue_feedback_record(record.id)
        second = service.enqueue_feedback_record(record.id)

        assert first.enqueued is True
        assert second.enqueued is False
        assert second.task_id == first.task_id
        assert queue.enqueued_feedback_ids == [record.id]


def test_enqueue_feedback_record_rejects_failed_record(session_factory: sessionmaker[Session]):
    with session_factory() as session:
        feedback_service = FeedbackService(FeedbackRepository(session))
        record = feedback_service.create_ingested_feedback(
            source_type=FeedbackSourceType.IMAGE,
            processing_status=FeedbackProcessingStatus.FAILED,
            error_code="ocr_error",
            error_message="OCR failed.",
        )
        service = ProcessingService(
            feedback_service=feedback_service,
            analysis_service=FakeAnalysisService(),
            queue=FakeQueue(),
            settings=Settings(),
        )

        with pytest.raises(BadRequestError):
            service.enqueue_feedback_record(record.id)


def test_process_feedback_record_success_updates_analysis_fields(session_factory: sessionmaker[Session]):
    with session_factory() as session:
        feedback_service = FeedbackService(FeedbackRepository(session))
        record = feedback_service.create_ingested_feedback(
            source_type=FeedbackSourceType.TEXT,
            raw_text="Payment failed.",
            extracted_text="Payment failed.",
            processing_status=FeedbackProcessingStatus.QUEUED,
        )
        service = ProcessingService(
            feedback_service=feedback_service,
            analysis_service=FakeAnalysisService(),
            queue=None,
            settings=Settings(),
        )

        updated = service.process_feedback_record(record.id)

        assert updated.processing_status == FeedbackProcessingStatus.COMPLETED
        assert updated.sentiment_label == "NEGATIVE"
        assert updated.routed_team == "Payment Team"
        assert updated.error_code is None


def test_process_feedback_record_uses_structured_analysis_when_available(session_factory: sessionmaker[Session]):
    with session_factory() as session:
        feedback_service = FeedbackService(FeedbackRepository(session))
        record = feedback_service.create_ingested_feedback(
            source_type=FeedbackSourceType.TEXT,
            raw_text="Payment failed.",
            extracted_text="Payment failed.",
            processing_status=FeedbackProcessingStatus.QUEUED,
        )
        service = ProcessingService(
            feedback_service=feedback_service,
            analysis_service=FakeAnalysisService(),
            llm_analysis_service=FakeStructuredAnalysisService(feedback_service),
            queue=None,
            settings=Settings(),
        )

        updated = service.process_feedback_record(record.id)

        assert updated.processing_status == FeedbackProcessingStatus.COMPLETED
        assert updated.latest_analysis_run_id == 123
        assert updated.category == "PAYMENT"
        assert updated.confidence_score == 0.88


def test_process_feedback_record_without_text_persists_failed(session_factory: sessionmaker[Session]):
    with session_factory() as session:
        feedback_service = FeedbackService(FeedbackRepository(session))
        record = feedback_service.repository.create(
            source_type=FeedbackSourceType.PDF,
            processing_status=FeedbackProcessingStatus.QUEUED,
        )
        session.commit()
        service = ProcessingService(
            feedback_service=feedback_service,
            analysis_service=FakeAnalysisService(),
            queue=None,
            settings=Settings(),
        )

        with pytest.raises(Exception):
            service.process_feedback_record(record.id)

        failed = session.get(FeedbackRecord, record.id)
        assert failed is not None
        assert failed.processing_status == FeedbackProcessingStatus.FAILED
        assert failed.error_code == "no_processable_text"


def test_process_feedback_record_transient_failure_keeps_processing_for_retry(session_factory: sessionmaker[Session]):
    with session_factory() as session:
        feedback_service = FeedbackService(FeedbackRepository(session))
        record = feedback_service.create_ingested_feedback(
            source_type=FeedbackSourceType.TEXT,
            raw_text="Payment failed.",
            extracted_text="Payment failed.",
            processing_status=FeedbackProcessingStatus.QUEUED,
        )
        service = ProcessingService(
            feedback_service=feedback_service,
            analysis_service=FakeAnalysisService(should_fail=True),
            queue=None,
            settings=Settings(),
        )

        with pytest.raises(TransientProcessingError):
            service.process_feedback_record(record.id)

        retryable = session.get(FeedbackRecord, record.id)
        assert retryable is not None
        assert retryable.processing_status == FeedbackProcessingStatus.PROCESSING
