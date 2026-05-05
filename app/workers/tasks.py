from celery.exceptions import MaxRetriesExceededError
import logging

from app.config import get_settings
from app.core.correlation import new_correlation_id, reset_correlation_id, set_correlation_id
from app.core.metrics import PROCESSING_JOBS_TOTAL
from app.dependencies import get_feedback_service_scope_provider
from app.domain.processing.processor import process_feedback_record_with_scope
from app.domain.processing.service import PermanentProcessingError, TransientProcessingError
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="feedbackiq.process_feedback_record", bind=True)
def process_feedback_record(self, feedback_id: int) -> dict:
    correlation_id = getattr(self.request, "correlation_id", None) or new_correlation_id()
    token = set_correlation_id(correlation_id)
    settings = get_settings()
    try:
        logger.info("Processing task started", extra={"feedback_id": feedback_id, "task_id": self.request.id})
        return process_feedback_record_with_scope(
            feedback_id,
            feedback_service_scope_provider=get_feedback_service_scope_provider(),
        )
    except PermanentProcessingError as exc:
        logger.warning(
            "Processing task permanent failure",
            extra={"feedback_id": feedback_id, "task_id": self.request.id, "error_code": exc.error_code},
        )
        PROCESSING_JOBS_TOTAL.labels(event="task", status="permanent_failed").inc()
        _persist_final_failure(feedback_id, exc.error_code, exc.error_message)
        return {
            "feedback_id": feedback_id,
            "processing_status": "FAILED",
            "error_code": exc.error_code,
        }
    except TransientProcessingError as exc:
        try:
            logger.warning(
                "Processing task retry scheduled",
                extra={"feedback_id": feedback_id, "task_id": self.request.id, "error_code": exc.error_code},
            )
            PROCESSING_JOBS_TOTAL.labels(event="task", status="retry").inc()
            raise self.retry(
                exc=exc,
                countdown=settings.processing_retry_backoff_seconds * (2 ** self.request.retries),
                max_retries=settings.processing_max_retries,
            )
        except MaxRetriesExceededError:
            logger.exception(
                "Processing task retries exhausted",
                extra={"feedback_id": feedback_id, "task_id": self.request.id, "error_code": exc.error_code},
            )
            PROCESSING_JOBS_TOTAL.labels(event="task", status="failed").inc()
            _persist_final_failure(feedback_id, exc.error_code, exc.error_message)
            return {
                "feedback_id": feedback_id,
                "processing_status": "FAILED",
                "error_code": exc.error_code,
            }
    finally:
        reset_correlation_id(token)


def _persist_final_failure(feedback_id: int, error_code: str, error_message: str) -> None:
    with get_feedback_service_scope_provider()() as feedback_service:
        feedback_service.mark_failed(feedback_id, error_code=error_code, error_message=error_message)
