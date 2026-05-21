"""add data sources and audiences

Revision ID: 0002_data_sources_and_audiences
Revises: 0001_initial_schema
Create Date: 2026-05-21
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = '0002_data_sources_and_audiences'
down_revision: str | None = '0001_initial_schema'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    data_source_type = postgresql.ENUM(
        'postgres',
        'mysql',
        'snowflake',
        'bigquery',
        'rest_api',
        'csv',
        'manual',
        name='datasourcetype',
        create_type=False,
    )
    data_source_status = postgresql.ENUM(
        'draft',
        'active',
        'paused',
        name='datasourcestatus',
        create_type=False,
    )
    audience_status = postgresql.ENUM(
        'draft',
        'active',
        'archived',
        name='audiencestatus',
        create_type=False,
    )
    data_source_type.create(op.get_bind(), checkfirst=True)
    data_source_status.create(op.get_bind(), checkfirst=True)
    audience_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'data_sources',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('source_type', data_source_type, nullable=False),
        sa.Column('status', data_source_status, nullable=False),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('secret_ref', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_data_sources_name'), 'data_sources', ['name'], unique=True)
    op.create_index(
        op.f('ix_data_sources_source_type'), 'data_sources', ['source_type'], unique=False
    )

    op.create_table(
        'audiences',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', audience_status, nullable=False),
        sa.Column('rule_tree', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('estimated_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_audiences_name'), 'audiences', ['name'], unique=True)

    op.create_table(
        'data_source_mappings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('data_source_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('object_type', sa.String(length=100), nullable=False),
        sa.Column('mapping', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('extraction_plan', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['data_source_id'], ['data_sources.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_data_source_mappings_name'),
        'data_source_mappings',
        ['name'],
        unique=False,
    )
    op.create_index(
        op.f('ix_data_source_mappings_object_type'),
        'data_source_mappings',
        ['object_type'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_data_source_mappings_object_type'), table_name='data_source_mappings')
    op.drop_index(op.f('ix_data_source_mappings_name'), table_name='data_source_mappings')
    op.drop_table('data_source_mappings')
    op.drop_index(op.f('ix_audiences_name'), table_name='audiences')
    op.drop_table('audiences')
    op.drop_index(op.f('ix_data_sources_source_type'), table_name='data_sources')
    op.drop_index(op.f('ix_data_sources_name'), table_name='data_sources')
    op.drop_table('data_sources')
    postgresql.ENUM(name='audiencestatus').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='datasourcestatus').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='datasourcetype').drop(op.get_bind(), checkfirst=True)
