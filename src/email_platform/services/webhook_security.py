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
