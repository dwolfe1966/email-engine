import smtplib
from dataclasses import dataclass
from datetime import datetime, timedelta
from urllib.parse import quote
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from email_platform.core.settings import Settings
from email_platform.models.entities import (
    CampaignSendJob,
    DeliveryAttempt,
    EmailEventType,
    EmailSendRecord,
    EmailSendStatus,
)
from email_platform.providers.email import EmailMessage, SmtpEmailProvider, build_email_provider
from email_platform.schemas.contracts import (
    DeliveryRunRead,
    EventCreate,
    ManagedSmtpRouteResolveRequest,
)
from email_platform.services.contacts import ContactService
from email_platform.services.delivery_routes import DeliveryRouteService
from email_platform.services.events import EventService
from email_platform.services.managed_smtp_routing import ManagedSmtpRoutingService
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
        self.managed_smtp_routing_service = ManagedSmtpRoutingService(db)
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
            block_reason = self._managed_smtp_submission_block_reason(attempt)
            if block_reason:
                self._handle_failure(record, attempt, block_reason, retryable=False)
                failed_count += 1
                continue
            template = self.template_service.get(record.template_id)
            if not template:
                self._handle_failure(record, attempt, 'Template not found')
                failed_count += 1
                continue

            try:
                variables = self._delivery_variables(record)
                subject, html, text = self.template_service.render(template, variables)
                result = self._submission_provider_for_attempt(attempt).send(
                    EmailMessage(
                        to_email=record.to_email,
                        from_email=str(self.settings.default_from_email),
                        subject=subject,
                        html_body=html,
                        text_body=text,
                        **self._managed_smtp_message_options(record, attempt),
                    )
                )
                record.status = EmailSendStatus.submitted
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
                    metadata_json={
                        'status_code': result.status_code,
                        **self._managed_smtp_event_metadata(attempt),
                    },
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
                            **self._managed_smtp_event_metadata(attempt),
                        },
                    )
                )
            except Exception as exc:  # noqa: BLE001
                self._handle_failure(
                    record,
                    attempt,
                    str(exc),
                    metadata_json=self._smtp_exception_metadata(exc),
                )
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
            .where(EmailSendRecord.status.in_([EmailSendStatus.queued, EmailSendStatus.deferred]))
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
        selected_route = self.route_service.select_for_record(
            record,
            self.settings,
            sender_domain=self._sender_domain(),
        )
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
        if selected_route.route_type == 'managed_smtp':
            metadata_json.update(self._managed_smtp_route_resolution_metadata(record, selected_route))
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

    def _managed_smtp_submission_block_reason(self, attempt: DeliveryAttempt) -> str | None:
        if attempt.route_type != 'managed_smtp':
            return None
        if attempt.metadata_json.get('mta_route_resolved') is True:
            username = getattr(self.settings, 'smtp_username', None)
            password = getattr(self.settings, 'smtp_password', None)
            if not username or not password:
                attempt.metadata_json = {
                    **attempt.metadata_json,
                    'mta_route_block_code': 'MANAGED_SMTP_SUBMISSION_AUTH_MISSING',
                    'mta_route_block_message': (
                        'Managed SMTP submission requires SMTP_USERNAME and SMTP_PASSWORD.'
                    ),
                }
                return (
                    'Managed SMTP route blocked (MANAGED_SMTP_SUBMISSION_AUTH_MISSING): '
                    'Managed SMTP submission requires SMTP_USERNAME and SMTP_PASSWORD.'
                )
            return None
        if attempt.metadata_json.get('mta_route_resolved') is not False:
            return None
        code = str(attempt.metadata_json.get('mta_route_block_code') or 'UNKNOWN')
        message = str(
            attempt.metadata_json.get('mta_route_block_message')
            or 'Managed SMTP route is not ready for submission.'
        )
        return f'Managed SMTP route blocked ({code}): {message}'

    def _managed_smtp_route_resolution_metadata(self, record, selected_route) -> dict[str, object]:
        resolver = getattr(self, 'managed_smtp_routing_service', None)
        if not resolver:
            return {}
        result = resolver.resolve(
            ManagedSmtpRouteResolveRequest(
                from_domain=self._sender_domain(),
                recipient_domain=self._recipient_domain(record),
                route_id=selected_route.route_id,
                send_type=self._send_type_for_record(record),
            )
        )
        if not result.ok or not result.route:
            reason = result.reason
            return {
                'mta_route_resolved': False,
                'mta_route_block_code': reason.code if reason else 'UNKNOWN',
                'mta_route_block_message': reason.message if reason else 'No reason returned.',
                'mta_route_block_details': reason.details if reason else {},
            }
        route = result.route
        return {
            'mta_route_resolved': True,
            'mta_route_domain': route.domain,
            'mta_route_sender_domain': route.sender_domain,
            'mta_route_recipient_domain': route.recipient_domain,
            'mta_route_send_type': route.send_type,
            'mta_route_decision_basis': route.decision_basis,
            'mta_routing_rule_name': route.routing_rule_name,
            'mta_routing_rule_source': route.routing_rule_source,
            'mta_preferred_providers': route.preferred_providers,
            'mta_rule_hit_send_type': route.send_type,
            'mta_rule_hit_sender_domain': route.sender_domain,
            'mta_rule_hit_recipient_domain': route.recipient_domain,
            'mta_rule_hit_name': route.routing_rule_name,
            'mta_rule_hit_source': route.routing_rule_source,
            'mta_rule_hit_pool_source': route.routing_rule_pool_source,
            'mta_rule_hit_provider_preference': route.routing_rule_provider_preference,
            'mta_provider_account_id': str(route.provider_account_id),
            'mta_provider': route.provider.value,
            'mta_ip_pool_id': str(route.ip_pool_id),
            'mta_ip_pool_name': route.ip_pool_name,
            'mta_ip_pool_type': route.ip_pool_type.value,
            'mta_ip_pool_selection_source': route.ip_pool_selection_source,
            'mta_node_id': str(route.mta_node_id),
            'mta_node_name': route.mta_node_name,
            'mta_node_selection_priority': route.mta_node_selection_priority,
            'mta_node_selection_weight': route.mta_node_selection_weight,
            'mta_node_candidate_count': route.mta_node_candidate_count,
            'mta_node_skipped_count': route.mta_node_skipped_count,
            'mta_hostname': route.hostname,
            'mta_public_ipv4': route.public_ipv4,
            'mta_submission_host': route.submission_host,
            'mta_submission_port': route.submission_port,
            'mta_auth_secret_ref': route.auth_secret_ref,
        }

    def _send_type_for_record(self, record: EmailSendRecord) -> str:
        if not record.send_job_id:
            return 'transactional'
        job = self.db.get(CampaignSendJob, record.send_job_id)
        metadata = job.metadata_json if job else {}
        if isinstance(metadata, dict):
            configured = metadata.get('send_type')
            if configured:
                return str(configured)
            if metadata.get('source') == 'campaign_test_send':
                return 'internal_test'
        return 'campaign' if record.campaign_id else 'transactional'

    def _managed_smtp_message_options(
        self,
        record: EmailSendRecord,
        attempt: DeliveryAttempt,
    ) -> dict[str, object]:
        if attempt.route_type != 'managed_smtp':
            return {}
        identity = self.route_service.managed_smtp_identity_for_record(
            record,
            sender_domain=self._sender_domain(),
        )
        if not identity:
            return {}
        headers: dict[str, str] = {
            'X-Email-Engine-Route': 'managed_smtp',
            'X-Email-Engine-Domain': identity.domain,
        }
        metadata_json: dict[str, object] = {
            'managed_smtp_domain': identity.domain,
            'dkim_signing_ready': identity.dkim_signing_ready,
        }
        if identity.bounce_domain:
            headers['X-Email-Engine-Bounce-Domain'] = identity.bounce_domain
            metadata_json['bounce_domain'] = identity.bounce_domain
        if identity.envelope_from:
            metadata_json['envelope_from'] = identity.envelope_from
        if identity.dkim_selector:
            headers['X-Email-Engine-DKIM-Selector'] = identity.dkim_selector
            metadata_json['dkim_selector'] = identity.dkim_selector
        if identity.dkim_key_ref:
            headers['X-Email-Engine-DKIM-Key-Ref'] = identity.dkim_key_ref
            metadata_json['dkim_key_ref'] = identity.dkim_key_ref
        attempt.metadata_json = {**attempt.metadata_json, **metadata_json}
        return {
            'envelope_from': identity.envelope_from,
            'headers': headers,
        }

    def _managed_smtp_event_metadata(self, attempt: DeliveryAttempt) -> dict[str, object]:
        keys = {
            'managed_smtp_domain',
            'bounce_domain',
            'envelope_from',
            'dkim_selector',
            'dkim_key_ref',
            'dkim_signing_ready',
            'mta_route_resolved',
            'mta_route_block_code',
            'mta_route_block_message',
            'mta_route_domain',
            'mta_route_sender_domain',
            'mta_route_recipient_domain',
            'mta_route_send_type',
            'mta_route_decision_basis',
            'mta_routing_rule_name',
            'mta_routing_rule_source',
            'mta_preferred_providers',
            'mta_rule_hit_send_type',
            'mta_rule_hit_sender_domain',
            'mta_rule_hit_recipient_domain',
            'mta_rule_hit_name',
            'mta_rule_hit_source',
            'mta_rule_hit_pool_source',
            'mta_rule_hit_provider_preference',
            'mta_provider_account_id',
            'mta_provider',
            'mta_ip_pool_id',
            'mta_ip_pool_name',
            'mta_ip_pool_type',
            'mta_ip_pool_selection_source',
            'mta_node_id',
            'mta_node_name',
            'mta_node_selection_priority',
            'mta_node_selection_weight',
            'mta_node_candidate_count',
            'mta_node_skipped_count',
            'mta_hostname',
            'mta_public_ipv4',
            'mta_submission_host',
            'mta_submission_port',
            'mta_submission_provider',
        }
        return {key: value for key, value in attempt.metadata_json.items() if key in keys}

    def _sender_domain(self) -> str | None:
        from_email = str(getattr(getattr(self, 'settings', None), 'default_from_email', '') or '')
        if '@' not in from_email:
            return None
        return from_email.rsplit('@', 1)[-1].lower()

    @staticmethod
    def _recipient_domain(record: EmailSendRecord) -> str | None:
        if '@' not in record.to_email:
            return None
        return record.to_email.rsplit('@', 1)[-1].lower()

    def _submission_provider_for_attempt(self, attempt: DeliveryAttempt):
        if attempt.route_type != 'managed_smtp':
            return self.provider
        if attempt.metadata_json.get('mta_route_resolved') is not True:
            return self.provider
        host = attempt.metadata_json.get('mta_submission_host')
        port = attempt.metadata_json.get('mta_submission_port')
        if not host:
            return self.provider
        attempt.metadata_json = {
            **attempt.metadata_json,
            'mta_submission_provider': 'managed_smtp',
        }
        return SmtpEmailProvider(
            self.settings,
            host=str(host),
            port=int(port) if port else None,
            provider_name='managed_smtp',
        )

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
        retryable: bool = True,
        metadata_json: dict[str, object] | None = None,
    ) -> None:
        record.error_message = message
        if not retryable or record.attempt_count >= record.max_attempts:
            record.status = EmailSendStatus.failed
            record.next_attempt_at = None
            self._complete_attempt(
                attempt,
                status='failed',
                provider=record.provider,
                provider_message_id=record.provider_message_id,
                error_message=message,
                metadata_json=metadata_json,
            )
            return
        record.status = EmailSendStatus.deferred
        record.next_attempt_at = datetime.utcnow() + self._retry_delay(record.attempt_count)
        self._complete_attempt(
            attempt,
            status='deferred',
            provider=record.provider,
            provider_message_id=record.provider_message_id,
            error_message=message,
            metadata_json={
                'next_attempt_at': record.next_attempt_at.isoformat(),
                **(metadata_json or {}),
            },
        )

    def _retry_delay(self, attempt_count: int) -> timedelta:
        return timedelta(minutes=min(60, 2 ** max(attempt_count - 1, 0)))

    @staticmethod
    def _smtp_exception_metadata(exc: Exception) -> dict[str, object]:
        if isinstance(exc, smtplib.SMTPRecipientsRefused):
            refused = exc.recipients or {}
            first = next(iter(refused.values()), None)
            if not first:
                return {}
            code, response = first
            return {
                'smtp_response_code': int(code),
                'smtp_response': response.decode('utf-8', errors='replace')
                if isinstance(response, bytes)
                else str(response),
                'smtp_refused_recipients': {
                    email: [
                        int(item[0]),
                        item[1].decode('utf-8', errors='replace')
                        if isinstance(item[1], bytes)
                        else str(item[1]),
                    ]
                    for email, item in refused.items()
                },
            }
        if isinstance(exc, smtplib.SMTPResponseException):
            return {
                'smtp_response_code': int(exc.smtp_code),
                'smtp_response': exc.smtp_error.decode('utf-8', errors='replace')
                if isinstance(exc.smtp_error, bytes)
                else str(exc.smtp_error),
            }
        return {}
