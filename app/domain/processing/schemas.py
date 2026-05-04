from pydantic import BaseModel

from app.domain.feedback.models import FeedbackProcessingStatus


class ProcessingEnqueueResponse(BaseModel):
    feedback_id: int
    processing_status: FeedbackProcessingStatus
    task_id: str | None
    enqueued: bool


class ProcessingStatusResponse(BaseModel):
    feedback_id: int
    processing_status: FeedbackProcessingStatus
    task_id: str | None
    error_code: str | None
    error_message: str | None
    sentiment_label: str | None
    sentiment_score: float | None
    routed_team: str | None
    matched_keyword: str | None
