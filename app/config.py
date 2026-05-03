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

    request_timeout_seconds: float = 10.0
    max_image_bytes: int = Field(default=5 * 1024 * 1024, ge=1)
    ocr_languages: str = "eng+hin"
    tesseract_timeout_seconds: int = 5

    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    sentiment_model_name: str = "distilbert-base-uncased-finetuned-sst-2-english"
    retrieval_top_k: int = 3


@lru_cache
def get_settings() -> Settings:
    return Settings()

