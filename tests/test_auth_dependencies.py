from fastapi import HTTPException

from email_platform.api.deps import optional_user, require_user


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
