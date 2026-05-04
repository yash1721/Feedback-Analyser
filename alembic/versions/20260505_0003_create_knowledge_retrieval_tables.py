"""create knowledge and retrieval evidence tables

Revision ID: 20260505_0003
Revises: 20260504_0002
Create Date: 2026-05-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260505_0003"
down_revision: str | None = "20260504_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "knowledge_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_name", sa.String(length=512), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_knowledge_documents_id"), "knowledge_documents", ["id"], unique=False)
    op.create_index(op.f("ix_knowledge_documents_source_type"), "knowledge_documents", ["source_type"], unique=False)
    op.create_index(op.f("ix_knowledge_documents_content_hash"), "knowledge_documents", ["content_hash"], unique=False)
    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("char_count", sa.Integer(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("qdrant_point_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["knowledge_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_knowledge_chunks_id"), "knowledge_chunks", ["id"], unique=False)
    op.create_index(op.f("ix_knowledge_chunks_document_id"), "knowledge_chunks", ["document_id"], unique=False)
    op.create_index(op.f("ix_knowledge_chunks_qdrant_point_id"), "knowledge_chunks", ["qdrant_point_id"], unique=False)
    op.create_table(
        "retrieval_traces",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("feedback_record_id", sa.Integer(), nullable=True),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("embedding_model", sa.String(length=255), nullable=False),
        sa.Column("collection_name", sa.String(length=255), nullable=True),
        sa.Column("top_k", sa.Integer(), nullable=False),
        sa.Column("filters_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["feedback_record_id"], ["feedback_records.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_retrieval_traces_id"), "retrieval_traces", ["id"], unique=False)
    op.create_index(op.f("ix_retrieval_traces_feedback_record_id"), "retrieval_traces", ["feedback_record_id"], unique=False)
    op.create_table(
        "retrieval_trace_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("retrieval_trace_id", sa.Integer(), nullable=False),
        sa.Column("knowledge_chunk_id", sa.Integer(), nullable=True),
        sa.Column("qdrant_point_id", sa.String(length=128), nullable=True),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("text_preview", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["knowledge_chunk_id"], ["knowledge_chunks.id"]),
        sa.ForeignKeyConstraint(["retrieval_trace_id"], ["retrieval_traces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_retrieval_trace_items_id"), "retrieval_trace_items", ["id"], unique=False)
    op.create_index(op.f("ix_retrieval_trace_items_retrieval_trace_id"), "retrieval_trace_items", ["retrieval_trace_id"], unique=False)
    op.create_index(op.f("ix_retrieval_trace_items_knowledge_chunk_id"), "retrieval_trace_items", ["knowledge_chunk_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_retrieval_trace_items_knowledge_chunk_id"), table_name="retrieval_trace_items")
    op.drop_index(op.f("ix_retrieval_trace_items_retrieval_trace_id"), table_name="retrieval_trace_items")
    op.drop_index(op.f("ix_retrieval_trace_items_id"), table_name="retrieval_trace_items")
    op.drop_table("retrieval_trace_items")
    op.drop_index(op.f("ix_retrieval_traces_feedback_record_id"), table_name="retrieval_traces")
    op.drop_index(op.f("ix_retrieval_traces_id"), table_name="retrieval_traces")
    op.drop_table("retrieval_traces")
    op.drop_index(op.f("ix_knowledge_chunks_qdrant_point_id"), table_name="knowledge_chunks")
    op.drop_index(op.f("ix_knowledge_chunks_document_id"), table_name="knowledge_chunks")
    op.drop_index(op.f("ix_knowledge_chunks_id"), table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")
    op.drop_index(op.f("ix_knowledge_documents_content_hash"), table_name="knowledge_documents")
    op.drop_index(op.f("ix_knowledge_documents_source_type"), table_name="knowledge_documents")
    op.drop_index(op.f("ix_knowledge_documents_id"), table_name="knowledge_documents")
    op.drop_table("knowledge_documents")
