from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven runtime settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "FeedbackIQ"
    environment: Literal["local", "test", "production"] = "local"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    service_name: str = "FeedbackIQ"
    log_level: str = "INFO"
    log_format: Literal["plain", "json"] = "plain"
    otel_enabled: bool = False
    otel_exporter_otlp_endpoint: str | None = None

    request_timeout_seconds: float = 10.0
    max_image_bytes: int = Field(default=5 * 1024 * 1024, ge=1)
    max_pdf_bytes: int = Field(default=10 * 1024 * 1024, ge=1)
    max_csv_bytes: int = Field(default=2 * 1024 * 1024, ge=1)
    ocr_languages: str = "eng+hin"
    tesseract_timeout_seconds: int = 5

    embedding_model_name: str = "BAAI/bge-m3"
    sentiment_model_name: str = "distilbert-base-uncased-finetuned-sst-2-english"
    retrieval_top_k: int = 3

    database_url: str = "postgresql+psycopg://feedbackiq:feedbackiq@localhost:5432/feedbackiq"
    test_database_url: str = "sqlite+pysqlite:///:memory:"
    local_storage_dir: str = ".local_storage"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    processing_max_retries: int = Field(default=3, ge=0)
    processing_retry_backoff_seconds: int = Field(default=5, ge=1)
    celery_task_always_eager: bool = False
    vector_provider: Literal["faiss", "qdrant"] = "qdrant"
    embedding_provider: Literal["minilm", "bge_m3"] = "bge_m3"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection_name: str = "feedbackiq_knowledge"
    vector_size: int = Field(default=1024, ge=1)
    vector_distance: Literal["cosine", "dot", "euclidean"] = "cosine"
    knowledge_chunk_size_chars: int = Field(default=1200, ge=100)
    knowledge_chunk_overlap_chars: int = Field(default=200, ge=0)
    llm_provider: Literal["fake", "rule_based"] = "rule_based"
    llm_fallback_provider: Literal["none", "rule_based"] = "rule_based"
    llm_model_name: str = "rule-based-feedback-analyzer-v1"
    llm_prompt_version: str = "feedback-analysis-v1"
    llm_confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    workflow_low_confidence_threshold: float = Field(default=0.65, ge=0.0, le=1.0)
    workflow_default_sla_hours: int = Field(default=48, ge=1)
    workflow_p0_sla_hours: int = Field(default=4, ge=1)
    workflow_p1_sla_hours: int = Field(default=12, ge=1)
    workflow_auto_create_tickets: bool = False
    notification_provider: Literal["log", "mock"] = "log"
    evaluation_report_dir: str = "eval_reports"


@lru_cache
def get_settings() -> Settings:
    return Settings()
