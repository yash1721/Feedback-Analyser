from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class KnowledgeDocumentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    text: str = Field(..., min_length=1)
    source_type: str = Field(default="manual", min_length=1, max_length=64)
    source_name: str | None = Field(default=None, max_length=512)
    metadata: dict[str, Any] | None = None


class KnowledgeDocumentRead(BaseModel):
    id: int
    title: str
    source_type: str
    source_name: str | None
    content_hash: str
    metadata_json: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeChunkRead(BaseModel):
    id: int
    document_id: int
    chunk_index: int
    text: str
    char_count: int
    metadata_json: dict[str, Any] | None
    qdrant_point_id: str | None

    model_config = {"from_attributes": True}


class KnowledgeDocumentDetail(KnowledgeDocumentRead):
    chunks: list[KnowledgeChunkRead]


class KnowledgeDocumentListResponse(BaseModel):
    items: list[KnowledgeDocumentRead]
    limit: int
    offset: int


class KnowledgeDocumentIndexResponse(BaseModel):
    document_id: int
    indexed_chunks: int
    vector_provider: str
    embedding_provider: str
