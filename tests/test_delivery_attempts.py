from types import SimpleNamespace
from uuid import uuid4

from email_platform.models.entities import EmailSendRecord, EmailSendStatus
from email_platform.services.delivery import DeliveryService


class FakeDb:
    def __init__(self) -> None:
        self.added = []
        self.flush_count = 0
        self.records = []

    def add(self, item) -> None:
        self.added.append(item)

    def flush(self) -> None:
        self.flush_count += 1

    def scalars(self, statement):
        return SimpleNamespace(all=lambda: self.records)


class FakeRouteService:
    def select_for_record(self, record, settings):
        return SimpleNamespace(
            route_type=settings.email_provider,
            route_key=settings.email_provider,
            route_id=None,
            domain_policy_id=None,
            name=None,
            domain='example.com',
            warmup_stage=None,
            max_per_minute=None,
            max_concurrent=None,
            source='settings',
        )


class SelectiveRouteService:
    def __init__(self, blocked_domain: str) -> None:
        self.blocked_domain = blocked_domain

    def claim_decision(self, record, reserved_count=0):
        domain = record.to_email.rsplit('@', 1)[-1].lower()
        return SimpleNamespace(
            can_claim=domain != self.blocked_domain,
            reason='domain_policy_max_per_minute' if domain == self.blocked_domain else None,
            domain=domain,
            domain_policy_id=uuid4() if domain == self.blocked_domain else None,
        )


def test_delivery_service_claim_records_skips_throttled_domains() -> None:
    db = FakeDb()
    blocked = EmailSendRecord(
        id=uuid4(),
        send_job_id=uuid4(),
        contact_id=uuid4(),
        template_id=uuid4(),
        status=EmailSendStatus.queued,
        to_email='blocked@gmail.com',
        variables={},
    )
    allowed = EmailSendRecord(
        id=uuid4(),
        send_job_id=uuid4(),
        contact_id=uuid4(),
        template_id=uuid4(),
        status=EmailSendStatus.queued,
        to_email='allowed@example.com',
        variables={},
    )
    db.records = [blocked, allowed]
    service = DeliveryService.__new__(DeliveryService)
    service.db = db
    service.route_service = SelectiveRouteService('gmail.com')

    claim_result = service._claim_records(limit=10)

    assert claim_result.records == [allowed]
    assert claim_result.skipped_record_ids == [str(blocked.id)]
    assert blocked.status == EmailSendStatus.queued
    assert allowed.status == EmailSendStatus.sending
    assert len(db.added) == 1
    assert db.added[0].send_record_id == blocked.id
    assert db.added[0].status == 'claim_blocked'
    assert db.added[0].route_type == 'queue_control'
    assert db.added[0].route_key == 'domain_policy_max_per_minute'
    assert db.added[0].metadata_json['reason'] == 'domain_policy_max_per_minute'
    assert db.flush_count == 1


def test_delivery_service_starts_attempt_with_route_context() -> None:
    db = FakeDb()
    service = DeliveryService.__new__(DeliveryService)
    service.db = db
    service.settings = SimpleNamespace(email_provider='console')
    service.route_service = FakeRouteService()
    record = EmailSendRecord(
        id=uuid4(),
        send_job_id=uuid4(),
        contact_id=uuid4(),
        template_id=uuid4(),
        status=EmailSendStatus.sending,
        to_email='recipient@example.com',
        variables={},
        attempt_count=2,
    )

    attempt = service._start_attempt(record)

    assert db.added == [attempt]
    assert db.flush_count == 1
    assert attempt.send_record_id == record.id
    assert attempt.send_job_id == record.send_job_id
    assert attempt.attempt_number == 2
    assert attempt.route_type == 'console'
    assert attempt.route_key == 'console'
    assert attempt.status == 'submitting'
    assert attempt.metadata_json['route_source'] == 'settings'
    assert attempt.metadata_json['to_domain'] == 'example.com'


def test_delivery_service_marks_retryable_failure_attempt_deferred() -> None:
    service = DeliveryService.__new__(DeliveryService)
    record = EmailSendRecord(
        id=uuid4(),
        send_job_id=uuid4(),
        contact_id=uuid4(),
        template_id=uuid4(),
        status=EmailSendStatus.sending,
        to_email='recipient@example.com',
        variables={},
        attempt_count=1,
        max_attempts=3,
    )
    attempt = SimpleNamespace(
        status='submitting',
        provider=None,
        provider_message_id=None,
        smtp_response_code=None,
        smtp_response=None,
        error_message=None,
        metadata_json={},
        completed_at=None,
    )

    service._handle_failure(record, attempt, 'temporary provider failure')

    assert record.status == EmailSendStatus.deferred
    assert record.next_attempt_at is not None
    assert attempt.status == 'deferred'
    assert attempt.error_message == 'temporary provider failure'
    assert 'next_attempt_at' in attempt.metadata_json


def test_delivery_service_marks_terminal_failure_attempt_failed() -> None:
    service = DeliveryService.__new__(DeliveryService)
    record = EmailSendRecord(
        id=uuid4(),
        send_job_id=uuid4(),
        contact_id=uuid4(),
        template_id=uuid4(),
        status=EmailSendStatus.sending,
        to_email='recipient@example.com',
        variables={},
        attempt_count=3,
        max_attempts=3,
    )
    attempt = SimpleNamespace(
        status='submitting',
        provider=None,
        provider_message_id=None,
        smtp_response_code=None,
        smtp_response=None,
        error_message=None,
        metadata_json={},
        completed_at=None,
    )

    service._handle_failure(record, attempt, 'permanent provider failure')

    assert record.status == EmailSendStatus.failed
    assert record.next_attempt_at is None
    assert attempt.status == 'failed'
    assert attempt.error_message == 'permanent provider failure'
