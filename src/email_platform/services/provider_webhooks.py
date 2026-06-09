from sqlalchemy import select
from sqlalchemy.orm import Session

from email_platform.models.entities import (
    EmailEventType,
    EmailSendRecord,
    EmailSendStatus,
    SuppressionReason,
)
from email_platform.schemas.contracts import (
    EventCreate,
    ProviderWebhookIngestRead,
    SendGridWebhookEvent,
)
from email_platform.services.events import EventService
from email_platform.services.suppressions import SuppressionService


class ProviderWebhookService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.events = EventService(db)
        self.suppressions = SuppressionService(db)

    def ingest_sendgrid(self, events: list[SendGridWebhookEvent]) -> ProviderWebhookIngestRead:
        suppressed_count = 0
        updated_send_records = 0
        for event in events:
            provider_message_id = self._provider_message_id(event)
            send_record = self._find_send_record(provider_message_id)
            event_type = self._event_type(event.event)
            if send_record and event_type:
                send_record.provider_message_id = provider_message_id
                send_record.status = self._send_status(event.event, send_record.status)
                updated_send_records += 1
                self.events.record_no_commit(
                    EventCreate(
                        send_record_id=send_record.id,
                        send_job_id=send_record.send_job_id,
                        contact_id=send_record.contact_id,
                        campaign_id=send_record.campaign_id,
                        event_type=event_type,
                        provider_message_id=provider_message_id,
                        metadata_json={
                            **event.model_dump(),
                            'send_record_id': str(send_record.id),
                            'send_job_id': str(send_record.send_job_id),
                        },
                    )
                )

            suppression_reason = self._suppression_reason(event.event)
            if suppression_reason:
                self.suppressions.create_or_update(
                    email=str(event.email),
                    reason=suppression_reason,
                    source='sendgrid_webhook',
                    provider_message_id=provider_message_id,
                    metadata_json=event.model_dump(),
                    contact_id=send_record.contact_id if send_record else None,
                )
                suppressed_count += 1

        self.db.commit()
        return ProviderWebhookIngestRead(
            processed_count=len(events),
            suppressed_count=suppressed_count,
            updated_send_records=updated_send_records,
        )

    def _find_send_record(self, provider_message_id: str | None) -> EmailSendRecord | None:
        if not provider_message_id:
            return None
        return self.db.scalar(
            select(EmailSendRecord).where(
                EmailSendRecord.provider_message_id == provider_message_id
            )
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
        status_map = {
            'delivered': EmailSendStatus.delivered,
            'bounce': EmailSendStatus.bounced,
            'dropped': EmailSendStatus.bounced,
            'spamreport': EmailSendStatus.complained,
            'unsubscribe': EmailSendStatus.unsubscribed,
            'group_unsubscribe': EmailSendStatus.unsubscribed,
        }
        return status_map.get(event_name, current_status)

    def _suppression_reason(self, event_name: str) -> SuppressionReason | None:
        reason_map = {
            'bounce': SuppressionReason.hard_bounce,
            'dropped': SuppressionReason.hard_bounce,
            'spamreport': SuppressionReason.spam_complaint,
            'unsubscribe': SuppressionReason.unsubscribe,
            'group_unsubscribe': SuppressionReason.unsubscribe,
        }
        return reason_map.get(event_name)
