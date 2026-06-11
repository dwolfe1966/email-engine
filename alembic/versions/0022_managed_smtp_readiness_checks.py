"""managed smtp readiness checks

Revision ID: 0022_smtp_readiness
Revises: 0021_provider_feedback_events
Create Date: 2026-06-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = '0022_smtp_readiness'
down_revision: str | None = '0021_provider_feedback_events'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'managed_smtp_readiness_checks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source', sa.String(length=100), nullable=False),
        sa.Column('check_type', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=40), nullable=False),
        sa.Column('domain', sa.String(length=255), nullable=True),
        sa.Column('host', sa.String(length=255), nullable=True),
        sa.Column('summary', sa.String(length=500), nullable=True),
        sa.Column('result_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_managed_smtp_readiness_checks_check_type'),
        'managed_smtp_readiness_checks',
        ['check_type'],
        unique=False,
    )
    op.create_index(
        op.f('ix_managed_smtp_readiness_checks_created_at'),
        'managed_smtp_readiness_checks',
        ['created_at'],
        unique=False,
    )
    op.create_index(
        op.f('ix_managed_smtp_readiness_checks_domain'),
        'managed_smtp_readiness_checks',
        ['domain'],
        unique=False,
    )
    op.create_index(
        op.f('ix_managed_smtp_readiness_checks_host'),
        'managed_smtp_readiness_checks',
        ['host'],
        unique=False,
    )
    op.create_index(
        op.f('ix_managed_smtp_readiness_checks_source'),
        'managed_smtp_readiness_checks',
        ['source'],
        unique=False,
    )
    op.create_index(
        op.f('ix_managed_smtp_readiness_checks_status'),
        'managed_smtp_readiness_checks',
        ['status'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f('ix_managed_smtp_readiness_checks_status'),
        table_name='managed_smtp_readiness_checks',
    )
    op.drop_index(
        op.f('ix_managed_smtp_readiness_checks_source'),
        table_name='managed_smtp_readiness_checks',
    )
    op.drop_index(
        op.f('ix_managed_smtp_readiness_checks_host'),
        table_name='managed_smtp_readiness_checks',
    )
    op.drop_index(
        op.f('ix_managed_smtp_readiness_checks_domain'),
        table_name='managed_smtp_readiness_checks',
    )
    op.drop_index(
        op.f('ix_managed_smtp_readiness_checks_created_at'),
        table_name='managed_smtp_readiness_checks',
    )
    op.drop_index(
        op.f('ix_managed_smtp_readiness_checks_check_type'),
        table_name='managed_smtp_readiness_checks',
    )
    op.drop_table('managed_smtp_readiness_checks')
