"""create feedback records

Revision ID: 20260504_0001
Revises:
Create Date: 2026-05-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260504_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "feedback_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "source_type",
            sa.Enum("TEXT", "IMAGE", "PDF", "CSV", "API", name="feedbacksourcetype", native_enum=False),
            nullable=False,
        ),
        sa.Column("original_input_reference", sa.String(length=512), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("normalized_text", sa.Text(), nullable=True),
        sa.Column("sentiment_label", sa.String(length=64), nullable=True),
        sa.Column("sentiment_score", sa.Float(), nullable=True),
        sa.Column("routed_team", sa.String(length=128), nullable=True),
        sa.Column("matched_keyword", sa.String(length=128), nullable=True),
        sa.Column(
            "processing_status",
            sa.Enum("PENDING", "PROCESSING", "COMPLETED", "FAILED", name="feedbackprocessingstatus", native_enum=False),
            nullable=False,
        ),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_feedback_records_id"), "feedback_records", ["id"], unique=False)
    op.create_index(op.f("ix_feedback_records_source_type"), "feedback_records", ["source_type"], unique=False)
    op.create_index(op.f("ix_feedback_records_sentiment_label"), "feedback_records", ["sentiment_label"], unique=False)
    op.create_index(op.f("ix_feedback_records_routed_team"), "feedback_records", ["routed_team"], unique=False)
    op.create_index(op.f("ix_feedback_records_processing_status"), "feedback_records", ["processing_status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_feedback_records_processing_status"), table_name="feedback_records")
    op.drop_index(op.f("ix_feedback_records_routed_team"), table_name="feedback_records")
    op.drop_index(op.f("ix_feedback_records_sentiment_label"), table_name="feedback_records")
    op.drop_index(op.f("ix_feedback_records_source_type"), table_name="feedback_records")
    op.drop_index(op.f("ix_feedback_records_id"), table_name="feedback_records")
    op.drop_table("feedback_records")
