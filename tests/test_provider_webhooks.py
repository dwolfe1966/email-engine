from email_platform.models.entities import EmailSendStatus
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
