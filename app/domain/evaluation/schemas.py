from datetime import datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field


class GroundednessStatus(StrEnum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


class EvaluationExampleSchema(BaseModel):
    id: str = Field(..., min_length=1, max_length=128)
    feedback_text: str = Field(..., min_length=1)
    expected_sentiment: str = Field(..., min_length=1)
    expected_category: str = Field(..., min_length=1)
    expected_severity: str = Field(..., min_length=1)
    expected_routed_team: str = Field(..., min_length=1)
    expected_keywords: list[str] = Field(default_factory=list)
    expected_relevant_chunk_ids: list[int] = Field(default_factory=list)
    expected_relevant_document_titles: list[str] = Field(default_factory=list)
    expected_escalate: bool | None = None
    expected_needs_review: bool | None = None
    notes: str | None = None

    def expected_json(self) -> dict:
        return self.model_dump(exclude={"id", "feedback_text", "notes"}, mode="json")


class EvaluationDatasetFile(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    version: str = Field(default="v1", min_length=1, max_length=64)
    description: str | None = None
    examples: list[EvaluationExampleSchema] = Field(..., min_length=1)


class EvaluationRunCreate(BaseModel):
    dataset_path: str | None = None
    dataset_name: str | None = None
    prompt_version: str | None = None
    provider: str | None = None
    model_name: str | None = None
    top_k: int | None = Field(default=None, ge=1, le=20)
    persist_dataset: bool = True
    write_report: bool = True


class EvaluationRunSummary(BaseModel):
    id: int
    dataset_id: int | None
    dataset_name: str
    dataset_version: str
    provider: str
    model_name: str
    prompt_version: str
    vector_provider: str
    embedding_model: str
    top_k: int
    total_examples: int
    metrics_json: dict | None
    report_path: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class EvaluationRunItemRead(BaseModel):
    id: int
    evaluation_run_id: int
    example_id: int | None
    example_external_id: str
    expected_json: dict
    predicted_json: dict | None
    retrieval_trace_id: int | None
    analysis_run_id: int | None
    metrics_json: dict | None
    error_code: str | None
    error_message: str | None
    retrieval_latency_ms: int | None
    analysis_latency_ms: int | None
    total_latency_ms: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class EvaluationRunDetail(EvaluationRunSummary):
    items: list[EvaluationRunItemRead] = Field(default_factory=list)


class EvaluationRunListResponse(BaseModel):
    items: list[EvaluationRunSummary]
    total: int
    limit: int
    offset: int


class EvaluationRunResult(BaseModel):
    run: EvaluationRunSummary
    metrics: dict
    report_path: str | None


class EvaluationServiceConfig(BaseModel):
    dataset_path: Path | None = None
    dataset_name: str | None = None
    prompt_version: str
    top_k: int
    persist_dataset: bool = True
    write_report: bool = True
