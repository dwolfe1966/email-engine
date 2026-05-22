"""add delivery retry state

Revision ID: 0012_delivery_retry_state
Revises: 0011_data_source_import_jobs
Create Date: 2026-05-21
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = '0012_delivery_retry_state'
down_revision: str | None = '0011_data_source_import_jobs'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'email_send_records',
        sa.Column('attempt_count', sa.Integer(), nullable=False, server_default='0'),
    )
    op.add_column(
        'email_send_records',
        sa.Column('max_attempts', sa.Integer(), nullable=False, server_default='3'),
    )
    op.add_column(
        'email_send_records',
        sa.Column('next_attempt_at', sa.DateTime(), nullable=True),
    )
    op.create_index(
        op.f('ix_email_send_records_next_attempt_at'),
        'email_send_records',
        ['next_attempt_at'],
        unique=False,
    )
    op.alter_column('email_send_records', 'attempt_count', server_default=None)
    op.alter_column('email_send_records', 'max_attempts', server_default=None)


def downgrade() -> None:
    op.drop_index(op.f('ix_email_send_records_next_attempt_at'), table_name='email_send_records')
    op.drop_column('email_send_records', 'next_attempt_at')
    op.drop_column('email_send_records', 'max_attempts')
    op.drop_column('email_send_records', 'attempt_count')
