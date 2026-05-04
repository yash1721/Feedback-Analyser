"""create workflow tables

Revision ID: 20260505_0005
Revises: 20260505_0004
Create Date: 2026-05-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260505_0005"
down_revision: str | None = "20260505_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workflow_tickets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("feedback_record_id", sa.Integer(), nullable=False),
        sa.Column("analysis_run_id", sa.Integer(), nullable=True),
        sa.Column("retrieval_trace_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=True),
        sa.Column("severity", sa.String(length=16), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("assigned_team", sa.String(length=128), nullable=True),
        sa.Column("assigned_owner", sa.String(length=128), nullable=True),
        sa.Column("duplicate_of_ticket_id", sa.Integer(), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("escalated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["llm_analysis_runs.id"]),
        sa.ForeignKeyConstraint(["duplicate_of_ticket_id"], ["workflow_tickets.id"]),
        sa.ForeignKeyConstraint(["feedback_record_id"], ["feedback_records.id"]),
        sa.ForeignKeyConstraint(["retrieval_trace_id"], ["retrieval_traces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ["id", "feedback_record_id", "analysis_run_id", "retrieval_trace_id", "category", "severity", "status", "assigned_team", "duplicate_of_ticket_id"]:
        op.create_index(op.f(f"ix_workflow_tickets_{column}"), "workflow_tickets", [column], unique=False)

    op.create_table(
        "workflow_review_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("feedback_record_id", sa.Integer(), nullable=False),
        sa.Column("analysis_run_id", sa.Integer(), nullable=True),
        sa.Column("ticket_id", sa.Integer(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("suggested_team", sa.String(length=128), nullable=True),
        sa.Column("suggested_severity", sa.String(length=16), nullable=True),
        sa.Column("final_team", sa.String(length=128), nullable=True),
        sa.Column("final_severity", sa.String(length=16), nullable=True),
        sa.Column("reviewer_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["llm_analysis_runs.id"]),
        sa.ForeignKeyConstraint(["feedback_record_id"], ["feedback_records.id"]),
        sa.ForeignKeyConstraint(["ticket_id"], ["workflow_tickets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ["id", "feedback_record_id", "analysis_run_id", "ticket_id", "status"]:
        op.create_index(op.f(f"ix_workflow_review_items_{column}"), "workflow_review_items", [column], unique=False)

    op.create_table(
        "workflow_audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("actor_type", sa.String(length=64), nullable=False),
        sa.Column("actor_id", sa.String(length=128), nullable=True),
        sa.Column("previous_state_json", sa.JSON(), nullable=True),
        sa.Column("new_state_json", sa.JSON(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ["id", "entity_type", "entity_id", "action"]:
        op.create_index(op.f(f"ix_workflow_audit_logs_{column}"), "workflow_audit_logs", [column], unique=False)


def downgrade() -> None:
    for column in ["action", "entity_id", "entity_type", "id"]:
        op.drop_index(op.f(f"ix_workflow_audit_logs_{column}"), table_name="workflow_audit_logs")
    op.drop_table("workflow_audit_logs")
    for column in ["status", "ticket_id", "analysis_run_id", "feedback_record_id", "id"]:
        op.drop_index(op.f(f"ix_workflow_review_items_{column}"), table_name="workflow_review_items")
    op.drop_table("workflow_review_items")
    for column in ["duplicate_of_ticket_id", "assigned_team", "status", "severity", "category", "retrieval_trace_id", "analysis_run_id", "feedback_record_id", "id"]:
        op.drop_index(op.f(f"ix_workflow_tickets_{column}"), table_name="workflow_tickets")
    op.drop_table("workflow_tickets")
