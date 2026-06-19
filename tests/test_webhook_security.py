from datetime import UTC, datetime
import hashlib
import hmac

import pytest

from email_platform.core.settings import Settings
from email_platform.services.webhook_security import (
    ManagedSmtpFeedbackVerifier,
    WebhookSignatureError,
)


def managed_smtp_signature(secret: str, timestamp: str, payload: bytes) -> str:
    return hmac.new(
        secret.encode('utf-8'),
        timestamp.encode('utf-8') + b'.' + payload,
        hashlib.sha256,
    ).hexdigest()


def test_managed_smtp_feedback_verifier_accepts_valid_signature() -> None:
    payload = b'[{"email":"recipient@example.com","event":"dsn_bounce"}]'
    timestamp = str(int(datetime.now(UTC).timestamp()))
    signature = managed_smtp_signature('secret-value', timestamp, payload)
    verifier = ManagedSmtpFeedbackVerifier(
        Settings(managed_smtp_feedback_secret='secret-value')
    )

    verifier.verify(payload, signature, timestamp)


def test_managed_smtp_feedback_verifier_accepts_previous_secret_during_rotation() -> None:
    payload = b'[{"email":"recipient@example.com","event":"delivered"}]'
    timestamp = str(int(datetime.now(UTC).timestamp()))
    signature = managed_smtp_signature('old-secret-value', timestamp, payload)
    verifier = ManagedSmtpFeedbackVerifier(
        Settings(
            managed_smtp_feedback_secret='new-secret-value',
            managed_smtp_feedback_previous_secret='old-secret-value',
        )
    )

    verifier.verify(payload, signature, timestamp)


def test_managed_smtp_feedback_verifier_prefers_current_secret_during_rotation() -> None:
    payload = b'[]'
    timestamp = str(int(datetime.now(UTC).timestamp()))
    signature = managed_smtp_signature('new-secret-value', timestamp, payload)
    verifier = ManagedSmtpFeedbackVerifier(
        Settings(
            managed_smtp_feedback_secret='new-secret-value',
            managed_smtp_feedback_previous_secret='old-secret-value',
        )
    )

    verifier.verify(payload, signature, timestamp)


def test_managed_smtp_feedback_verifier_rejects_missing_secret_by_default() -> None:
    verifier = ManagedSmtpFeedbackVerifier(Settings())

    with pytest.raises(WebhookSignatureError, match='secret is not configured'):
        verifier.verify(b'[]', None, None)


def test_managed_smtp_feedback_verifier_rejects_invalid_signature() -> None:
    payload = b'[]'
    timestamp = str(int(datetime.now(UTC).timestamp()))
    verifier = ManagedSmtpFeedbackVerifier(
        Settings(managed_smtp_feedback_secret='secret-value')
    )

    with pytest.raises(WebhookSignatureError, match='Invalid managed SMTP feedback signature'):
        verifier.verify(payload, 'bad-signature', timestamp)


def test_managed_smtp_feedback_verifier_rejects_unknown_secret_during_rotation() -> None:
    payload = b'[]'
    timestamp = str(int(datetime.now(UTC).timestamp()))
    signature = managed_smtp_signature('unknown-secret', timestamp, payload)
    verifier = ManagedSmtpFeedbackVerifier(
        Settings(
            managed_smtp_feedback_secret='new-secret-value',
            managed_smtp_feedback_previous_secret='old-secret-value',
        )
    )

    with pytest.raises(WebhookSignatureError, match='Invalid managed SMTP feedback signature'):
        verifier.verify(payload, signature, timestamp)


def test_managed_smtp_feedback_verifier_rejects_stale_timestamp() -> None:
    payload = b'[]'
    timestamp = '1'
    signature = managed_smtp_signature('secret-value', timestamp, payload)
    verifier = ManagedSmtpFeedbackVerifier(
        Settings(
            managed_smtp_feedback_secret='secret-value',
            managed_smtp_feedback_signature_tolerance_seconds=300,
        )
    )

    with pytest.raises(WebhookSignatureError, match='outside tolerance'):
        verifier.verify(payload, signature, timestamp)
