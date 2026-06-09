from datetime import datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

from email_platform.models.entities import DeliveryRouteStatus, DeliveryRouteType
from email_platform.services.delivery_routes import DeliveryRouteService


class FakeDb:
    def __init__(self, scalar_results=None, get_result=None) -> None:
        self.scalar_results = list(scalar_results or [])
        self.get_result = get_result

    def scalar(self, statement):
        if self.scalar_results:
            return self.scalar_results.pop(0)
        return None

    def get(self, model, item_id):
        return self.get_result


def test_delivery_route_selector_falls_back_to_settings_provider() -> None:
    service = DeliveryRouteService(FakeDb())

    selected = service.select_for_record(
        SimpleNamespace(to_email='recipient@example.com'),
        SimpleNamespace(email_provider='console'),
    )

    assert selected.route_type == 'console'
    assert selected.route_key == 'console'
    assert selected.route_id is None
    assert selected.source == 'settings'


def test_delivery_route_selector_maps_smtp_provider_to_smtp_relay() -> None:
    service = DeliveryRouteService(FakeDb())

    selected = service.select_for_record(
        SimpleNamespace(to_email='recipient@example.com'),
        SimpleNamespace(email_provider='smtp'),
    )

    assert selected.route_type == 'smtp_relay'
    assert selected.route_key == 'smtp'
    assert selected.source == 'settings'


def test_delivery_route_selector_prefers_active_matching_route() -> None:
    route_id = uuid4()
    service = DeliveryRouteService(
        FakeDb(
            scalar_results=[
                None,
                SimpleNamespace(
                    id=route_id,
                    name='primary-console',
                    route_type=DeliveryRouteType.console,
                ),
            ],
        )
    )

    selected = service.select_for_record(
        SimpleNamespace(to_email='recipient@example.com'),
        SimpleNamespace(email_provider='console'),
    )

    assert selected.route_type == 'console'
    assert selected.route_key == 'primary-console'
    assert selected.route_id == route_id
    assert selected.name == 'primary-console'
    assert selected.source == 'delivery_routes'


def test_delivery_route_selector_prefers_matching_domain_policy_route() -> None:
    route_id = uuid4()
    policy_id = uuid4()
    route = SimpleNamespace(
        id=route_id,
        name='gmail-warmup',
        route_type=DeliveryRouteType.managed_smtp,
        status=DeliveryRouteStatus.active,
    )
    policy = SimpleNamespace(
        id=policy_id,
        domain='gmail.com',
        route_id=route_id,
        warmup_stage='stage_1',
        max_per_minute=25,
        max_concurrent=2,
        paused_until=None,
    )
    service = DeliveryRouteService(FakeDb(scalar_results=[policy], get_result=route))

    selected = service.select_for_record(
        SimpleNamespace(to_email='recipient@gmail.com'),
        SimpleNamespace(email_provider='console'),
    )

    assert selected.route_type == 'managed_smtp'
    assert selected.route_key == 'gmail-warmup'
    assert selected.route_id == route_id
    assert selected.domain_policy_id == policy_id
    assert selected.domain == 'gmail.com'
    assert selected.warmup_stage == 'stage_1'
    assert selected.max_per_minute == 25
    assert selected.max_concurrent == 2
    assert selected.source == 'domain_policy'


def test_delivery_route_selector_ignores_paused_domain_policy() -> None:
    policy = SimpleNamespace(
        id=uuid4(),
        domain='gmail.com',
        route_id=uuid4(),
        warmup_stage='stage_1',
        max_per_minute=25,
        max_concurrent=2,
        paused_until=datetime.utcnow() + timedelta(hours=1),
    )
    service = DeliveryRouteService(FakeDb(scalar_results=[policy, None]))

    selected = service.select_for_record(
        SimpleNamespace(to_email='recipient@gmail.com'),
        SimpleNamespace(email_provider='console'),
    )

    assert selected.route_type == 'console'
    assert selected.route_key == 'console'
    assert selected.source == 'settings'


def test_delivery_claim_decision_blocks_paused_domain_policy() -> None:
    policy = SimpleNamespace(
        id=uuid4(),
        domain='gmail.com',
        paused_until=datetime.utcnow() + timedelta(minutes=10),
        max_per_minute=None,
        max_concurrent=None,
    )
    service = DeliveryRouteService(FakeDb(scalar_results=[policy]))

    decision = service.claim_decision(SimpleNamespace(to_email='recipient@gmail.com'))

    assert not decision.can_claim
    assert decision.reason == 'domain_policy_paused'
    assert decision.domain == 'gmail.com'
    assert decision.domain_policy_id == policy.id


def test_delivery_claim_decision_blocks_per_minute_limit() -> None:
    policy = SimpleNamespace(
        id=uuid4(),
        domain='gmail.com',
        paused_until=None,
        max_per_minute=2,
        max_concurrent=None,
    )
    service = DeliveryRouteService(FakeDb(scalar_results=[policy, 2]))

    decision = service.claim_decision(SimpleNamespace(to_email='recipient@gmail.com'))

    assert not decision.can_claim
    assert decision.reason == 'domain_policy_max_per_minute'


def test_delivery_claim_decision_accounts_for_reserved_batch_count() -> None:
    policy = SimpleNamespace(
        id=uuid4(),
        domain='gmail.com',
        paused_until=None,
        max_per_minute=2,
        max_concurrent=None,
    )
    service = DeliveryRouteService(FakeDb(scalar_results=[policy, 1]))

    decision = service.claim_decision(
        SimpleNamespace(to_email='recipient@gmail.com'),
        reserved_count=1,
    )

    assert not decision.can_claim
    assert decision.reason == 'domain_policy_max_per_minute'


def test_delivery_claim_decision_allows_under_limits() -> None:
    policy = SimpleNamespace(
        id=uuid4(),
        domain='gmail.com',
        paused_until=None,
        max_per_minute=3,
        max_concurrent=2,
    )
    service = DeliveryRouteService(FakeDb(scalar_results=[policy, 1, 0]))

    decision = service.claim_decision(SimpleNamespace(to_email='recipient@gmail.com'))

    assert decision.can_claim
    assert decision.domain == 'gmail.com'
    assert decision.domain_policy_id == policy.id
