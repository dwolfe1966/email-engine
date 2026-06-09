from dataclasses import dataclass
from datetime import datetime, timedelta
from urllib.parse import quote
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from email_platform.core.settings import Settings
from email_platform.models.entities import (
    DeliveryAttempt,
    EmailEventType,
    EmailSendRecord,
    EmailSendStatus,
)
from email_platform.providers.email import EmailMessage, build_email_provider
from email_platform.schemas.contracts import DeliveryRunRead, EventCreate
from email_platform.services.contacts import ContactService
from email_platform.services.delivery_routes import DeliveryRouteService
from email_platform.services.events import EventService
from email_platform.services.templates import TemplateService
from email_platform.services.tracking import TrackingService


@dataclass(frozen=True)
class DeliveryClaimResult:
    records: list[EmailSendRecord]
    skipped_record_ids: list[str]


class DeliveryService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.provider = build_email_provider(settings)
        self.route_service = DeliveryRouteService(db)
        self.event_service = EventService(db)
        self.template_service = TemplateService(db)

    def process_queued(
        self,
        limit: int = 25,
        campaign_id: UUID | None = None,
        send_job_id: UUID | None = None,
    ) -> DeliveryRunRead:
        claim_result = self._claim_records(
            limit,
            campaign_id=campaign_id,
            send_job_id=send_job_id,
        )
        records = claim_result.records
        sent_count = 0
        failed_count = 0
        processed_ids: list[str] = []

        for record in records:
            processed_ids.append(str(record.id))
            record.attempt_count += 1
            attempt = self._start_attempt(record)
            template = self.template_service.get(record.template_id)
            if not template:
                self._handle_failure(record, attempt, 'Template not found')
                failed_count += 1
                continue

            try:
                variables = self._delivery_variables(record)
                subject, html, text = self.template_service.render(template, variables)
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
                self._complete_attempt(
                    attempt,
                    status='submitted',
                    provider=result.provider,
                    provider_message_id=result.provider_message_id,
                    smtp_response_code=result.status_code,
                    smtp_response=f'Provider accepted message with status {result.status_code}',
                    metadata_json={'status_code': result.status_code},
                )
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
                self._handle_failure(record, attempt, str(exc))
                failed_count += 1

        self.db.commit()
        return DeliveryRunRead(
            claimed_count=len(records),
            sent_count=sent_count,
            failed_count=failed_count,
            processed_record_ids=processed_ids,
            skipped_count=len(claim_result.skipped_record_ids),
            skipped_record_ids=claim_result.skipped_record_ids,
        )

    def _delivery_variables(self, record: EmailSendRecord) -> dict[str, object]:
        base_url = self.settings.public_base_url.rstrip('/')
        token = TrackingService(self.db, self.settings.unsubscribe_secret).create_token(record.id)
        click_target = f'{base_url}/'
        variables = {
            **record.variables,
            'tracking_open': f'{base_url}/api/v1/tracking/open/{token}',
            'tracking_click': (
                f'{base_url}/api/v1/tracking/click/{token}'
                f'?url={quote(click_target, safe="")}'
            ),
            'tracking_click_base': f'{base_url}/api/v1/tracking/click/{token}',
        }
        if record.contact_id:
            unsubscribe_token = ContactService(self.db).build_unsubscribe_token(
                record.contact_id,
                self.settings,
            )
            variables['unsubscribe_url'] = f'{base_url}/api/v1/unsubscribe/{unsubscribe_token}'
        return variables

    def _claim_records(
        self,
        limit: int,
        campaign_id: UUID | None = None,
        send_job_id: UUID | None = None,
    ) -> DeliveryClaimResult:
        statement = (
            select(EmailSendRecord)
            .where(EmailSendRecord.status == EmailSendStatus.queued)
            .where(
                (EmailSendRecord.next_attempt_at.is_(None))
                | (EmailSendRecord.next_attempt_at <= datetime.utcnow())
            )
            .order_by(EmailSendRecord.created_at.asc())
            .limit(max(limit * 5, limit))
        )
        if campaign_id:
            statement = statement.where(EmailSendRecord.campaign_id == campaign_id)
        if send_job_id:
            statement = statement.where(EmailSendRecord.send_job_id == send_job_id)
        candidates = list(self.db.scalars(statement).all())
        records: list[EmailSendRecord] = []
        skipped_record_ids: list[str] = []
        reserved_by_domain: dict[str, int] = {}
        for record in candidates:
            domain = record.to_email.rsplit('@', 1)[-1].lower() if '@' in record.to_email else ''
            reserved_count = reserved_by_domain.get(domain, 0)
            decision = self.route_service.claim_decision(record, reserved_count=reserved_count)
            if not decision.can_claim:
                skipped_record_ids.append(str(record.id))
                self._record_claim_block(record, decision, reserved_count=reserved_count)
                continue
            records.append(record)
            if decision.domain:
                reserved_by_domain[decision.domain] = reserved_by_domain.get(decision.domain, 0) + 1
            if len(records) >= limit:
                break

        for record in records:
            record.status = EmailSendStatus.sending
        self.db.flush()
        return DeliveryClaimResult(records=records, skipped_record_ids=skipped_record_ids)

    def _record_claim_block(
        self,
        record: EmailSendRecord,
        decision,
        reserved_count: int,
    ) -> DeliveryAttempt:
        metadata_json: dict[str, object] = {
            'source': 'delivery_claim',
            'reason': decision.reason,
            'to_domain': decision.domain,
            'reserved_count': reserved_count,
        }
        if decision.domain_policy_id:
            metadata_json['domain_delivery_policy_id'] = str(decision.domain_policy_id)
        attempt = DeliveryAttempt(
            send_record_id=record.id,
            send_job_id=record.send_job_id,
            campaign_id=record.campaign_id,
            attempt_number=record.attempt_count,
            provider=record.provider,
            route_type='queue_control',
            route_key=decision.reason or 'not_claimed',
            status='claim_blocked',
            error_message=decision.reason,
            metadata_json=metadata_json,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )
        self.db.add(attempt)
        return attempt

    def _start_attempt(self, record: EmailSendRecord) -> DeliveryAttempt:
        selected_route = self.route_service.select_for_record(record, self.settings)
        metadata_json: dict[str, object] = {
            'email_provider': self.settings.email_provider,
            'route_source': selected_route.source,
            'to_domain': record.to_email.rsplit('@', 1)[-1].lower()
            if '@' in record.to_email
            else None,
        }
        if selected_route.route_id:
            metadata_json['delivery_route_id'] = str(selected_route.route_id)
        if selected_route.domain_policy_id:
            metadata_json['domain_delivery_policy_id'] = str(selected_route.domain_policy_id)
        if selected_route.name:
            metadata_json['delivery_route_name'] = selected_route.name
        if selected_route.warmup_stage:
            metadata_json['warmup_stage'] = selected_route.warmup_stage
        if selected_route.max_per_minute is not None:
            metadata_json['max_per_minute'] = selected_route.max_per_minute
        if selected_route.max_concurrent is not None:
            metadata_json['max_concurrent'] = selected_route.max_concurrent
        attempt = DeliveryAttempt(
            send_record_id=record.id,
            send_job_id=record.send_job_id,
            campaign_id=record.campaign_id,
            attempt_number=record.attempt_count,
            provider=record.provider,
            route_type=selected_route.route_type,
            route_key=selected_route.route_key,
            status='submitting',
            metadata_json=metadata_json,
            started_at=datetime.utcnow(),
        )
        self.db.add(attempt)
        self.db.flush()
        return attempt

    def _complete_attempt(
        self,
        attempt: DeliveryAttempt,
        *,
        status: str,
        provider: str | None = None,
        provider_message_id: str | None = None,
        smtp_response_code: int | None = None,
        smtp_response: str | None = None,
        error_message: str | None = None,
        metadata_json: dict[str, object] | None = None,
    ) -> None:
        attempt.status = status
        attempt.provider = provider
        attempt.provider_message_id = provider_message_id
        attempt.smtp_response_code = smtp_response_code
        attempt.smtp_response = smtp_response
        attempt.error_message = error_message
        attempt.metadata_json = {**attempt.metadata_json, **(metadata_json or {})}
        attempt.completed_at = datetime.utcnow()

    def _handle_failure(
        self,
        record: EmailSendRecord,
        attempt: DeliveryAttempt,
        message: str,
    ) -> None:
        record.error_message = message
        if record.attempt_count >= record.max_attempts:
            record.status = EmailSendStatus.failed
            record.next_attempt_at = None
            self._complete_attempt(
                attempt,
                status='failed',
                provider=record.provider,
                provider_message_id=record.provider_message_id,
                error_message=message,
            )
            return
        record.status = EmailSendStatus.queued
        record.next_attempt_at = datetime.utcnow() + self._retry_delay(record.attempt_count)
        self._complete_attempt(
            attempt,
            status='deferred',
            provider=record.provider,
            provider_message_id=record.provider_message_id,
            error_message=message,
            metadata_json={'next_attempt_at': record.next_attempt_at.isoformat()},
        )

    def _retry_delay(self, attempt_count: int) -> timedelta:
        return timedelta(minutes=min(60, 2 ** max(attempt_count - 1, 0)))
