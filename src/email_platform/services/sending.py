from collections.abc import Mapping
from uuid import UUID

from sqlalchemy.orm import Session

from email_platform.core.settings import Settings
from email_platform.models.entities import EmailEventType
from email_platform.providers.email import EmailMessage, build_email_provider
from email_platform.schemas.contracts import EventCreate
from email_platform.services.contacts import ContactService
from email_platform.services.events import EventService
from email_platform.services.templates import TemplateService


class SendingService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.provider = build_email_provider(settings)
        self.contact_service = ContactService(db)
        self.event_service = EventService(db)
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

    def send_to_contact(
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
                    'source': 'send_to_contact',
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
