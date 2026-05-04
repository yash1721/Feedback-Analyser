from contextlib import AbstractContextManager
from typing import Callable

from app.config import get_settings
from app.dependencies import build_analysis_service, build_workflow_service, get_feedback_analysis_service_for_worker
from app.domain.feedback.service import FeedbackService
from app.domain.processing.service import ProcessingService


def process_feedback_record_with_scope(
    feedback_id: int,
    *,
    feedback_service_scope_provider: Callable[[], AbstractContextManager[FeedbackService]],
) -> dict:
    with feedback_service_scope_provider() as feedback_service:
        service = ProcessingService(
            feedback_service=feedback_service,
            analysis_service=get_feedback_analysis_service_for_worker(),
            queue=None,
            llm_analysis_service=build_analysis_service(feedback_service),
            workflow_service=build_workflow_service(feedback_service),
            settings=get_settings(),
        )
        record = service.process_feedback_record(feedback_id)
        return {
            "feedback_id": record.id,
            "processing_status": record.processing_status,
            "sentiment_label": record.sentiment_label,
            "routed_team": record.routed_team,
        }
