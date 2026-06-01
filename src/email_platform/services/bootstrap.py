from sqlalchemy import select
from sqlalchemy.orm import Session

from email_platform.core.settings import Settings
from email_platform.models.entities import User
from email_platform.services.auth import hash_password, verify_password


def should_bootstrap_operator(settings: Settings) -> bool:
    return bool(settings.bootstrap_operator_email and settings.bootstrap_operator_password)


def bootstrap_operator_user(db: Session, settings: Settings) -> User | None:
    if not should_bootstrap_operator(settings):
        return None
    if settings.bootstrap_operator_password is None or len(settings.bootstrap_operator_password) < 8:
        raise ValueError('BOOTSTRAP_OPERATOR_PASSWORD must be at least 8 characters')

    email = str(settings.bootstrap_operator_email)
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None:
        user = User(
            email=email,
            display_name=settings.bootstrap_operator_display_name,
            role=settings.bootstrap_operator_role,
            password_hash=hash_password(settings.bootstrap_operator_password),
            is_active=True,
            failed_login_count=0,
        )
        db.add(user)
    else:
        user.display_name = settings.bootstrap_operator_display_name
        user.role = settings.bootstrap_operator_role
        user.is_active = True
        user.failed_login_count = 0
        user.locked_until = None
        if user.password_hash is None or not verify_password(
            settings.bootstrap_operator_password,
            user.password_hash,
        ):
            user.password_hash = hash_password(settings.bootstrap_operator_password)

    db.commit()
    db.refresh(user)
    return user


def ensure_visitor_user(db: Session, settings: Settings) -> User:
    email = str(settings.visitor_access_email)
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None:
        user = User(
            email=email,
            display_name=settings.visitor_access_display_name,
            role='visitor',
            password_hash=None,
            is_active=True,
            failed_login_count=0,
        )
        db.add(user)
    else:
        user.display_name = settings.visitor_access_display_name
        user.role = 'visitor'
        user.is_active = True
        user.failed_login_count = 0
        user.locked_until = None

    db.flush()
    return user
