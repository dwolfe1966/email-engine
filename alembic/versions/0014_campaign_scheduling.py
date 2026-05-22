"""add campaign scheduling

Revision ID: 0014_campaign_scheduling
Revises: 0013_audience_snapshots
Create Date: 2026-05-22
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = '0014_campaign_scheduling'
down_revision: str | None = '0013_audience_snapshots'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('campaigns', sa.Column('scheduled_at', sa.DateTime(), nullable=True))
    op.create_index(
        op.f('ix_campaigns_scheduled_at'),
        'campaigns',
        ['scheduled_at'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_campaigns_scheduled_at'), table_name='campaigns')
    op.drop_column('campaigns', 'scheduled_at')
