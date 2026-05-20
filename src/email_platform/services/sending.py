from uuid import UUID

from sqlalchemy.orm import Session

from email_platform.core.settings import Settings
from email_platform.providers.email import EmailMessage, build_email_provider
from email_platform.services.templates import TemplateService


class SendingService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.provider = build_email_provider(settings)
        self.template_service = TemplateService(db)

    def send_test(self, template_id: UUID, to_email: str, variables: dict) -> dict:
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
