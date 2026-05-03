from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, Float, String, Text, func
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
    PROCESSING = "PROCESSING"
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
    sentiment_label: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    routed_team: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    matched_keyword: Mapped[str | None] = mapped_column(String(128), nullable=True)
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
