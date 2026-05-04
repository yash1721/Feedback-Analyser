from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    source_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    chunks: Mapped[list["KnowledgeChunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("knowledge_documents.id", ondelete="CASCADE"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    char_count: Mapped[int] = mapped_column(Integer, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    qdrant_point_id: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    document: Mapped[KnowledgeDocument] = relationship(back_populates="chunks")


class RetrievalTrace(Base):
    __tablename__ = "retrieval_traces"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    feedback_record_id: Mapped[int | None] = mapped_column(ForeignKey("feedback_records.id"), nullable=True, index=True)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(255), nullable=False)
    collection_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    top_k: Mapped[int] = mapped_column(Integer, nullable=False)
    filters_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    items: Mapped[list["RetrievalTraceItem"]] = relationship(
        back_populates="trace",
        cascade="all, delete-orphan",
    )


class RetrievalTraceItem(Base):
    __tablename__ = "retrieval_trace_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    retrieval_trace_id: Mapped[int] = mapped_column(ForeignKey("retrieval_traces.id", ondelete="CASCADE"), index=True)
    knowledge_chunk_id: Mapped[int | None] = mapped_column(ForeignKey("knowledge_chunks.id"), nullable=True, index=True)
    qdrant_point_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    text_preview: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    trace: Mapped[RetrievalTrace] = relationship(back_populates="items")
