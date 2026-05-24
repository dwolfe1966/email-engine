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
    EmailEventType,
    EmailSendRecord,
    EmailSendStatus,
    SendJobStatus,
)
from email_platform.providers.email import EmailMessage, build_email_provider
from email_platform.schemas.contracts import EventCreate
from email_platform.services.contacts import ContactService
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
        subject, html, text = self.template_service.render(template, variables)
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
            status=SendJobStatus.processing,
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
            status=EmailSendStatus.sending,
            to_email=to_email,
            variables=context,
            attempt_count=1,
            max_attempts=1,
        )
        self.db.add(record)
        self.db.flush()

        tracked_context = self._tracked_variables(record)
        record.variables = tracked_context
        subject, html, text = self.template_service.render(template, tracked_context)
        try:
            result = self.provider.send(
                EmailMessage(
                    to_email=to_email,
                    from_email=str(self.settings.default_from_email),
                    subject=subject,
                    html_body=html,
                    text_body=text,
                )
            )
        except Exception as exc:  # noqa: BLE001
            record.status = EmailSendStatus.failed
            record.error_message = str(exc)
            job.status = SendJobStatus.failed
            self.db.commit()
            raise

        record.status = EmailSendStatus.sent
        record.provider = result.provider
        record.provider_message_id = result.provider_message_id
        record.error_message = None
        record.next_attempt_at = None
        job.status = SendJobStatus.completed
        self.event_service.record_no_commit(
            EventCreate(
                send_record_id=record.id,
                send_job_id=job.id,
                contact_id=contact.id,
                campaign_id=campaign.id,
                event_type=EmailEventType.sent,
                provider_message_id=result.provider_message_id,
                metadata_json={
                    'provider': result.provider,
                    'status_code': result.status_code,
                    'template_id': str(template.id),
                    'to_email': to_email,
                    'subject': subject,
                    'send_record_id': str(record.id),
                    'send_job_id': str(job.id),
                    'source': 'campaign_test_send',
                },
            )
        )
        self.db.commit()
        self.db.refresh(record)
        self.db.refresh(job)
        return {
            'provider': result.provider,
            'provider_message_id': result.provider_message_id,
            'status_code': result.status_code,
            'campaign_id': campaign.id,
            'template_id': template.id,
            'send_job_id': job.id,
            'send_record_id': record.id,
            'contact_id': contact.id,
            'subject': subject,
            'html_body': html,
            'text_body': text,
            'variables': tracked_context,
            'tracking_open_url': tracked_context.get('tracking_open'),
            'tracking_click_base': tracked_context.get('tracking_click_base'),
            'unsubscribe_url': tracked_context.get('unsubscribe_url'),
            'to_email': to_email,
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
