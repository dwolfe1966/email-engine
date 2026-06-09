from fastapi import HTTPException
from fastapi.testclient import TestClient

from email_platform.api.deps import (
    is_public_api_path,
    optional_user,
    require_user,
    requires_operator_auth_path,
    visitor_method_allowed,
)
from email_platform.main import app, settings


def test_optional_user_without_cookie_is_none() -> None:
    assert optional_user(db=object(), token=None) is None  # type: ignore[arg-type]


def test_require_user_rejects_anonymous_request() -> None:
    try:
        require_user(None)
    except HTTPException as exc:
        assert exc.status_code == 401
        assert exc.detail == 'Not authenticated'
        assert exc.headers == {'WWW-Authenticate': 'Cookie'}
    else:
        raise AssertionError('require_user should reject anonymous requests')


def test_operator_auth_path_classifier_keeps_public_delivery_routes_open() -> None:
    public_paths = [
        '/api/v1/auth/login',
        '/api/auth/login',
        '/api/v1/tracking/open/token',
        '/api/v1/tracking/click/token',
        '/api/v1/provider-webhooks/sendgrid',
        '/api/v1/unsubscribe/token',
    ]
    protected_paths = [
        '/api/v1/templates',
        '/api/v1/campaigns/process-due',
        '/api/v1/email-send-records/abc/tracking-links',
        '/api/v1/delivery/managed-smtp/feedback',
        '/api/v1/tests/send-email',
        '/api/v1/system/diagnostics',
    ]

    for path in public_paths:
        assert is_public_api_path(path)
        assert not requires_operator_auth_path(path)

    for path in protected_paths:
        assert not is_public_api_path(path)
        assert requires_operator_auth_path(path)


def test_require_gui_auth_blocks_operator_api_but_not_public_api(monkeypatch) -> None:
    monkeypatch.setattr(settings, 'require_gui_auth', True)
    client = TestClient(app, follow_redirects=False)

    protected = client.get('/api/v1/templates')
    assert protected.status_code == 401
    assert protected.json() == {'detail': 'Not authenticated'}

    public = client.get('/api/v1/tracking/open/not-a-real-token')
    assert public.status_code != 401


def test_user_management_routes_always_require_operator_session(monkeypatch) -> None:
    monkeypatch.setattr(settings, 'require_gui_auth', False)
    client = TestClient(app, follow_redirects=False)

    response = client.get('/api/v1/users/list')
    assert response.status_code == 401
    assert response.json() == {'detail': 'Not authenticated'}


def test_visitor_access_allows_read_and_safe_preview_posts_only() -> None:
    assert visitor_method_allowed('GET', '/api/v1/templates/list')
    assert visitor_method_allowed('HEAD', '/api/v1/templates/list')
    assert visitor_method_allowed('POST', '/api/v1/templates/preview')
    assert visitor_method_allowed('POST', '/api/v1/audiences/preview')
    assert not visitor_method_allowed('GET', '/api/v1/users/list')
    assert not visitor_method_allowed('GET', '/api/v1/users/user-id')
    assert not visitor_method_allowed('POST', '/api/v1/templates')
    assert not visitor_method_allowed('PATCH', '/api/v1/templates/template-id')
    assert not visitor_method_allowed('DELETE', '/api/v1/templates/template-id')


def test_visitor_link_is_disabled_by_default(monkeypatch) -> None:
    monkeypatch.setattr(settings, 'visitor_access_enabled', False)
    client = TestClient(app, follow_redirects=False)

    response = client.get('/esp/visitor')
    assert response.status_code == 404
