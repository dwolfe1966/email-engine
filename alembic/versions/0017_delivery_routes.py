"""add delivery routes table

Revision ID: 0017_delivery_routes
Revises: 0016_delivery_attempts
Create Date: 2026-06-09
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = '0017_delivery_routes'
down_revision: str | None = '0016_delivery_attempts'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    route_type = postgresql.ENUM(
        'console',
        'sendgrid',
        'smtp_relay',
        'managed_smtp',
        'ses',
        name='deliveryroutetype',
        create_type=False,
    )
    route_status = postgresql.ENUM(
        'active',
        'paused',
        'disabled',
        name='deliveryroutestatus',
        create_type=False,
    )
    route_type.create(op.get_bind(), checkfirst=True)
    route_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'delivery_routes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('route_type', route_type, nullable=False),
        sa.Column('status', route_status, nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('secret_ref', sa.String(length=255), nullable=True),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('name', name='uq_delivery_routes_name'),
    )
    op.create_index(op.f('ix_delivery_routes_name'), 'delivery_routes', ['name'])
    op.create_index(op.f('ix_delivery_routes_route_type'), 'delivery_routes', ['route_type'])
    op.create_index(op.f('ix_delivery_routes_status'), 'delivery_routes', ['status'])
    op.create_index(op.f('ix_delivery_routes_priority'), 'delivery_routes', ['priority'])


def downgrade() -> None:
    op.drop_index(op.f('ix_delivery_routes_priority'), table_name='delivery_routes')
    op.drop_index(op.f('ix_delivery_routes_status'), table_name='delivery_routes')
    op.drop_index(op.f('ix_delivery_routes_route_type'), table_name='delivery_routes')
    op.drop_index(op.f('ix_delivery_routes_name'), table_name='delivery_routes')
    op.drop_table('delivery_routes')
    postgresql.ENUM(name='deliveryroutestatus').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='deliveryroutetype').drop(op.get_bind(), checkfirst=True)
