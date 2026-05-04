from celery.exceptions import MaxRetriesExceededError

from app.config import get_settings
from app.dependencies import get_feedback_service_scope_provider
from app.domain.processing.processor import process_feedback_record_with_scope
from app.domain.processing.service import PermanentProcessingError, TransientProcessingError
from app.workers.celery_app import celery_app


@celery_app.task(name="feedbackiq.process_feedback_record", bind=True)
def process_feedback_record(self, feedback_id: int) -> dict:
    settings = get_settings()
    try:
        return process_feedback_record_with_scope(
            feedback_id,
            feedback_service_scope_provider=get_feedback_service_scope_provider(),
        )
    except PermanentProcessingError as exc:
        _persist_final_failure(feedback_id, exc.error_code, exc.error_message)
        return {
            "feedback_id": feedback_id,
            "processing_status": "FAILED",
            "error_code": exc.error_code,
        }
    except TransientProcessingError as exc:
        try:
            raise self.retry(
                exc=exc,
                countdown=settings.processing_retry_backoff_seconds * (2 ** self.request.retries),
                max_retries=settings.processing_max_retries,
            )
        except MaxRetriesExceededError:
            _persist_final_failure(feedback_id, exc.error_code, exc.error_message)
            return {
                "feedback_id": feedback_id,
                "processing_status": "FAILED",
                "error_code": exc.error_code,
            }


def _persist_final_failure(feedback_id: int, error_code: str, error_message: str) -> None:
    with get_feedback_service_scope_provider()() as feedback_service:
        feedback_service.mark_failed(feedback_id, error_code=error_code, error_message=error_message)
