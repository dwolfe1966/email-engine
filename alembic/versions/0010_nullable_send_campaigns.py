"""allow journey sends without campaigns

Revision ID: 0010_nullable_send_campaigns
Revises: 0009_journey_execution
Create Date: 2026-05-21
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = '0010_nullable_send_campaigns'
down_revision: str | None = '0009_journey_execution'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column('campaign_send_jobs', 'campaign_id', existing_type=sa.UUID(), nullable=True)
    op.alter_column('email_send_records', 'campaign_id', existing_type=sa.UUID(), nullable=True)


def downgrade() -> None:
    op.alter_column('email_send_records', 'campaign_id', existing_type=sa.UUID(), nullable=False)
    op.alter_column('campaign_send_jobs', 'campaign_id', existing_type=sa.UUID(), nullable=False)
