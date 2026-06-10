import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from email_platform.models.entities import (
    EmailEventType,
    EmailSendRecord,
    EmailSendStatus,
    ProviderFeedbackEvent,
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
    idempotency_key: str | None = None
    payload_json: dict[str, object] = field(default_factory=dict)


class FeedbackIngestionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.events = EventService(db)
        self.suppressions = SuppressionService(db)

    def ingest(self, feedback_items: list[DeliveryFeedback]) -> ProviderWebhookIngestRead:
        suppressed_count = 0
        updated_send_records = 0
        duplicate_count = 0
        seen_keys: set[tuple[str, str, str]] = set()
        for feedback in feedback_items:
            idempotency_key = feedback.idempotency_key or self._feedback_idempotency_key(feedback)
            key = (feedback.provider, feedback.source, idempotency_key)
            if key in seen_keys or self._feedback_already_processed(feedback, idempotency_key):
                duplicate_count += 1
                continue
            seen_keys.add(key)
            self._record_raw_feedback(feedback, idempotency_key)
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
            duplicate_count=duplicate_count,
        )

    def ingest_managed_smtp(
        self, events: list[ManagedSmtpFeedbackEvent]
    ) -> ProviderWebhookIngestRead:
        return self.ingest([self.normalize_managed_smtp(event) for event in events])

    def list_feedback_events(
        self,
        provider: str | None = None,
        source: str | None = None,
        event_name: str | None = None,
        email: str | None = None,
        provider_message_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ProviderFeedbackEvent]:
        statement = self._feedback_event_statement(
            provider=provider,
            source=source,
            event_name=event_name,
            email=email,
            provider_message_id=provider_message_id,
        ).order_by(ProviderFeedbackEvent.received_at.desc())
        return list(self.db.scalars(statement.limit(limit).offset(offset)).all())

    def count_feedback_events(
        self,
        provider: str | None = None,
        source: str | None = None,
        event_name: str | None = None,
        email: str | None = None,
        provider_message_id: str | None = None,
    ) -> int:
        statement = self._feedback_event_statement(
            provider=provider,
            source=source,
            event_name=event_name,
            email=email,
            provider_message_id=provider_message_id,
            count=True,
        )
        return self.db.scalar(statement) or 0

    def normalize_managed_smtp(self, event: ManagedSmtpFeedbackEvent) -> DeliveryFeedback:
        event_name = event.event.lower()
        payload_json = event.model_dump(mode='json')
        metadata_json = self._managed_smtp_metadata(event)
        return DeliveryFeedback(
            provider='managed_smtp',
            source=event.source,
            event_name=event_name,
            email=str(event.email),
            provider_message_id=event.provider_message_id,
            event_type=self._managed_smtp_event_type(event_name),
            send_status=self._managed_smtp_send_status(event_name),
            suppression_reason=self._managed_smtp_suppression_reason(event_name),
            metadata_json=metadata_json,
            idempotency_key=self._managed_smtp_idempotency_key(event, metadata_json),
            payload_json=payload_json,
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

    def _feedback_event_statement(
        self,
        *,
        provider: str | None = None,
        source: str | None = None,
        event_name: str | None = None,
        email: str | None = None,
        provider_message_id: str | None = None,
        count: bool = False,
    ):
        statement = (
            select(func.count()).select_from(ProviderFeedbackEvent)
            if count
            else select(ProviderFeedbackEvent)
        )
        if provider:
            statement = statement.where(ProviderFeedbackEvent.provider == provider)
        if source:
            statement = statement.where(ProviderFeedbackEvent.source == source)
        if event_name:
            statement = statement.where(ProviderFeedbackEvent.event_name == event_name)
        if email:
            statement = statement.where(ProviderFeedbackEvent.email == email.lower())
        if provider_message_id:
            statement = statement.where(
                ProviderFeedbackEvent.provider_message_id == provider_message_id
            )
        return statement

    def _feedback_already_processed(
        self,
        feedback: DeliveryFeedback,
        idempotency_key: str,
    ) -> bool:
        return bool(
            self.db.scalar(
                select(ProviderFeedbackEvent.id)
                .where(ProviderFeedbackEvent.provider == feedback.provider)
                .where(ProviderFeedbackEvent.source == feedback.source)
                .where(ProviderFeedbackEvent.idempotency_key == idempotency_key)
            )
        )

    def _record_raw_feedback(
        self,
        feedback: DeliveryFeedback,
        idempotency_key: str,
    ) -> None:
        self.db.add(
            ProviderFeedbackEvent(
                provider=feedback.provider,
                source=feedback.source,
                event_name=feedback.event_name,
                email=feedback.email,
                provider_message_id=feedback.provider_message_id,
                idempotency_key=idempotency_key,
                payload_json=feedback.payload_json or self._feedback_payload(feedback),
                metadata_json=feedback.metadata_json,
                received_at=datetime.utcnow(),
            )
        )

    def _feedback_idempotency_key(self, feedback: DeliveryFeedback) -> str:
        metadata_key = feedback.metadata_json.get('idempotency_key')
        if metadata_key:
            return str(metadata_key)
        queue_id = self._feedback_queue_id(feedback.metadata_json)
        if queue_id:
            return self._hash_key(
                {
                    'queue_id': queue_id,
                    'event': feedback.event_name,
                    'email': feedback.email.lower(),
                    'provider_message_id': feedback.provider_message_id,
                }
            )
        return self._hash_key(feedback.payload_json or self._feedback_payload(feedback))

    def _managed_smtp_idempotency_key(
        self,
        event: ManagedSmtpFeedbackEvent,
        metadata: dict[str, object],
    ) -> str:
        explicit_key = metadata.get('idempotency_key')
        if explicit_key:
            return str(explicit_key)
        queue_id = self._feedback_queue_id(metadata)
        if queue_id:
            return self._hash_key(
                {
                    'queue_id': queue_id,
                    'event': event.event.lower(),
                    'email': str(event.email).lower(),
                    'provider_message_id': event.provider_message_id,
                }
            )
        return self._hash_key(event.model_dump(mode='json'))

    def _feedback_queue_id(self, metadata: dict[str, object]) -> str | None:
        for key in ('postfix_queue_id', 'queue_id', 'smtp_queue_id'):
            value = metadata.get(key)
            if value:
                return str(value)
        return None

    def _feedback_payload(self, feedback: DeliveryFeedback) -> dict[str, object]:
        return {
            'provider': feedback.provider,
            'source': feedback.source,
            'event_name': feedback.event_name,
            'email': feedback.email,
            'provider_message_id': feedback.provider_message_id,
            'metadata_json': feedback.metadata_json,
        }

    def _hash_key(self, payload: dict[str, object]) -> str:
        body = json.dumps(payload, sort_keys=True, separators=(',', ':'), default=str)
        return hashlib.sha256(body.encode('utf-8')).hexdigest()

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
