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
from email_platform.services.managed_smtp_routing import (
    ManagedSmtpRoutingService,
    MtaNodeSelection,
    MtaPoolSelection,
)


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

    def _selected_pool(
        self,
        requested_pool_id,
        policy,
        route,
        sender_domain=None,
        recipient_domain=None,
        send_type=None,
    ):
        return MtaPoolSelection(self.pool, 'domain_policy')

    def _healthy_node_for_pool(self, pool_id, preferred_providers=None):
        return MtaNodeSelection(
            node=self.node,
            provider=self.provider,
            membership=SimpleNamespace(id=uuid4(), priority=100, weight=100) if self.node else None,
            candidate_count=1 if self.node else 0,
            skipped=[],
            available_count=1 if self.node else 0,
        )


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
        'metadata_json': {},
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _node(**overrides):
    values = {
        'id': uuid4(),
        'provider_account_id': uuid4(),
        'name': 'mta-001',
        'hostname': 'mta-001.email-engine.example',
        'public_ipv4': '192.0.2.10',
        'submission_host': None,
        'submission_port': 587,
        'auth_secret_ref': 'secret/mta-001/submission',
        'status': MtaOperationalStatus.active,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _provider(**overrides):
    values = {
        'id': uuid4(),
        'provider': MtaProviderType.aws,
        'status': MtaOperationalStatus.active,
        'port25_status': 'approved',
        'rdns_status': 'configured',
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _membership(**overrides):
    values = {
        'id': uuid4(),
        'ip_pool_id': uuid4(),
        'mta_node_id': uuid4(),
        'priority': 100,
        'weight': 100,
        'created_at': datetime.utcnow(),
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
    assert result.reason.details['candidate_count'] == 0


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
    assert result.route.send_type == 'internal_test'
    assert result.route.sender_domain == 'example.com'
    assert result.route.recipient_domain is None
    assert result.route.decision_basis == 'sender_domain_policy'
    assert result.route.delivery_route_name == 'managed-smtp-primary'
    assert result.route.ip_pool_name == 'warmup-a'
    assert result.route.ip_pool_selection_source == 'domain_policy'
    assert result.route.mta_node_name == 'mta-001'
    assert result.route.mta_node_selection_membership_id is not None
    assert result.route.mta_node_candidate_count == 1
    assert result.route.mta_pool_available_node_count == 1
    assert result.route.mta_pool_required_available_node_count is None
    assert result.route.mta_pool_capacity_status == 'ok'
    assert result.route.mta_node_selection_priority == 100
    assert result.route.mta_node_selection_weight == 100
    assert result.route.mta_node_skipped_nodes == []
    assert result.route.provider == MtaProviderType.aws
    assert result.route.submission_host == 'mta-001.email-engine.example'
    assert result.route.envelope_sender_domain == 'bounces.example.com'
    assert result.route.dkim_selector == 'ee1'
    assert result.route.telemetry_tags['selection']['candidate_count'] == 1
    assert result.route.telemetry_tags['selection']['priority'] == 100


def test_resolve_can_fall_back_to_recipient_domain_policy() -> None:
    service = ResolverHarness()
    service.policy = _policy()
    service.route = _route()
    service.pool = _pool()
    service.node = _node()
    service.provider = _provider()

    result = service.resolve(ManagedSmtpRouteResolveRequest(recipient_domain='recipient@example.com'))

    assert result.ok
    assert result.route is not None
    assert result.route.domain == 'example.com'
    assert result.route.sender_domain is None
    assert result.route.recipient_domain == 'example.com'
    assert result.route.decision_basis == 'recipient_domain_policy'


def test_resolve_blocks_when_pool_available_capacity_is_below_required_minimum() -> None:
    service = ResolverHarness()
    service.policy = _policy()
    service.route = _route()
    service.pool = _pool(metadata_json={'min_available_nodes': 2})
    service.node = _node()
    service.provider = _provider()

    result = service.resolve(ManagedSmtpRouteResolveRequest(from_domain='sender@example.com'))

    assert not result.ok
    assert result.reason is not None
    assert result.reason.code == 'POOL_CAPACITY_EXHAUSTED'
    assert result.reason.details['available_node_count'] == 1
    assert result.reason.details['required_available_node_count'] == 2


def test_resolve_blocks_when_pool_rate_limit_is_exhausted() -> None:
    service = ResolverHarness()
    pool_id = uuid4()
    service.policy = _policy()
    service.route = _route()
    service.pool = _pool(id=pool_id, metadata_json={'max_per_minute': 1})
    service.node = _node()
    service.provider = _provider()
    service._recent_managed_smtp_attempt_count = lambda key, value: 1

    result = service.resolve(ManagedSmtpRouteResolveRequest(from_domain='sender@example.com'))

    assert not result.ok
    assert result.reason is not None
    assert result.reason.code == 'POOL_RATE_LIMITED'
    assert result.reason.details['rate_limit_scope'] == 'ip_pool'
    assert result.reason.details['rate_limit_max_per_minute'] == 1
    assert result.reason.details['rate_limit_recent_count'] == 1


def test_resolve_blocks_when_pool_node_rate_limit_is_exhausted() -> None:
    service = ResolverHarness()
    service.policy = _policy()
    service.route = _route()
    service.pool = _pool()
    service.node = _node()
    service.provider = _provider()
    service._healthy_node_for_pool = lambda pool_id, preferred_providers=None: MtaNodeSelection(
        node=service.node,
        provider=service.provider,
        membership=SimpleNamespace(id=uuid4(), priority=100, weight=100, metadata_json={'max_per_minute': 1}),
        candidate_count=1,
        skipped=[],
        available_count=1,
    )
    service._recent_managed_smtp_attempt_count = lambda key, value: 1

    result = service.resolve(ManagedSmtpRouteResolveRequest(from_domain='sender@example.com'))

    assert not result.ok
    assert result.reason is not None
    assert result.reason.code == 'POOL_RATE_LIMITED'
    assert result.reason.details['rate_limit_scope'] == 'pool_node'
    assert result.reason.details['rate_limit_max_per_minute'] == 1
    assert result.reason.details['rate_limit_recent_count'] == 1


def test_route_config_rule_selects_pool_and_provider_preference() -> None:
    selected_pool_id = uuid4()
    route = _route(
        config={
            'routing_rules': [
                {
                    'name': 'transactional-scaleway',
                    'priority': 10,
                    'send_types': ['transactional'],
                    'sender_domains': ['example.com'],
                    'recipient_domains': ['gmail.com'],
                    'mta_ip_pool_id': str(selected_pool_id),
                    'preferred_providers': ['scaleway'],
                }
            ]
        }
    )
    pool = _pool(id=selected_pool_id, name='scaleway-transactional')
    node = _node(name='mta-002', hostname='mta-002.email-engine.example')
    provider = _provider(provider=MtaProviderType.scaleway)
    membership_id = uuid4()
    skipped = [
        {
            'membership_id': str(uuid4()),
            'mta_node_id': str(uuid4()),
            'provider': 'aws',
            'reason': 'provider_not_preferred',
        }
    ]

    class FakeDb:
        def get(self, model, item_id):
            return pool if item_id == selected_pool_id else None

    service = ManagedSmtpRoutingService(FakeDb())

    selection = service._selected_pool(
        None,
        _policy(),
        route,
        sender_domain='example.com',
        recipient_domain='gmail.com',
        send_type='transactional',
    )

    assert selection.pool is pool
    assert selection.source == 'delivery_route_rule'
    assert selection.rule_name == 'transactional-scaleway'
    assert selection.preferred_providers == ['scaleway']

    class RuleHarness(ManagedSmtpRoutingService):
        def _domain_policy(self, domain):
            return _policy()

        def _delivery_route(self, route_id):
            return route

        def _healthy_node_for_pool(self, pool_id, preferred_providers=None):
            return MtaNodeSelection(
                node=node,
                provider=provider,
                membership=SimpleNamespace(id=membership_id, priority=100, weight=100),
                candidate_count=2,
                skipped=skipped,
                available_count=1,
            )

    resolved = RuleHarness(FakeDb()).resolve(
        ManagedSmtpRouteResolveRequest(
            from_domain='example.com',
            recipient_domain='gmail.com',
            send_type='transactional',
        )
    )

    assert resolved.ok
    assert resolved.route is not None
    assert resolved.route.routing_rule_name == 'transactional-scaleway'
    assert resolved.route.preferred_providers == ['scaleway']
    assert resolved.route.routing_rule_provider_preference == ['scaleway']
    assert resolved.route.ip_pool_selection_source == 'delivery_route_rule'
    assert resolved.route.routing_rule_pool_source == 'delivery_route_rule'
    assert resolved.route.send_type == 'transactional'
    assert resolved.route.sender_domain == 'example.com'
    assert resolved.route.recipient_domain == 'gmail.com'
    assert resolved.route.mta_node_selection_membership_id == membership_id
    assert resolved.route.mta_node_candidate_count == 2
    assert resolved.route.mta_pool_available_node_count == 1
    assert resolved.route.mta_node_skipped_count == 1
    assert resolved.route.mta_node_skipped_nodes == skipped


def test_healthy_node_selection_skips_non_preferred_provider() -> None:
    pool_id = uuid4()
    first_node_id = uuid4()
    second_node_id = uuid4()
    first_provider_id = uuid4()
    second_provider_id = uuid4()
    first_membership = _membership(
        ip_pool_id=pool_id,
        mta_node_id=first_node_id,
        priority=10,
    )
    second_membership = _membership(
        ip_pool_id=pool_id,
        mta_node_id=second_node_id,
        priority=20,
    )
    first_node = _node(id=first_node_id, provider_account_id=first_provider_id)
    second_node = _node(
        id=second_node_id,
        provider_account_id=second_provider_id,
        name='mta-002',
    )
    first_provider = _provider(id=first_provider_id, provider=MtaProviderType.aws)
    second_provider = _provider(id=second_provider_id, provider=MtaProviderType.scaleway)

    class ScalarResult:
        def all(self):
            return [first_membership, second_membership]

    class FakeDb:
        def scalars(self, statement):
            return ScalarResult()

        def get(self, model, item_id):
            values = {
                first_node_id: first_node,
                second_node_id: second_node,
                first_provider_id: first_provider,
                second_provider_id: second_provider,
            }
            return values.get(item_id)

    service = ManagedSmtpRoutingService(FakeDb())
    service._latest_readiness_ok = lambda node: True

    selection = service._healthy_node_for_pool(pool_id, preferred_providers=['scaleway'])

    assert selection.node is second_node
    assert selection.provider is second_provider
    assert selection.skipped[0]['reason'] == 'provider_not_preferred'


def test_healthy_node_selection_skips_provider_without_port25_approval() -> None:
    pool_id = uuid4()
    node_id = uuid4()
    provider_id = uuid4()
    membership = _membership(ip_pool_id=pool_id, mta_node_id=node_id)
    node = _node(id=node_id, provider_account_id=provider_id)
    provider = _provider(id=provider_id, port25_status='pending')

    class ScalarResult:
        def all(self):
            return [membership]

    class FakeDb:
        def scalars(self, statement):
            return ScalarResult()

        def get(self, model, item_id):
            return {node_id: node, provider_id: provider}.get(item_id)

    service = ManagedSmtpRoutingService(FakeDb())
    service._latest_readiness_ok = lambda node: True

    selection = service._healthy_node_for_pool(pool_id)

    assert selection.node is None
    assert selection.available_count == 0
    assert selection.skipped[0]['reason'] == 'provider_port25_not_ready'
    assert selection.skipped[0]['provider_port25_status'] == 'pending'


def test_healthy_node_selection_skips_provider_without_rdns() -> None:
    pool_id = uuid4()
    node_id = uuid4()
    provider_id = uuid4()
    membership = _membership(ip_pool_id=pool_id, mta_node_id=node_id)
    node = _node(id=node_id, provider_account_id=provider_id)
    provider = _provider(id=provider_id, rdns_status='pending')

    class ScalarResult:
        def all(self):
            return [membership]

    class FakeDb:
        def scalars(self, statement):
            return ScalarResult()

        def get(self, model, item_id):
            return {node_id: node, provider_id: provider}.get(item_id)

    service = ManagedSmtpRoutingService(FakeDb())
    service._latest_readiness_ok = lambda node: True

    selection = service._healthy_node_for_pool(pool_id)

    assert selection.node is None
    assert selection.available_count == 0
    assert selection.skipped[0]['reason'] == 'provider_rdns_not_ready'
    assert selection.skipped[0]['provider_rdns_status'] == 'pending'


def test_resolve_blocks_with_provider_preference_fallback_evidence() -> None:
    pool = _pool()
    fallback_node = _node(name='mta-aws-001')
    fallback_provider = _provider(provider=MtaProviderType.aws)

    class PreferenceHarness(ResolverHarness):
        def _selected_pool(
            self,
            requested_pool_id,
            policy,
            route,
            sender_domain=None,
            recipient_domain=None,
            send_type=None,
        ):
            return MtaPoolSelection(pool, 'delivery_route_rule', 'scaleway-only', 'delivery_route_rule', ['scaleway'])

        def _healthy_node_for_pool(self, pool_id, preferred_providers=None):
            if preferred_providers:
                return MtaNodeSelection(
                    node=None,
                    provider=None,
                    membership=None,
                    candidate_count=1,
                    skipped=[
                        {
                            'mta_node_id': str(fallback_node.id),
                            'provider': 'aws',
                            'reason': 'provider_not_preferred',
                        }
                    ],
                )
            return MtaNodeSelection(
                node=fallback_node,
                provider=fallback_provider,
                membership=SimpleNamespace(id=uuid4(), priority=100, weight=100),
                candidate_count=1,
                skipped=[],
            )

    service = PreferenceHarness()
    service.policy = _policy()
    service.route = _route()

    result = service.resolve(ManagedSmtpRouteResolveRequest(from_domain='example.com'))

    assert not result.ok
    assert result.reason is not None
    assert result.reason.code == 'NO_HEALTHY_MTA_NODE'
    assert result.reason.details['preferred_providers'] == ['scaleway']
    assert result.reason.details['provider_preference_blocked'] is True
    assert result.reason.details['provider_preference_fallback_available'] is True
    assert result.reason.details['provider_preference_fallback_provider'] == 'aws'
    assert result.reason.details['provider_preference_fallback_mta_node_name'] == 'mta-aws-001'


def test_resolve_uses_provider_preference_fallback_when_rule_allows_it() -> None:
    pool = _pool()
    fallback_node = _node(name='mta-aws-001')
    fallback_provider = _provider(provider=MtaProviderType.aws)

    class PreferenceHarness(ResolverHarness):
        def _selected_pool(
            self,
            requested_pool_id,
            policy,
            route,
            sender_domain=None,
            recipient_domain=None,
            send_type=None,
        ):
            return MtaPoolSelection(
                pool,
                'delivery_route_rule',
                'scaleway-or-fallback',
                'delivery_route_rule',
                ['scaleway'],
                'fallback_allowed',
            )

        def _healthy_node_for_pool(self, pool_id, preferred_providers=None):
            if preferred_providers:
                return MtaNodeSelection(
                    node=None,
                    provider=None,
                    membership=None,
                    candidate_count=1,
                    skipped=[
                        {
                            'mta_node_id': str(fallback_node.id),
                            'provider': 'aws',
                            'reason': 'provider_not_preferred',
                        }
                    ],
                )
            return MtaNodeSelection(
                node=fallback_node,
                provider=fallback_provider,
                membership=SimpleNamespace(id=uuid4(), priority=100, weight=100),
                candidate_count=1,
                skipped=[],
                available_count=1,
            )

    service = PreferenceHarness()
    service.policy = _policy()
    service.route = _route()

    result = service.resolve(ManagedSmtpRouteResolveRequest(from_domain='example.com'))

    assert result.ok
    assert result.route is not None
    assert result.route.provider == MtaProviderType.aws
    assert result.route.mta_node_name == 'mta-aws-001'
    assert result.route.routing_rule_provider_preference == ['scaleway']
    assert result.route.routing_rule_provider_preference_mode == 'fallback_allowed'
    assert result.route.provider_preference_fallback_used is True
    assert result.route.provider_preference_fallback_provider == 'aws'
    assert result.route.provider_preference_fallback_node_name == 'mta-aws-001'


def test_healthy_node_selection_skips_paused_node_and_uses_next_candidate() -> None:
    pool_id = uuid4()
    first_node_id = uuid4()
    second_node_id = uuid4()
    first_provider_id = uuid4()
    second_provider_id = uuid4()
    first_membership = _membership(
        ip_pool_id=pool_id,
        mta_node_id=first_node_id,
        priority=10,
        weight=100,
    )
    second_membership = _membership(
        ip_pool_id=pool_id,
        mta_node_id=second_node_id,
        priority=20,
        weight=50,
    )
    first_node = _node(
        id=first_node_id,
        provider_account_id=first_provider_id,
        status=MtaOperationalStatus.paused,
    )
    second_node = _node(
        id=second_node_id,
        provider_account_id=second_provider_id,
        name='mta-002',
        hostname='mta-002.email-engine.example',
    )
    first_provider = _provider(id=first_provider_id)
    second_provider = _provider(id=second_provider_id, provider=MtaProviderType.scaleway)

    class ScalarResult:
        def all(self):
            return [first_membership, second_membership]

    class FakeDb:
        def scalars(self, statement):
            return ScalarResult()

        def get(self, model, item_id):
            values = {
                first_node_id: first_node,
                second_node_id: second_node,
                first_provider_id: first_provider,
                second_provider_id: second_provider,
            }
            return values.get(item_id)

    service = ManagedSmtpRoutingService(FakeDb())
    service._latest_readiness_ok = lambda node: node.id == second_node_id

    selection = service._healthy_node_for_pool(pool_id)

    assert selection.node is second_node
    assert selection.provider is second_provider
    assert selection.membership is second_membership
    assert selection.candidate_count == 2
    assert selection.skipped[0]['reason'] == 'node_not_active'
    assert selection.skipped[0]['node_status'] == 'paused'
