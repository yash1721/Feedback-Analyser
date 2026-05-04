"""create llm analysis runs

Revision ID: 20260505_0004
Revises: 20260505_0003
Create Date: 2026-05-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260505_0004"
down_revision: str | None = "20260505_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("feedback_records", sa.Column("category", sa.String(length=64), nullable=True))
    op.add_column("feedback_records", sa.Column("severity", sa.String(length=16), nullable=True))
    op.add_column("feedback_records", sa.Column("summary", sa.Text(), nullable=True))
    op.add_column("feedback_records", sa.Column("recommended_action", sa.Text(), nullable=True))
    op.add_column("feedback_records", sa.Column("confidence_score", sa.Float(), nullable=True))
    op.add_column("feedback_records", sa.Column("latest_analysis_run_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_feedback_records_category"), "feedback_records", ["category"], unique=False)
    op.create_index(op.f("ix_feedback_records_severity"), "feedback_records", ["severity"], unique=False)

    op.create_table(
        "llm_analysis_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("feedback_record_id", sa.Integer(), nullable=False),
        sa.Column("retrieval_trace_id", sa.Integer(), nullable=True),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column("prompt_version", sa.String(length=128), nullable=False),
        sa.Column("input_preview", sa.Text(), nullable=True),
        sa.Column("output_json", sa.JSON(), nullable=True),
        sa.Column("validation_status", sa.String(length=32), nullable=False),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["feedback_record_id"], ["feedback_records.id"]),
        sa.ForeignKeyConstraint(["retrieval_trace_id"], ["retrieval_traces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_llm_analysis_runs_id"), "llm_analysis_runs", ["id"], unique=False)
    op.create_index(op.f("ix_llm_analysis_runs_feedback_record_id"), "llm_analysis_runs", ["feedback_record_id"], unique=False)
    op.create_index(op.f("ix_llm_analysis_runs_retrieval_trace_id"), "llm_analysis_runs", ["retrieval_trace_id"], unique=False)
    op.create_index(op.f("ix_llm_analysis_runs_validation_status"), "llm_analysis_runs", ["validation_status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_llm_analysis_runs_validation_status"), table_name="llm_analysis_runs")
    op.drop_index(op.f("ix_llm_analysis_runs_retrieval_trace_id"), table_name="llm_analysis_runs")
    op.drop_index(op.f("ix_llm_analysis_runs_feedback_record_id"), table_name="llm_analysis_runs")
    op.drop_index(op.f("ix_llm_analysis_runs_id"), table_name="llm_analysis_runs")
    op.drop_table("llm_analysis_runs")
    op.drop_index(op.f("ix_feedback_records_severity"), table_name="feedback_records")
    op.drop_index(op.f("ix_feedback_records_category"), table_name="feedback_records")
    op.drop_column("feedback_records", "latest_analysis_run_id")
    op.drop_column("feedback_records", "confidence_score")
    op.drop_column("feedback_records", "recommended_action")
    op.drop_column("feedback_records", "summary")
    op.drop_column("feedback_records", "severity")
    op.drop_column("feedback_records", "category")
