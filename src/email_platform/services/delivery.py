from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from email_platform.core.settings import Settings
from email_platform.models.entities import EmailEventType, EmailSendRecord, EmailSendStatus
from email_platform.providers.email import EmailMessage, build_email_provider
from email_platform.schemas.contracts import DeliveryRunRead, EventCreate
from email_platform.services.events import EventService
from email_platform.services.templates import TemplateService


class DeliveryService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.provider = build_email_provider(settings)
        self.event_service = EventService(db)
        self.template_service = TemplateService(db)

    def process_queued(
        self,
        limit: int = 25,
        campaign_id: UUID | None = None,
        send_job_id: UUID | None = None,
    ) -> DeliveryRunRead:
        records = self._claim_records(limit, campaign_id=campaign_id, send_job_id=send_job_id)
        sent_count = 0
        failed_count = 0
        processed_ids: list[str] = []

        for record in records:
            processed_ids.append(str(record.id))
            record.attempt_count += 1
            template = self.template_service.get(record.template_id)
            if not template:
                self._handle_failure(record, 'Template not found')
                failed_count += 1
                continue

            try:
                subject, html, text = self.template_service.render(template, record.variables)
                result = self.provider.send(
                    EmailMessage(
                        to_email=record.to_email,
                        from_email=str(self.settings.default_from_email),
                        subject=subject,
                        html_body=html,
                        text_body=text,
                    )
                )
                record.status = EmailSendStatus.sent
                record.provider = result.provider
                record.provider_message_id = result.provider_message_id
                record.error_message = None
                record.next_attempt_at = None
                sent_count += 1
                self.event_service.record_no_commit(
                    EventCreate(
                        send_record_id=record.id,
                        send_job_id=record.send_job_id,
                        contact_id=record.contact_id,
                        campaign_id=record.campaign_id,
                        event_type=EmailEventType.sent,
                        provider_message_id=result.provider_message_id,
                        metadata_json={
                            'provider': result.provider,
                            'status_code': result.status_code,
                            'send_record_id': str(record.id),
                            'send_job_id': str(record.send_job_id),
                            'source': 'delivery_worker',
                        },
                    )
                )
            except Exception as exc:  # noqa: BLE001
                self._handle_failure(record, str(exc))
                failed_count += 1

        self.db.commit()
        return DeliveryRunRead(
            claimed_count=len(records),
            sent_count=sent_count,
            failed_count=failed_count,
            processed_record_ids=processed_ids,
        )

    def _claim_records(
        self,
        limit: int,
        campaign_id: UUID | None = None,
        send_job_id: UUID | None = None,
    ) -> list[EmailSendRecord]:
        statement = (
            select(EmailSendRecord)
            .where(EmailSendRecord.status == EmailSendStatus.queued)
            .where(
                (EmailSendRecord.next_attempt_at.is_(None))
                | (EmailSendRecord.next_attempt_at <= datetime.utcnow())
            )
            .order_by(EmailSendRecord.created_at.asc())
            .limit(limit)
        )
        if campaign_id:
            statement = statement.where(EmailSendRecord.campaign_id == campaign_id)
        if send_job_id:
            statement = statement.where(EmailSendRecord.send_job_id == send_job_id)
        records = list(self.db.scalars(statement).all())
        for record in records:
            record.status = EmailSendStatus.sending
        self.db.flush()
        return records

    def _handle_failure(self, record: EmailSendRecord, message: str) -> None:
        record.error_message = message
        if record.attempt_count >= record.max_attempts:
            record.status = EmailSendStatus.failed
            record.next_attempt_at = None
            return
        record.status = EmailSendStatus.queued
        record.next_attempt_at = datetime.utcnow() + self._retry_delay(record.attempt_count)

    def _retry_delay(self, attempt_count: int) -> timedelta:
        return timedelta(minutes=min(60, 2 ** max(attempt_count - 1, 0)))
