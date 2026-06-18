"""add scaleway mta provider

Revision ID: 0024_scaleway_mta_provider
Revises: 0023_mta_inventory
Create Date: 2026-06-18
"""

from collections.abc import Sequence

from alembic import op

revision: str = '0024_scaleway_mta_provider'
down_revision: str | None = '0023_mta_inventory'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE mtaprovidertype ADD VALUE IF NOT EXISTS 'scaleway'")


def downgrade() -> None:
    # PostgreSQL cannot drop enum values without recreating the enum type.
    # Leave the value in place on downgrade; no rows are created by this migration.
    pass
