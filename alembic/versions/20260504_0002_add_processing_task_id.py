"""add processing task id

Revision ID: 20260504_0002
Revises: 20260504_0001
Create Date: 2026-05-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260504_0002"
down_revision: str | None = "20260504_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("feedback_records", sa.Column("processing_task_id", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("feedback_records", "processing_task_id")
