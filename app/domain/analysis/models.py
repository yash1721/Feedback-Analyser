from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LLMAnalysisRun(Base):
    __tablename__ = "llm_analysis_runs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    feedback_record_id: Mapped[int] = mapped_column(ForeignKey("feedback_records.id"), index=True)
    retrieval_trace_id: Mapped[int | None] = mapped_column(ForeignKey("retrieval_traces.id"), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(128), nullable=False)
    input_preview: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    validation_status: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
