from app.core.exceptions import BadRequestError, NotFoundError
from app.domain.feedback.models import FeedbackProcessingStatus, FeedbackRecord, FeedbackSourceType
from app.domain.feedback.repository import FeedbackRepository
from app.domain.ingestion.text_normalizer import TextNormalizer
from app.domain.routing.team_router import RoutingResult
from app.domain.sentiment.sentiment_analyzer import SentimentResult
from app.domain.analysis.schemas import StructuredAnalysisOutput


class FeedbackService:
    def __init__(self, repository: FeedbackRepository, normalizer: TextNormalizer | None = None) -> None:
        self.repository = repository
        self.normalizer = normalizer or TextNormalizer()

    def create_text_feedback(
        self,
        *,
        text: str,
        source_type: FeedbackSourceType = FeedbackSourceType.TEXT,
        original_input_reference: str | None = None,
    ) -> FeedbackRecord:
        if source_type != FeedbackSourceType.TEXT:
            raise BadRequestError("Text feedback records must use source_type TEXT.", {"source_type": source_type})
        normalized_text = self.normalize_text(text)
        record = self.repository.create(
            source_type=source_type,
            original_input_reference=original_input_reference,
            raw_text=text,
            extracted_text=text,
            normalized_text=normalized_text,
            processing_status=FeedbackProcessingStatus.PENDING,
        )
        self.repository.session.commit()
        return record

    def create_ingested_feedback(
        self,
        *,
        source_type: FeedbackSourceType,
        original_input_reference: str | None = None,
        raw_text: str | None = None,
        extracted_text: str | None = None,
        processing_status: FeedbackProcessingStatus = FeedbackProcessingStatus.EXTRACTED,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> FeedbackRecord:
        normalized_text = self.normalize_text(extracted_text) if extracted_text is not None else None
        record = self.repository.create(
            source_type=source_type,
            original_input_reference=original_input_reference,
            raw_text=raw_text,
            extracted_text=extracted_text,
            normalized_text=normalized_text,
            processing_status=processing_status,
        )
        record.error_code = error_code
        record.error_message = error_message
        self.repository.session.commit()
        self.repository.session.refresh(record)
        return record

    def get_feedback_record(self, feedback_id: int) -> FeedbackRecord:
        record = self.repository.get_by_id(feedback_id)
        if record is None:
            raise NotFoundError("Feedback record was not found.", {"feedback_id": feedback_id})
        return record

    def list_feedback_records(
        self,
        *,
        limit: int,
        offset: int,
        source_type: FeedbackSourceType | None = None,
        processing_status: FeedbackProcessingStatus | None = None,
        routed_team: str | None = None,
        sentiment_label: str | None = None,
    ) -> tuple[list[FeedbackRecord], int]:
        return self.repository.list(
            limit=limit,
            offset=offset,
            source_type=source_type,
            processing_status=processing_status,
            routed_team=routed_team,
            sentiment_label=sentiment_label,
        )

    def update_status(
        self,
        feedback_id: int,
        *,
        processing_status: FeedbackProcessingStatus,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> FeedbackRecord:
        record = self.get_feedback_record(feedback_id)
        updated = self.repository.update_status(
            record,
            processing_status=processing_status,
            error_code=error_code,
            error_message=error_message,
        )
        self.repository.session.commit()
        return updated

    def attach_processing_task_id(self, feedback_id: int, *, processing_task_id: str | None) -> FeedbackRecord:
        record = self.get_feedback_record(feedback_id)
        updated = self.repository.update_processing_task_id(record, processing_task_id=processing_task_id)
        self.repository.session.commit()
        return updated

    def attach_analysis_result(
        self,
        feedback_id: int,
        *,
        sentiment: SentimentResult,
        routing: RoutingResult,
    ) -> FeedbackRecord:
        record = self.get_feedback_record(feedback_id)
        updated = self.repository.update_analysis_result(
            record,
            sentiment_label=sentiment.label,
            sentiment_score=sentiment.score,
            routed_team=routing.team,
            matched_keyword=routing.matched_keyword,
        )
        self.repository.session.commit()
        return updated

    def attach_structured_analysis_result(
        self,
        feedback_id: int,
        *,
        analysis_run_id: int,
        output: StructuredAnalysisOutput,
    ) -> FeedbackRecord:
        record = self.get_feedback_record(feedback_id)
        updated = self.repository.update_structured_analysis_result(
            record,
            latest_analysis_run_id=analysis_run_id,
            sentiment_label=output.sentiment_label.value,
            sentiment_score=output.sentiment_score,
            category=output.category.value,
            severity=output.severity.value,
            routed_team=output.routed_team,
            summary=output.summary,
            recommended_action=output.recommended_action,
            confidence_score=output.confidence_score,
        )
        self.repository.session.commit()
        return updated

    def mark_failed(self, feedback_id: int, *, error_code: str, error_message: str) -> FeedbackRecord:
        return self.update_status(
            feedback_id,
            processing_status=FeedbackProcessingStatus.FAILED,
            error_code=error_code,
            error_message=error_message,
        )

    def store_extracted_text(self, feedback_id: int, *, extracted_text: str) -> FeedbackRecord:
        record = self.get_feedback_record(feedback_id)
        record.extracted_text = extracted_text
        record.normalized_text = self.normalize_text(extracted_text)
        self.repository.session.flush()
        self.repository.session.refresh(record)
        self.repository.session.commit()
        return record

    def normalize_text(self, text: str) -> str:
        return self.normalizer.normalize(text)
