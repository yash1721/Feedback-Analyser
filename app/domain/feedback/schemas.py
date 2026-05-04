from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.feedback.models import FeedbackProcessingStatus, FeedbackSourceType


class FeedbackRecordCreate(BaseModel):
    text: str = Field(..., min_length=1)
    source_type: FeedbackSourceType = FeedbackSourceType.TEXT
    original_input_reference: str | None = Field(default=None, max_length=512)


class FeedbackStatusUpdate(BaseModel):
    processing_status: FeedbackProcessingStatus
    error_code: str | None = Field(default=None, max_length=128)
    error_message: str | None = None


class FeedbackRecordRead(BaseModel):
    id: int
    source_type: FeedbackSourceType
    original_input_reference: str | None
    raw_text: str | None
    extracted_text: str | None
    normalized_text: str | None
    sentiment_label: str | None
    sentiment_score: float | None
    category: str | None
    severity: str | None
    routed_team: str | None
    matched_keyword: str | None
    summary: str | None
    recommended_action: str | None
    confidence_score: float | None
    latest_analysis_run_id: int | None
    processing_task_id: str | None
    processing_status: FeedbackProcessingStatus
    error_code: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FeedbackRecordListResponse(BaseModel):
    items: list[FeedbackRecordRead]
    total: int
    limit: int
    offset: int


class FeedbackAnalysisResponse(BaseModel):
    text: str
    sentiment: dict
    routing: dict
    retrieval: list[dict]
    rag_context: str
    record_id: int | None = None
