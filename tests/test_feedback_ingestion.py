from uuid import uuid4

from email_platform.models.entities import (
    EmailEventType,
    EmailSendRecord,
    EmailSendStatus,
    SuppressionReason,
)
from email_platform.services.feedback import DeliveryFeedback, FeedbackIngestionService


class FakeDb:
    def __init__(self) -> None:
        self.committed = False

    def commit(self) -> None:
        self.committed = True


class FakeEventService:
    def __init__(self) -> None:
        self.payloads = []

    def record_no_commit(self, payload) -> None:
        self.payloads.append(payload)


class FakeSuppressionService:
    def __init__(self) -> None:
        self.payloads = []

    def create_or_update(self, **kwargs) -> None:
        self.payloads.append(kwargs)


class FakeFeedbackIngestionService(FeedbackIngestionService):
    def __init__(self, record: EmailSendRecord | None) -> None:
        self.db = FakeDb()
        self.events = FakeEventService()
        self.suppressions = FakeSuppressionService()
        self.record = record

    def _find_send_record(self, provider_message_id: str | None) -> EmailSendRecord | None:
        if provider_message_id == 'provider-message':
            return self.record
        return None


def test_feedback_ingestion_updates_record_events_and_suppressions() -> None:
    record = EmailSendRecord(
        id=uuid4(),
        campaign_id=uuid4(),
        send_job_id=uuid4(),
        contact_id=uuid4(),
        template_id=uuid4(),
        status=EmailSendStatus.submitted,
        to_email='recipient@example.com',
        variables={},
        provider_message_id='provider-message',
    )
    service = FakeFeedbackIngestionService(record)
    feedback = DeliveryFeedback(
        provider='managed_smtp',
        source='managed_smtp_feedback',
        event_name='dsn_bounce',
        email='recipient@example.com',
        provider_message_id='provider-message',
        event_type=EmailEventType.bounced,
        send_status=EmailSendStatus.bounced,
        suppression_reason=SuppressionReason.hard_bounce,
        metadata_json={'smtp_response': '550 mailbox unavailable'},
    )

    result = service.ingest([feedback])

    assert result.processed_count == 1
    assert result.updated_send_records == 1
    assert result.suppressed_count == 1
    assert record.status == EmailSendStatus.bounced
    assert service.db.committed
    assert service.events.payloads[0].send_record_id == record.id
    assert service.events.payloads[0].event_type == EmailEventType.bounced
    assert service.events.payloads[0].metadata_json['provider'] == 'managed_smtp'
    assert service.events.payloads[0].metadata_json['send_record_id'] == str(record.id)
    assert service.suppressions.payloads[0]['reason'] == SuppressionReason.hard_bounce
    assert service.suppressions.payloads[0]['contact_id'] == record.contact_id


def test_feedback_ingestion_suppresses_unmatched_feedback_without_event() -> None:
    service = FakeFeedbackIngestionService(record=None)
    feedback = DeliveryFeedback(
        provider='managed_smtp',
        source='managed_smtp_feedback',
        event_name='complaint',
        email='recipient@example.com',
        provider_message_id='unknown-message',
        event_type=EmailEventType.complained,
        send_status=EmailSendStatus.complained,
        suppression_reason=SuppressionReason.spam_complaint,
    )

    result = service.ingest([feedback])

    assert result.processed_count == 1
    assert result.updated_send_records == 0
    assert result.suppressed_count == 1
    assert service.events.payloads == []
    assert service.suppressions.payloads[0]['contact_id'] is None
