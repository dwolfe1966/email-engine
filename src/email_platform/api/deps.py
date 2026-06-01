"""Shared FastAPI dependencies for API route protection."""
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from email_platform.db.session import get_db
from email_platform.models.entities import User
from email_platform.services.auth import SESSION_COOKIE_NAME, lookup_session

DbSession = Annotated[Session, Depends(get_db)]
SessionCookie = Annotated[str | None, Cookie(default=None, alias=SESSION_COOKIE_NAME)]


def optional_user(db: DbSession, token: SessionCookie = None) -> User | None:
    """Return the authenticated user for a live session cookie, if present."""
    if not token:
        return None

    row = lookup_session(db, token)
    if row is None:
        return None

    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        return None

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
