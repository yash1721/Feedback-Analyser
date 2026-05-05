"""create evaluation tables

Revision ID: 20260505_0006
Revises: 20260505_0005
Create Date: 2026-05-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260505_0006"
down_revision: str | None = "20260505_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "evaluation_datasets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_path", sa.String(length=512), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ["id", "name", "version"]:
        op.create_index(op.f(f"ix_evaluation_datasets_{column}"), "evaluation_datasets", [column], unique=False)

    op.create_table(
        "evaluation_examples",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dataset_id", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.String(length=128), nullable=False),
        sa.Column("feedback_text", sa.Text(), nullable=False),
        sa.Column("expected_json", sa.JSON(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["evaluation_datasets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ["id", "dataset_id", "external_id"]:
        op.create_index(op.f(f"ix_evaluation_examples_{column}"), "evaluation_examples", [column], unique=False)

    op.create_table(
        "evaluation_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dataset_id", sa.Integer(), nullable=True),
        sa.Column("dataset_name", sa.String(length=128), nullable=False),
        sa.Column("dataset_version", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column("prompt_version", sa.String(length=128), nullable=False),
        sa.Column("vector_provider", sa.String(length=64), nullable=False),
        sa.Column("embedding_model", sa.String(length=255), nullable=False),
        sa.Column("top_k", sa.Integer(), nullable=False),
        sa.Column("total_examples", sa.Integer(), nullable=False),
        sa.Column("metrics_json", sa.JSON(), nullable=True),
        sa.Column("report_path", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["evaluation_datasets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ["id", "dataset_id", "dataset_name", "provider", "prompt_version"]:
        op.create_index(op.f(f"ix_evaluation_runs_{column}"), "evaluation_runs", [column], unique=False)

    op.create_table(
        "evaluation_run_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("evaluation_run_id", sa.Integer(), nullable=False),
        sa.Column("example_id", sa.Integer(), nullable=True),
        sa.Column("example_external_id", sa.String(length=128), nullable=False),
        sa.Column("feedback_text", sa.Text(), nullable=False),
        sa.Column("expected_json", sa.JSON(), nullable=False),
        sa.Column("predicted_json", sa.JSON(), nullable=True),
        sa.Column("retrieval_trace_id", sa.Integer(), nullable=True),
        sa.Column("analysis_run_id", sa.Integer(), nullable=True),
        sa.Column("metrics_json", sa.JSON(), nullable=True),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retrieval_latency_ms", sa.Integer(), nullable=True),
        sa.Column("analysis_latency_ms", sa.Integer(), nullable=True),
        sa.Column("total_latency_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["llm_analysis_runs.id"]),
        sa.ForeignKeyConstraint(["evaluation_run_id"], ["evaluation_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["example_id"], ["evaluation_examples.id"]),
        sa.ForeignKeyConstraint(["retrieval_trace_id"], ["retrieval_traces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ["id", "evaluation_run_id", "example_id", "example_external_id", "retrieval_trace_id", "analysis_run_id"]:
        op.create_index(op.f(f"ix_evaluation_run_items_{column}"), "evaluation_run_items", [column], unique=False)


def downgrade() -> None:
    for column in ["analysis_run_id", "retrieval_trace_id", "example_external_id", "example_id", "evaluation_run_id", "id"]:
        op.drop_index(op.f(f"ix_evaluation_run_items_{column}"), table_name="evaluation_run_items")
    op.drop_table("evaluation_run_items")
    for column in ["prompt_version", "provider", "dataset_name", "dataset_id", "id"]:
        op.drop_index(op.f(f"ix_evaluation_runs_{column}"), table_name="evaluation_runs")
    op.drop_table("evaluation_runs")
    for column in ["external_id", "dataset_id", "id"]:
        op.drop_index(op.f(f"ix_evaluation_examples_{column}"), table_name="evaluation_examples")
    op.drop_table("evaluation_examples")
    for column in ["version", "name", "id"]:
        op.drop_index(op.f(f"ix_evaluation_datasets_{column}"), table_name="evaluation_datasets")
    op.drop_table("evaluation_datasets")
