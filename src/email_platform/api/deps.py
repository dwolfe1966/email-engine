"""Shared FastAPI dependencies and helpers for route protection."""
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from email_platform.db.session import get_db
from email_platform.models.entities import User
from email_platform.services.auth import SESSION_COOKIE_NAME, lookup_session

DbSession = Annotated[Session, Depends(get_db)]
SessionCookie = Annotated[str | None, Cookie(default=None, alias=SESSION_COOKIE_NAME)]

PUBLIC_API_EXACT_PATHS = {
    '/api/auth',
    '/api/v1/auth',
    '/api/v1/provider-webhooks/sendgrid',
}
PUBLIC_API_PREFIXES = (
    '/api/auth/',
    '/api/v1/auth/',
    '/api/v1/tracking/open/',
    '/api/v1/tracking/click/',
    '/api/v1/unsubscribe/',
)


def is_public_api_path(path: str) -> bool:
    """Return true for API endpoints that must remain publicly callable."""
    return path in PUBLIC_API_EXACT_PATHS or path.startswith(PUBLIC_API_PREFIXES)


def requires_operator_auth_path(path: str) -> bool:
    """Return true for request paths protected by REQUIRE_GUI_AUTH."""
    if is_public_api_path(path):
        return False
    return path == '/api/v1' or path.startswith('/api/v1/')


def user_from_session_token(db: Session, token: str | None) -> User | None:
    """Return the active user for a raw session token, if it is valid."""
    if not token:
        return None

    row = lookup_session(db, token)
    if row is None:
        return None

    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        return None

    return user


def optional_user(db: DbSession, token: SessionCookie = None) -> User | None:
    """Return the authenticated user for a live session cookie, if present."""
    user = user_from_session_token(db, token)
    if user is not None:
        db.commit()
    return user


def require_user(user: User | None = Depends(optional_user)) -> User:
    """Require a valid operator session cookie for protected admin/API routes."""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Not authenticated',
            headers={'WWW-Authenticate': 'Cookie'},
        )
    return user
