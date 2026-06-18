"""add managed mta inventory

Revision ID: 0023_mta_inventory
Revises: 0022_smtp_readiness
Create Date: 2026-06-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = '0023_mta_inventory'
down_revision: str | None = '0022_smtp_readiness'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    provider_type = postgresql.ENUM(
        'aws',
        'scaleway',
        'vultr',
        'akamai_linode',
        'hetzner',
        'ovh',
        'leaseweb',
        'hivelocity',
        'buyvm',
        'custom',
        name='mtaprovidertype',
        create_type=False,
    )
    operational_status = postgresql.ENUM(
        'pending',
        'active',
        'paused',
        'draining',
        'failed',
        'retired',
        'suspended',
        name='mtaoperationalstatus',
        create_type=False,
    )
    ip_pool_type = postgresql.ENUM(
        'shared_marketing',
        'shared_transactional',
        'warmup',
        'quarantine',
        'dedicated_customer',
        'internal_test',
        name='mtaippooltype',
        create_type=False,
    )
    provider_type.create(op.get_bind(), checkfirst=True)
    operational_status.create(op.get_bind(), checkfirst=True)
    ip_pool_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'mta_provider_accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('provider', provider_type, nullable=False),
        sa.Column('status', operational_status, nullable=False),
        sa.Column('account_ref', sa.String(length=255), nullable=True),
        sa.Column('region', sa.String(length=100), nullable=True),
        sa.Column('abuse_contact_email', sa.String(length=320), nullable=True),
        sa.Column('support_case_ref', sa.String(length=255), nullable=True),
        sa.Column('port25_status', sa.String(length=40), nullable=False),
        sa.Column('rdns_status', sa.String(length=40), nullable=False),
        sa.Column('secret_ref', sa.String(length=255), nullable=True),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_mta_provider_accounts_name'),
    )
    op.create_index(
        op.f('ix_mta_provider_accounts_account_ref'),
        'mta_provider_accounts',
        ['account_ref'],
    )
    op.create_index(op.f('ix_mta_provider_accounts_name'), 'mta_provider_accounts', ['name'])
    op.create_index(
        op.f('ix_mta_provider_accounts_port25_status'),
        'mta_provider_accounts',
        ['port25_status'],
    )
    op.create_index(
        op.f('ix_mta_provider_accounts_provider'),
        'mta_provider_accounts',
        ['provider'],
    )
    op.create_index(
        op.f('ix_mta_provider_accounts_rdns_status'),
        'mta_provider_accounts',
        ['rdns_status'],
    )
    op.create_index(op.f('ix_mta_provider_accounts_region'), 'mta_provider_accounts', ['region'])
    op.create_index(op.f('ix_mta_provider_accounts_status'), 'mta_provider_accounts', ['status'])

    op.create_table(
        'mta_ip_pools',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('pool_type', ip_pool_type, nullable=False),
        sa.Column('status', operational_status, nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_mta_ip_pools_name'),
    )
    op.create_index(op.f('ix_mta_ip_pools_name'), 'mta_ip_pools', ['name'])
    op.create_index(op.f('ix_mta_ip_pools_pool_type'), 'mta_ip_pools', ['pool_type'])
    op.create_index(op.f('ix_mta_ip_pools_status'), 'mta_ip_pools', ['status'])

    op.create_table(
        'mta_nodes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('provider_account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('hostname', sa.String(length=255), nullable=False),
        sa.Column('public_ipv4', sa.String(length=64), nullable=True),
        sa.Column('status', operational_status, nullable=False),
        sa.Column('submission_host', sa.String(length=255), nullable=True),
        sa.Column('submission_port', sa.Integer(), nullable=False),
        sa.Column('auth_secret_ref', sa.String(length=255), nullable=True),
        sa.Column('last_readiness_at', sa.DateTime(), nullable=True),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['provider_account_id'], ['mta_provider_accounts.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('hostname', name='uq_mta_nodes_hostname'),
    )
    op.create_index(op.f('ix_mta_nodes_hostname'), 'mta_nodes', ['hostname'])
    op.create_index(op.f('ix_mta_nodes_last_readiness_at'), 'mta_nodes', ['last_readiness_at'])
    op.create_index(op.f('ix_mta_nodes_name'), 'mta_nodes', ['name'])
    op.create_index(op.f('ix_mta_nodes_provider_account_id'), 'mta_nodes', ['provider_account_id'])
    op.create_index(op.f('ix_mta_nodes_public_ipv4'), 'mta_nodes', ['public_ipv4'])
    op.create_index(op.f('ix_mta_nodes_status'), 'mta_nodes', ['status'])

    op.create_table(
        'mta_ip_pool_nodes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ip_pool_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('mta_node_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('weight', sa.Integer(), nullable=False),
        sa.Column('status', operational_status, nullable=False),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['ip_pool_id'], ['mta_ip_pools.id']),
        sa.ForeignKeyConstraint(['mta_node_id'], ['mta_nodes.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ip_pool_id', 'mta_node_id', name='uq_mta_ip_pool_nodes_pool_node'),
    )
    op.create_index(op.f('ix_mta_ip_pool_nodes_ip_pool_id'), 'mta_ip_pool_nodes', ['ip_pool_id'])
    op.create_index(op.f('ix_mta_ip_pool_nodes_mta_node_id'), 'mta_ip_pool_nodes', ['mta_node_id'])
    op.create_index(op.f('ix_mta_ip_pool_nodes_priority'), 'mta_ip_pool_nodes', ['priority'])
    op.create_index(op.f('ix_mta_ip_pool_nodes_status'), 'mta_ip_pool_nodes', ['status'])


def downgrade() -> None:
    op.drop_index(op.f('ix_mta_ip_pool_nodes_status'), table_name='mta_ip_pool_nodes')
    op.drop_index(op.f('ix_mta_ip_pool_nodes_priority'), table_name='mta_ip_pool_nodes')
    op.drop_index(op.f('ix_mta_ip_pool_nodes_mta_node_id'), table_name='mta_ip_pool_nodes')
    op.drop_index(op.f('ix_mta_ip_pool_nodes_ip_pool_id'), table_name='mta_ip_pool_nodes')
    op.drop_table('mta_ip_pool_nodes')

    op.drop_index(op.f('ix_mta_nodes_status'), table_name='mta_nodes')
    op.drop_index(op.f('ix_mta_nodes_public_ipv4'), table_name='mta_nodes')
    op.drop_index(op.f('ix_mta_nodes_provider_account_id'), table_name='mta_nodes')
    op.drop_index(op.f('ix_mta_nodes_name'), table_name='mta_nodes')
    op.drop_index(op.f('ix_mta_nodes_last_readiness_at'), table_name='mta_nodes')
    op.drop_index(op.f('ix_mta_nodes_hostname'), table_name='mta_nodes')
    op.drop_table('mta_nodes')

    op.drop_index(op.f('ix_mta_ip_pools_status'), table_name='mta_ip_pools')
    op.drop_index(op.f('ix_mta_ip_pools_pool_type'), table_name='mta_ip_pools')
    op.drop_index(op.f('ix_mta_ip_pools_name'), table_name='mta_ip_pools')
    op.drop_table('mta_ip_pools')

    op.drop_index(op.f('ix_mta_provider_accounts_status'), table_name='mta_provider_accounts')
    op.drop_index(op.f('ix_mta_provider_accounts_region'), table_name='mta_provider_accounts')
    op.drop_index(op.f('ix_mta_provider_accounts_rdns_status'), table_name='mta_provider_accounts')
    op.drop_index(op.f('ix_mta_provider_accounts_provider'), table_name='mta_provider_accounts')
    op.drop_index(
        op.f('ix_mta_provider_accounts_port25_status'),
        table_name='mta_provider_accounts',
    )
    op.drop_index(op.f('ix_mta_provider_accounts_name'), table_name='mta_provider_accounts')
    op.drop_index(op.f('ix_mta_provider_accounts_account_ref'), table_name='mta_provider_accounts')
    op.drop_table('mta_provider_accounts')

    postgresql.ENUM(name='mtaippooltype').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='mtaoperationalstatus').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='mtaprovidertype').drop(op.get_bind(), checkfirst=True)
