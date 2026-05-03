from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.domain.feedback.models import FeedbackProcessingStatus, FeedbackRecord, FeedbackSourceType


class FeedbackRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        *,
        source_type: FeedbackSourceType,
        original_input_reference: str | None = None,
        raw_text: str | None = None,
        extracted_text: str | None = None,
        normalized_text: str | None = None,
        processing_status: FeedbackProcessingStatus = FeedbackProcessingStatus.PENDING,
    ) -> FeedbackRecord:
        record = FeedbackRecord(
            source_type=source_type,
            original_input_reference=original_input_reference,
            raw_text=raw_text,
            extracted_text=extracted_text,
            normalized_text=normalized_text,
            processing_status=processing_status,
        )
        self.session.add(record)
        self.session.flush()
        self.session.refresh(record)
        return record

    def get_by_id(self, feedback_id: int) -> FeedbackRecord | None:
        return self.session.get(FeedbackRecord, feedback_id)

    def list(
        self,
        *,
        limit: int,
        offset: int,
        source_type: FeedbackSourceType | None = None,
        processing_status: FeedbackProcessingStatus | None = None,
        routed_team: str | None = None,
        sentiment_label: str | None = None,
    ) -> tuple[list[FeedbackRecord], int]:
        statement = self._filtered_statement(
            source_type=source_type,
            processing_status=processing_status,
            routed_team=routed_team,
            sentiment_label=sentiment_label,
        )
        count_statement = select(func.count()).select_from(statement.subquery())
        total = self.session.scalar(count_statement) or 0
        records = list(
            self.session.scalars(
                statement.order_by(FeedbackRecord.created_at.desc(), FeedbackRecord.id.desc())
                .limit(limit)
                .offset(offset)
            )
        )
        return records, total

    def update_status(
        self,
        record: FeedbackRecord,
        *,
        processing_status: FeedbackProcessingStatus,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> FeedbackRecord:
        record.processing_status = processing_status
        record.error_code = error_code
        record.error_message = error_message
        self.session.flush()
        self.session.refresh(record)
        return record

    def update_analysis_result(
        self,
        record: FeedbackRecord,
        *,
        sentiment_label: str,
        sentiment_score: float,
        routed_team: str,
        matched_keyword: str | None,
        processing_status: FeedbackProcessingStatus = FeedbackProcessingStatus.COMPLETED,
    ) -> FeedbackRecord:
        record.sentiment_label = sentiment_label
        record.sentiment_score = sentiment_score
        record.routed_team = routed_team
        record.matched_keyword = matched_keyword
        record.processing_status = processing_status
        record.error_code = None
        record.error_message = None
        self.session.flush()
        self.session.refresh(record)
        return record

    def _filtered_statement(
        self,
        *,
        source_type: FeedbackSourceType | None,
        processing_status: FeedbackProcessingStatus | None,
        routed_team: str | None,
        sentiment_label: str | None,
    ) -> Select[tuple[FeedbackRecord]]:
        statement = select(FeedbackRecord)
        if source_type is not None:
            statement = statement.where(FeedbackRecord.source_type == source_type)
        if processing_status is not None:
            statement = statement.where(FeedbackRecord.processing_status == processing_status)
        if routed_team is not None:
            statement = statement.where(FeedbackRecord.routed_team == routed_team)
        if sentiment_label is not None:
            statement = statement.where(FeedbackRecord.sentiment_label == sentiment_label)
        return statement
