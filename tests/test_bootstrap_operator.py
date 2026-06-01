from unittest.mock import Mock

import pytest

from email_platform.core.settings import Settings
from email_platform.models.entities import User
from email_platform.services.auth import verify_password
from email_platform.services.bootstrap import bootstrap_operator_user, should_bootstrap_operator


def test_bootstrap_operator_is_disabled_without_complete_credentials() -> None:
    assert not should_bootstrap_operator(Settings())
    assert not should_bootstrap_operator(
        Settings(bootstrap_operator_email='admin@example.com')
    )


def test_bootstrap_operator_rejects_short_password() -> None:
    db = Mock()
    settings = Settings(
        bootstrap_operator_email='admin@example.com',
        bootstrap_operator_password='short',
    )

    with pytest.raises(ValueError, match='BOOTSTRAP_OPERATOR_PASSWORD'):
        bootstrap_operator_user(db, settings)

    db.execute.assert_not_called()


def test_bootstrap_operator_creates_active_admin_user() -> None:
    db = Mock()
    db.execute.return_value.scalar_one_or_none.return_value = None
    settings = Settings(
        bootstrap_operator_email='admin@example.com',
        bootstrap_operator_password='long-enough-password',
        bootstrap_operator_display_name='Admin User',
        bootstrap_operator_role='admin',
    )

    user = bootstrap_operator_user(db, settings)

    assert user is not None
    assert user.email == 'admin@example.com'
    assert user.display_name == 'Admin User'
    assert user.role == 'admin'
    assert user.is_active is True
    assert user.failed_login_count == 0
    assert verify_password('long-enough-password', user.password_hash or '')
    db.add.assert_called_once_with(user)
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(user)


def test_bootstrap_operator_updates_existing_user_and_clears_lockout() -> None:
    existing = User(
        email='admin@example.com',
        display_name='Old Name',
        role='viewer',
        password_hash=None,
        is_active=False,
        failed_login_count=5,
    )
    db = Mock()
    db.execute.return_value.scalar_one_or_none.return_value = existing
    settings = Settings(
        bootstrap_operator_email='admin@example.com',
        bootstrap_operator_password='replacement-password',
        bootstrap_operator_display_name='Updated Name',
        bootstrap_operator_role='admin',
    )

    user = bootstrap_operator_user(db, settings)

    assert user is existing
    assert user.display_name == 'Updated Name'
    assert user.role == 'admin'
    assert user.is_active is True
    assert user.failed_login_count == 0
    assert user.locked_until is None
    assert verify_password('replacement-password', user.password_hash or '')
    db.add.assert_not_called()
    db.commit.assert_called_once()
