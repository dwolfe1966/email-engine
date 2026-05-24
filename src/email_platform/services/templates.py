from __future__ import annotations

import builtins
import re
from collections.abc import Mapping
from uuid import UUID

from jinja2 import StrictUndefined, meta
from jinja2.exceptions import TemplateError
from jinja2.sandbox import SandboxedEnvironment
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from email_platform.models.entities import (
    Campaign,
    CampaignSendJob,
    EmailEvent,
    EmailSendRecord,
    EmailTemplate,
    EmailTemplateVersion,
    JourneyStepExecution,
)
from email_platform.schemas.contracts import (
    TemplateCreate,
    TemplateDocumentRead,
    TemplateDocumentUpdate,
    TemplateLintRead,
    TemplatePreviewRead,
    TemplatePreviewRequest,
    TemplateUpdate,
    TemplateValidationRead,
    TemplateValidationRequest,
    TemplateVariableRead,
    TemplateVariablesRead,
    TemplateVersionCreate,
)
from email_platform.services.documents import document_to_html

template_environment = SandboxedEnvironment(autoescape=False, undefined=StrictUndefined)

NATIVE_TEMPLATE_VARIABLES: dict[str, object] = {
    'unsubscribe_url': 'https://email-engine.app/api/v1/unsubscribe/test-token',
    'tracking_open': '<img src="https://email-engine.app/api/v1/tracking/open/test-token" alt="" width="1" height="1" />',
    'tracking_click': 'https://email-engine.app/api/v1/tracking/click/test-token?url=https%3A%2F%2Fexample.com',
    'tracking_click_base': 'https://email-engine.app/api/v1/tracking/click/test-token',
}

SAMPLE_TEMPLATES: tuple[TemplateCreate, ...] = (
    TemplateCreate(
        name='Sample - Plan Branching',
        subject='{{ first_name }}, your {{ plan }} plan update',
        html_body="""<div class="email-shell">
  <div class="email-container">
    <p class="eyebrow">Account update</p>
    <h1>Hello {{ first_name }}</h1>
    {% if plan == "trial" %}
      <p>Your trial plan is active. You have {{ days_remaining }} days left to explore the platform.</p>
      <p><a class="button" href="{{ upgrade_url }}">Upgrade now</a></p>
    {% else %}
      <p>Your {{ plan }} plan is active. Your next renewal is {{ renewal_date }}.</p>
      <p><a class="button" href="{{ account_url }}">Review account</a></p>
    {% endif %}
    {{ tracking_open }}
    <p class="footer"><a href="{{ unsubscribe_url }}">Unsubscribe</a></p>
  </div>
</div>""",
        css_body=""".email-shell { background: #f6f7f9; padding: 24px 0; }
.email-container { max-width: 620px; margin: 0 auto; background: #ffffff; padding: 24px; }
.eyebrow { color: #2563eb; font-size: 12px; font-weight: 700; text-transform: uppercase; }
.button { background: #2563eb; color: #ffffff; display: inline-block; padding: 11px 16px; text-decoration: none; }
.footer { color: #5b6673; font-size: 12px; }""",
        text_body="""Hello {{ first_name }}.
{% if plan == "trial" %}Your trial has {{ days_remaining }} days left: {{ upgrade_url }}{% else %}Your {{ plan }} plan renews on {{ renewal_date }}: {{ account_url }}{% endif %}
Unsubscribe: {{ unsubscribe_url }}""",
    ),
    TemplateCreate(
        name='Sample - Recommendation Loop',
        subject='{{ first_name }}, {{ recommendation_count }} recommendations for you',
        html_body="""<h1>Recommended next steps</h1>
<p>Hello {{ first_name }}, here are the highest-impact actions for {{ company }}.</p>
<ol class="article-list">
{% for item in recommendations %}
  <li><strong>{{ loop.index }}. {{ item }}</strong></li>
{% else %}
  <li>No recommendations are available yet.</li>
{% endfor %}
</ol>
<p><a class="button" href="{{ tracking_click }}">View recommendations</a></p>
{{ tracking_open }}
<p class="footer"><a href="{{ unsubscribe_url }}">Unsubscribe</a></p>""",
        css_body=""".article-list li { margin: 8px 0; line-height: 1.45; }
.button { color: #ffffff; background: #16a34a; padding: 10px 14px; text-decoration: none; }
.footer { color: #5b6673; font-size: 12px; }""",
        text_body="""Recommended next steps for {{ first_name }}:
{% for item in recommendations %}{{ loop.index }}. {{ item }}
{% else %}No recommendations are available yet.
{% endfor %}
Unsubscribe: {{ unsubscribe_url }}""",
    ),
    TemplateCreate(
        name='Sample - Order Summary Table',
        subject='Receipt for {{ order_number }}',
        html_body="""<h1>Thanks, {{ first_name }}</h1>
<p>Your order {{ order_number }} is {{ order_status }}.</p>
<table class="summary" role="presentation">
  <tr><th>Item</th><th>Qty</th><th>Total</th></tr>
  {% for item in order_items %}
    <tr><td>{{ item.name }}</td><td>{{ item.quantity }}</td><td>{{ item.total }}</td></tr>
  {% endfor %}
</table>
{% if discount_code %}
  <p class="callout">Discount {{ discount_code }} was applied.</p>
{% endif %}
<p><a href="{{ tracking_click }}">Track your order</a></p>
{{ tracking_open }}
<p class="footer"><a href="{{ unsubscribe_url }}">Unsubscribe</a></p>""",
        css_body=""".summary { width: 100%; border-collapse: collapse; }
.summary th, .summary td { border-bottom: 1px solid #d8dee6; padding: 10px; text-align: left; }
.callout { background: #eff6ff; border-left: 4px solid #2563eb; padding: 12px; }
.footer { color: #5b6673; font-size: 12px; }""",
        text_body="""Order {{ order_number }} is {{ order_status }}.
{% for item in order_items %}- {{ item.quantity }} x {{ item.name }}: {{ item.total }}
{% endfor %}
Track: {{ tracking_click }}
Unsubscribe: {{ unsubscribe_url }}""",
    ),
    TemplateCreate(
        name='Sample - Segment Personalization',
        subject='{% if is_vip %}VIP: {% endif %}{{ event_name }} starts {{ event_date }}',
        html_body="""{% set greeting = "VIP invitation" if is_vip else "Invitation" %}
<p class="eyebrow">{{ greeting }}</p>
<h1>{{ event_name }}</h1>
<p>Hello {{ first_name }}, this event starts {{ event_date }}.</p>
{% if city %}
  <p>We selected the {{ city }} agenda for you.</p>
{% endif %}
<ul>
{% for benefit in benefits %}
  <li>{{ benefit }}</li>
{% endfor %}
</ul>
<p><a class="button" href="{{ registration_url }}">Register</a></p>
{{ tracking_open }}
<p class="footer"><a href="{{ unsubscribe_url }}">Unsubscribe</a></p>""",
        css_body=""".eyebrow { color: #7c3aed; font-size: 12px; font-weight: 700; text-transform: uppercase; }
.button { background: #111827; color: #ffffff; display: inline-block; padding: 11px 16px; text-decoration: none; }
.footer { color: #5b6673; font-size: 12px; }""",
        text_body="""{{ event_name }} starts {{ event_date }}.
{% for benefit in benefits %}- {{ benefit }}
{% endfor %}
Register: {{ registration_url }}
Unsubscribe: {{ unsubscribe_url }}""",
    ),
)


class TemplateService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: TemplateCreate) -> EmailTemplate:
        template_data = payload.model_dump(exclude={'document_json'})
        if self._has_document_blocks(payload.document_json):
            template_data['html_body'] = document_to_html(payload.document_json)
        template = EmailTemplate(**template_data)
        self.db.add(template)
        self.db.flush()
        self._add_version(
            template,
            TemplateVersionCreate(
                subject=template.subject,
                html_body=template.html_body,
                css_body=template.css_body,
                text_body=template.text_body,
                document_json=payload.document_json,
            ),
        )
        self.db.commit()
        self.db.refresh(template)
        return template

    def ensure_sample_templates(self, reset: bool = False) -> list[EmailTemplate]:
        templates: list[EmailTemplate] = []
        for payload in SAMPLE_TEMPLATES:
            template = self.db.scalar(
                select(EmailTemplate).where(EmailTemplate.name == payload.name)
            )
            if not template:
                template = EmailTemplate(**payload.model_dump(exclude={'document_json'}))
                self.db.add(template)
                self.db.flush()
                self._add_version(
                    template,
                    TemplateVersionCreate(
                        subject=template.subject,
                        html_body=template.html_body,
                        css_body=template.css_body,
                        text_body=template.text_body,
                        document_json=payload.document_json,
                    ),
                )
            elif reset:
                template.subject = payload.subject
                template.html_body = payload.html_body
                template.css_body = payload.css_body
                template.text_body = payload.text_body
                self._add_version(
                    template,
                    TemplateVersionCreate(
                        subject=payload.subject,
                        html_body=payload.html_body,
                        css_body=payload.css_body,
                        text_body=payload.text_body,
                        document_json=payload.document_json,
                        set_current=True,
                    ),
                )
            templates.append(template)
        self.db.commit()
        for template in templates:
            self.db.refresh(template)
        return templates

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

    def variables_for_template(self, template_id: UUID) -> TemplateVariablesRead | None:
        template = self.get(template_id)
        if not template:
            return None
        return self.variables(
            TemplateValidationRequest(
                subject=template.subject,
                html_body=template.html_body,
                css_body=template.css_body,
                text_body=template.text_body,
                variables={},
            )
        )

    def preview_sample(self, template_id: UUID) -> TemplatePreviewRead | None:
        template = self.get(template_id)
        if not template:
            return None
        variables = self.variables_for_template(template_id)
        if not variables:
            return None
        return self.preview(
            TemplatePreviewRequest(
                subject=template.subject,
                html_body=template.html_body,
                css_body=template.css_body,
                text_body=template.text_body,
                variables=variables.sample_variables,
            )
        )

    def update(self, template_id: UUID, payload: TemplateUpdate) -> EmailTemplate | None:
        template = self.get(template_id)
        if not template:
            return None
        payload_values = payload.model_dump(exclude_unset=True)
        document_json = payload_values.pop('document_json', None)
        for key, value in payload_values.items():
            setattr(template, key, value)
        version_fields = {'subject', 'html_body', 'css_body', 'text_body', 'document_json'}
        if version_fields & payload.model_fields_set:
            self._add_version(
                template,
                TemplateVersionCreate(
                    subject=template.subject,
                    html_body=template.html_body,
                    css_body=template.css_body,
                    text_body=template.text_body,
                    document_json=document_json or {},
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

    def current_document(self, template_id: UUID) -> TemplateDocumentRead | None:
        template = self.get(template_id)
        if not template:
            return None
        version = self.db.scalar(
            select(EmailTemplateVersion)
            .where(
                EmailTemplateVersion.template_id == template_id,
                EmailTemplateVersion.is_current.is_(True),
            )
            .order_by(EmailTemplateVersion.version_number.desc())
        )
        if not version:
            return TemplateDocumentRead(template_id=template_id, document_json={})
        return TemplateDocumentRead(
            template_id=template_id,
            version_id=version.id,
            version_number=version.version_number,
            document_json=version.document_json or {},
        )

    def update_document(
        self, template_id: UUID, payload: TemplateDocumentUpdate
    ) -> TemplateDocumentRead | None:
        template = self.get(template_id)
        if not template:
            return None
        version = self._add_version(
            template,
            TemplateVersionCreate(
                subject=template.subject,
                html_body=template.html_body,
                css_body=template.css_body,
                text_body=template.text_body,
                document_json=payload.document_json,
                set_current=payload.set_current,
            ),
        )
        self.db.commit()
        self.db.refresh(version)
        return TemplateDocumentRead(
            template_id=template_id,
            version_id=version.id,
            version_number=version.version_number,
            document_json=version.document_json or {},
        )

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
        self._delete_template_dependencies(template_id)
        self.db.execute(
            delete(EmailTemplateVersion).where(EmailTemplateVersion.template_id == template_id)
        )
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

    def _delete_template_dependencies(self, template_id: UUID) -> None:
        campaign_ids = list(
            self.db.scalars(select(Campaign.id).where(Campaign.template_id == template_id)).all()
        )
        send_job_ids: list[UUID] = []
        if campaign_ids:
            send_job_ids = list(
                self.db.scalars(
                    select(CampaignSendJob.id).where(
                        CampaignSendJob.campaign_id.in_(campaign_ids)
                    )
                ).all()
            )

        send_record_filters = [EmailSendRecord.template_id == template_id]
        if campaign_ids:
            send_record_filters.append(EmailSendRecord.campaign_id.in_(campaign_ids))
        if send_job_ids:
            send_record_filters.append(EmailSendRecord.send_job_id.in_(send_job_ids))
        send_record_ids = list(
            self.db.scalars(
                select(EmailSendRecord.id).where(or_(*send_record_filters))
            ).all()
        )

        if send_record_ids:
            self.db.execute(
                delete(JourneyStepExecution).where(
                    JourneyStepExecution.send_record_id.in_(send_record_ids)
                )
            )
            self.db.execute(
                delete(EmailEvent).where(EmailEvent.send_record_id.in_(send_record_ids))
            )
            self.db.execute(delete(EmailSendRecord).where(EmailSendRecord.id.in_(send_record_ids)))

        if send_job_ids:
            self.db.execute(delete(EmailEvent).where(EmailEvent.send_job_id.in_(send_job_ids)))
            self.db.execute(delete(CampaignSendJob).where(CampaignSendJob.id.in_(send_job_ids)))

        if campaign_ids:
            self.db.execute(delete(EmailEvent).where(EmailEvent.campaign_id.in_(campaign_ids)))
            self.db.execute(delete(Campaign).where(Campaign.id.in_(campaign_ids)))

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

    def variables(self, payload: TemplateValidationRequest) -> TemplateVariablesRead:
        errors: list[str] = []
        sources_by_variable: dict[str, list[str]] = {}
        for label, source in self._sources(payload).items():
            try:
                parsed = template_environment.parse(source)
                for variable in sorted(meta.find_undeclared_variables(parsed)):
                    sources_by_variable.setdefault(variable, []).append(label)
            except TemplateError as exc:
                errors.append(f'{label}: {exc}')

        detected = sorted(sources_by_variable)
        native_names = sorted(name for name in detected if name in NATIVE_TEMPLATE_VARIABLES)
        user_names = sorted(name for name in detected if name not in NATIVE_TEMPLATE_VARIABLES)
        sample_variables: JsonObject = {
            name: self._sample_value(name) for name in user_names
        }
        sample_variables.update(NATIVE_TEMPLATE_VARIABLES)

        return TemplateVariablesRead(
            ok=not errors,
            variables=[
                TemplateVariableRead(
                    name=name,
                    native=False,
                    sources=sources_by_variable[name],
                    sample_value=sample_variables[name],
                )
                for name in user_names
            ],
            native_variables=[
                TemplateVariableRead(
                    name=name,
                    native=True,
                    required=False,
                    sources=sources_by_variable[name],
                    sample_value=NATIVE_TEMPLATE_VARIABLES[name],
                )
                for name in native_names
            ],
            sample_variables=sample_variables,
            errors=errors,
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
        document_json = payload.document_json
        html_body = payload.html_body or template.html_body
        if self._has_document_blocks(document_json):
            html_body = document_to_html(document_json)
        next_number = self._next_version_number(template.id)
        version = EmailTemplateVersion(
            template_id=template.id,
            version_number=next_number,
            subject=payload.subject or template.subject,
            html_body=html_body,
            css_body=payload.css_body if payload.css_body is not None else template.css_body,
            text_body=payload.text_body if payload.text_body is not None else template.text_body,
            document_json=document_json,
            is_current=payload.set_current,
        )
        self.db.add(version)
        return version

    def _has_document_blocks(self, document_json: Mapping[str, object]) -> bool:
        blocks = document_json.get('blocks')
        return isinstance(blocks, list) and bool(blocks)

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

    def _sample_value(self, name: str) -> object:
        lowered = name.lower()
        if lowered in {'first_name', 'firstname', 'given_name'}:
            return 'Alex'
        if lowered in {'last_name', 'lastname', 'surname'}:
            return 'Morgan'
        if lowered in {'email', 'email_address'}:
            return 'alex@example.com'
        if lowered == 'order_items':
            return [
                {'name': 'Starter plan', 'quantity': 1, 'total': '$49.00'},
                {'name': 'Implementation session', 'quantity': 2, 'total': '$300.00'},
            ]
        if lowered == 'benefits':
            return ['Priority access', 'Expert office hours', 'Implementation checklist']
        if 'recommendation' in lowered or lowered.endswith('items') or lowered.endswith('list'):
            return ['First recommendation', 'Second recommendation', 'Third recommendation']
        if lowered == 'discount_code':
            return 'WELCOME10'
        if lowered == 'is_vip':
            return True
        if lowered in {'plan', 'tier'}:
            return 'trial'
        if lowered == 'days_remaining':
            return 7
        if lowered.startswith('is_') or lowered.startswith('has_'):
            return True
        if 'count' in lowered or 'total' in lowered or lowered.endswith('_number'):
            return 3
        if 'url' in lowered or 'link' in lowered:
            return 'https://example.com'
        return f'sample {name.replace("_", " ")}'
