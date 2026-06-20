from collections.abc import Mapping
from urllib.parse import quote
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from email_platform.core.settings import Settings
from email_platform.models.entities import (
    Campaign,
    CampaignSendJob,
    Contact,
    DeliveryAttempt,
    EmailEventType,
    EmailSendRecord,
    EmailSendStatus,
    SendJobStatus,
)
from email_platform.providers.email import EmailMessage, build_email_provider
from email_platform.schemas.contracts import EventCreate
from email_platform.services.contacts import ContactService
from email_platform.services.delivery import DeliveryService
from email_platform.services.events import EventService
from email_platform.services.suppressions import SuppressionService
from email_platform.services.templates import TemplateService
from email_platform.services.tracking import TrackingService


class SendingService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.provider = build_email_provider(settings)
        self.contact_service = ContactService(db)
        self.event_service = EventService(db)
        self.suppression_service = SuppressionService(db)
        self.template_service = TemplateService(db)

    def send_test(
        self, template_id: UUID, to_email: str, variables: Mapping[str, object]
    ) -> dict[str, str | int | None]:
        template = self.template_service.get(template_id)
        if not template:
            raise ValueError('Template not found')
        context = self._template_test_context(template_id, variables)
        subject, html, text = self.template_service.render(template, context)
        result = self.provider.send(
            EmailMessage(
                to_email=to_email,
                from_email=str(self.settings.default_from_email),
                subject=subject,
                html_body=html,
                text_body=text,
            )
        )
        return {
            'provider': result.provider,
            'provider_message_id': result.provider_message_id,
            'status_code': result.status_code,
            'subject': subject,
            'html_body': html,
            'text_body': text,
            'variables': context,
        }

    def send_campaign_test(
        self, campaign_id: UUID, to_email: str, variables: Mapping[str, object]
    ) -> dict[str, object]:
        campaign = self.db.get(Campaign, campaign_id)
        if not campaign:
            raise ValueError('Campaign not found')
        template = self.template_service.get(campaign.template_id)
        if not template:
            raise ValueError('Template not found')
        contact = self._test_contact(to_email, variables)
        if contact.is_unsubscribed:
            raise PermissionError('Contact is unsubscribed')
        if self.suppression_service.is_suppressed(contact.email):
            raise PermissionError('Contact is suppressed')

        context = self._campaign_test_context(campaign, variables)
        job = CampaignSendJob(
            campaign_id=campaign.id,
            status=SendJobStatus.queued,
            requested_count=1,
            queued_count=1,
            suppressed_count=0,
            metadata_json={'source': 'campaign_test_send', 'to_email': to_email},
        )
        self.db.add(job)
        self.db.flush()

        record = EmailSendRecord(
            campaign_id=campaign.id,
            send_job_id=job.id,
            contact_id=contact.id,
            template_id=template.id,
            status=EmailSendStatus.queued,
            to_email=to_email,
            variables=context,
            attempt_count=0,
            max_attempts=1,
        )
        self.db.add(record)
        self.db.flush()

        tracked_context = self._tracked_variables(record)
        record.variables = tracked_context
        subject, html, text = self.template_service.render(template, tracked_context)
        job.status = SendJobStatus.processing
        delivery = DeliveryService(self.db, self.settings).process_queued(
            limit=1,
            send_job_id=job.id,
        )
        self.db.refresh(record)
        self.db.refresh(job)
        attempt = self._latest_delivery_attempt(record)
        if delivery.sent_count != 1 or record.status not in {
            EmailSendStatus.submitted,
            EmailSendStatus.sent,
            EmailSendStatus.delivered,
        }:
            job.status = SendJobStatus.failed
            self.db.commit()
            return self._campaign_test_send_response(
                campaign=campaign,
                template=template,
                job=job,
                record=record,
                contact=contact,
                to_email=to_email,
                subject=subject,
                html=html,
                text=text,
                variables=tracked_context,
                attempt=attempt,
                fallback_status_code=500,
            )
        job.status = SendJobStatus.completed
        self.db.commit()
        self.db.refresh(record)
        self.db.refresh(job)
        return self._campaign_test_send_response(
            campaign=campaign,
            template=template,
            job=job,
            record=record,
            contact=contact,
            to_email=to_email,
            subject=subject,
            html=html,
            text=text,
            variables=tracked_context,
            attempt=attempt,
            fallback_status_code=250,
        )

    def _campaign_test_send_response(
        self,
        *,
        campaign: Campaign,
        template,
        job: CampaignSendJob,
        record: EmailSendRecord,
        contact: Contact,
        to_email: str,
        subject: str,
        html: str,
        text: str | None,
        variables: dict[str, object],
        attempt: DeliveryAttempt | None,
        fallback_status_code: int,
    ) -> dict[str, object]:
        attempt_metadata = attempt.metadata_json if attempt else {}
        smtp_response_code = attempt.smtp_response_code if attempt else None
        route_resolved = attempt_metadata.get('mta_route_resolved')
        if route_resolved is True:
            mta_route_status = 'resolved'
        elif route_resolved is False:
            mta_route_status = 'blocked'
        elif attempt:
            mta_route_status = 'attempted'
        else:
            mta_route_status = 'not_attempted'
        return {
            'provider': record.provider or (attempt.route_type if attempt else None) or 'delivery_worker',
            'provider_message_id': record.provider_message_id,
            'status_code': smtp_response_code or fallback_status_code,
            'campaign_id': campaign.id,
            'template_id': template.id,
            'send_job_id': job.id,
            'send_record_id': record.id,
            'delivery_attempt_id': attempt.id if attempt else None,
            'contact_id': contact.id,
            'send_job_status': job.status.value,
            'send_record_status': record.status.value,
            'subject': subject,
            'html_body': html,
            'text_body': text,
            'variables': variables,
            'tracking_open_url': variables.get('tracking_open'),
            'tracking_click_base': variables.get('tracking_click_base'),
            'unsubscribe_url': variables.get('unsubscribe_url'),
            'to_email': to_email,
            'route_type': attempt.route_type if attempt else None,
            'route_key': attempt.route_key if attempt else None,
            'mta_provider': attempt_metadata.get('mta_provider'),
            'mta_route_domain': attempt_metadata.get('mta_route_domain'),
            'mta_route_sender_domain': attempt_metadata.get('mta_route_sender_domain'),
            'mta_route_recipient_domain': attempt_metadata.get('mta_route_recipient_domain'),
            'mta_route_send_type': attempt_metadata.get('mta_route_send_type'),
            'mta_route_decision_basis': attempt_metadata.get('mta_route_decision_basis'),
            'mta_routing_rule_name': attempt_metadata.get('mta_routing_rule_name'),
            'mta_routing_rule_source': attempt_metadata.get('mta_routing_rule_source'),
            'mta_preferred_providers': attempt_metadata.get('mta_preferred_providers'),
            'mta_rule_hit_send_type': attempt_metadata.get('mta_rule_hit_send_type'),
            'mta_rule_hit_sender_domain': attempt_metadata.get('mta_rule_hit_sender_domain'),
            'mta_rule_hit_recipient_domain': attempt_metadata.get('mta_rule_hit_recipient_domain'),
            'mta_rule_hit_name': attempt_metadata.get('mta_rule_hit_name'),
            'mta_rule_hit_source': attempt_metadata.get('mta_rule_hit_source'),
            'mta_rule_hit_pool_source': attempt_metadata.get('mta_rule_hit_pool_source'),
            'mta_rule_hit_provider_preference': attempt_metadata.get(
                'mta_rule_hit_provider_preference'
            ),
            'mta_node_name': attempt_metadata.get('mta_node_name'),
            'mta_node_selection_membership_id': attempt_metadata.get(
                'mta_node_selection_membership_id'
            ),
            'mta_node_selection_priority': attempt_metadata.get('mta_node_selection_priority'),
            'mta_node_selection_weight': attempt_metadata.get('mta_node_selection_weight'),
            'mta_node_candidate_count': attempt_metadata.get('mta_node_candidate_count'),
            'mta_node_skipped_count': attempt_metadata.get('mta_node_skipped_count'),
            'mta_node_skipped_nodes': attempt_metadata.get('mta_node_skipped_nodes'),
            'mta_hostname': attempt_metadata.get('mta_hostname'),
            'mta_public_ipv4': attempt_metadata.get('mta_public_ipv4'),
            'mta_submission_host': attempt_metadata.get('mta_submission_host'),
            'mta_submission_port': attempt_metadata.get('mta_submission_port'),
            'mta_ip_pool_name': attempt_metadata.get('mta_ip_pool_name'),
            'mta_ip_pool_selection_source': attempt_metadata.get('mta_ip_pool_selection_source'),
            'mta_route_resolved': attempt_metadata.get('mta_route_resolved'),
            'mta_route_status': mta_route_status,
            'mta_route_block_code': attempt_metadata.get('mta_route_block_code'),
            'mta_route_block_message': attempt_metadata.get('mta_route_block_message'),
            'envelope_from': attempt_metadata.get('envelope_from'),
            'bounce_domain': attempt_metadata.get('bounce_domain'),
            'dkim_selector': attempt_metadata.get('dkim_selector'),
            'dkim_signing_ready': attempt_metadata.get('dkim_signing_ready'),
            'smtp_response_code': attempt.smtp_response_code if attempt else None,
            'smtp_response': attempt.smtp_response if attempt else None,
            'delivery_error_message': record.error_message
            or (attempt.error_message if attempt else None),
        }

    def preview_campaign_test(
        self, campaign_id: UUID, variables: Mapping[str, object]
    ) -> dict[str, object]:
        campaign = self.db.get(Campaign, campaign_id)
        if not campaign:
            raise ValueError('Campaign not found')
        template = self.template_service.get(campaign.template_id)
        if not template:
            raise ValueError('Template not found')

        context = self._campaign_test_context(campaign, variables)
        subject, html, text = self.template_service.render(template, context)
        return {
            'campaign_id': campaign.id,
            'template_id': template.id,
            'subject': subject,
            'html_body': html,
            'text_body': text,
            'variables': context,
        }

    def _campaign_test_context(
        self, campaign: Campaign, variables: Mapping[str, object]
    ) -> dict[str, object]:
        template_variables = self.template_service.variables_for_template(campaign.template_id)
        return {
            **(template_variables.sample_variables if template_variables else {}),
            **variables,
        }

    def _template_test_context(
        self, template_id: UUID, variables: Mapping[str, object]
    ) -> dict[str, object]:
        template_variables = self.template_service.variables_for_template(template_id)
        return {
            **(template_variables.sample_variables if template_variables else {}),
            **variables,
        }

    def _test_contact(self, to_email: str, variables: Mapping[str, object]) -> Contact:
        contact = self.db.scalar(select(Contact).where(Contact.email == to_email))
        if contact:
            return contact
        contact = Contact(
            email=to_email,
            first_name=(
                variables.get('first_name')
                if isinstance(variables.get('first_name'), str)
                else None
            ),
            last_name=(
                variables.get('last_name')
                if isinstance(variables.get('last_name'), str)
                else None
            ),
            source='campaign_test_send',
            attributes={'source': 'campaign_test_send'},
        )
        self.db.add(contact)
        self.db.flush()
        return contact

    def _tracked_variables(self, record: EmailSendRecord) -> dict[str, object]:
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
        unsubscribe_token = self.contact_service.build_unsubscribe_token(
            record.contact_id,
            self.settings,
        )
        variables['unsubscribe_url'] = f'{base_url}/api/v1/unsubscribe/{unsubscribe_token}'
        return variables

    def _latest_delivery_attempt(self, record: EmailSendRecord) -> DeliveryAttempt | None:
        return self.db.scalar(
            select(DeliveryAttempt)
            .where(DeliveryAttempt.send_record_id == record.id)
            .order_by(DeliveryAttempt.started_at.desc())
            .limit(1)
        )

    def send_email_to_contact(
        self,
        contact_id: UUID,
        template_id: UUID,
        variables: Mapping[str, object],
        campaign_id: UUID | None = None,
    ) -> dict[str, str | int | UUID | None]:
        contact = self.contact_service.get(contact_id)
        if not contact:
            raise ValueError('Contact not found')
        if contact.is_unsubscribed:
            raise PermissionError('Contact is unsubscribed')
        if self.suppression_service.is_suppressed(contact.email):
            raise PermissionError('Contact is suppressed')

        template = self.template_service.get(template_id)
        if not template:
            raise ValueError('Template not found')

        context = {
            'email': contact.email,
            'first_name': contact.first_name,
            'last_name': contact.last_name,
            'source': contact.source,
            'attributes': contact.attributes,
            **contact.attributes,
            **variables,
        }
        subject, html, text = self.template_service.render(template, context)
        result = self.provider.send(
            EmailMessage(
                to_email=contact.email,
                from_email=str(self.settings.default_from_email),
                subject=subject,
                html_body=html,
                text_body=text,
            )
        )
        self.event_service.record(
            EventCreate(
                contact_id=contact.id,
                campaign_id=campaign_id,
                event_type=EmailEventType.sent,
                provider_message_id=result.provider_message_id,
                metadata_json={
                    'provider': result.provider,
                    'status_code': result.status_code,
                    'template_id': str(template.id),
                    'source': 'send_email_to_contact',
                },
            )
        )
        return {
            'provider': result.provider,
            'provider_message_id': result.provider_message_id,
            'status_code': result.status_code,
            'contact_id': contact.id,
            'template_id': template.id,
            'campaign_id': campaign_id,
        }
