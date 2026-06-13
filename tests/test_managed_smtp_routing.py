from datetime import datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

from email_platform.models.entities import (
    DeliveryRouteStatus,
    DeliveryRouteType,
    MtaIpPoolType,
    MtaOperationalStatus,
    MtaProviderType,
)
from email_platform.schemas.contracts import ManagedSmtpRouteResolveRequest
from email_platform.services.managed_smtp_routing import ManagedSmtpRoutingService


class ResolverHarness(ManagedSmtpRoutingService):
    def __init__(self) -> None:
        super().__init__(db=SimpleNamespace())
        self.policy = None
        self.route = None
        self.pool = None
        self.node = None
        self.provider = None

    def _domain_policy(self, domain):
        return self.policy

    def _delivery_route(self, route_id):
        return self.route

    def _selected_pool(self, requested_pool_id, policy, route):
        return self.pool

    def _healthy_node_for_pool(self, pool_id):
        return self.node, self.provider


def _policy(**overrides):
    values = {
        'id': uuid4(),
        'domain': 'example.com',
        'route_id': uuid4(),
        'paused_until': None,
        'metadata_json': {
            'domain_authentication_verification': {'verified': True},
            'domain_authentication': {'bounce_domain': 'bounces.example.com'},
            'dkim_key': {'selector': 'ee1'},
        },
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _route(**overrides):
    values = {
        'id': uuid4(),
        'name': 'managed-smtp-primary',
        'route_type': DeliveryRouteType.managed_smtp,
        'status': DeliveryRouteStatus.active,
        'config': {},
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _pool(**overrides):
    values = {
        'id': uuid4(),
        'name': 'warmup-a',
        'pool_type': MtaIpPoolType.warmup,
        'status': MtaOperationalStatus.active,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _node(**overrides):
    values = {
        'id': uuid4(),
        'name': 'mta-001',
        'hostname': 'mta-001.email-engine.example',
        'public_ipv4': '192.0.2.10',
        'submission_host': None,
        'submission_port': 587,
        'auth_secret_ref': 'secret/mta-001/submission',
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _provider(**overrides):
    values = {
        'id': uuid4(),
        'provider': MtaProviderType.aws,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_resolve_blocks_missing_domain() -> None:
    result = ResolverHarness().resolve(ManagedSmtpRouteResolveRequest())

    assert not result.ok
    assert result.reason is not None
    assert result.reason.code == 'DOMAIN_NOT_READY'


def test_resolve_blocks_unverified_domain_authentication() -> None:
    service = ResolverHarness()
    service.policy = _policy(
        metadata_json={'domain_authentication_verification': {'verified': False}}
    )

    result = service.resolve(ManagedSmtpRouteResolveRequest(from_domain='example.com'))

    assert not result.ok
    assert result.reason is not None
    assert result.reason.code == 'DOMAIN_NOT_READY'


def test_resolve_blocks_active_compliance_hold() -> None:
    service = ResolverHarness()
    service.policy = _policy(
        metadata_json={
            'domain_authentication_verification': {'verified': True},
            'compliance_hold': {'status': 'active', 'reason': 'manual review'},
        }
    )

    result = service.resolve(ManagedSmtpRouteResolveRequest(from_domain='example.com'))

    assert not result.ok
    assert result.reason is not None
    assert result.reason.code == 'COMPLIANCE_HOLD'


def test_resolve_blocks_temporarily_paused_policy() -> None:
    service = ResolverHarness()
    service.policy = _policy(paused_until=datetime.utcnow() + timedelta(hours=1))

    result = service.resolve(ManagedSmtpRouteResolveRequest(from_domain='example.com'))

    assert not result.ok
    assert result.reason is not None
    assert result.reason.code == 'COMPLIANCE_HOLD'
    assert result.reason.details['paused_until']


def test_resolve_blocks_paused_pool() -> None:
    service = ResolverHarness()
    service.policy = _policy()
    service.route = _route()
    service.pool = _pool(status=MtaOperationalStatus.paused)

    result = service.resolve(ManagedSmtpRouteResolveRequest(from_domain='example.com'))

    assert not result.ok
    assert result.reason is not None
    assert result.reason.code == 'POOL_PAUSED'
    assert result.reason.details['ip_pool_status'] == 'paused'


def test_resolve_blocks_when_pool_has_no_healthy_node() -> None:
    service = ResolverHarness()
    service.policy = _policy()
    service.route = _route()
    service.pool = _pool()

    result = service.resolve(ManagedSmtpRouteResolveRequest(from_domain='example.com'))

    assert not result.ok
    assert result.reason is not None
    assert result.reason.code == 'NO_HEALTHY_MTA_NODE'


def test_resolve_returns_selected_submission_route() -> None:
    service = ResolverHarness()
    service.policy = _policy()
    service.route = _route()
    service.pool = _pool()
    service.node = _node()
    service.provider = _provider()

    result = service.resolve(ManagedSmtpRouteResolveRequest(from_domain='sender@example.com'))

    assert result.ok
    assert result.route is not None
    assert result.route.domain == 'example.com'
    assert result.route.delivery_route_name == 'managed-smtp-primary'
    assert result.route.ip_pool_name == 'warmup-a'
    assert result.route.mta_node_name == 'mta-001'
    assert result.route.provider == MtaProviderType.aws
    assert result.route.submission_host == 'mta-001.email-engine.example'
    assert result.route.envelope_sender_domain == 'bounces.example.com'
    assert result.route.dkim_selector == 'ee1'
