from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from email_platform.models.entities import MtaOperationalStatus, MtaProviderAccount
from email_platform.schemas.contracts import (
    ManagedSmtpReadinessSummaryRead,
    MtaIpPoolNodeCreate,
    MtaNodeCreate,
    MtaNodeUpdate,
    MtaProviderAccountCreate,
)
from email_platform.services import mta_inventory as mta_inventory_module
from email_platform.services.mta_inventory import MtaInventoryError, MtaInventoryService


class FakeDb:
    def __init__(self, get_results=None) -> None:
        self.get_results = get_results or {}
        self.added = []
        self.committed = False
        self.refreshed = []

    def add(self, item):
        self.added.append(item)

    def commit(self):
        self.committed = True

    def refresh(self, item):
        self.refreshed.append(item)

    def get(self, model, item_id):
        return self.get_results.get((model, item_id))


def test_create_provider_account_defaults_to_secret_ref_not_raw_credentials() -> None:
    db = FakeDb()
    service = MtaInventoryService(db)

    account = service.create_provider_account(
        MtaProviderAccountCreate(
            name='aws-staging',
            provider='aws',
            account_ref='123456789012',
            region='us-west-2',
            secret_ref='secret/email-engine/mta/aws-staging',
        )
    )

    assert account.name == 'aws-staging'
    assert account.provider == 'aws'
    assert account.secret_ref == 'secret/email-engine/mta/aws-staging'
    assert db.added == [account]
    assert db.committed
    assert db.refreshed == [account]


def test_create_node_requires_existing_provider_account() -> None:
    service = MtaInventoryService(FakeDb())

    with pytest.raises(MtaInventoryError, match='MTA provider account not found'):
        service.create_node(
            MtaNodeCreate(
                provider_account_id=uuid4(),
                name='mta-001',
                hostname='mta-001.email-engine.example',
            )
        )


def test_update_node_validates_reassigned_provider_account() -> None:
    node_id = uuid4()
    node = SimpleNamespace(id=node_id)
    service = MtaInventoryService(FakeDb(get_results={(object, node_id): node}))

    def fake_get_node(item_id):
        return node if item_id == node_id else None

    service.get_node = fake_get_node

    with pytest.raises(MtaInventoryError, match='MTA provider account not found'):
        service.update_node(node_id, MtaNodeUpdate(provider_account_id=uuid4()))


def test_provider_account_pause_and_resume_change_operational_status() -> None:
    account_id = uuid4()
    account = SimpleNamespace(id=account_id, status=MtaOperationalStatus.active)
    db = FakeDb(get_results={(MtaProviderAccount, account_id): account})
    service = MtaInventoryService(db)

    paused = service.set_provider_account_status(account_id, MtaOperationalStatus.paused)
    resumed = service.set_provider_account_status(account_id, MtaOperationalStatus.active)

    assert paused is account
    assert resumed is account
    assert account.status == MtaOperationalStatus.active
    assert db.committed
    assert db.refreshed == [account, account]


def test_create_pool_node_requires_existing_pool_before_node() -> None:
    service = MtaInventoryService(FakeDb())

    with pytest.raises(MtaInventoryError, match='MTA IP pool not found'):
        service.create_pool_node(MtaIpPoolNodeCreate(ip_pool_id=uuid4(), mta_node_id=uuid4()))


def test_deployment_summary_combines_inventory_counts_and_node_readiness(monkeypatch) -> None:
    account_id = uuid4()
    node_id = uuid4()
    pool_node_id = uuid4()
    pool_id = uuid4()
    now = datetime.utcnow()
    account = SimpleNamespace(
        id=account_id,
        name='aws-staging',
        provider='aws',
        status=MtaOperationalStatus.active,
        account_ref='123456789012',
        region='us-west-2',
        abuse_contact_email='abuse@example.com',
        support_case_ref='case-123',
        port25_status='approved',
        rdns_status='configured',
        secret_ref='secret/provider/aws-staging',
        metadata_json={},
        created_at=now,
        updated_at=now,
    )
    node = SimpleNamespace(
        id=node_id,
        provider_account_id=account_id,
        name='mta-001',
        hostname='smtp.example.com',
        public_ipv4='192.0.2.10',
        status=MtaOperationalStatus.active,
        submission_host='smtp.example.com',
        submission_port=587,
        auth_secret_ref='secret/mta-001/submission',
        last_readiness_at=now,
        metadata_json={},
        created_at=now,
        updated_at=now,
    )
    pool_node = SimpleNamespace(
        id=pool_node_id,
        ip_pool_id=pool_id,
        mta_node_id=node_id,
        priority=100,
        weight=100,
        status=MtaOperationalStatus.active,
        metadata_json={},
        created_at=now,
        updated_at=now,
    )

    class FakeReadinessService:
        def __init__(self, db) -> None:
            self.db = db

        def summary(self, **kwargs):
            assert kwargs == {'host': 'smtp.example.com'}
            return ManagedSmtpReadinessSummaryRead(
                total_count=2,
                ok_count=2,
                warning_count=0,
                failed_count=0,
            )

    class FakeSummaryService(MtaInventoryService):
        def list_nodes(self, **kwargs):
            assert kwargs['limit'] == 5
            return [node]

        def get_provider_account(self, item_id):
            return account if item_id == account_id else None

        def list_pool_nodes(self, **kwargs):
            assert kwargs['mta_node_id'] == node_id
            return [pool_node]

        def count_provider_accounts(self, status=None):
            return 1 if status in {None, MtaOperationalStatus.active} else 0

        def count_nodes(self, status=None, provider_account_id=None):
            return 1 if status in {None, MtaOperationalStatus.active} else 0

        def count_ip_pools(self, status=None):
            return 1 if status in {None, MtaOperationalStatus.paused} else 0

        def count_pool_nodes(self, ip_pool_id=None, mta_node_id=None, status=None):
            return 1 if status in {None, MtaOperationalStatus.active} else 0

        def _managed_smtp_route_count(self):
            return 1

        def _managed_smtp_domain_policy_count(self):
            return 1

    monkeypatch.setattr(
        mta_inventory_module,
        'ManagedSmtpReadinessService',
        FakeReadinessService,
    )

    summary = FakeSummaryService(FakeDb()).deployment_summary(
        limit=5,
        settings=SimpleNamespace(
            smtp_username='submission-user',
            smtp_password='submission-password',
            smtp_use_tls=True,
        ),
    )

    assert summary.provider_accounts.total == 1
    assert summary.provider_accounts.active == 1
    assert summary.ip_pools.paused == 1
    assert summary.managed_smtp_route_count == 1
    assert summary.managed_smtp_domain_policy_count == 1
    assert summary.submission_credentials_configured is True
    assert summary.submission_tls_enabled is True
    assert summary.recent_nodes[0].node.hostname == 'smtp.example.com'
    assert summary.recent_nodes[0].provider_account is not None
    assert summary.recent_nodes[0].provider_account.name == 'aws-staging'
    assert summary.recent_nodes[0].pool_memberships[0].id == pool_node_id
    assert summary.recent_nodes[0].readiness_summary.ok_count == 2
