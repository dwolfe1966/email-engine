from __future__ import annotations

import builtins
import re
from collections.abc import Mapping
from uuid import UUID

from jinja2 import StrictUndefined, meta
from jinja2.exceptions import TemplateError
from jinja2.sandbox import SandboxedEnvironment
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from email_platform.models.entities import EmailTemplate, EmailTemplateVersion
from email_platform.schemas.contracts import (
    TemplateCreate,
    TemplateLintRead,
    TemplatePreviewRead,
    TemplatePreviewRequest,
    TemplateUpdate,
    TemplateValidationRead,
    TemplateValidationRequest,
    TemplateVersionCreate,
)

template_environment = SandboxedEnvironment(autoescape=False, undefined=StrictUndefined)


class TemplateService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: TemplateCreate) -> EmailTemplate:
        template = EmailTemplate(**payload.model_dump())
        self.db.add(template)
        self.db.flush()
        self._add_version(
            template,
            TemplateVersionCreate(
                subject=template.subject,
                html_body=template.html_body,
                css_body=template.css_body,
                text_body=template.text_body,
            ),
        )
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
        if {'subject', 'html_body', 'css_body', 'text_body'} & payload.model_fields_set:
            self._add_version(
                template,
                TemplateVersionCreate(
                    subject=template.subject,
                    html_body=template.html_body,
                    css_body=template.css_body,
                    text_body=template.text_body,
                ),
            )
        self.db.commit()
        self.db.refresh(template)
        return template

    def list_versions(self, template_id: UUID) -> builtins.list[EmailTemplateVersion]:
        statement = (
            select(EmailTemplateVersion)
            .where(EmailTemplateVersion.template_id == template_id)
            .order_by(EmailTemplateVersion.version_number.desc())
        )
        return builtins.list(self.db.scalars(statement).all())

    def create_version(
        self, template_id: UUID, payload: TemplateVersionCreate
    ) -> EmailTemplateVersion | None:
        template = self.get(template_id)
        if not template:
            return None
        version = self._add_version(template, payload)
        if payload.set_current:
            template.subject = version.subject
            template.html_body = version.html_body
            template.css_body = version.css_body
            template.text_body = version.text_body
        self.db.commit()
        self.db.refresh(version)
        self.db.refresh(template)
        return version

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
        html = self._render_html(template.html_body, template.css_body, variables)
        text = self._render_source(template.text_body, variables) if template.text_body else None
        return subject, html, text

    def preview(self, payload: TemplatePreviewRequest) -> TemplatePreviewRead:
        validation = self.validate(
            TemplateValidationRequest(
                subject=payload.subject,
                html_body=payload.html_body,
                css_body=payload.css_body,
                text_body=payload.text_body,
                variables=payload.variables,
            )
        )
        if validation.errors or validation.missing_variables:
            return TemplatePreviewRead(
                ok=False,
                subject='',
                html_body='',
                text_body=None,
                errors=[
                    *validation.errors,
                    *[
                        f'Missing required variable: {variable}'
                        for variable in validation.missing_variables
                    ],
                ],
                undeclared_variables=validation.undeclared_variables,
            )
        variables = payload.variables
        try:
            return TemplatePreviewRead(
                ok=True,
                subject=self._render_source(payload.subject, variables),
                html_body=self._render_html(payload.html_body, payload.css_body, variables),
                css_body=self._render_source(payload.css_body, variables)
                if payload.css_body
                else None,
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
        lint = self.lint(payload)
        return TemplateValidationRead(
            ok=not errors and not missing_variables and not lint.errors,
            errors=errors,
            undeclared_variables=sorted(undeclared_variables),
            missing_variables=missing_variables,
            lint_errors=lint.errors,
            lint_warnings=lint.warnings,
        )

    def lint(self, payload: TemplateValidationRequest) -> TemplateLintRead:
        errors: list[str] = []
        warnings: list[str] = []
        sources = self._sources(payload)
        html = payload.html_body
        combined = '\n'.join(sources.values()).lower()

        self._lint_unsafe_html(html, errors)
        self._lint_unsubscribe(combined, errors)
        self._lint_tracking(html, warnings)
        self._lint_email_hygiene(payload, html, warnings)

        return TemplateLintRead(ok=not errors, errors=errors, warnings=warnings)

    def _render_source(self, source: str, variables: Mapping[str, object]) -> str:
        return template_environment.from_string(source).render(**variables)

    def _add_version(
        self, template: EmailTemplate, payload: TemplateVersionCreate
    ) -> EmailTemplateVersion:
        if payload.set_current:
            for current in self.list_versions(template.id):
                current.is_current = False
        next_number = self._next_version_number(template.id)
        version = EmailTemplateVersion(
            template_id=template.id,
            version_number=next_number,
            subject=payload.subject or template.subject,
            html_body=payload.html_body or template.html_body,
            css_body=payload.css_body if payload.css_body is not None else template.css_body,
            text_body=payload.text_body if payload.text_body is not None else template.text_body,
            document_json=payload.document_json,
            is_current=payload.set_current,
        )
        self.db.add(version)
        return version

    def _next_version_number(self, template_id: UUID) -> int:
        current = self.db.scalar(
            select(func.max(EmailTemplateVersion.version_number)).where(
                EmailTemplateVersion.template_id == template_id
            )
        )
        return (current or 0) + 1

    def _render_html(
        self, html_body: str, css_body: str | None, variables: Mapping[str, object]
    ) -> str:
        html = self._render_source(html_body, variables)
        if not css_body:
            return html
        css = self._render_source(css_body, variables)
        style_block = f'<style>\n{css}\n</style>'
        lower_html = html.lower()
        head_index = lower_html.find('</head>')
        if head_index >= 0:
            return f'{html[:head_index]}{style_block}\n{html[head_index:]}'
        return f'{style_block}\n{html}'

    def _sources(
        self, payload: TemplateValidationRequest | TemplatePreviewRequest
    ) -> dict[str, str]:
        sources = {'subject': payload.subject, 'html_body': payload.html_body}
        if payload.css_body:
            sources['css_body'] = payload.css_body
        if payload.text_body:
            sources['text_body'] = payload.text_body
        return sources

    def _lint_unsafe_html(self, html: str, errors: builtins.list[str]) -> None:
        unsafe_tags = ('script', 'iframe', 'object', 'embed', 'form', 'input', 'button')
        for tag in unsafe_tags:
            if re.search(rf'<\s*{tag}(\s|>|/)', html, flags=re.IGNORECASE):
                errors.append(f'Unsafe HTML tag is not allowed in email templates: <{tag}>.')
        if re.search(r'\son[a-z]+\s*=', html, flags=re.IGNORECASE):
            errors.append('Inline event handlers are not allowed in email templates.')
        if re.search(r'(href|src)\s*=\s*["\']\s*javascript:', html, flags=re.IGNORECASE):
            errors.append('javascript: URLs are not allowed in email templates.')

    def _lint_unsubscribe(self, combined: str, errors: builtins.list[str]) -> None:
        has_unsubscribe = any(
            marker in combined
            for marker in (
                'unsubscribe',
                'unsubscribe_url',
                'unsubscribe_link',
                '/unsubscribe/',
                '{{ unsubscribe',
            )
        )
        if not has_unsubscribe:
            errors.append('Template must include an unsubscribe link or unsubscribe variable.')

    def _lint_tracking(self, html: str, warnings: builtins.list[str]) -> None:
        href_count = len(re.findall(r'<a\b[^>]*\bhref\s*=', html, flags=re.IGNORECASE))
        if href_count and not re.search(
            r'(tracking|click_url|tracking_click|/tracking/click)',
            html,
            flags=re.IGNORECASE,
        ):
            warnings.append(
                'Template contains links, but no tracking click placeholder was detected.'
            )
        if not re.search(r'(tracking_open|open_pixel|/tracking/open)', html, flags=re.IGNORECASE):
            warnings.append('No open-tracking placeholder was detected.')

    def _lint_email_hygiene(
        self,
        payload: TemplateValidationRequest,
        html: str,
        warnings: builtins.list[str],
    ) -> None:
        if len(payload.subject) > 120:
            warnings.append('Subject is longer than 120 characters.')
        if not payload.text_body:
            warnings.append('Plain-text body is missing.')
        image_tags = re.findall(r'<img\b[^>]*>', html, flags=re.IGNORECASE)
        missing_alt = [
            tag for tag in image_tags if not re.search(r'\balt\s*=', tag, flags=re.IGNORECASE)
        ]
        if missing_alt:
            warnings.append('One or more images are missing alt text.')
