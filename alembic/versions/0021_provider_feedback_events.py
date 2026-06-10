"""provider feedback event retention

Revision ID: 0021_provider_feedback_events
Revises: 0020_send_lifecycle_statuses
Create Date: 2026-06-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = '0021_provider_feedback_events'
down_revision: str | None = '0020_send_lifecycle_statuses'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'provider_feedback_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('provider', sa.String(length=100), nullable=False),
        sa.Column('source', sa.String(length=100), nullable=False),
        sa.Column('event_name', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=320), nullable=False),
        sa.Column('provider_message_id', sa.String(length=255), nullable=True),
        sa.Column('idempotency_key', sa.String(length=128), nullable=False),
        sa.Column('payload_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('received_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'provider',
            'source',
            'idempotency_key',
            name='uq_provider_feedback_events_idempotency',
        ),
    )
    op.create_index(
        op.f('ix_provider_feedback_events_email'),
        'provider_feedback_events',
        ['email'],
        unique=False,
    )
    op.create_index(
        op.f('ix_provider_feedback_events_event_name'),
        'provider_feedback_events',
        ['event_name'],
        unique=False,
    )
    op.create_index(
        op.f('ix_provider_feedback_events_idempotency_key'),
        'provider_feedback_events',
        ['idempotency_key'],
        unique=False,
    )
    op.create_index(
        op.f('ix_provider_feedback_events_provider'),
        'provider_feedback_events',
        ['provider'],
        unique=False,
    )
    op.create_index(
        op.f('ix_provider_feedback_events_provider_message_id'),
        'provider_feedback_events',
        ['provider_message_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_provider_feedback_events_received_at'),
        'provider_feedback_events',
        ['received_at'],
        unique=False,
    )
    op.create_index(
        op.f('ix_provider_feedback_events_source'),
        'provider_feedback_events',
        ['source'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_provider_feedback_events_source'), table_name='provider_feedback_events')
    op.drop_index(
        op.f('ix_provider_feedback_events_received_at'),
        table_name='provider_feedback_events',
    )
    op.drop_index(
        op.f('ix_provider_feedback_events_provider_message_id'),
        table_name='provider_feedback_events',
    )
    op.drop_index(
        op.f('ix_provider_feedback_events_provider'),
        table_name='provider_feedback_events',
    )
    op.drop_index(
        op.f('ix_provider_feedback_events_idempotency_key'),
        table_name='provider_feedback_events',
    )
    op.drop_index(
        op.f('ix_provider_feedback_events_event_name'),
        table_name='provider_feedback_events',
    )
    op.drop_index(op.f('ix_provider_feedback_events_email'), table_name='provider_feedback_events')
    op.drop_table('provider_feedback_events')
