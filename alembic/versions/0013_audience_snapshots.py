"""add audience snapshots

Revision ID: 0013_audience_snapshots
Revises: 0012_delivery_retry_state
Create Date: 2026-05-22
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = '0013_audience_snapshots'
down_revision: str | None = '0012_delivery_retry_state'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'audience_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('audience_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('rule_tree', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('estimated_count', sa.Integer(), nullable=False),
        sa.Column('contact_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['audience_id'], ['audiences.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('audience_id', 'version_number', name='uq_audience_snapshots_number'),
    )
    op.create_index(
        op.f('ix_audience_snapshots_audience_id'),
        'audience_snapshots',
        ['audience_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_audience_snapshots_name'),
        'audience_snapshots',
        ['name'],
        unique=False,
    )
    op.add_column(
        'campaign_send_jobs',
        sa.Column('audience_snapshot_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        'fk_campaign_send_jobs_audience_snapshot_id',
        'campaign_send_jobs',
        'audience_snapshots',
        ['audience_snapshot_id'],
        ['id'],
    )
    op.create_index(
        op.f('ix_campaign_send_jobs_audience_snapshot_id'),
        'campaign_send_jobs',
        ['audience_snapshot_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f('ix_campaign_send_jobs_audience_snapshot_id'),
        table_name='campaign_send_jobs',
    )
    op.drop_constraint(
        'fk_campaign_send_jobs_audience_snapshot_id',
        'campaign_send_jobs',
        type_='foreignkey',
    )
    op.drop_column('campaign_send_jobs', 'audience_snapshot_id')
    op.drop_index(op.f('ix_audience_snapshots_name'), table_name='audience_snapshots')
    op.drop_index(op.f('ix_audience_snapshots_audience_id'), table_name='audience_snapshots')
    op.drop_table('audience_snapshots')
