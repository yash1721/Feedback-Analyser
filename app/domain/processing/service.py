from dataclasses import dataclass
import logging

from app.config import Settings
from app.core.exceptions import BadRequestError, FeedbackIQError, NotFoundError, QueueUnavailableError
from app.core.metrics import PROCESSING_JOBS_TOTAL, PROCESSING_JOB_DURATION_SECONDS, Timer, update_processing_status_gauges
from app.domain.analysis.schemas import ValidationStatus
from app.domain.analysis.service import AnalysisService
from app.domain.feedback.feedback_analysis_service import FeedbackAnalysisService
from app.domain.feedback.models import FeedbackProcessingStatus, FeedbackRecord
from app.domain.feedback.service import FeedbackService
from app.domain.processing.queue import ProcessingQueue
from app.domain.workflow.service import WorkflowService

logger = logging.getLogger(__name__)


class PermanentProcessingError(Exception):
    def __init__(self, error_code: str, error_message: str) -> None:
        super().__init__(error_message)
        self.error_code = error_code
        self.error_message = error_message


class TransientProcessingError(Exception):
    def __init__(self, error_code: str, error_message: str) -> None:
        super().__init__(error_message)
        self.error_code = error_code
        self.error_message = error_message


@dataclass(frozen=True)
class ProcessingEnqueueResult:
    record: FeedbackRecord
    task_id: str | None
    enqueued: bool


class ProcessingService:
    def __init__(
        self,
        *,
        feedback_service: FeedbackService,
        analysis_service: FeedbackAnalysisService,
        queue: ProcessingQueue | None,
        settings: Settings,
        llm_analysis_service: AnalysisService | None = None,
        workflow_service: WorkflowService | None = None,
    ) -> None:
        self.feedback_service = feedback_service
        self.analysis_service = analysis_service
        self.llm_analysis_service = llm_analysis_service
        self.workflow_service = workflow_service
        self.queue = queue
        self.settings = settings

    def enqueue_feedback_record(self, feedback_id: int) -> ProcessingEnqueueResult:
        record = self.feedback_service.get_feedback_record(feedback_id)
        if record.processing_status in {
            FeedbackProcessingStatus.QUEUED,
            FeedbackProcessingStatus.PROCESSING,
            FeedbackProcessingStatus.COMPLETED,
        }:
            return ProcessingEnqueueResult(
                record=record,
                task_id=record.processing_task_id,
                enqueued=False,
            )
        if record.processing_status == FeedbackProcessingStatus.FAILED:
            raise BadRequestError(
                "Failed feedback records cannot be enqueued without an explicit reset.",
                {"feedback_id": feedback_id, "processing_status": record.processing_status},
            )
        if record.processing_status not in {FeedbackProcessingStatus.PENDING, FeedbackProcessingStatus.EXTRACTED}:
            raise BadRequestError(
                "Feedback record is not in an enqueueable state.",
                {"feedback_id": feedback_id, "processing_status": record.processing_status},
            )
        previous_status = record.processing_status
        self.feedback_service.update_status(feedback_id, processing_status=FeedbackProcessingStatus.QUEUED)
        if self.queue is None:
            self.feedback_service.update_status(
                feedback_id,
                processing_status=previous_status,
                error_code="queue_unavailable",
                error_message="Processing queue is not configured.",
            )
            raise QueueUnavailableError("Processing queue is not configured.", {"feedback_id": feedback_id})
        try:
            enqueued_job = self.queue.enqueue_feedback_record(feedback_id)
        except Exception as exc:
            self.feedback_service.update_status(
                feedback_id,
                processing_status=previous_status,
                error_code="queue_unavailable",
                error_message="Processing queue could not enqueue the record.",
            )
            raise QueueUnavailableError("Processing queue could not enqueue the record.", {"feedback_id": feedback_id}) from exc
        updated = self.feedback_service.attach_processing_task_id(
            feedback_id,
            processing_task_id=enqueued_job.task_id,
        )
        PROCESSING_JOBS_TOTAL.labels(event="enqueue", status="queued").inc()
        return ProcessingEnqueueResult(record=updated, task_id=enqueued_job.task_id, enqueued=True)

    def get_feedback_status(self, feedback_id: int) -> FeedbackRecord:
        record = self.feedback_service.get_feedback_record(feedback_id)
        if hasattr(self.feedback_service.repository, "count_by_processing_status"):
            update_processing_status_gauges(self.feedback_service.repository.count_by_processing_status())
        return record

    def process_feedback_record(self, feedback_id: int) -> FeedbackRecord:
        timer = Timer()
        final_status = "failed"
        try:
            record = self.feedback_service.get_feedback_record(feedback_id)
        except NotFoundError as exc:
            raise PermanentProcessingError("record_not_found", "Feedback record was not found.") from exc
        if record.processing_status == FeedbackProcessingStatus.COMPLETED:
            PROCESSING_JOBS_TOTAL.labels(event="process", status="completed").inc()
            return record
        if record.processing_status == FeedbackProcessingStatus.FAILED:
            raise PermanentProcessingError("invalid_processing_state", "Failed records require an explicit reset before processing.")
        if record.processing_status not in {
            FeedbackProcessingStatus.PENDING,
            FeedbackProcessingStatus.EXTRACTED,
            FeedbackProcessingStatus.QUEUED,
            FeedbackProcessingStatus.PROCESSING,
        }:
            raise PermanentProcessingError("invalid_processing_state", "Feedback record is not processable.")

        text = record.normalized_text or record.extracted_text or record.raw_text
        if not text:
            failed = self.feedback_service.mark_failed(
                feedback_id,
                error_code="no_processable_text",
                error_message="Feedback record does not contain text that can be analyzed.",
            )
            raise PermanentProcessingError(failed.error_code or "no_processable_text", failed.error_message or "No processable text.")

        self.feedback_service.update_status(feedback_id, processing_status=FeedbackProcessingStatus.PROCESSING)
        if self.llm_analysis_service is not None:
            try:
                analysis_response = self.llm_analysis_service.run_feedback_analysis(feedback_id)
            except FeedbackIQError as exc:
                raise TransientProcessingError(exc.code, exc.message) from exc
            except Exception as exc:
                raise TransientProcessingError("analysis_error", "Structured feedback analysis failed.") from exc
            if analysis_response.validation_status != ValidationStatus.VALID:
                self.feedback_service.mark_failed(
                    feedback_id,
                    error_code=analysis_response.error_code or "analysis_validation_error",
                    error_message=analysis_response.error_message or "Structured analysis output was invalid.",
                )
                raise PermanentProcessingError(
                    analysis_response.error_code or "analysis_validation_error",
                    analysis_response.error_message or "Structured analysis output was invalid.",
                )
            if self.settings.workflow_auto_create_tickets and self.workflow_service is not None:
                try:
                    self.workflow_service.create_ticket_for_feedback(feedback_id)
                except Exception:
                    logger.exception("Workflow ticket creation failed after processing", extra={"feedback_id": feedback_id})
            final_status = "completed"
            PROCESSING_JOBS_TOTAL.labels(event="process", status=final_status).inc()
            PROCESSING_JOB_DURATION_SECONDS.labels(status=final_status).observe(timer.elapsed())
            return self.feedback_service.get_feedback_record(feedback_id)

        try:
            result = self.analysis_service.analyze(text, self.settings.retrieval_top_k)
        except FeedbackIQError as exc:
            raise TransientProcessingError(exc.code, exc.message) from exc
        except Exception as exc:
            raise TransientProcessingError("processing_error", "Feedback processing failed.") from exc

        updated = self.feedback_service.attach_analysis_result(
            feedback_id,
            sentiment=result.sentiment,
            routing=result.routing,
        )
        final_status = "completed"
        PROCESSING_JOBS_TOTAL.labels(event="process", status=final_status).inc()
        PROCESSING_JOB_DURATION_SECONDS.labels(status=final_status).observe(timer.elapsed())
        return updated

    def mark_failed(self, feedback_id: int, *, error_code: str, error_message: str) -> FeedbackRecord:
        return self.feedback_service.mark_failed(feedback_id, error_code=error_code, error_message=error_message)
