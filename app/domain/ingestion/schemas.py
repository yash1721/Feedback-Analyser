from pydantic import BaseModel, Field, HttpUrl

from app.domain.feedback.models import FeedbackProcessingStatus, FeedbackSourceType


class TextIngestionRequest(BaseModel):
    text: str = Field(..., min_length=1)


class ImageUrlIngestionRequest(BaseModel):
    url: HttpUrl


class IngestionResult(BaseModel):
    feedback_id: int
    source_type: FeedbackSourceType
    processing_status: FeedbackProcessingStatus
    original_input_reference: str | None = None
    raw_text: str | None = None
    extracted_text: str | None = None
    normalized_text: str | None = None
    sanitized_text: str | None = None
    pii_detected: bool = False
    prompt_injection_detected: bool = False
    prompt_injection_risk: str | None = None
    error_code: str | None = None
    error_message: str | None = None


class CsvRowError(BaseModel):
    row_number: int
    error_code: str
    error_message: str


class CsvIngestionResponse(BaseModel):
    source_type: FeedbackSourceType = FeedbackSourceType.CSV
    original_input_reference: str | None = None
    created_count: int
    failed_count: int
    feedback_ids: list[int]
    row_errors: list[CsvRowError]
