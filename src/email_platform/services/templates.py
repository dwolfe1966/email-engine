from collections.abc import Mapping
from uuid import UUID

from jinja2 import StrictUndefined, meta
from jinja2.exceptions import TemplateError
from jinja2.sandbox import SandboxedEnvironment
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from email_platform.models.entities import EmailTemplate
from email_platform.schemas.contracts import (
    TemplateCreate,
    TemplatePreviewRead,
    TemplatePreviewRequest,
    TemplateUpdate,
    TemplateValidationRead,
    TemplateValidationRequest,
)

template_environment = SandboxedEnvironment(autoescape=False, undefined=StrictUndefined)


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
        subject = self._render_source(template.subject, variables)
        html = self._render_source(template.html_body, variables)
        text = self._render_source(template.text_body, variables) if template.text_body else None
        return subject, html, text

    def preview(self, payload: TemplatePreviewRequest) -> TemplatePreviewRead:
        validation = self.validate(
            TemplateValidationRequest(
                subject=payload.subject,
                html_body=payload.html_body,
                text_body=payload.text_body,
                variables=payload.variables,
            )
        )
        if not validation.ok:
            return TemplatePreviewRead(
                ok=False,
                subject='',
                html_body='',
                text_body=None,
                errors=validation.errors,
                undeclared_variables=validation.undeclared_variables,
            )
        variables = payload.variables
        try:
            return TemplatePreviewRead(
                ok=True,
                subject=self._render_source(payload.subject, variables),
                html_body=self._render_source(payload.html_body, variables),
                text_body=self._render_source(payload.text_body, variables)
                if payload.text_body
                else None,
                undeclared_variables=validation.undeclared_variables,
            )
        except TemplateError as exc:
            return TemplatePreviewRead(
                ok=False,
                subject='',
                html_body='',
                text_body=None,
                errors=[str(exc)],
                undeclared_variables=validation.undeclared_variables,
            )

    def validate(self, payload: TemplateValidationRequest) -> TemplateValidationRead:
        errors: list[str] = []
        undeclared_variables: set[str] = set()
        for label, source in self._sources(payload).items():
            try:
                parsed = template_environment.parse(source)
                undeclared_variables.update(meta.find_undeclared_variables(parsed))
            except TemplateError as exc:
                errors.append(f'{label}: {exc}')
        missing_variables = sorted(
            variable
            for variable in undeclared_variables
            if variable not in payload.variables
        )
        return TemplateValidationRead(
            ok=not errors and not missing_variables,
            errors=errors,
            undeclared_variables=sorted(undeclared_variables),
            missing_variables=missing_variables,
        )

    def _render_source(self, source: str, variables: Mapping[str, object]) -> str:
        return template_environment.from_string(source).render(**variables)

    def _sources(
        self, payload: TemplateValidationRequest | TemplatePreviewRequest
    ) -> dict[str, str]:
        sources = {'subject': payload.subject, 'html_body': payload.html_body}
        if payload.text_body:
            sources['text_body'] = payload.text_body
        return sources
