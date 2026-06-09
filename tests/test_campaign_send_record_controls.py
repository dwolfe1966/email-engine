from uuid import uuid4

import pytest

from email_platform.models.entities import EmailSendRecord, EmailSendStatus
from email_platform.services.campaigns import CampaignService


class FakeDb:
    def __init__(self, record=None) -> None:
        self.record = record
        self.added = []
        self.committed = False
        self.refreshed = []

    def get(self, model, item_id):
        return self.record

    def add(self, item) -> None:
        self.added.append(item)

    def commit(self) -> None:
        self.committed = True

    def refresh(self, item) -> None:
        self.refreshed.append(item)


def send_record(status: EmailSendStatus) -> EmailSendRecord:
    return EmailSendRecord(
        id=uuid4(),
        send_job_id=uuid4(),
        contact_id=uuid4(),
        template_id=uuid4(),
        status=status,
        to_email='recipient@example.com',
        variables={},
        attempt_count=2,
    )


def test_dead_letter_send_record_marks_terminal_and_audits_previous_status() -> None:
    record = send_record(EmailSendStatus.failed)
    db = FakeDb(record)
    service = CampaignService.__new__(CampaignService)
    service.db = db

    result = service.dead_letter_send_record(record.id, reason='bad mailbox')

    assert result is record
    assert record.status == EmailSendStatus.dead_lettered
    assert record.next_attempt_at is None
    assert record.error_message == 'bad mailbox'
    assert db.committed
    assert db.refreshed == [record]
    assert len(db.added) == 1
    audit = db.added[0]
    assert audit.send_record_id == record.id
    assert audit.status == 'dead_lettered'
    assert audit.route_type == 'queue_control'
    assert audit.route_key == 'dead_lettered'
    assert audit.metadata_json['previous_status'] == 'failed'
    assert audit.metadata_json['reason'] == 'bad mailbox'


def test_dead_letter_send_record_rejects_sent_or_sending_records() -> None:
    record = send_record(EmailSendStatus.sending)
    db = FakeDb(record)
    service = CampaignService.__new__(CampaignService)
    service.db = db

    with pytest.raises(ValueError, match='cannot be dead-lettered'):
        service.dead_letter_send_record(record.id)

    assert record.status == EmailSendStatus.sending
    assert not db.added
    assert not db.committed


def test_requeue_send_record_can_restore_dead_lettered_record() -> None:
    record = send_record(EmailSendStatus.dead_lettered)
    record.error_message = 'bad mailbox'
    record.provider = 'sendgrid'
    record.provider_message_id = 'msg_123'
    db = FakeDb(record)
    service = CampaignService.__new__(CampaignService)
    service.db = db

    result = service.requeue_send_record(record.id)

    assert result is record
    assert record.status == EmailSendStatus.queued
    assert record.error_message is None
    assert record.provider is None
    assert record.provider_message_id is None
    assert db.committed
