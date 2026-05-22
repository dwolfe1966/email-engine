"""add journey execution state

Revision ID: 0009_journey_execution
Revises: 0008_journeys
Create Date: 2026-05-21
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = '0009_journey_execution'
down_revision: str | None = '0008_journeys'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    enrollment_status = postgresql.ENUM(
        'active',
        'completed',
        'exited',
        'paused',
        'failed',
        name='journeyenrollmentstatus',
        create_type=False,
    )
    execution_status = postgresql.ENUM(
        'completed',
        'failed',
        'skipped',
        name='journeystepexecutionstatus',
        create_type=False,
    )
    enrollment_status.create(op.get_bind(), checkfirst=True)
    execution_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'journey_enrollments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('journey_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('contact_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('current_step_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', enrollment_status, nullable=False),
        sa.Column('variables', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('due_at', sa.DateTime(), nullable=True),
        sa.Column('entered_at', sa.DateTime(), nullable=False),
        sa.Column('exited_at', sa.DateTime(), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['contact_id'], ['contacts.id']),
        sa.ForeignKeyConstraint(['current_step_id'], ['journey_steps.id']),
        sa.ForeignKeyConstraint(['journey_id'], ['journeys.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('journey_id', 'contact_id', name='uq_journey_enrollment_contact'),
    )
    op.create_index(
        op.f('ix_journey_enrollments_contact_id'),
        'journey_enrollments',
        ['contact_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_journey_enrollments_current_step_id'),
        'journey_enrollments',
        ['current_step_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_journey_enrollments_due_at'),
        'journey_enrollments',
        ['due_at'],
        unique=False,
    )
    op.create_index(
        op.f('ix_journey_enrollments_journey_id'),
        'journey_enrollments',
        ['journey_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_journey_enrollments_status'),
        'journey_enrollments',
        ['status'],
        unique=False,
    )
    op.create_table(
        'journey_step_executions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('enrollment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('journey_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('step_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('contact_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', execution_status, nullable=False),
        sa.Column('send_record_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('executed_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['contact_id'], ['contacts.id']),
        sa.ForeignKeyConstraint(['enrollment_id'], ['journey_enrollments.id']),
        sa.ForeignKeyConstraint(['journey_id'], ['journeys.id']),
        sa.ForeignKeyConstraint(['send_record_id'], ['email_send_records.id']),
        sa.ForeignKeyConstraint(['step_id'], ['journey_steps.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_journey_step_executions_contact_id'),
        'journey_step_executions',
        ['contact_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_journey_step_executions_enrollment_id'),
        'journey_step_executions',
        ['enrollment_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_journey_step_executions_journey_id'),
        'journey_step_executions',
        ['journey_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_journey_step_executions_status'),
        'journey_step_executions',
        ['status'],
        unique=False,
    )
    op.create_index(
        op.f('ix_journey_step_executions_step_id'),
        'journey_step_executions',
        ['step_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_journey_step_executions_step_id'), table_name='journey_step_executions')
    op.drop_index(op.f('ix_journey_step_executions_status'), table_name='journey_step_executions')
    op.drop_index(
        op.f('ix_journey_step_executions_journey_id'),
        table_name='journey_step_executions',
    )
    op.drop_index(
        op.f('ix_journey_step_executions_enrollment_id'),
        table_name='journey_step_executions',
    )
    op.drop_index(
        op.f('ix_journey_step_executions_contact_id'),
        table_name='journey_step_executions',
    )
    op.drop_table('journey_step_executions')
    op.drop_index(op.f('ix_journey_enrollments_status'), table_name='journey_enrollments')
    op.drop_index(op.f('ix_journey_enrollments_journey_id'), table_name='journey_enrollments')
    op.drop_index(op.f('ix_journey_enrollments_due_at'), table_name='journey_enrollments')
    op.drop_index(op.f('ix_journey_enrollments_current_step_id'), table_name='journey_enrollments')
    op.drop_index(op.f('ix_journey_enrollments_contact_id'), table_name='journey_enrollments')
    op.drop_table('journey_enrollments')
    postgresql.ENUM(name='journeystepexecutionstatus').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='journeyenrollmentstatus').drop(op.get_bind(), checkfirst=True)
