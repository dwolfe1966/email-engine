"""add template versions

Revision ID: 0007_template_versions
Revises: 0006_template_css_body
Create Date: 2026-05-21
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = '0007_template_versions'
down_revision: str | None = '0006_template_css_body'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'email_template_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('subject', sa.String(length=300), nullable=False),
        sa.Column('html_body', sa.Text(), nullable=False),
        sa.Column('css_body', sa.Text(), nullable=True),
        sa.Column('text_body', sa.Text(), nullable=True),
        sa.Column('document_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('is_current', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['template_id'], ['email_templates.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('template_id', 'version_number', name='uq_template_versions_number'),
    )
    op.create_index(
        op.f('ix_email_template_versions_is_current'),
        'email_template_versions',
        ['is_current'],
        unique=False,
    )
    op.create_index(
        op.f('ix_email_template_versions_template_id'),
        'email_template_versions',
        ['template_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f('ix_email_template_versions_template_id'),
        table_name='email_template_versions',
    )
    op.drop_index(
        op.f('ix_email_template_versions_is_current'),
        table_name='email_template_versions',
    )
    op.drop_table('email_template_versions')
