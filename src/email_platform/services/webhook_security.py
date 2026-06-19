from datetime import UTC, datetime
import hashlib
import hmac

from sendgrid.helpers.eventwebhook import EventWebhook

from email_platform.core.settings import Settings


class WebhookSignatureError(ValueError):
    pass


class SendGridWebhookVerifier:
    signature_header = 'X-Twilio-Email-Event-Webhook-Signature'
    timestamp_header = 'X-Twilio-Email-Event-Webhook-Timestamp'

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.event_webhook = EventWebhook()

    def verify(self, payload: bytes, signature: str | None, timestamp: str | None) -> None:
        public_key_value = self.settings.sendgrid_event_webhook_public_key
        if not public_key_value:
            if self.settings.sendgrid_event_webhook_require_signature:
                raise WebhookSignatureError('SendGrid webhook public key is not configured')
            return
        if not signature or not timestamp:
            raise WebhookSignatureError('Missing SendGrid webhook signature headers')

        public_key = self.event_webhook.convert_public_key_to_ecdsa(public_key_value)
        is_valid = self.event_webhook.verify_signature(
            payload.decode('utf-8'),
            signature,
            timestamp,
            public_key,
        )
        if not is_valid:
            raise WebhookSignatureError('Invalid SendGrid webhook signature')


class ManagedSmtpFeedbackVerifier:
    signature_header = 'X-Email-Engine-Signature'
    timestamp_header = 'X-Email-Engine-Timestamp'

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def verify(self, payload: bytes, signature: str | None, timestamp: str | None) -> None:
        secret = self.settings.managed_smtp_feedback_secret
        previous_secret = self.settings.managed_smtp_feedback_previous_secret
        secrets = [value for value in (secret, previous_secret) if value]
        if not secrets:
            if self.settings.managed_smtp_feedback_require_signature:
                raise WebhookSignatureError('Managed SMTP feedback secret is not configured')
            return
        if not signature or not timestamp:
            raise WebhookSignatureError('Missing managed SMTP feedback signature headers')

        timestamp_value = self._timestamp_value(timestamp)
        now = int(datetime.now(UTC).timestamp())
        tolerance = self.settings.managed_smtp_feedback_signature_tolerance_seconds
        if tolerance > 0 and abs(now - timestamp_value) > tolerance:
            raise WebhookSignatureError(
                'Managed SMTP feedback signature timestamp is outside tolerance'
            )

        signed_payload = timestamp.encode('utf-8') + b'.' + payload
        for candidate_secret in secrets:
            expected = hmac.new(
                candidate_secret.encode('utf-8'),
                signed_payload,
                hashlib.sha256,
            ).hexdigest()
            if hmac.compare_digest(signature, expected):
                return
        raise WebhookSignatureError('Invalid managed SMTP feedback signature')

    def _timestamp_value(self, timestamp: str) -> int:
        try:
            return int(timestamp)
        except ValueError as exc:
            raise WebhookSignatureError('Invalid managed SMTP feedback timestamp') from exc
