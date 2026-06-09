"""add domain delivery policies table

Revision ID: 0018_domain_delivery_policies
Revises: 0017_delivery_routes
Create Date: 2026-06-09
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = '0018_domain_delivery_policies'
down_revision: str | None = '0017_delivery_routes'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'domain_delivery_policies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('domain', sa.String(length=255), nullable=False),
        sa.Column(
            'route_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('delivery_routes.id'),
            nullable=True,
        ),
        sa.Column('max_per_minute', sa.Integer(), nullable=True),
        sa.Column('max_concurrent', sa.Integer(), nullable=True),
        sa.Column('warmup_stage', sa.String(length=100), nullable=True),
        sa.Column('paused_until', sa.DateTime(), nullable=True),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('domain', name='uq_domain_delivery_policies_domain'),
    )
    op.create_index(
        op.f('ix_domain_delivery_policies_domain'),
        'domain_delivery_policies',
        ['domain'],
    )
    op.create_index(
        op.f('ix_domain_delivery_policies_route_id'),
        'domain_delivery_policies',
        ['route_id'],
    )
    op.create_index(
        op.f('ix_domain_delivery_policies_warmup_stage'),
        'domain_delivery_policies',
        ['warmup_stage'],
    )
    op.create_index(
        op.f('ix_domain_delivery_policies_paused_until'),
        'domain_delivery_policies',
        ['paused_until'],
    )


def downgrade() -> None:
    op.drop_index(
        op.f('ix_domain_delivery_policies_paused_until'),
        table_name='domain_delivery_policies',
    )
    op.drop_index(
        op.f('ix_domain_delivery_policies_warmup_stage'),
        table_name='domain_delivery_policies',
    )
    op.drop_index(
        op.f('ix_domain_delivery_policies_route_id'),
        table_name='domain_delivery_policies',
    )
    op.drop_index(
        op.f('ix_domain_delivery_policies_domain'),
        table_name='domain_delivery_policies',
    )
    op.drop_table('domain_delivery_policies')
