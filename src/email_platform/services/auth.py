"""Authentication primitives — password hashing, cookie session lifecycle.

Pure business logic; route handlers wire HTTP semantics on top.

Login flow (per the shared SentientMail/SpokeoESP contract):
  POST /api/v1/auth/login   {email, password} → 200 + Set-Cookie
  POST /api/v1/auth/logout                   → 204 + clear cookie
  GET  /api/v1/auth/me                       → 200 with user, 401 otherwise

Cookie shape:
  Name:  SESSION_COOKIE_NAME
  Value: 32-byte URL-safe random token (only its sha256 is stored)
  Flags: HttpOnly, Secure (in non-local envs), SameSite=Lax

Sliding expiry: each authenticated request bumps last_seen_at and, when
the remaining window is < SESSION_REFRESH_THRESHOLD, extends expires_at
by another SESSION_LIFETIME. Active users stay logged in; idle ones
get logged out after SESSION_LIFETIME of no activity.

Rate limiting: failed_login_count / locked_until on the user row.
Single-instance friendly; DB-level so multi-worker setups still work.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Final

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sqlalchemy import select
from sqlalchemy.orm import Session

from email_platform.models.entities import User, UserSession

SESSION_COOKIE_NAME: Final = 'esp_session'
SESSION_LIFETIME: Final = timedelta(days=30)
# When less than this much time remains, the next authenticated request
# refreshes expires_at by SESSION_LIFETIME.
SESSION_REFRESH_THRESHOLD: Final = timedelta(days=7)

MAX_FAILED_ATTEMPTS: Final = 5
LOCKOUT_DURATION: Final = timedelta(minutes=30)

_hasher = PasswordHasher()


def hash_password(plain: str) -> str:
    return _hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """True iff plain matches the hash; False on any failure mode.
    Never raises — login route relies on this for the constant-time
    decoy path against a dummy hash when the user doesn't exist."""
    try:
        return _hasher.verify(hashed, plain)
    except (VerifyMismatchError, Exception):
        return False


def generate_token() -> str:
    """32 url-safe bytes (~256 bits of entropy). Suitable as the raw
    cookie value; we never store this — only sha256(token)."""
    return secrets.token_urlsafe(32)


def hash_token(raw: str) -> str:
    """sha256 hex of the raw token. Stored in user_sessions.token_hash."""
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def is_locked_out(user: User, *, now: datetime | None = None) -> bool:
    now = now or datetime.utcnow()
    return user.locked_until is not None and user.locked_until > now


def record_failed_login(db: Session, user: User) -> None:
    user.failed_login_count = (user.failed_login_count or 0) + 1
    if user.failed_login_count >= MAX_FAILED_ATTEMPTS:
        user.locked_until = datetime.utcnow() + LOCKOUT_DURATION


def record_successful_login(db: Session, user: User) -> None:
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = datetime.utcnow()


def create_session(
    db: Session,
    *,
    user: User,
    ip: str | None = None,
    user_agent: str | None = None,
) -> tuple[UserSession, str]:
    """Insert a new session row, return (row, raw_token). The raw token
    is the cookie value; the row stores only its hash."""
    raw = generate_token()
    now = datetime.utcnow()
    row = UserSession(
        user_id=user.id,
        token_hash=hash_token(raw),
        expires_at=now + SESSION_LIFETIME,
        last_seen_at=now,
        ip=(ip[:64] if ip else None),
        user_agent=(user_agent[:255] if user_agent else None),
    )
    db.add(row)
    db.flush()
    return row, raw


def revoke_session(db: Session, row: UserSession) -> None:
    if row.revoked_at is None:
        row.revoked_at = datetime.utcnow()


def lookup_session(db: Session, raw_token: str) -> UserSession | None:
    """Return the live UserSession or None. Bumps last_seen_at and
    applies sliding expiry on the way out."""
    row = db.execute(
        select(UserSession).where(UserSession.token_hash == hash_token(raw_token))
    ).scalar_one_or_none()
    if row is None:
        return None
    now = datetime.utcnow()
    if row.revoked_at is not None or row.expires_at < now:
        return None
    row.last_seen_at = now
    if row.expires_at - now < SESSION_REFRESH_THRESHOLD:
        row.expires_at = now + SESSION_LIFETIME
    return row


# Stable decoy hash for the "no such user" path. Recomputing per request
# would be slow; computed once at import.
_DECOY_HASH = hash_password('decoy-decoy-decoy-decoy-decoy-decoy')


def authenticate(db: Session, *, email: str, password: str) -> tuple[User | None, str | None]:
    """Try to authenticate (email, password). Returns:
      (user, None)           on success
      (None, 'locked')       on rate-limit lockout
      (None, 'invalid')      on bad credentials / missing user / inactive

    The caller commits the DB session — successful auth touches
    last_login_at, failed auth bumps the failure counter.
    """
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()

    if user is None:
        # Burn argon2 time so timing doesn't leak account existence.
        verify_password(password, _DECOY_HASH)
        return None, 'invalid'

    if not user.is_active:
        return None, 'invalid'

    if is_locked_out(user):
        return None, 'locked'

    if user.password_hash is None or not verify_password(password, user.password_hash):
        record_failed_login(db, user)
        return None, 'invalid'

    record_successful_login(db, user)
    return user, None
