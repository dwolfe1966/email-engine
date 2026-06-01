from fastapi import HTTPException
from fastapi.testclient import TestClient

from email_platform.api.deps import (
    is_public_api_path,
    optional_user,
    require_user,
    requires_operator_auth_path,
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
