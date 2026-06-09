from dataclasses import dataclass, field

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
    ManagedSmtpFeedbackEvent,
    ProviderWebhookIngestRead,
)
from email_platform.services.events import EventService
from email_platform.services.suppressions import SuppressionService


@dataclass(frozen=True)
class DeliveryFeedback:
    provider: str
    source: str
    event_name: str
    email: str
    provider_message_id: str | None = None
    event_type: EmailEventType | None = None
    send_status: EmailSendStatus | None = None
    suppression_reason: SuppressionReason | None = None
    metadata_json: dict[str, object] = field(default_factory=dict)


class FeedbackIngestionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.events = EventService(db)
        self.suppressions = SuppressionService(db)

    def ingest(self, feedback_items: list[DeliveryFeedback]) -> ProviderWebhookIngestRead:
        suppressed_count = 0
        updated_send_records = 0
        for feedback in feedback_items:
            send_record = self._find_send_record(feedback.provider_message_id)
            if send_record and (feedback.event_type or feedback.send_status):
                self._apply_send_record_feedback(send_record, feedback)
                updated_send_records += 1

            if feedback.suppression_reason:
                self.suppressions.create_or_update(
                    email=feedback.email,
                    reason=feedback.suppression_reason,
                    source=feedback.source,
                    provider_message_id=feedback.provider_message_id,
                    metadata_json=self._metadata(feedback, send_record),
                    contact_id=send_record.contact_id if send_record else None,
                )
                suppressed_count += 1

        self.db.commit()
        return ProviderWebhookIngestRead(
            processed_count=len(feedback_items),
            suppressed_count=suppressed_count,
            updated_send_records=updated_send_records,
        )

    def ingest_managed_smtp(
        self, events: list[ManagedSmtpFeedbackEvent]
    ) -> ProviderWebhookIngestRead:
        return self.ingest([self.normalize_managed_smtp(event) for event in events])

    def normalize_managed_smtp(self, event: ManagedSmtpFeedbackEvent) -> DeliveryFeedback:
        event_name = event.event.lower()
        return DeliveryFeedback(
            provider='managed_smtp',
            source=event.source,
            event_name=event_name,
            email=str(event.email),
            provider_message_id=event.provider_message_id,
            event_type=self._managed_smtp_event_type(event_name),
            send_status=self._managed_smtp_send_status(event_name),
            suppression_reason=self._managed_smtp_suppression_reason(event_name),
            metadata_json=self._managed_smtp_metadata(event),
        )

    def _apply_send_record_feedback(
        self, send_record: EmailSendRecord, feedback: DeliveryFeedback
    ) -> None:
        send_record.provider_message_id = feedback.provider_message_id
        if feedback.send_status:
            send_record.status = feedback.send_status
        if feedback.event_type:
            self.events.record_no_commit(
                EventCreate(
                    send_record_id=send_record.id,
                    send_job_id=send_record.send_job_id,
                    contact_id=send_record.contact_id,
                    campaign_id=send_record.campaign_id,
                    event_type=feedback.event_type,
                    provider_message_id=feedback.provider_message_id,
                    metadata_json=self._metadata(feedback, send_record),
                )
            )

    def _find_send_record(self, provider_message_id: str | None) -> EmailSendRecord | None:
        if not provider_message_id:
            return None
        return self.db.scalar(
            select(EmailSendRecord).where(
                EmailSendRecord.provider_message_id == provider_message_id
            )
        )

    def _metadata(
        self, feedback: DeliveryFeedback, send_record: EmailSendRecord | None
    ) -> dict[str, object]:
        metadata = {
            **feedback.metadata_json,
            'provider': feedback.provider,
            'feedback_source': feedback.source,
            'feedback_event': feedback.event_name,
        }
        if send_record:
            metadata['send_record_id'] = str(send_record.id)
            metadata['send_job_id'] = str(send_record.send_job_id)
        return metadata

    def _managed_smtp_metadata(self, event: ManagedSmtpFeedbackEvent) -> dict[str, object]:
        metadata = {
            **event.metadata_json,
            'event': event.event,
        }
        if event.smtp_response_code is not None:
            metadata['smtp_response_code'] = event.smtp_response_code
        if event.smtp_response:
            metadata['smtp_response'] = event.smtp_response
        if event.diagnostic_code:
            metadata['diagnostic_code'] = event.diagnostic_code
        if event.timestamp is not None:
            metadata['timestamp'] = event.timestamp
        return metadata

    def _managed_smtp_event_type(self, event_name: str) -> EmailEventType | None:
        event_map = {
            'delivered': EmailEventType.delivered,
            'dsn_delivered': EmailEventType.delivered,
            'bounced': EmailEventType.bounced,
            'bounce': EmailEventType.bounced,
            'hard_bounce': EmailEventType.bounced,
            'dsn_bounce': EmailEventType.bounced,
            'complained': EmailEventType.complained,
            'complaint': EmailEventType.complained,
            'feedback_loop_complaint': EmailEventType.complained,
            'unsubscribed': EmailEventType.unsubscribed,
            'unsubscribe': EmailEventType.unsubscribed,
        }
        return event_map.get(event_name)

    def _managed_smtp_send_status(self, event_name: str) -> EmailSendStatus | None:
        status_map = {
            'delivered': EmailSendStatus.delivered,
            'dsn_delivered': EmailSendStatus.delivered,
            'deferred': EmailSendStatus.deferred,
            'deferral': EmailSendStatus.deferred,
            'tempfail': EmailSendStatus.deferred,
            'soft_bounce': EmailSendStatus.deferred,
            'bounced': EmailSendStatus.bounced,
            'bounce': EmailSendStatus.bounced,
            'hard_bounce': EmailSendStatus.bounced,
            'dsn_bounce': EmailSendStatus.bounced,
            'complained': EmailSendStatus.complained,
            'complaint': EmailSendStatus.complained,
            'feedback_loop_complaint': EmailSendStatus.complained,
            'unsubscribed': EmailSendStatus.unsubscribed,
            'unsubscribe': EmailSendStatus.unsubscribed,
        }
        return status_map.get(event_name)

    def _managed_smtp_suppression_reason(
        self, event_name: str
    ) -> SuppressionReason | None:
        reason_map = {
            'bounced': SuppressionReason.hard_bounce,
            'bounce': SuppressionReason.hard_bounce,
            'hard_bounce': SuppressionReason.hard_bounce,
            'dsn_bounce': SuppressionReason.hard_bounce,
            'complained': SuppressionReason.spam_complaint,
            'complaint': SuppressionReason.spam_complaint,
            'feedback_loop_complaint': SuppressionReason.spam_complaint,
            'unsubscribed': SuppressionReason.unsubscribe,
            'unsubscribe': SuppressionReason.unsubscribe,
        }
        return reason_map.get(event_name)
