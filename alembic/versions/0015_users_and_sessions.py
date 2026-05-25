"""add users and user_sessions tables

Revision ID: 0015_users_and_sessions
Revises: 0014_campaign_scheduling
Create Date: 2026-05-25

App-level auth for the operator GUI. Mirrors the contract used by the
SentientMail React UI: login POSTs email+password, server sets an
httpOnly cookie carrying a 32-byte random token, sha256(token) is
indexed in user_sessions for the hot-path lookup.

Single-tenant scaffold — tenant_id / RBAC layer is the P0 follow-up in
PRODUCT_BACKLOG.md.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = '0015_users_and_sessions'
down_revision: str | None = '0014_campaign_scheduling'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column('email', sa.String(length=320), nullable=False, unique=True),
        sa.Column('display_name', sa.String(length=200), nullable=False),
        sa.Column('role', sa.String(length=40), nullable=False, server_default='admin'),
        sa.Column('password_hash', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('last_login_at', sa.DateTime(), nullable=True),
        sa.Column('failed_login_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('locked_until', sa.DateTime(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    op.create_table(
        'user_sessions',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            'user_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('users.id'),
            nullable=False,
        ),
        sa.Column('token_hash', sa.String(length=64), nullable=False, unique=True),
        sa.Column(
            'created_at',
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column(
            'last_seen_at',
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column('ip', sa.String(length=64), nullable=True),
        sa.Column('user_agent', sa.String(length=255), nullable=True),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
    )
    op.create_index(op.f('ix_user_sessions_user_id'), 'user_sessions', ['user_id'])
    op.create_index(
        op.f('ix_user_sessions_token_hash'),
        'user_sessions',
        ['token_hash'],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_user_sessions_token_hash'), table_name='user_sessions')
    op.drop_index(op.f('ix_user_sessions_user_id'), table_name='user_sessions')
    op.drop_table('user_sessions')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
