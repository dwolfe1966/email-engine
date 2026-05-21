"""add template css body

Revision ID: 0006_template_css_body
Revises: 0005_event_send_links
Create Date: 2026-05-21
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = '0006_template_css_body'
down_revision: str | None = '0005_event_send_links'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('email_templates', sa.Column('css_body', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('email_templates', 'css_body')
