from sqlalchemy.orm import Session

from email_platform.models.entities import (
    EmailEventType,
    EmailSendStatus,
    SuppressionReason,
)
from email_platform.schemas.contracts import ProviderWebhookIngestRead, SendGridWebhookEvent
from email_platform.services.feedback import DeliveryFeedback, FeedbackIngestionService


class ProviderWebhookService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.feedback = FeedbackIngestionService(db)

    def ingest_sendgrid(self, events: list[SendGridWebhookEvent]) -> ProviderWebhookIngestRead:
        return self.feedback.ingest([self.normalize_sendgrid(event) for event in events])

    def normalize_sendgrid(self, event: SendGridWebhookEvent) -> DeliveryFeedback:
        return DeliveryFeedback(
            provider='sendgrid',
            source='sendgrid_webhook',
            event_name=event.event,
            email=str(event.email),
            provider_message_id=self._provider_message_id(event),
            event_type=self._event_type(event.event),
            send_status=self._target_send_status(event.event),
            suppression_reason=self._suppression_reason(event.event),
            metadata_json=event.model_dump(),
        )

    def _provider_message_id(self, event: SendGridWebhookEvent) -> str | None:
        if event.sg_message_id:
            return event.sg_message_id.split('.')[0]
        return event.smtp_id

    def _event_type(self, event_name: str) -> EmailEventType | None:
        event_map = {
            'delivered': EmailEventType.delivered,
            'open': EmailEventType.opened,
            'click': EmailEventType.clicked,
            'bounce': EmailEventType.bounced,
            'dropped': EmailEventType.bounced,
            'spamreport': EmailEventType.complained,
            'unsubscribe': EmailEventType.unsubscribed,
            'group_unsubscribe': EmailEventType.unsubscribed,
        }
        return event_map.get(event_name)

    def _send_status(
        self, event_name: str, current_status: EmailSendStatus
    ) -> EmailSendStatus:
        return self._target_send_status(event_name) or current_status

    def _target_send_status(self, event_name: str) -> EmailSendStatus | None:
        status_map = {
            'delivered': EmailSendStatus.delivered,
            'bounce': EmailSendStatus.bounced,
            'dropped': EmailSendStatus.bounced,
            'spamreport': EmailSendStatus.complained,
            'unsubscribe': EmailSendStatus.unsubscribed,
            'group_unsubscribe': EmailSendStatus.unsubscribed,
        }
        return status_map.get(event_name)

    def _suppression_reason(self, event_name: str) -> SuppressionReason | None:
        reason_map = {
            'bounce': SuppressionReason.hard_bounce,
            'dropped': SuppressionReason.hard_bounce,
            'spamreport': SuppressionReason.spam_complaint,
            'unsubscribe': SuppressionReason.unsubscribe,
            'group_unsubscribe': SuppressionReason.unsubscribe,
        }
        return reason_map.get(event_name)
