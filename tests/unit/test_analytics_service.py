from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.domain.analytics.repository import AnalyticsRepository
from app.domain.analytics.report import AnalyticsReportGenerator
from app.domain.analytics.schemas import TrendInterval
from app.domain.analytics.service import AnalyticsService
from app.domain.evaluation.repository import EvaluationRepository
from app.domain.feedback.models import FeedbackProcessingStatus, FeedbackSourceType
from app.domain.feedback.repository import FeedbackRepository
from app.domain.feedback.service import FeedbackService
from app.domain.workflow.models import ReviewStatus, TicketStatus
from app.domain.workflow.repository import WorkflowRepository


def _session_factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def _service(session: Session, report_dir: Path) -> AnalyticsService:
    return AnalyticsService(
        repository=AnalyticsRepository(session),
        report_generator=AnalyticsReportGenerator(report_dir),
    )


def test_analytics_summary_handles_empty_database(tmp_path: Path):
    with _session_factory()() as session:
        service = _service(session, tmp_path)
        time_range = service.time_range(interval=TrendInterval.DAY)

        summary = service.summary(time_range)

        assert summary.total_feedback == 0
        assert summary.negative_feedback_percentage == 0
        assert summary.source_type_breakdown == []


def test_analytics_summary_trends_tickets_reviews_and_evaluation(tmp_path: Path):
    with _session_factory()() as session:
        feedback_service = FeedbackService(FeedbackRepository(session))
        first = feedback_service.create_ingested_feedback(
            source_type=FeedbackSourceType.TEXT,
            raw_text="Payment failed.",
            extracted_text="Payment failed.",
            processing_status=FeedbackProcessingStatus.COMPLETED,
        )
        first.sentiment_label = "NEGATIVE"
        first.category = "PAYMENT"
        first.severity = "P1"
        first.routed_team = "Payment Team"
        first.confidence_score = 0.8
        first.pii_detected = True
        second = feedback_service.create_ingested_feedback(
            source_type=FeedbackSourceType.CSV,
            raw_text="UI works well.",
            extracted_text="UI works well.",
            processing_status=FeedbackProcessingStatus.FAILED,
        )
        second.sentiment_label = "POSITIVE"
        second.category = "UI"
        second.severity = "P3"
        second.routed_team = "Frontend Team"
        workflow_repository = WorkflowRepository(session)
        ticket = workflow_repository.create_ticket(
            feedback_record_id=first.id,
            analysis_run_id=None,
            retrieval_trace_id=None,
            title="Payment issue",
            description="Payment issue",
            category="PAYMENT",
            severity="P1",
            status=TicketStatus.ESCALATED,
            assigned_team="Payment Team",
        )
        workflow_repository.create_review(
            feedback_record_id=first.id,
            analysis_run_id=None,
            ticket_id=ticket.id,
            reason="High severity P1 requires review.",
            status=ReviewStatus.PENDING,
            suggested_team="Payment Team",
            suggested_severity="P1",
        )
        EvaluationRepository(session).create_run(
            dataset_id=None,
            dataset_name="seed",
            dataset_version="v1",
            provider="rule_based",
            model_name="rule",
            prompt_version="v1",
            vector_provider="qdrant",
            embedding_model="BAAI/bge-m3",
            top_k=3,
            total_examples=2,
            metrics_json={"analysis": {"exact_label_match_rate": 0.75}},
        )
        session.commit()
        service = _service(session, tmp_path)
        time_range = service.time_range(interval=TrendInterval.DAY)

        summary = service.summary(time_range)
        trends = service.feedback_trends(time_range)
        tickets = service.tickets(time_range)
        reviews = service.reviews(time_range)
        evaluation = service.evaluations()
        executive = service.executive_summary(time_range)
        report = service.report(time_range)

        assert summary.total_feedback == 2
        assert summary.negative_feedback_percentage == 50
        assert summary.failed_processing_percentage == 50
        assert summary.pii_detected_count == 1
        assert trends.points
        assert tickets.escalated_ticket_count == 1
        assert reviews.pending_review_count == 1
        assert evaluation.latest_run_id is not None
        assert "FeedbackIQ processed 2 feedback items" in executive.summary_text
        assert Path(report.report_path).exists()
