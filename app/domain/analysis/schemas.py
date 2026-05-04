from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class SentimentLabel(StrEnum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"
    MIXED = "MIXED"


class AnalysisCategory(StrEnum):
    PAYMENT = "PAYMENT"
    UI = "UI"
    BACKEND = "BACKEND"
    SUPPORT = "SUPPORT"
    PERFORMANCE = "PERFORMANCE"
    SECURITY = "SECURITY"
    PRODUCT = "PRODUCT"
    DELIVERY = "DELIVERY"
    OTHER = "OTHER"


class Severity(StrEnum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class ValidationStatus(StrEnum):
    VALID = "VALID"
    INVALID = "INVALID"
    FAILED = "FAILED"


class StructuredAnalysisOutput(BaseModel):
    sentiment_label: SentimentLabel
    sentiment_score: float = Field(..., ge=0.0, le=1.0)
    category: AnalysisCategory
    severity: Severity
    routed_team: str = Field(..., min_length=1, max_length=128)
    summary: str = Field(..., min_length=1, max_length=1000)
    recommended_action: str = Field(..., min_length=1, max_length=1000)
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    reasoning_summary: str = Field(..., min_length=1, max_length=1000)
    evidence_chunk_ids: list[int] = Field(default_factory=list)


class AnalysisRunResponse(BaseModel):
    id: int
    feedback_record_id: int
    retrieval_trace_id: int | None
    provider: str
    model_name: str
    prompt_version: str
    output_json: dict | None
    validation_status: ValidationStatus
    error_code: str | None
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalysisResponse(BaseModel):
    feedback_id: int
    analysis_run_id: int
    retrieval_trace_id: int | None
    validation_status: ValidationStatus
    output: StructuredAnalysisOutput | None
    provider: str
    model_name: str
    prompt_version: str
    error_code: str | None = None
    error_message: str | None = None


class LatestAnalysisResponse(BaseModel):
    feedback_id: int
    latest_analysis_run_id: int | None
    sentiment_label: str | None
    sentiment_score: float | None
    category: str | None
    severity: str | None
    routed_team: str | None
    summary: str | None
    recommended_action: str | None
    confidence_score: float | None
