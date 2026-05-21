"""add campaign send jobs

Revision ID: 0003_campaign_send_jobs
Revises: 0002_data_sources_and_audiences
Create Date: 2026-05-21
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = '0003_campaign_send_jobs'
down_revision: str | None = '0002_data_sources_and_audiences'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    send_job_status = postgresql.ENUM(
        'queued',
        'processing',
        'completed',
        'failed',
        name='sendjobstatus',
        create_type=False,
    )
    email_send_status = postgresql.ENUM(
        'queued',
        'sending',
        'sent',
        'failed',
        'suppressed',
        'skipped',
        name='emailsendstatus',
        create_type=False,
    )
    send_job_status.create(op.get_bind(), checkfirst=True)
    email_send_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'campaign_send_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('campaign_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', send_job_status, nullable=False),
        sa.Column('audience_rule_tree', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('requested_count', sa.Integer(), nullable=False),
        sa.Column('queued_count', sa.Integer(), nullable=False),
        sa.Column('suppressed_count', sa.Integer(), nullable=False),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'email_send_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('campaign_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('send_job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('contact_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', email_send_status, nullable=False),
        sa.Column('to_email', sa.String(length=320), nullable=False),
        sa.Column('variables', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('provider', sa.String(length=100), nullable=True),
        sa.Column('provider_message_id', sa.String(length=255), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id']),
        sa.ForeignKeyConstraint(['contact_id'], ['contacts.id']),
        sa.ForeignKeyConstraint(['send_job_id'], ['campaign_send_jobs.id']),
        sa.ForeignKeyConstraint(['template_id'], ['email_templates.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_email_send_records_provider_message_id'),
        'email_send_records',
        ['provider_message_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_email_send_records_status'),
        'email_send_records',
        ['status'],
        unique=False,
    )
    op.create_index(
        op.f('ix_email_send_records_to_email'),
        'email_send_records',
        ['to_email'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_email_send_records_to_email'), table_name='email_send_records')
    op.drop_index(op.f('ix_email_send_records_status'), table_name='email_send_records')
    op.drop_index(
        op.f('ix_email_send_records_provider_message_id'), table_name='email_send_records'
    )
    op.drop_table('email_send_records')
    op.drop_table('campaign_send_jobs')
    postgresql.ENUM(name='emailsendstatus').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='sendjobstatus').drop(op.get_bind(), checkfirst=True)
