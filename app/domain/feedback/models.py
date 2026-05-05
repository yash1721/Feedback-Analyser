from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Enum, Float, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FeedbackSourceType(StrEnum):
    TEXT = "TEXT"
    IMAGE = "IMAGE"
    PDF = "PDF"
    CSV = "CSV"
    API = "API"


class FeedbackProcessingStatus(StrEnum):
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    EXTRACTED = "EXTRACTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class FeedbackRecord(Base):
    __tablename__ = "feedback_records"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    source_type: Mapped[FeedbackSourceType] = mapped_column(
        Enum(FeedbackSourceType, native_enum=False),
        index=True,
    )
    original_input_reference: Mapped[str | None] = mapped_column(String(512), nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalized_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    sanitized_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    pii_detected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    pii_types_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    prompt_injection_detected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    prompt_injection_risk: Mapped[str | None] = mapped_column(String(32), nullable=True)
    prompt_injection_patterns_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    sentiment_label: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    category: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    severity: Mapped[str | None] = mapped_column(String(16), index=True, nullable=True)
    routed_team: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    matched_keyword: Mapped[str | None] = mapped_column(String(128), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    latest_analysis_run_id: Mapped[int | None] = mapped_column(nullable=True)
    processing_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    processing_status: Mapped[FeedbackProcessingStatus] = mapped_column(
        Enum(FeedbackProcessingStatus, native_enum=False),
        default=FeedbackProcessingStatus.PENDING,
        index=True,
    )
    error_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
