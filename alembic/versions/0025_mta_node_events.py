"""add mta node events

Revision ID: 0025_mta_node_events
Revises: 0024_scaleway_mta_provider
Create Date: 2026-06-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = '0025_mta_node_events'
down_revision: str | None = '0024_scaleway_mta_provider'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'mta_node_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('mta_node_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('severity', sa.String(length=40), nullable=False),
        sa.Column('summary', sa.String(length=500), nullable=True),
        sa.Column('payload_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('observed_at', sa.DateTime(), nullable=False),
        sa.Column('received_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['mta_node_id'], ['mta_nodes.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_mta_node_events_event_type'), 'mta_node_events', ['event_type'])
    op.create_index(op.f('ix_mta_node_events_mta_node_id'), 'mta_node_events', ['mta_node_id'])
    op.create_index(op.f('ix_mta_node_events_observed_at'), 'mta_node_events', ['observed_at'])
    op.create_index(op.f('ix_mta_node_events_received_at'), 'mta_node_events', ['received_at'])
    op.create_index(op.f('ix_mta_node_events_severity'), 'mta_node_events', ['severity'])


def downgrade() -> None:
    op.drop_index(op.f('ix_mta_node_events_severity'), table_name='mta_node_events')
    op.drop_index(op.f('ix_mta_node_events_received_at'), table_name='mta_node_events')
    op.drop_index(op.f('ix_mta_node_events_observed_at'), table_name='mta_node_events')
    op.drop_index(op.f('ix_mta_node_events_mta_node_id'), table_name='mta_node_events')
    op.drop_index(op.f('ix_mta_node_events_event_type'), table_name='mta_node_events')
    op.drop_table('mta_node_events')
