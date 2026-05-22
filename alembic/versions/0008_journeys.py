"""add journeys

Revision ID: 0008_journeys
Revises: 0007_template_versions
Create Date: 2026-05-21
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = '0008_journeys'
down_revision: str | None = '0007_template_versions'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    journey_status = postgresql.ENUM(
        'draft',
        'active',
        'paused',
        'archived',
        name='journeystatus',
        create_type=False,
    )
    journey_step_type = postgresql.ENUM(
        'send_email',
        'wait',
        'branch',
        'update_contact',
        'webhook',
        name='journeysteptype',
        create_type=False,
    )
    journey_status.create(op.get_bind(), checkfirst=True)
    journey_step_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'journeys',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', journey_status, nullable=False),
        sa.Column('entry_rule_tree', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('exit_rule_tree', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )
    op.create_index(op.f('ix_journeys_name'), 'journeys', ['name'], unique=True)
    op.create_table(
        'journey_steps',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('journey_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('step_type', journey_step_type, nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['journey_id'], ['journeys.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_journey_steps_journey_id'),
        'journey_steps',
        ['journey_id'],
        unique=False,
    )
    op.create_index(op.f('ix_journey_steps_name'), 'journey_steps', ['name'], unique=False)
    op.create_index(
        op.f('ix_journey_steps_step_type'),
        'journey_steps',
        ['step_type'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_journey_steps_step_type'), table_name='journey_steps')
    op.drop_index(op.f('ix_journey_steps_name'), table_name='journey_steps')
    op.drop_index(op.f('ix_journey_steps_journey_id'), table_name='journey_steps')
    op.drop_table('journey_steps')
    op.drop_index(op.f('ix_journeys_name'), table_name='journeys')
    op.drop_table('journeys')
    postgresql.ENUM(name='journeysteptype').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='journeystatus').drop(op.get_bind(), checkfirst=True)
