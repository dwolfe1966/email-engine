from datetime import datetime
from uuid import uuid4

from email_platform.models.entities import (
    DeliveryRoute,
    DomainDeliveryPolicy,
    MtaIpPool,
    MtaIpPoolNode,
    MtaNode,
    MtaOperationalStatus,
    MtaProviderAccount,
)
from email_platform.schemas.contracts import (
    ManagedSmtpBootstrapRequest,
    ManagedSmtpRouteBlockReason,
    ManagedSmtpRouteResolutionRead,
)
from email_platform.services import managed_smtp_bootstrap as bootstrap_module
from email_platform.services.managed_smtp_bootstrap import ManagedSmtpBootstrapService


class FakeScalarResult:
    def __init__(self, items=None) -> None:
        self.items = items or []

    def all(self):
        return self.items


class FakeDb:
    def __init__(self, scalar_results=None) -> None:
        self.scalar_results = list(scalar_results or [])
        self.added = []
        self.commit_count = 0
        self.refreshed = []

    def scalar(self, statement):
        if self.scalar_results:
            return self.scalar_results.pop(0)
        return None

    def scalars(self, statement):
        return FakeScalarResult([])

    def get(self, model, item_id):
        return None

    def add(self, item):
        self.added.append(item)

    def flush(self):
        for item in self.added:
            self._hydrate(item)

    def commit(self):
        self.commit_count += 1

    def refresh(self, item):
        self._hydrate(item)
        self.refreshed.append(item)

    def _hydrate(self, item):
        if getattr(item, 'id', None) is None:
            item.id = uuid4()
        if hasattr(item, 'provider_account') and getattr(item, 'provider_account', None):
            item.provider_account_id = item.provider_account.id
        if hasattr(item, 'ip_pool') and getattr(item, 'ip_pool', None):
            item.ip_pool_id = item.ip_pool.id
        if hasattr(item, 'mta_node') and getattr(item, 'mta_node', None):
            item.mta_node_id = item.mta_node.id
        if hasattr(item, 'route') and getattr(item, 'route', None):
            item.route_id = item.route.id
        now = datetime.utcnow()
        if hasattr(item, 'created_at') and getattr(item, 'created_at', None) is None:
            item.created_at = now
        if hasattr(item, 'updated_at') and getattr(item, 'updated_at', None) is None:
            item.updated_at = now


class FakeResolver:
    def __init__(self, db):
        self.db = db

    def resolve(self, payload):
        return ManagedSmtpRouteResolutionRead(
            ok=False,
            reason=ManagedSmtpRouteBlockReason(
                code='DOMAIN_NOT_READY',
                message='Domain authentication has not been verified.',
                details={'domain': payload.from_domain},
            ),
        )


def test_managed_smtp_bootstrap_creates_conservative_first_node(monkeypatch) -> None:
    monkeypatch.setattr(bootstrap_module, 'ManagedSmtpRoutingService', FakeResolver)
    db = FakeDb()
    payload = ManagedSmtpBootstrapRequest(
        provider_account_name='aws-staging',
        provider='aws',
        region='us-west-2',
        node_name='mta-001',
        hostname='mta-001.email-engine.example',
        public_ipv4='192.0.2.10',
        auth_secret_ref='secret/mta-001/submission',
        ip_pool_name='warmup-a',
        route_name='managed-smtp-primary',
        domain='Example.com',
        dkim_selector='ee1',
        dkim_key_ref='vault://dkim/example/ee1',
    )

    result = ManagedSmtpBootstrapService(db).bootstrap(payload)

    assert db.commit_count == 1
    assert [type(item) for item in db.added] == [
        MtaProviderAccount,
        MtaNode,
        MtaIpPool,
        MtaIpPoolNode,
        DeliveryRoute,
        DomainDeliveryPolicy,
    ]
    assert result.provider_account.name == 'aws-staging'
    assert result.provider_account.status == MtaOperationalStatus.pending
    assert result.node.hostname == 'mta-001.email-engine.example'
    assert result.node.status == MtaOperationalStatus.pending
    assert result.ip_pool.name == 'warmup-a'
    assert result.ip_pool.status == MtaOperationalStatus.paused
    assert result.pool_node.status == MtaOperationalStatus.paused
    assert result.delivery_route.route_type == 'managed_smtp'
    assert result.domain_policy.domain == 'example.com'
    assert result.domain_policy.route_id == result.delivery_route.id
    assert result.domain_policy.metadata_json['mta_ip_pool_id'] == str(result.ip_pool.id)
    assert result.domain_policy.metadata_json['domain_authentication']['bounce_domain'] == (
        'bounces.example.com'
    )
    assert result.domain_policy.metadata_json['dkim_key']['selector'] == 'ee1'
    assert not result.route_resolution.ok
    assert 'Publish and verify SPF' in ' '.join(result.next_steps)
    assert 'Activate provider account' in ' '.join(result.next_steps)


def test_managed_smtp_bootstrap_can_activate_inventory_and_verify_domain(
    monkeypatch,
) -> None:
    monkeypatch.setattr(bootstrap_module, 'ManagedSmtpRoutingService', FakeResolver)
    db = FakeDb()
    payload = ManagedSmtpBootstrapRequest(
        provider_account_name='aws-staging',
        provider='aws',
        port25_status='approved',
        rdns_status='configured',
        node_name='mta-001',
        hostname='mta-001.email-engine.example',
        ip_pool_name='warmup-a',
        domain='example.com',
        activate_inventory=True,
        mark_domain_verified=True,
    )

    result = ManagedSmtpBootstrapService(db).bootstrap(payload)

    assert result.provider_account.status == MtaOperationalStatus.active
    assert result.node.status == MtaOperationalStatus.active
    assert result.ip_pool.status == MtaOperationalStatus.active
    assert result.pool_node.status == MtaOperationalStatus.active
    assert result.domain_policy.metadata_json['domain_authentication_verification']['verified']
    assert 'Verify provider outbound TCP port 25 approval.' not in result.next_steps
