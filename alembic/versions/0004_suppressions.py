"""add suppressions

Revision ID: 0004_suppressions
Revises: 0003_campaign_send_jobs
Create Date: 2026-05-21
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = '0004_suppressions'
down_revision: str | None = '0003_campaign_send_jobs'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    suppression_reason = postgresql.ENUM(
        'hard_bounce',
        'spam_complaint',
        'unsubscribe',
        'manual',
        name='suppressionreason',
        create_type=False,
    )
    suppression_reason.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'suppressions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(length=320), nullable=False),
        sa.Column('contact_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('reason', suppression_reason, nullable=False),
        sa.Column('source', sa.String(length=100), nullable=False),
        sa.Column('provider_message_id', sa.String(length=255), nullable=True),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['contact_id'], ['contacts.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email', 'reason', name='uq_suppressions_email_reason'),
    )
    op.create_index(op.f('ix_suppressions_email'), 'suppressions', ['email'], unique=False)
    op.create_index(
        op.f('ix_suppressions_provider_message_id'),
        'suppressions',
        ['provider_message_id'],
        unique=False,
    )
    op.create_index(op.f('ix_suppressions_reason'), 'suppressions', ['reason'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_suppressions_reason'), table_name='suppressions')
    op.drop_index(op.f('ix_suppressions_provider_message_id'), table_name='suppressions')
    op.drop_index(op.f('ix_suppressions_email'), table_name='suppressions')
    op.drop_table('suppressions')
    postgresql.ENUM(name='suppressionreason').drop(op.get_bind(), checkfirst=True)
