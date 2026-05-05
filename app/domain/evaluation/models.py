from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class EvaluationDataset(Base):
    __tablename__ = "evaluation_datasets"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    version: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    examples: Mapped[list["EvaluationExample"]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
    )


class EvaluationExample(Base):
    __tablename__ = "evaluation_examples"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("evaluation_datasets.id", ondelete="CASCADE"), index=True)
    external_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    feedback_text: Mapped[str] = mapped_column(Text, nullable=False)
    expected_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    dataset: Mapped[EvaluationDataset] = relationship(back_populates="examples")


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    dataset_id: Mapped[int | None] = mapped_column(ForeignKey("evaluation_datasets.id"), nullable=True, index=True)
    dataset_name: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    vector_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(255), nullable=False)
    top_k: Mapped[int] = mapped_column(Integer, nullable=False)
    total_examples: Mapped[int] = mapped_column(Integer, nullable=False)
    metrics_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    report_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    items: Mapped[list["EvaluationRunItem"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )


class EvaluationRunItem(Base):
    __tablename__ = "evaluation_run_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    evaluation_run_id: Mapped[int] = mapped_column(ForeignKey("evaluation_runs.id", ondelete="CASCADE"), index=True)
    example_id: Mapped[int | None] = mapped_column(ForeignKey("evaluation_examples.id"), nullable=True, index=True)
    example_external_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    feedback_text: Mapped[str] = mapped_column(Text, nullable=False)
    expected_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    predicted_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    retrieval_trace_id: Mapped[int | None] = mapped_column(ForeignKey("retrieval_traces.id"), nullable=True, index=True)
    analysis_run_id: Mapped[int | None] = mapped_column(ForeignKey("llm_analysis_runs.id"), nullable=True, index=True)
    metrics_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retrieval_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    analysis_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    run: Mapped[EvaluationRun] = relationship(back_populates="items")
