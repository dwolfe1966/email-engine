"""add send lifecycle statuses

Revision ID: 0020_send_lifecycle_statuses
Revises: 0019_dead_letter_send_status
Create Date: 2026-06-09
"""
from collections.abc import Sequence

from alembic import op

revision: str = '0020_send_lifecycle_statuses'
down_revision: str | None = '0019_dead_letter_send_status'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE emailsendstatus ADD VALUE IF NOT EXISTS 'submitted'")
    op.execute("ALTER TYPE emailsendstatus ADD VALUE IF NOT EXISTS 'delivered'")
    op.execute("ALTER TYPE emailsendstatus ADD VALUE IF NOT EXISTS 'deferred'")
    op.execute("ALTER TYPE emailsendstatus ADD VALUE IF NOT EXISTS 'bounced'")
    op.execute("ALTER TYPE emailsendstatus ADD VALUE IF NOT EXISTS 'complained'")
    op.execute("ALTER TYPE emailsendstatus ADD VALUE IF NOT EXISTS 'unsubscribed'")


def downgrade() -> None:
    # PostgreSQL cannot drop enum values without recreating the enum type.
    # Leave the values in place on downgrade; no rows are created by this migration.
    pass
