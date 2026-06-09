from types import SimpleNamespace
from uuid import uuid4

from email_platform.models.entities import DeliveryRouteType
from email_platform.services.delivery_routes import DeliveryRouteService


class FakeDb:
    def __init__(self, scalar_result=None) -> None:
        self.scalar_result = scalar_result

    def scalar(self, statement):
        return self.scalar_result


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
            SimpleNamespace(
                id=route_id,
                name='primary-console',
                route_type=DeliveryRouteType.console,
            )
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
