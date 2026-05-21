from collections.abc import Mapping
from uuid import UUID

from jinja2 import Template
from sqlalchemy import select
from sqlalchemy.orm import Session

from email_platform.models.entities import EmailTemplate
from email_platform.schemas.contracts import TemplateCreate


class TemplateService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: TemplateCreate) -> EmailTemplate:
        template = EmailTemplate(**payload.model_dump())
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        return template

    def list(self, limit: int = 100, offset: int = 0) -> list[EmailTemplate]:
        statement = (
            select(EmailTemplate)
            .order_by(EmailTemplate.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.scalars(statement).all())

    def get(self, template_id: UUID) -> EmailTemplate | None:
        return self.db.get(EmailTemplate, template_id)

    def render(
        self, template: EmailTemplate, variables: Mapping[str, object]
    ) -> tuple[str, str, str | None]:
        subject = Template(template.subject).render(**variables)
        html = Template(template.html_body).render(**variables)
        text = Template(template.text_body).render(**variables) if template.text_body else None
        return subject, html, text
