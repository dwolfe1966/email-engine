from email_platform.models.entities import EmailSendStatus
from email_platform.schemas.contracts import SendGridWebhookEvent
from email_platform.services.provider_webhooks import ProviderWebhookService


def test_provider_webhooks_map_feedback_events_to_lifecycle_statuses() -> None:
    service = ProviderWebhookService.__new__(ProviderWebhookService)

    assert service._send_status('delivered', EmailSendStatus.submitted) == (
        EmailSendStatus.delivered
    )
    assert service._send_status('bounce', EmailSendStatus.submitted) == EmailSendStatus.bounced
    assert service._send_status('dropped', EmailSendStatus.submitted) == EmailSendStatus.bounced
    assert service._send_status('spamreport', EmailSendStatus.submitted) == (
        EmailSendStatus.complained
    )
    assert service._send_status('unsubscribe', EmailSendStatus.submitted) == (
        EmailSendStatus.unsubscribed
    )
    assert service._send_status('processed', EmailSendStatus.submitted) == (
        EmailSendStatus.submitted
    )


def test_sendgrid_webhook_normalizes_to_delivery_feedback() -> None:
    service = ProviderWebhookService.__new__(ProviderWebhookService)
    event = SendGridWebhookEvent(
        email='recipient@example.com',
        event='bounce',
        sg_message_id='provider-message.filter123',
        reason='550 mailbox unavailable',
        timestamp=1710000000,
    )

    feedback = service.normalize_sendgrid(event)

    assert feedback.provider == 'sendgrid'
    assert feedback.source == 'sendgrid_webhook'
    assert feedback.event_name == 'bounce'
    assert feedback.email == 'recipient@example.com'
    assert feedback.provider_message_id == 'provider-message'
    assert feedback.send_status == EmailSendStatus.bounced
    assert feedback.metadata_json['reason'] == '550 mailbox unavailable'
