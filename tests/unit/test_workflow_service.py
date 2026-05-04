from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.db.base import Base
from app.domain.analysis.repository import AnalysisRepository
from app.domain.feedback.models import FeedbackProcessingStatus, FeedbackSourceType
from app.domain.feedback.repository import FeedbackRepository
from app.domain.feedback.service import FeedbackService
from app.domain.notifications.mock_provider import MockNotificationProvider
from app.domain.workflow.models import ReviewStatus, TicketStatus
from app.domain.workflow.repository import WorkflowRepository
from app.domain.workflow.schemas import ReviewDecisionAction
from app.domain.workflow.service import WorkflowService


def _session_factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def _create_analyzed_feedback(session: Session, *, severity: str = "P1", confidence: float = 0.9):
    feedback_service = FeedbackService(FeedbackRepository(session))
    record = feedback_service.create_ingested_feedback(
        source_type=FeedbackSourceType.TEXT,
        raw_text="Payment failed during checkout.",
        extracted_text="Payment failed during checkout.",
        processing_status=FeedbackProcessingStatus.COMPLETED,
    )
    run = AnalysisRepository(session).create_run(
        feedback_record_id=record.id,
        retrieval_trace_id=77,
        provider="fake",
        model_name="fake",
        prompt_version="test",
        input_preview="Payment failed during checkout.",
        output_json={"category": "PAYMENT"},
        validation_status="VALID",
    )
    record.latest_analysis_run_id = run.id
    record.sentiment_label = "NEGATIVE"
    record.sentiment_score = 0.91
    record.category = "PAYMENT"
    record.severity = severity
    record.routed_team = "Payment Team"
    record.summary = "Payment failed."
    record.recommended_action = "Investigate checkout."
    record.confidence_score = confidence
    session.flush()
    return feedback_service, record


def _workflow_service(session: Session, feedback_service: FeedbackService, provider: MockNotificationProvider | None = None):
    return WorkflowService(
        repository=WorkflowRepository(session),
        feedback_service=feedback_service,
        notification_provider=provider or MockNotificationProvider(),
        settings=Settings(),
    )


def test_create_ticket_from_analysis_escalates_and_creates_review():
    with _session_factory()() as session:
        feedback_service, record = _create_analyzed_feedback(session, severity="P1")
        provider = MockNotificationProvider()
        service = _workflow_service(session, feedback_service, provider)

        result = service.create_ticket_for_feedback(record.id)

        assert result.ticket.status == TicketStatus.ESCALATED
        assert result.review_created is True
        assert result.ticket.retrieval_trace_id == 77
        assert result.audit_event_ids
        assert any(call["event"] == "ticket_escalated" for call in provider.calls)
        reviews, total = service.list_reviews(limit=10, offset=0)
        assert total == 1
        assert reviews[0].status == ReviewStatus.PENDING


def test_create_ticket_is_idempotent_for_same_feedback():
    with _session_factory()() as session:
        feedback_service, record = _create_analyzed_feedback(session)
        service = _workflow_service(session, feedback_service)

        first = service.create_ticket_for_feedback(record.id)
        second = service.create_ticket_for_feedback(record.id)

        assert second.ticket.id == first.ticket.id
        assert second.audit_event_ids == []


def test_duplicate_feedback_creates_duplicate_ticket_link():
    with _session_factory()() as session:
        feedback_service, first = _create_analyzed_feedback(session, severity="P2")
        service = _workflow_service(session, feedback_service)
        first_result = service.create_ticket_for_feedback(first.id)

        _, second = _create_analyzed_feedback(session, severity="P2")
        second_result = service.create_ticket_for_feedback(second.id)

        assert second_result.ticket.status == TicketStatus.DUPLICATE
        assert second_result.ticket.duplicate_of_ticket_id == first_result.ticket.id


def test_review_override_team_updates_ticket_and_audit_log():
    with _session_factory()() as session:
        feedback_service, record = _create_analyzed_feedback(session, confidence=0.3, severity="P3")
        service = _workflow_service(session, feedback_service)
        result = service.create_ticket_for_feedback(record.id)
        reviews, _ = service.list_reviews(limit=10, offset=0)

        decision = service.decide_review(
            reviews[0].id,
            action=ReviewDecisionAction.OVERRIDE_TEAM,
            final_team="Backend Team",
            reviewer_note="Backend owns checkout API.",
        )

        assert decision.review.status == ReviewStatus.OVERRIDDEN
        assert decision.ticket is not None
        assert decision.ticket.id == result.ticket.id
        assert decision.ticket.assigned_team == "Backend Team"
        assert decision.audit_event.action == "REVIEW_OVERRIDE_TEAM"
