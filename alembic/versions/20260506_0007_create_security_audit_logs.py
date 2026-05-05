"""create security audit logs and feedback security fields

Revision ID: 20260506_0007
Revises: 20260505_0006
Create Date: 2026-05-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260506_0007"
down_revision: str | None = "20260505_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("feedback_records", sa.Column("sanitized_text", sa.Text(), nullable=True))
    op.add_column("feedback_records", sa.Column("pii_detected", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("feedback_records", sa.Column("pii_types_json", sa.JSON(), nullable=True))
    op.add_column("feedback_records", sa.Column("prompt_injection_detected", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("feedback_records", sa.Column("prompt_injection_risk", sa.String(length=32), nullable=True))
    op.add_column("feedback_records", sa.Column("prompt_injection_patterns_json", sa.JSON(), nullable=True))
    op.create_table(
        "security_audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("actor_type", sa.String(length=64), nullable=False),
        sa.Column("actor_id", sa.String(length=128), nullable=True),
        sa.Column("correlation_id", sa.String(length=128), nullable=True),
        sa.Column("path", sa.String(length=512), nullable=True),
        sa.Column("method", sa.String(length=16), nullable=True),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ["id", "event_type", "severity", "correlation_id", "decision"]:
        op.create_index(op.f(f"ix_security_audit_logs_{column}"), "security_audit_logs", [column], unique=False)


def downgrade() -> None:
    for column in ["decision", "correlation_id", "severity", "event_type", "id"]:
        op.drop_index(op.f(f"ix_security_audit_logs_{column}"), table_name="security_audit_logs")
    op.drop_table("security_audit_logs")
    op.drop_column("feedback_records", "prompt_injection_patterns_json")
    op.drop_column("feedback_records", "prompt_injection_risk")
    op.drop_column("feedback_records", "prompt_injection_detected")
    op.drop_column("feedback_records", "pii_types_json")
    op.drop_column("feedback_records", "pii_detected")
    op.drop_column("feedback_records", "sanitized_text")
