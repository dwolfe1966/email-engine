"""add dead letter send status

Revision ID: 0019_dead_letter_send_status
Revises: 0018_domain_delivery_policies
Create Date: 2026-06-09
"""
from collections.abc import Sequence

from alembic import op

revision: str = '0019_dead_letter_send_status'
down_revision: str | None = '0018_domain_delivery_policies'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE emailsendstatus ADD VALUE IF NOT EXISTS 'dead_lettered'")


def downgrade() -> None:
    # PostgreSQL cannot drop enum values without recreating the enum type.
    # Leave the value in place on downgrade; no rows are created by this migration.
    pass
