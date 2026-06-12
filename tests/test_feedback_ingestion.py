from datetime import datetime
from uuid import uuid4

from email_platform.models.entities import (
    EmailEventType,
    EmailSendRecord,
    EmailSendStatus,
    SuppressionReason,
)
from email_platform.schemas.contracts import ManagedSmtpFeedbackEvent
from email_platform.schemas.contracts import ManagedSmtpReadinessCheckCreate
from email_platform.services.feedback import DeliveryFeedback, FeedbackIngestionService
from email_platform.services.managed_smtp_readiness import ManagedSmtpReadinessService


class FakeDb:
    def __init__(self) -> None:
        self.committed = False

    def commit(self) -> None:
        self.committed = True


class FakeFeedbackListDb:
    def __init__(self, rows=None, total: int = 0) -> None:
        self.rows = rows or []
        self.total = total
        self.statements = []

    def scalars(self, statement):
        self.statements.append(statement)
        return type('Result', (), {'all': lambda _self: self.rows})()

    def scalar(self, statement):
        self.statements.append(statement)
        return self.total


class FakeReadinessDb:
    def __init__(self) -> None:
        self.rows = []
        self.committed = False
        self.refreshed = None

    def add(self, row) -> None:
        self.rows.append(row)

    def commit(self) -> None:
        self.committed = True

    def refresh(self, row) -> None:
        self.refreshed = row


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
        self.raw_feedback = []
        self.seen_keys = set()

    def _find_send_record(self, provider_message_id: str | None) -> EmailSendRecord | None:
        if provider_message_id == 'provider-message':
            return self.record
        return None

    def _feedback_already_processed(self, feedback, idempotency_key: str) -> bool:
        return (feedback.provider, feedback.source, idempotency_key) in self.seen_keys

    def _record_raw_feedback(self, feedback, idempotency_key: str) -> None:
        self.seen_keys.add((feedback.provider, feedback.source, idempotency_key))
        self.raw_feedback.append((feedback, idempotency_key))


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
    assert len(service.raw_feedback) == 1


def test_managed_smtp_readiness_service_normalizes_and_persists_check() -> None:
    db = FakeReadinessDb()
    service = ManagedSmtpReadinessService(db)

    check = service.create(
        ManagedSmtpReadinessCheckCreate(
            source=' managed_smtp_mta_smoke ',
            check_type='mta_smoke',
            status='OK',
            domain='Example.COM',
            host='SMTP.Example.COM',
            summary='Ready',
            result_json={'ok': True},
        )
    )

    assert check.status == 'ok'
    assert check.domain == 'example.com'
    assert check.host == 'smtp.example.com'
    assert check.result_json == {'ok': True}
    assert db.rows == [check]
    assert db.committed is True
    assert db.refreshed is check


def test_managed_smtp_readiness_summary_counts_latest_and_latest_success() -> None:
    latest = type(
        'Check',
        (),
        {
            'status': 'failed',
            'source': 'managed_smtp_mta_smoke',
            'check_type': 'mta_smoke',
            'domain': 'example.com',
            'host': 'smtp.example.com',
            'summary': 'failed',
            'result_json': {'ok': False},
            'id': uuid4(),
            'created_at': datetime.utcnow(),
        },
    )()
    latest_success = type(
        'Check',
        (),
        {
            'status': 'ok',
            'source': 'managed_smtp_mta_smoke',
            'check_type': 'mta_smoke',
            'domain': 'example.com',
            'host': 'smtp.example.com',
            'summary': 'passed',
            'result_json': {'ok': True},
            'id': uuid4(),
            'created_at': datetime.utcnow(),
        },
    )()

    class FakeSummaryService(ManagedSmtpReadinessService):
        def __init__(self) -> None:
            self.count_requests = []

        def count_checks(self, **kwargs) -> int:
            self.count_requests.append(kwargs)
            return {
                None: 5,
                'ok': 3,
                'warning': 1,
                'failed': 1,
            }[kwargs.get('status')]

        def _latest_check(self, **kwargs):
            return latest_success if kwargs.get('status') == 'ok' else latest

    summary = FakeSummaryService().summary(domain='example.com', host='smtp.example.com')

    assert summary.total_count == 5
    assert summary.ok_count == 3
    assert summary.warning_count == 1
    assert summary.failed_count == 1
    assert summary.latest_check is not None
    assert summary.latest_check.status == 'failed'
    assert summary.latest_check.host == 'smtp.example.com'
    assert summary.latest_success is not None
    assert summary.latest_success.status == 'ok'
    assert summary.latest_success.result_json == {'ok': True}


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


def test_managed_smtp_feedback_normalizes_bounces_to_delivery_feedback() -> None:
    service = FakeFeedbackIngestionService(record=None)
    event = ManagedSmtpFeedbackEvent(
        email='recipient@example.com',
        event='dsn_bounce',
        provider_message_id='provider-message',
        smtp_response_code=550,
        smtp_response='550 5.1.1 mailbox unavailable',
        diagnostic_code='smtp; 550 5.1.1',
        metadata_json={'queue_id': 'smtp-queue-1'},
    )

    feedback = service.normalize_managed_smtp(event)

    assert feedback.provider == 'managed_smtp'
    assert feedback.source == 'managed_smtp_feedback'
    assert feedback.event_name == 'dsn_bounce'
    assert feedback.event_type == EmailEventType.bounced
    assert feedback.send_status == EmailSendStatus.bounced
    assert feedback.suppression_reason == SuppressionReason.hard_bounce
    assert feedback.metadata_json['queue_id'] == 'smtp-queue-1'
    assert feedback.metadata_json['smtp_response_code'] == 550
    assert feedback.metadata_json['diagnostic_code'] == 'smtp; 550 5.1.1'


def test_managed_smtp_deferral_updates_status_without_event() -> None:
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

    result = service.ingest_managed_smtp(
        [
            ManagedSmtpFeedbackEvent(
                email='recipient@example.com',
                event='tempfail',
                provider_message_id='provider-message',
                smtp_response_code=421,
                smtp_response='421 try again later',
            )
        ]
    )

    assert result.processed_count == 1
    assert result.updated_send_records == 1
    assert result.suppressed_count == 0
    assert record.status == EmailSendStatus.deferred
    assert service.events.payloads == []


def test_managed_smtp_feedback_skips_duplicate_queue_event() -> None:
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
    event = ManagedSmtpFeedbackEvent(
        email='recipient@example.com',
        event='dsn_bounce',
        provider_message_id='provider-message',
        smtp_response_code=550,
        smtp_response='550 5.1.1 mailbox unavailable',
        metadata_json={'postfix_queue_id': 'ABC123DEF'},
    )

    result = service.ingest_managed_smtp([event, event])

    assert result.processed_count == 2
    assert result.duplicate_count == 1
    assert result.updated_send_records == 1
    assert result.suppressed_count == 1
    assert len(service.raw_feedback) == 1
    assert len(service.events.payloads) == 1
    assert len(service.suppressions.payloads) == 1


def test_feedback_service_lists_and_counts_retained_feedback_events() -> None:
    row = type(
        'FeedbackRow',
        (),
        {
            'provider': 'managed_smtp',
            'source': 'managed_smtp_dsn_feedback',
            'event_name': 'dsn_bounce',
            'email': 'recipient@example.com',
        },
    )()
    db = FakeFeedbackListDb(rows=[row], total=1)
    service = FeedbackIngestionService.__new__(FeedbackIngestionService)
    service.db = db

    items = service.list_feedback_events(
        provider='managed_smtp',
        source='managed_smtp_dsn_feedback',
        event_name='dsn_bounce',
        email='recipient@example.com',
        provider_message_id='ABC123DEF',
        limit=10,
        offset=0,
    )
    total = service.count_feedback_events(provider='managed_smtp')

    assert items == [row]
    assert total == 1
    assert len(db.statements) == 2
