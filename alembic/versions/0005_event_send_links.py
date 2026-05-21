"""add event send links

Revision ID: 0005_event_send_links
Revises: 0004_suppressions
Create Date: 2026-05-21
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = '0005_event_send_links'
down_revision: str | None = '0004_suppressions'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'email_events',
        sa.Column('send_record_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        'email_events',
        sa.Column('send_job_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        'fk_email_events_send_record_id_email_send_records',
        'email_events',
        'email_send_records',
        ['send_record_id'],
        ['id'],
    )
    op.create_foreign_key(
        'fk_email_events_send_job_id_campaign_send_jobs',
        'email_events',
        'campaign_send_jobs',
        ['send_job_id'],
        ['id'],
    )
    op.create_index(
        op.f('ix_email_events_send_record_id'),
        'email_events',
        ['send_record_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_email_events_send_job_id'),
        'email_events',
        ['send_job_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_email_events_send_job_id'), table_name='email_events')
    op.drop_index(op.f('ix_email_events_send_record_id'), table_name='email_events')
    op.drop_constraint(
        'fk_email_events_send_job_id_campaign_send_jobs',
        'email_events',
        type_='foreignkey',
    )
    op.drop_constraint(
        'fk_email_events_send_record_id_email_send_records',
        'email_events',
        type_='foreignkey',
    )
    op.drop_column('email_events', 'send_job_id')
    op.drop_column('email_events', 'send_record_id')
