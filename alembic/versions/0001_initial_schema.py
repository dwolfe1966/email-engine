"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-20
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '0001_initial_schema'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    campaign_status = postgresql.ENUM('draft', 'scheduled', 'sending', 'sent', 'paused', name='campaignstatus')
    event_type = postgresql.ENUM('queued', 'sent', 'delivered', 'opened', 'clicked', 'bounced', 'complained', 'unsubscribed', name='emaileventtype')
    campaign_status.create(op.get_bind(), checkfirst=True)
    event_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'contacts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(length=320), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=True),
        sa.Column('last_name', sa.String(length=100), nullable=True),
        sa.Column('source', sa.String(length=100), nullable=True),
        sa.Column('attributes', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('is_unsubscribed', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email', name='uq_contacts_email'),
    )
    op.create_index(op.f('ix_contacts_email'), 'contacts', ['email'], unique=False)

    op.create_table(
        'email_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('subject', sa.String(length=300), nullable=False),
        sa.Column('html_body', sa.Text(), nullable=False),
        sa.Column('text_body', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_email_templates_name'), 'email_templates', ['name'], unique=True)

    op.create_table(
        'campaigns',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('status', campaign_status, nullable=False),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('audience_query', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['template_id'], ['email_templates.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_campaigns_name'), 'campaigns', ['name'], unique=False)

    op.create_table(
        'email_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('contact_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('campaign_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('event_type', event_type, nullable=False),
        sa.Column('provider_message_id', sa.String(length=255), nullable=True),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('occurred_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id']),
        sa.ForeignKeyConstraint(['contact_id'], ['contacts.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_email_events_event_type'), 'email_events', ['event_type'], unique=False)
    op.create_index(op.f('ix_email_events_provider_message_id'), 'email_events', ['provider_message_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_email_events_provider_message_id'), table_name='email_events')
    op.drop_index(op.f('ix_email_events_event_type'), table_name='email_events')
    op.drop_table('email_events')
    op.drop_index(op.f('ix_campaigns_name'), table_name='campaigns')
    op.drop_table('campaigns')
    op.drop_index(op.f('ix_email_templates_name'), table_name='email_templates')
    op.drop_table('email_templates')
    op.drop_index(op.f('ix_contacts_email'), table_name='contacts')
    op.drop_table('contacts')
    postgresql.ENUM(name='emaileventtype').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='campaignstatus').drop(op.get_bind(), checkfirst=True)
