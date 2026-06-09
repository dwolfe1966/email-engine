"""add delivery attempts table

Revision ID: 0016_delivery_attempts
Revises: 0015_users_and_sessions
Create Date: 2026-06-09
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = '0016_delivery_attempts'
down_revision: str | None = '0015_users_and_sessions'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'delivery_attempts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'send_record_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('email_send_records.id'),
            nullable=False,
        ),
        sa.Column(
            'send_job_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('campaign_send_jobs.id'),
            nullable=True,
        ),
        sa.Column(
            'campaign_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('campaigns.id'),
            nullable=True,
        ),
        sa.Column('attempt_number', sa.Integer(), nullable=False),
        sa.Column('provider', sa.String(length=100), nullable=True),
        sa.Column('route_type', sa.String(length=100), nullable=True),
        sa.Column('route_key', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=40), nullable=False),
        sa.Column('provider_message_id', sa.String(length=255), nullable=True),
        sa.Column('smtp_response_code', sa.Integer(), nullable=True),
        sa.Column('smtp_response', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
    )
    op.create_index(
        op.f('ix_delivery_attempts_send_record_id'),
        'delivery_attempts',
        ['send_record_id'],
    )
    op.create_index(op.f('ix_delivery_attempts_send_job_id'), 'delivery_attempts', ['send_job_id'])
    op.create_index(op.f('ix_delivery_attempts_campaign_id'), 'delivery_attempts', ['campaign_id'])
    op.create_index(op.f('ix_delivery_attempts_provider'), 'delivery_attempts', ['provider'])
    op.create_index(op.f('ix_delivery_attempts_route_type'), 'delivery_attempts', ['route_type'])
    op.create_index(op.f('ix_delivery_attempts_route_key'), 'delivery_attempts', ['route_key'])
    op.create_index(op.f('ix_delivery_attempts_status'), 'delivery_attempts', ['status'])
    op.create_index(
        op.f('ix_delivery_attempts_provider_message_id'),
        'delivery_attempts',
        ['provider_message_id'],
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_delivery_attempts_provider_message_id'), table_name='delivery_attempts')
    op.drop_index(op.f('ix_delivery_attempts_status'), table_name='delivery_attempts')
    op.drop_index(op.f('ix_delivery_attempts_route_key'), table_name='delivery_attempts')
    op.drop_index(op.f('ix_delivery_attempts_route_type'), table_name='delivery_attempts')
    op.drop_index(op.f('ix_delivery_attempts_provider'), table_name='delivery_attempts')
    op.drop_index(op.f('ix_delivery_attempts_campaign_id'), table_name='delivery_attempts')
    op.drop_index(op.f('ix_delivery_attempts_send_job_id'), table_name='delivery_attempts')
    op.drop_index(op.f('ix_delivery_attempts_send_record_id'), table_name='delivery_attempts')
    op.drop_table('delivery_attempts')
