from collections.abc import Mapping
from uuid import UUID

from jinja2 import Template
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from email_platform.models.entities import EmailTemplate
from email_platform.schemas.contracts import (
    TemplateCreate,
    TemplatePreviewRead,
    TemplatePreviewRequest,
    TemplateUpdate,
)


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

    def count(self) -> int:
        return self.db.scalar(select(func.count()).select_from(EmailTemplate)) or 0

    def get(self, template_id: UUID) -> EmailTemplate | None:
        return self.db.get(EmailTemplate, template_id)

    def update(self, template_id: UUID, payload: TemplateUpdate) -> EmailTemplate | None:
        template = self.get(template_id)
        if not template:
            return None
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(template, key, value)
        self.db.commit()
        self.db.refresh(template)
        return template

    def delete(self, template_id: UUID) -> bool:
        template = self.get(template_id)
        if not template:
            return False
        self.db.delete(template)
        self.db.commit()
        return True

    def render(
        self, template: EmailTemplate, variables: Mapping[str, object]
    ) -> tuple[str, str, str | None]:
        subject = Template(template.subject).render(**variables)
        html = Template(template.html_body).render(**variables)
        text = Template(template.text_body).render(**variables) if template.text_body else None
        return subject, html, text

    def preview(self, payload: TemplatePreviewRequest) -> TemplatePreviewRead:
        variables = payload.variables
        return TemplatePreviewRead(
            subject=Template(payload.subject).render(**variables),
            html_body=Template(payload.html_body).render(**variables),
            text_body=Template(payload.text_body).render(**variables)
            if payload.text_body
            else None,
        )
