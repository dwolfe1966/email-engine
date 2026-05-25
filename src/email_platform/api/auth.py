"""Authentication endpoints for the email-engine API.

Contract mirrors the SentientMail/SpokeoESP shared UI so a single
client codebase works against either backend with only a base-URL
swap (`/api/v1/auth/...` here vs `/api/auth/...` on the SpokeoESP
backend).

  POST /api/v1/auth/login   {email, password}  → 200 + Set-Cookie
  POST /api/v1/auth/logout                     → 204 + clear cookie
  GET  /api/v1/auth/me                         → 200 with user / 401

Generic 'Invalid email or password' on every credential-fail branch so
an attacker can't enumerate accounts by error-text or timing (we burn
argon2 time against a decoy hash when the email doesn't exist).
Lockout is the exception — telling a real user 'try again later' is
worth the small enumeration leak there.
"""
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from email_platform.db.session import get_db
from email_platform.models.entities import User
from email_platform.schemas.contracts import (
    AuthUserRead,
    LoginRequest,
    LoginResponse,
    MeResponse,
)
from email_platform.services.auth import (
    SESSION_COOKIE_NAME,
    SESSION_LIFETIME,
    authenticate,
    create_session,
    lookup_session,
    revoke_session,
)

router = APIRouter(prefix='/api/v1/auth', tags=['auth'])

DbSession = Annotated[Session, Depends(get_db)]
CookieToken = Annotated[str | None, Cookie(alias=SESSION_COOKIE_NAME)]


def _set_session_cookie(response: Response, raw_token: str) -> None:
    """Apply the standard cookie shape. Secure flag is conditioned on
    the deployment env so local HTTP dev still receives the cookie."""
    # Settings imported lazily to avoid a circular at module load.
    from email_platform.core.settings import get_settings

    secure = get_settings().environment != 'local'
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=raw_token,
        max_age=int(SESSION_LIFETIME.total_seconds()),
        httponly=True,
        secure=secure,
        samesite='lax',
        path='/',
    )


def _clear_session_cookie(response: Response) -> None:
    from email_platform.core.settings import get_settings

    secure = get_settings().environment != 'local'
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path='/',
        httponly=True,
        samesite='lax',
        secure=secure,
    )


@router.post('/login', response_model=LoginResponse)
def login(body: LoginRequest, request: Request, response: Response, db: DbSession) -> LoginResponse:
    # authenticate() commits state via the DbSession dep — both
    # success (resets lockout) and failure (bumps counter) need to
    # persist regardless of whether we raise after. We finalize the
    # response (or error) after authenticate returns so the bookkeeping
    # always lands.
    user, err = authenticate(db, email=body.email, password=body.password)
    db.commit()

    if err == 'locked':
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                'Account temporarily locked due to repeated failed '
                'login attempts. Try again later.'
            ),
        )
    if err == 'invalid' or user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid email or password',
        )

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get('user-agent')
    _row, raw_token = create_session(db, user=user, ip=client_ip, user_agent=user_agent)
    db.commit()

    _set_session_cookie(response, raw_token)
    return LoginResponse(user=AuthUserRead.model_validate(user))


@router.post('/logout', status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response, db: DbSession, token: CookieToken = None) -> Response:
    """Revoke the current session + clear the cookie. Idempotent."""
    if token:
        row = lookup_session(db, token)
        if row is not None:
            revoke_session(db, row)
            db.commit()
    _clear_session_cookie(response)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get('/me', response_model=MeResponse)
def me(db: DbSession, token: CookieToken = None) -> MeResponse:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Not authenticated',
        )
    row = lookup_session(db, token)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Not authenticated',
        )
    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Not authenticated',
        )
    db.commit()  # persist sliding-expiry bump from lookup_session
    return MeResponse(user=AuthUserRead.model_validate(user))
