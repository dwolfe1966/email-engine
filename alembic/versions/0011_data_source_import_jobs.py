"""add data source import jobs

Revision ID: 0011_data_source_import_jobs
Revises: 0010_nullable_send_campaigns
Create Date: 2026-05-21
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = '0011_data_source_import_jobs'
down_revision: str | None = '0010_nullable_send_campaigns'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    import_status = postgresql.ENUM(
        'completed',
        'failed',
        'dry_run',
        name='datasourceimportstatus',
        create_type=False,
    )
    import_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        'data_source_import_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('data_source_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('mapping_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', import_status, nullable=False),
        sa.Column('object_type', sa.String(length=100), nullable=False),
        sa.Column('received_count', sa.Integer(), nullable=False),
        sa.Column('imported_count', sa.Integer(), nullable=False),
        sa.Column('created_count', sa.Integer(), nullable=False),
        sa.Column('updated_count', sa.Integer(), nullable=False),
        sa.Column('skipped_count', sa.Integer(), nullable=False),
        sa.Column('errors', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['data_source_id'], ['data_sources.id']),
        sa.ForeignKeyConstraint(['mapping_id'], ['data_source_mappings.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_data_source_import_jobs_data_source_id'),
        'data_source_import_jobs',
        ['data_source_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_data_source_import_jobs_mapping_id'),
        'data_source_import_jobs',
        ['mapping_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_data_source_import_jobs_object_type'),
        'data_source_import_jobs',
        ['object_type'],
        unique=False,
    )
    op.create_index(
        op.f('ix_data_source_import_jobs_status'),
        'data_source_import_jobs',
        ['status'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_data_source_import_jobs_status'), table_name='data_source_import_jobs')
    op.drop_index(
        op.f('ix_data_source_import_jobs_object_type'),
        table_name='data_source_import_jobs',
    )
    op.drop_index(
        op.f('ix_data_source_import_jobs_mapping_id'),
        table_name='data_source_import_jobs',
    )
    op.drop_index(
        op.f('ix_data_source_import_jobs_data_source_id'),
        table_name='data_source_import_jobs',
    )
    op.drop_table('data_source_import_jobs')
    postgresql.ENUM(name='datasourceimportstatus').drop(op.get_bind(), checkfirst=True)
