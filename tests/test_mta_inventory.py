from types import SimpleNamespace
from uuid import uuid4

import pytest

from email_platform.models.entities import MtaOperationalStatus, MtaProviderAccount
from email_platform.schemas.contracts import (
    MtaIpPoolNodeCreate,
    MtaNodeCreate,
    MtaNodeUpdate,
    MtaProviderAccountCreate,
)
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
