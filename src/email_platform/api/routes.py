import json
from collections.abc import Mapping
from datetime import datetime
from html import escape
from typing import Annotated, cast
from urllib.parse import quote, urlparse
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from email_platform.api.deps import require_user
from email_platform.core.settings import Settings, get_settings
from email_platform.db.session import get_db
from email_platform.models.entities import (
    Audience,
    Campaign,
    CampaignSendJob,
    Contact,
    DataSource,
    DataSourceMapping,
    DeliveryAttempt,
    DeliveryRoute,
    DeliveryRouteStatus,
    DeliveryRouteType,
    DomainDeliveryPolicy,
    EmailEvent,
    EmailEventType,
    EmailSendRecord,
    EmailTemplate,
    EmailTemplateVersion,
    Journey,
    JourneyEnrollment,
    JourneyEnrollmentStatus,
    JourneyStep,
    MtaIpPool,
    MtaIpPoolNode,
    MtaNode,
    MtaOperationalStatus,
    MtaProviderAccount,
    Suppression,
    User,
)
from email_platform.schemas.contracts import (
    AIAnalyticsAnalysisRead,
    AIAnalyticsAnalysisRequest,
    AIAnalyticsRecommendationRead,
    AIAudienceAnalysisRead,
    AIAudienceAnalysisRequest,
    AIAudienceRecommendationRead,
    AICampaignAnalysisRead,
    AICampaignAnalysisRequest,
    AICampaignRecommendationRead,
    AIDeliveryAnalysisRead,
    AIDeliveryAnalysisRequest,
    AIDeliveryRecommendationRead,
    AIJourneyAnalysisRead,
    AIJourneyAnalysisRequest,
    AIJourneyRecommendationRead,
    AITemplateDraftRead,
    AITemplateDraftRequest,
    AITemplateEditRequest,
    AITemplateRecommendationRead,
    AITemplateRecommendationsRead,
    AITemplateRecommendRequest,
    AnalyticsOverviewRead,
    AudienceCreate,
    AudienceImportPreviewRead,
    AudienceImportRead,
    AudiencePerformanceRead,
    AudiencePreviewRead,
    AudiencePreviewRequest,
    AudienceRead,
    AudienceSnapshotCreate,
    AudienceSnapshotRead,
    AudienceUpdate,
    CampaignAnalyticsRead,
    CampaignCloneRequest,
    CampaignCreate,
    CampaignLaunchRead,
    CampaignLaunchRequest,
    CampaignListSummaryRead,
    CampaignPerformanceRead,
    CampaignProofRouteRead,
    CampaignProcessDueRead,
    CampaignRead,
    CampaignSendJobProgressRead,
    CampaignSendJobRead,
    CampaignTestPreviewRead,
    CampaignTestPreviewRequest,
    CampaignTestSendRequest,
    CampaignTestSendResponse,
    CampaignTimelineRead,
    CampaignUpdate,
    CampaignValidationRead,
    CampaignWorkflowStatusRead,
    ContactRead,
    ContactUpdate,
    ContactUpsert,
    DataSourceCreate,
    DataSourceImportJobRead,
    DataSourceIngestRequest,
    DataSourceMappingCreate,
    DataSourceMappingRead,
    DataSourceMappingUpdate,
    DataSourceRead,
    DataSourceSchemaRead,
    DataSourceUpdate,
    DataSourceValidationRead,
    DeleteResponse,
    DeliveryAttemptRead,
    DeliveryRouteCreate,
    DeliveryRouteRead,
    DeliveryRouteUpdate,
    DeliveryRunRead,
    DomainAuthenticationPlanRead,
    DomainAuthenticationPlanRequest,
    DomainAuthenticationVerificationRead,
    DomainBlocklistScanRead,
    DomainBlocklistScanRequest,
    DomainComplianceHoldRequest,
    DomainComplianceReleaseRequest,
    DomainDeliverabilityRead,
    DomainDeliveryPolicyCreate,
    DomainDeliveryPolicyRead,
    DomainDeliveryPolicyUpdate,
    DomainDkimKeyCreateRead,
    DomainDkimKeyCreateRequest,
    DomainReputationDashboardRead,
    DomainWarmupProgressionRead,
    DomainWarmupProgressionRequest,
    EmailSendRecordRead,
    EmailSendRequest,
    EmailSendResponse,
    EventCreate,
    EventRead,
    JourneyCreate,
    JourneyEnrollmentCreate,
    JourneyEnrollmentRead,
    JourneyGraphRead,
    JourneyPerformanceRead,
    JourneyProcessRead,
    JourneyRead,
    JourneyStepCreate,
    JourneyStepExecutionRead,
    JourneyStepRead,
    JourneyStepUpdate,
    JourneyUpdate,
    JsonObject,
    ListResponse,
    ManagedSmtpBootstrapProfileRead,
    ManagedSmtpBootstrapRead,
    ManagedSmtpBootstrapRequest,
    ManagedSmtpDeploymentSummaryRead,
    ManagedSmtpFeedbackEvent,
    ManagedSmtpFirstSendRead,
    ManagedSmtpMaintenanceRead,
    ManagedSmtpMaintenanceRequest,
    ManagedSmtpReadinessAlertsRead,
    ManagedSmtpReadinessCheckCreate,
    ManagedSmtpReadinessCheckRead,
    ManagedSmtpReadinessNotificationRead,
    ManagedSmtpReadinessSummaryRead,
    ManagedSmtpReadinessTrendRead,
    ManagedSmtpRouteMatrixRead,
    ManagedSmtpRouteMatrixRequest,
    ManagedSmtpRouteMatrixResult,
    ManagedSmtpRouteResolutionRead,
    ManagedSmtpRouteResolveRequest,
    ManagedSmtpRoutingRuleUpsert,
    ManagedSmtpRoutingRulesRead,
    MtaIpPoolCreate,
    MtaIpPoolNodeCreate,
    MtaIpPoolNodeRead,
    MtaIpPoolNodeUpdate,
    MtaIpPoolRead,
    MtaIpPoolUpdate,
    MtaNodeCreate,
    MtaNodeEventCreate,
    MtaNodeEventRead,
    MtaNodeHeartbeatRequest,
    MtaNodeRead,
    MtaNodeRuntimeConfigRead,
    MtaNodeStatusActionRequest,
    MtaNodeUpdate,
    MtaProviderAccountCreate,
    MtaProviderAccountRead,
    MtaProviderAccountUpdate,
    OperatorUserCreate,
    OperatorUserPasswordUpdate,
    OperatorUserRead,
    OperatorUserUpdate,
    ProviderFeedbackEventRead,
    ProviderWebhookIngestRead,
    SendGridWebhookEvent,
    SendResponse,
    SuppressionCreate,
    SuppressionRead,
    TemplateCreate,
    TemplateDocumentImportRead,
    TemplateDocumentImportRequest,
    TemplateDocumentRead,
    TemplateDocumentRenderRequest,
    TemplateDocumentUpdate,
    TemplateLintRead,
    TemplatePreviewRead,
    TemplatePreviewRequest,
    TemplateRead,
    TemplateUpdate,
    TemplateValidationRead,
    TemplateValidationRequest,
    TemplateVariablesRead,
    TemplateVersionCreate,
    TemplateVersionRead,
    TestEmailSendRequest,
    TrackingEventRead,
    TrackingLinksRead,
    UnsubscribeRead,
    UnsubscribeTokenRead,
)
from email_platform.services.analytics import AnalyticsService
from email_platform.services.audience_imports import AudienceImportService
from email_platform.services.audiences import AudienceService
from email_platform.services.auth import hash_password
from email_platform.services.campaigns import CampaignService
from email_platform.services.contacts import ContactService
from email_platform.services.data_sources import DataSourceService
from email_platform.services.delivery import DeliveryService
from email_platform.services.delivery_routes import DeliveryRouteService
from email_platform.services.documents import document_to_html, html_to_document
from email_platform.services.events import EventService
from email_platform.services.feedback import FeedbackIngestionService
from email_platform.services.journeys import JourneyService
from email_platform.services.managed_smtp_agent import ManagedSmtpAgentService
from email_platform.services.managed_smtp_bootstrap import (
    ManagedSmtpBootstrapService,
    bootstrap_profile_payload,
    list_bootstrap_profiles,
)
from email_platform.services.managed_smtp_readiness import ManagedSmtpReadinessService
from email_platform.services.managed_smtp_routing import ManagedSmtpRoutingService
from email_platform.services.mta_inventory import MtaInventoryError, MtaInventoryService
from email_platform.services.provider_webhooks import ProviderWebhookService
from email_platform.services.sending import SendingService
from email_platform.services.suppressions import SuppressionService
from email_platform.services.system import schema_status, system_diagnostics
from email_platform.services.templates import TemplateService
from email_platform.services.tracking import TrackingService
from email_platform.services.webhook_security import (
    ManagedSmtpFeedbackVerifier,
    SendGridWebhookVerifier,
    WebhookSignatureError,
)

router = APIRouter(prefix='/api/v1')
DbSession = Annotated[Session, Depends(get_db)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
Limit = Annotated[int, Query(ge=1, le=500)]
RecentEventLimit = Annotated[int, Query(ge=0, le=500)]
Offset = Annotated[int, Query(ge=0)]
TRANSPARENT_GIF = (
    b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!'
    b'\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00'
    b'\x01\x00\x00\x02\x02D\x01\x00;'
)


@router.get('/system/schema-status')
def read_schema_status(db: DbSession) -> JsonObject:
    return schema_status(db)


@router.get('/system/diagnostics')
def read_system_diagnostics(db: DbSession, settings: SettingsDep) -> JsonObject:
    return system_diagnostics(db, settings)


@router.get('/users/list', response_model=ListResponse[OperatorUserRead], dependencies=[Depends(require_user)])
def list_operator_users(
    db: DbSession,
    limit: Limit = 100,
    offset: Offset = 0,
) -> ListResponse[OperatorUserRead]:
    total = db.scalar(select(func.count()).select_from(User)) or 0
    users = (
        db.execute(select(User).order_by(User.created_at.desc()).offset(offset).limit(limit))
        .scalars()
        .all()
    )
    return ListResponse[OperatorUserRead](items=users, limit=limit, offset=offset, total=total)


@router.post('/users', response_model=OperatorUserRead, dependencies=[Depends(require_user)])
def create_operator_user(payload: OperatorUserCreate, db: DbSession) -> User:
    existing = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail='User email already exists')
    user = User(
        email=str(payload.email),
        display_name=payload.display_name,
        role=payload.role,
        password_hash=hash_password(payload.password),
        is_active=payload.is_active,
        failed_login_count=0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get('/users/{user_id}', response_model=OperatorUserRead, dependencies=[Depends(require_user)])
def get_operator_user(user_id: UUID, db: DbSession) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail='User not found')
    return user


@router.patch('/users/{user_id}', response_model=OperatorUserRead, dependencies=[Depends(require_user)])
def update_operator_user(user_id: UUID, payload: OperatorUserUpdate, db: DbSession) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail='User not found')
    if payload.display_name is not None:
        user.display_name = payload.display_name
    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active
    db.commit()
    db.refresh(user)
    return user


@router.post('/users/{user_id}/password', response_model=OperatorUserRead, dependencies=[Depends(require_user)])
def update_operator_user_password(
    user_id: UUID,
    payload: OperatorUserPasswordUpdate,
    db: DbSession,
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail='User not found')
    user.password_hash = hash_password(payload.password)
    user.failed_login_count = 0
    user.locked_until = None
    db.commit()
    db.refresh(user)
    return user


@router.post('/users/{user_id}/unlock', response_model=OperatorUserRead, dependencies=[Depends(require_user)])
def unlock_operator_user(user_id: UUID, db: DbSession) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail='User not found')
    user.failed_login_count = 0
    user.locked_until = None
    db.commit()
    db.refresh(user)
    return user


def _deterministic_template_draft(payload: AITemplateDraftRequest) -> dict[str, object]:
    brief = payload.brief.strip() or 'Email campaign'
    brand_name = str(payload.brand.get('name') or 'SentientMail')
    primary_color = str(payload.brand.get('primary_color') or '#2563eb')
    tone = str(payload.brand.get('tone') or 'clear and helpful')
    variables = _normalized_required_variables(payload.required_variables)
    greeting = '{{ first_name }}' if 'first_name' in variables else 'there'
    list_block = ''
    if 'recommendations' in variables:
        list_block = (
            '<ul class="recommendations">'
            '{% for item in recommendations %}'
            '<li>{{ loop.index }}. {{ item }}</li>'
            '{% endfor %}'
            '</ul>'
        )
    plan_block = ''
    if 'plan' in variables:
        plan_block = (
            '{% if plan == "trial" %}'
            '<p>Your trial plan is active. Here are the next best steps.</p>'
            '{% else %}'
            '<p>Your {{ plan }} plan is ready for the next step.</p>'
            '{% endif %}'
        )
    audience_note = (
        f'<p class="audience-note">{escape(payload.audience_summary)}</p>'
        if payload.audience_summary
        else ''
    )
    subject_variable = '{{ first_name }}' if 'first_name' in variables else brand_name
    html_body = (
        '<div class="email-shell">'
        f'<p class="eyebrow">{escape(brand_name)}</p>'
        f'<h1>{escape(brief[:90])}</h1>'
        f'<p>Hello {greeting},</p>'
        f'{plan_block}'
        f'<p>This draft follows a {escape(tone)} tone and is ready for review.</p>'
        f'{list_block}'
        f'{audience_note}'
        '<p><a class="button" href="{{ tracking_click }}">Review details</a></p>'
        '{{ tracking_open }}'
        '<p class="footer"><a href="{{ unsubscribe_url }}">Unsubscribe</a></p>'
        '</div>'
    )
    text_body = (
        f'{brief}\n\nHello {greeting}.\n'
        '{% if plan is defined %}Plan: {{ plan }}.\n{% endif %}'
        '{% if recommendations is defined %}'
        '{% for item in recommendations %}{{ loop.index }}. {{ item }}\n{% endfor %}'
        '{% endif %}'
        'Review details: {{ tracking_click }}\n'
        'Unsubscribe: {{ unsubscribe_url }}'
    )
    css_body = (
        '.email-shell { font-family: Arial, sans-serif; color: #17212b; line-height: 1.5; } '
        f'.eyebrow {{ color: {primary_color}; font-weight: 700; text-transform: uppercase; }} '
        f'.button {{ display: inline-block; background: {primary_color}; color: #ffffff; '
        'padding: 12px 18px; border-radius: 6px; text-decoration: none; } '
        '.footer { color: #687787; font-size: 12px; } '
        '.recommendations { padding-left: 20px; }'
    )
    return {
        'subject': f'{brief[:60]} for {subject_variable}',
        'html_body': html_body,
        'css_body': css_body,
        'text_body': text_body,
        'notes': [
            'Generated by deterministic draft mode; review copy before saving.',
            'Includes tracking and unsubscribe placeholders for Email Engine delivery.',
        ],
    }


def _deterministic_template_edit(payload: AITemplateEditRequest) -> dict[str, object]:
    instruction = payload.instruction.strip() or 'Update this email template.'
    subject = payload.current_subject.strip() or 'Updated email'
    css_body = payload.current_css or ''
    html_body = payload.current_html.strip() or '<p>Hello {{ first_name }},</p>'
    text_body = payload.current_text or ''
    edit_note = (
        '<div class="ai-edit-note">'
        f'<p><strong>Requested update:</strong> {escape(instruction)}</p>'
        '</div>'
    )
    if '</body>' in html_body.lower():
        body_close = html_body.lower().rfind('</body>')
        html_body = f'{html_body[:body_close]}{edit_note}{html_body[body_close:]}'
    else:
        html_body = f'{html_body}\n{edit_note}'
    if '{{ tracking_open }}' not in html_body:
        html_body += '{{ tracking_open }}'
    if '{{ unsubscribe_url }}' not in html_body:
        html_body += '<p class="footer"><a href="{{ unsubscribe_url }}">Unsubscribe</a></p>'
    if '{{ unsubscribe_url }}' not in text_body:
        text_body = f'{text_body}\n\nUnsubscribe: {{{{ unsubscribe_url }}}}'.strip()
    return {
        'subject': subject,
        'html_body': html_body,
        'css_body': css_body,
        'text_body': text_body,
        'notes': [
            'Edited by deterministic mode; review copy before saving.',
            'Preserved the existing template body and appended the requested change.',
        ],
    }


def _normalized_required_variables(values: list[str]) -> set[str]:
    normalized = {value.strip() for value in values if value.strip()}
    if not normalized:
        normalized = {'first_name', 'plan', 'recommendations'}
    return normalized


def _ai_template_provider(settings: Settings) -> str:
    provider = settings.ai_template_provider.strip().lower()
    if provider == 'auto':
        return 'openai' if settings.openai_api_key else 'deterministic'
    return provider


def _template_draft_payload(payload: AITemplateDraftRequest, settings: Settings) -> dict[str, object]:
    provider = _ai_template_provider(settings)
    if provider == 'openai':
        if not settings.openai_api_key:
            raise HTTPException(
                status_code=503,
                detail='OPENAI_API_KEY is required when AI_TEMPLATE_PROVIDER=openai',
            )
        try:
            return _openai_template_draft(payload, settings)
        except HTTPException:
            raise
        except Exception as exc:
            if settings.ai_template_provider.strip().lower() == 'auto':
                draft = _deterministic_template_draft(payload)
                draft['notes'] = [
                    *cast(list[str], draft['notes']),
                    f'OpenAI draft failed; used deterministic fallback: {exc}',
                ]
                return draft
            raise HTTPException(status_code=502, detail=f'OpenAI template draft failed: {exc}') from exc
    if provider != 'deterministic':
        raise HTTPException(status_code=400, detail=f'Unsupported AI template provider: {provider}')
    return _deterministic_template_draft(payload)


def _template_edit_payload(payload: AITemplateEditRequest, settings: Settings) -> dict[str, object]:
    provider = _ai_template_provider(settings)
    if provider == 'openai':
        if not settings.openai_api_key:
            raise HTTPException(
                status_code=503,
                detail='OPENAI_API_KEY is required when AI_TEMPLATE_PROVIDER=openai',
            )
        try:
            return _openai_template_edit(payload, settings)
        except HTTPException:
            raise
        except Exception as exc:
            if settings.ai_template_provider.strip().lower() == 'auto':
                edit = _deterministic_template_edit(payload)
                edit['notes'] = [
                    *cast(list[str], edit['notes']),
                    f'OpenAI edit failed; used deterministic fallback: {exc}',
                ]
                return edit
            raise HTTPException(status_code=502, detail=f'OpenAI template edit failed: {exc}') from exc
    if provider != 'deterministic':
        raise HTTPException(status_code=400, detail=f'Unsupported AI template provider: {provider}')
    return _deterministic_template_edit(payload)


def _template_recommendation_payload(
    payload: AITemplateRecommendRequest,
    validation: TemplateValidationRead,
    variables: TemplateVariablesRead,
    settings: Settings,
) -> tuple[list[AITemplateRecommendationRead], list[str], str, str]:
    provider = _ai_template_provider(settings)
    if provider == 'openai':
        if not settings.openai_api_key:
            raise HTTPException(
                status_code=503,
                detail='OPENAI_API_KEY is required when AI_TEMPLATE_PROVIDER=openai',
            )
        try:
            recommendations, summary = _openai_template_recommendations(
                payload,
                validation,
                variables,
                settings,
            )
            return recommendations, summary, 'openai', settings.openai_model
        except HTTPException:
            raise
        except Exception as exc:
            if settings.ai_template_provider.strip().lower() == 'auto':
                recommendations = _template_recommendations(payload, validation, variables)
                summary = _template_recommendation_summary(recommendations, validation)
                summary.append(f'OpenAI recommendations failed; used deterministic fallback: {exc}')
                return recommendations, summary, 'email-engine', 'deterministic-template-recommend-v1'
            raise HTTPException(
                status_code=502,
                detail=f'OpenAI template recommendations failed: {exc}',
            ) from exc
    if provider != 'deterministic':
        raise HTTPException(status_code=400, detail=f'Unsupported AI template provider: {provider}')
    recommendations = _template_recommendations(payload, validation, variables)
    return (
        recommendations,
        _template_recommendation_summary(recommendations, validation),
        'email-engine',
        'deterministic-template-recommend-v1',
    )


def _openai_template_draft(
    payload: AITemplateDraftRequest,
    settings: Settings,
) -> dict[str, object]:
    schema = {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'subject': {'type': 'string'},
            'html_body': {'type': 'string'},
            'css_body': {'type': 'string'},
            'text_body': {'type': 'string'},
            'notes': {'type': 'array', 'items': {'type': 'string'}},
        },
        'required': ['subject', 'html_body', 'css_body', 'text_body', 'notes'],
    }
    variables = sorted(_normalized_required_variables(payload.required_variables))
    prompt = {
        'brief': payload.brief,
        'brand': payload.brand,
        'required_variables': variables,
        'audience_summary': payload.audience_summary,
        'requirements': [
            'Return production-ready email template content as JSON only.',
            'Use Jinja syntax for variables, loops, and conditionals where useful.',
            'Include {{ tracking_open }}, {{ tracking_click }}, and {{ unsubscribe_url }}.',
            'Use {{ tracking_open }} as a standalone tracking pixel placeholder, not as an href.',
            'Use {{ tracking_click }} only as an href value for one primary call-to-action link.',
            'Keep HTML email friendly: simple tables/divs, inline-safe CSS classes, no script.',
            'Preserve every required variable at least once in subject, HTML, or text.',
        ],
    }
    with httpx.Client(timeout=45) as client:
        response = client.post(
            'https://api.openai.com/v1/responses',
            headers={
                'Authorization': f'Bearer {settings.openai_api_key}',
                'Content-Type': 'application/json',
            },
            json={
                'model': settings.openai_model,
                'input': [
                    {
                        'role': 'system',
                        'content': (
                            'You are an expert lifecycle email template builder. '
                            'Generate concise, compliant, Jinja-compatible campaign templates.'
                        ),
                    },
                    {'role': 'user', 'content': json.dumps(prompt)},
                ],
                'text': {
                    'format': {
                        'type': 'json_schema',
                        'name': 'email_template_draft',
                        'strict': True,
                        'schema': schema,
                    }
                },
            },
        )
    if response.status_code >= 400:
        raise RuntimeError(f'{response.status_code} {response.text[:500]}')
    raw = response.json()
    text = raw.get('output_text') or _responses_output_text(raw)
    if not text:
        raise RuntimeError('OpenAI response did not include output_text')
    draft = json.loads(text)
    notes = draft.get('notes') if isinstance(draft.get('notes'), list) else []
    return {
        'subject': str(draft.get('subject') or payload.brief[:60] or 'Email campaign'),
        'html_body': _normalize_ai_html_body(str(draft.get('html_body') or '')),
        'css_body': str(draft.get('css_body') or ''),
        'text_body': _normalize_ai_text_body(str(draft.get('text_body') or '')),
        'notes': [str(note) for note in notes],
        'provider': 'openai',
        'model': settings.openai_model,
    }


def _openai_template_edit(
    payload: AITemplateEditRequest,
    settings: Settings,
) -> dict[str, object]:
    schema = {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'subject': {'type': 'string'},
            'html_body': {'type': 'string'},
            'css_body': {'type': 'string'},
            'text_body': {'type': 'string'},
            'notes': {'type': 'array', 'items': {'type': 'string'}},
        },
        'required': ['subject', 'html_body', 'css_body', 'text_body', 'notes'],
    }
    variables = sorted(_normalized_required_variables(payload.required_variables))
    prompt = {
        'instruction': payload.instruction,
        'current_template': {
            'subject': payload.current_subject,
            'html_body': payload.current_html,
            'css_body': payload.current_css or '',
            'text_body': payload.current_text or '',
        },
        'brand': payload.brand,
        'required_variables': variables,
        'sample_variables': payload.sample_variables,
        'audience_summary': payload.audience_summary,
        'requirements': [
            'Return the fully revised email template as JSON only.',
            'Modify the existing template according to the instruction; preserve structure, styling, and unchanged copy unless the instruction requires a change.',
            'Keep Jinja syntax valid, including loops and conditionals already present in the template.',
            'Preserve every required variable at least once in subject, HTML, or text.',
            'Include {{ tracking_open }}, {{ tracking_click }}, and {{ unsubscribe_url }}.',
            'Use {{ tracking_open }} as a standalone tracking pixel placeholder, not as an href.',
            'Use {{ tracking_click }} only as an href value for one primary call-to-action link.',
            'Keep HTML email friendly: simple tables/divs, inline-safe CSS classes, no script.',
        ],
    }
    with httpx.Client(timeout=45) as client:
        response = client.post(
            'https://api.openai.com/v1/responses',
            headers={
                'Authorization': f'Bearer {settings.openai_api_key}',
                'Content-Type': 'application/json',
            },
            json={
                'model': settings.openai_model,
                'input': [
                    {
                        'role': 'system',
                        'content': (
                            'You are an expert lifecycle email template editor. '
                            'Make targeted, safe edits to existing Jinja-compatible email templates.'
                        ),
                    },
                    {'role': 'user', 'content': json.dumps(prompt)},
                ],
                'text': {
                    'format': {
                        'type': 'json_schema',
                        'name': 'email_template_edit',
                        'strict': True,
                        'schema': schema,
                    }
                },
            },
        )
    if response.status_code >= 400:
        raise RuntimeError(f'{response.status_code} {response.text[:500]}')
    raw = response.json()
    text = raw.get('output_text') or _responses_output_text(raw)
    if not text:
        raise RuntimeError('OpenAI response did not include output_text')
    edit = json.loads(text)
    notes = edit.get('notes') if isinstance(edit.get('notes'), list) else []
    return {
        'subject': str(edit.get('subject') or payload.current_subject or 'Updated email'),
        'html_body': _normalize_ai_html_body(str(edit.get('html_body') or payload.current_html)),
        'css_body': str(edit.get('css_body') if edit.get('css_body') is not None else payload.current_css or ''),
        'text_body': _normalize_ai_text_body(str(edit.get('text_body') or payload.current_text or '')),
        'notes': [str(note) for note in notes],
        'provider': 'openai',
        'model': settings.openai_model,
    }


def _openai_template_recommendations(
    payload: AITemplateRecommendRequest,
    validation: TemplateValidationRead,
    variables: TemplateVariablesRead,
    settings: Settings,
) -> tuple[list[AITemplateRecommendationRead], list[str]]:
    schema = {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'recommendations': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'additionalProperties': False,
                    'properties': {
                        'code': {'type': 'string'},
                        'category': {'type': 'string'},
                        'priority': {'type': 'string', 'enum': ['high', 'medium', 'low']},
                        'title': {'type': 'string'},
                        'detail': {'type': 'string'},
                        'suggested_instruction': {'type': 'string'},
                        'confidence': {'type': 'number', 'minimum': 0, 'maximum': 1},
                    },
                    'required': [
                        'code',
                        'category',
                        'priority',
                        'title',
                        'detail',
                        'suggested_instruction',
                        'confidence',
                    ],
                },
            },
            'summary': {'type': 'array', 'items': {'type': 'string'}},
        },
        'required': ['recommendations', 'summary'],
    }
    prompt = {
        'current_template': {
            'subject': payload.current_subject,
            'html_body': payload.current_html,
            'css_body': payload.current_css or '',
            'text_body': payload.current_text or '',
        },
        'sample_variables': payload.sample_variables,
        'goals': payload.goals,
        'audience_summary': payload.audience_summary,
        'validation': validation.model_dump(mode='json'),
        'template_variables': variables.model_dump(mode='json'),
        'requirements': [
            'Return JSON only.',
            'Recommend targeted improvements for a lifecycle email template editor.',
            'Prefer concrete recommendations the user can apply with an AI edit instruction.',
            'Prioritize validation blockers, compliance, tracking, dynamic personalization, and email-client-safe design.',
            'Do not recommend removing existing Jinja variables, loops, conditionals, tracking placeholders, or unsubscribe links.',
            'Use stable snake_case codes.',
            'Return at most 8 recommendations sorted by priority and usefulness.',
        ],
    }
    with httpx.Client(timeout=45) as client:
        response = client.post(
            'https://api.openai.com/v1/responses',
            headers={
                'Authorization': f'Bearer {settings.openai_api_key}',
                'Content-Type': 'application/json',
            },
            json={
                'model': settings.openai_model,
                'input': [
                    {
                        'role': 'system',
                        'content': (
                            'You are an expert lifecycle email strategist and template QA reviewer. '
                            'Produce concise, safe, actionable template recommendations.'
                        ),
                    },
                    {'role': 'user', 'content': json.dumps(prompt)},
                ],
                'text': {
                    'format': {
                        'type': 'json_schema',
                        'name': 'email_template_recommendations',
                        'strict': True,
                        'schema': schema,
                    }
                },
            },
        )
    if response.status_code >= 400:
        raise RuntimeError(f'{response.status_code} {response.text[:500]}')
    raw = response.json()
    text = raw.get('output_text') or _responses_output_text(raw)
    if not text:
        raise RuntimeError('OpenAI response did not include output_text')
    result = json.loads(text)
    items = result.get('recommendations') if isinstance(result, Mapping) else []
    summary_items = result.get('summary') if isinstance(result, Mapping) else []
    recommendations = [
        AITemplateRecommendationRead(
            code=str(item.get('code') or 'template_improvement'),
            category=str(item.get('category') or 'quality'),
            priority=str(item.get('priority') or 'medium'),
            title=str(item.get('title') or 'Improve template'),
            detail=str(item.get('detail') or ''),
            suggested_instruction=str(item.get('suggested_instruction') or item.get('detail') or ''),
            confidence=float(item.get('confidence') or 0.7),
        )
        for item in items
        if isinstance(item, Mapping)
    ][:8]
    summary = [str(item) for item in summary_items if str(item).strip()]
    if not summary:
        summary = _template_recommendation_summary(recommendations, validation)
    return recommendations, summary


def _responses_output_text(response: Mapping[str, object]) -> str | None:
    output = response.get('output')
    if not isinstance(output, list):
        return None
    parts: list[str] = []
    for item in output:
        if not isinstance(item, Mapping):
            continue
        content = item.get('content')
        if not isinstance(content, list):
            continue
        for chunk in content:
            if isinstance(chunk, Mapping) and isinstance(chunk.get('text'), str):
                parts.append(chunk['text'])
    return ''.join(parts) or None


def _normalize_ai_html_body(html_body: str) -> str:
    normalized = html_body.replace('src="{{ tracking_open }}"', '')
    normalized = normalized.replace("src='{{ tracking_open }}'", '')
    if '{{ tracking_open }}' not in normalized:
        normalized += '{{ tracking_open }}'
    if '{{ unsubscribe_url }}' not in normalized:
        normalized += '<p class="footer"><a href="{{ unsubscribe_url }}">Unsubscribe</a></p>'
    return normalized


def _normalize_ai_text_body(text_body: str) -> str:
    normalized = text_body
    if '{{ unsubscribe_url }}' not in normalized:
        normalized += '\n\nUnsubscribe: {{ unsubscribe_url }}'
    return normalized


def _ai_edit_change_metadata(
    payload: AITemplateEditRequest,
    draft: Mapping[str, object],
) -> tuple[list[str], list[str]]:
    current = {
        'subject': payload.current_subject or '',
        'html_body': payload.current_html or '',
        'css_body': payload.current_css or '',
        'text_body': payload.current_text or '',
    }
    changed_fields = [
        field for field, old_value in current.items()
        if str(draft.get(field) or '') != old_value
    ]
    labels = {
        'subject': 'Subject line changed.',
        'html_body': 'HTML body changed.',
        'css_body': 'CSS changed.',
        'text_body': 'Plain-text body changed.',
    }
    summary = [labels[field] for field in changed_fields]
    if not summary:
        summary = ['No material field changes were detected.']
    return changed_fields, summary


def _template_recommendations(
    payload: AITemplateRecommendRequest,
    validation: TemplateValidationRead,
    variables: TemplateVariablesRead,
) -> list[AITemplateRecommendationRead]:
    subject = payload.current_subject or ''
    html_body = payload.current_html or ''
    css_body = payload.current_css or ''
    text_body = payload.current_text or ''
    recommendations: list[AITemplateRecommendationRead] = []

    def add(
        code: str,
        category: str,
        priority: str,
        title: str,
        detail: str,
        suggested_instruction: str,
        confidence: float,
    ) -> None:
        recommendations.append(
            AITemplateRecommendationRead(
                code=code,
                category=category,
                priority=priority,
                title=title,
                detail=detail,
                suggested_instruction=suggested_instruction,
                confidence=confidence,
            )
        )

    if not validation.ok:
        findings = [
            *validation.errors,
            *[f'Missing variable: {name}' for name in validation.missing_variables],
            *validation.lint_errors,
        ]
        add(
            'fix_validation_blockers',
            'quality',
            'high',
            'Fix validation blockers before launch',
            '; '.join(findings[:4]) or 'Template validation did not pass.',
            'Fix the validation blockers while preserving the template intent and Jinja variables.',
            0.98,
        )

    if '{{ tracking_click' not in html_body and 'tracking_click' not in html_body:
        add(
            'add_tracked_cta',
            'tracking',
            'high',
            'Add a tracked primary CTA',
            'The template does not appear to use the native tracking_click variable for a primary call to action.',
            'Add one clear primary CTA that uses {{ tracking_click }} as the href and keeps the current visual style.',
            0.9,
        )

    if '{{ tracking_open' not in html_body and 'tracking_open' not in html_body:
        add(
            'add_open_tracking',
            'tracking',
            'medium',
            'Include open tracking placeholder',
            'The HTML does not include the native tracking_open placeholder.',
            'Add {{ tracking_open }} as a standalone tracking placeholder near the end of the HTML body.',
            0.86,
        )

    if '{{ unsubscribe_url' not in html_body and 'unsubscribe_url' not in html_body:
        add(
            'add_unsubscribe',
            'compliance',
            'high',
            'Add unsubscribe link',
            'Marketing email templates should expose the native unsubscribe_url variable.',
            'Add a compact footer with an unsubscribe link using {{ unsubscribe_url }}.',
            0.94,
        )

    if '<h1' not in html_body.lower() and '<h2' not in html_body.lower():
        add(
            'add_clear_headline',
            'content',
            'medium',
            'Add a scannable headline',
            'The HTML does not contain a heading tag, which makes the message harder to scan.',
            'Add a concise H1 headline that summarizes the email value proposition.',
            0.78,
        )

    if len(html_body.strip()) < 360:
        add(
            'expand_message_structure',
            'content',
            'medium',
            'Add supporting structure',
            'The email body is short; it may need supporting copy, benefits, or next steps.',
            'Expand the email with a short intro, 2-3 benefit bullets, and a clear CTA while keeping it concise.',
            0.72,
        )

    user_variable_names = {item.name for item in variables.variables}
    has_subject_personalization = any(f'{{{{ {name}' in subject for name in user_variable_names)
    if user_variable_names and not has_subject_personalization:
        add(
            'personalize_subject',
            'personalization',
            'low',
            'Personalize the subject line',
            'The subject line does not appear to use detected user variables.',
            'Test a subject line variant that uses the most relevant user variable naturally.',
            0.68,
        )

    sample_values = payload.sample_variables or variables.sample_variables
    has_collection = any(isinstance(value, list) for value in sample_values.values())
    if has_collection and '{% for ' not in html_body:
        add(
            'use_loop_for_collection',
            'personalization',
            'medium',
            'Render collection data with a loop',
            'Sample data includes list-like values, but the template does not use a Jinja for-loop.',
            'Use a Jinja {% for %} loop to render the relevant list data in a readable section.',
            0.82,
        )

    has_boolean_or_segment = any(isinstance(value, bool) for value in sample_values.values()) or bool(
        payload.audience_summary
    )
    if has_boolean_or_segment and '{% if ' not in html_body:
        add(
            'add_conditional_copy',
            'personalization',
            'low',
            'Add conditional copy',
            'Audience or boolean sample data is available, but the template does not use Jinja conditionals.',
            'Add a small Jinja {% if %} block that changes one sentence based on audience or profile data.',
            0.65,
        )

    if not css_body.strip():
        add(
            'add_email_css',
            'design',
            'low',
            'Add basic email CSS',
            'No CSS body is defined, so previews and email clients may render inconsistently.',
            'Add simple email-safe CSS for typography, layout width, links, buttons, and footer text.',
            0.7,
        )

    if text_body and '{{ unsubscribe_url' not in text_body and 'unsubscribe_url' not in text_body:
        add(
            'sync_plain_text_unsubscribe',
            'compliance',
            'medium',
            'Add unsubscribe to plain text',
            'The plain-text body does not include the unsubscribe URL.',
            'Add an unsubscribe line to the plain-text body using {{ unsubscribe_url }}.',
            0.88,
        )

    priority_order = {'high': 0, 'medium': 1, 'low': 2}
    return sorted(
        recommendations,
        key=lambda item: (priority_order.get(item.priority, 9), -item.confidence, item.code),
    )[:8]


def _template_recommendation_summary(
    recommendations: list[AITemplateRecommendationRead],
    validation: TemplateValidationRead,
) -> list[str]:
    high_count = sum(1 for item in recommendations if item.priority == 'high')
    medium_count = sum(1 for item in recommendations if item.priority == 'medium')
    summary = [
        f'{len(recommendations)} recommendation(s) generated.',
        f'{high_count} high priority, {medium_count} medium priority.',
    ]
    if validation.ok:
        summary.append('Template validation currently passes with merged sample variables.')
    else:
        summary.append('Template validation needs attention before launch.')
    return summary


def _number(value: object) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _analytics_rows(context: Mapping[str, object]) -> list[Mapping[str, object]]:
    items = context.get('items')
    if isinstance(items, list):
        return [item for item in items if isinstance(item, Mapping)]
    return [context]


def _deterministic_analytics_analysis(
    payload: AIAnalyticsAnalysisRequest,
) -> AIAnalyticsAnalysisRead:
    context = payload.report_context or {}
    rows = _analytics_rows(context)
    sent = sum(_number(row.get('sent_count')) for row in rows)
    opened = sum(_number(row.get('opened_count')) for row in rows)
    clicked = sum(_number(row.get('clicked_count')) for row in rows)
    failed = sum(_number(row.get('failed_count')) for row in rows)
    bounced = sum(_number(row.get('bounced_count')) for row in rows)
    open_rate = opened / sent if sent else max((_number(row.get('open_rate')) for row in rows), default=0)
    click_rate = clicked / sent if sent else max((_number(row.get('click_rate')) for row in rows), default=0)
    bounce_rate = bounced / sent if sent else max((_number(row.get('bounce_rate')) for row in rows), default=0)
    recommendations: list[AIAnalyticsRecommendationRead] = []

    def add(
        code: str,
        category: str,
        priority: str,
        title: str,
        detail: str,
        suggested_action: str,
        confidence: float,
    ) -> None:
        recommendations.append(
            AIAnalyticsRecommendationRead(
                code=code,
                category=category,
                priority=priority,
                title=title,
                detail=detail,
                suggested_action=suggested_action,
                confidence=confidence,
            )
        )

    if failed > 0:
        add(
            'review_failed_delivery',
            'delivery',
            'high',
            'Review failed send records',
            f'{int(failed)} failed send record(s) appear in the selected report context.',
            'Open Delivery Manager filtered to the campaign or send job and inspect provider errors before scaling volume.',
            0.94,
        )
    if bounce_rate > 0:
        add(
            'tighten_domain_hygiene',
            'deliverability',
            'high' if bounce_rate >= 0.03 else 'medium',
            'Investigate bounce concentration',
            f'Bounce rate is {round(bounce_rate * 100, 1)}% in this report context.',
            'Run Domain Deliverability, suppress recurring bad addresses, and verify domain/authentication health.',
            0.9,
        )
    if sent > 0 and open_rate < 0.15:
        add(
            'improve_subject_and_segment',
            'engagement',
            'medium',
            'Improve opens with subject and audience tests',
            f'Open rate is {round(open_rate * 100, 1)}%, below a healthy test benchmark.',
            'Create a subject-line variant and compare performance by audience segment before broad launch.',
            0.78,
        )
    if sent > 0 and click_rate < 0.03:
        add(
            'strengthen_cta',
            'engagement',
            'medium',
            'Strengthen CTA clarity',
            f'Click rate is {round(click_rate * 100, 1)}% in this report context.',
            'Use Template Editor AI to make the primary CTA clearer, higher on the page, and tied to one offer.',
            0.8,
        )
    if not recommendations:
        add(
            'continue_controlled_testing',
            'optimization',
            'low',
            'Continue controlled testing',
            'No major risk signal is visible in the selected report context.',
            'Compare campaign variants and audience constraints while monitoring open, click, bounce, and failure trends.',
            0.7,
        )

    summary = [
        f'Analyzed {len(rows)} row(s) for {payload.report_type or "analytics"} context.',
        f'Sent {int(sent)}, opened {int(opened)}, clicked {int(clicked)}, failed {int(failed)}.',
        f'Open rate {round(open_rate * 100, 1)}%, click rate {round(click_rate * 100, 1)}%, bounce rate {round(bounce_rate * 100, 1)}%.',
    ]
    if payload.goals:
        summary.append(f'User goal focus: {"; ".join(payload.goals[:3])}.')
    return AIAnalyticsAnalysisRead(summary=summary, recommendations=recommendations)


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _deterministic_campaign_analysis(
    payload: AICampaignAnalysisRequest,
) -> AICampaignAnalysisRead:
    context = payload.campaign_context or {}
    campaign = _mapping(context.get('campaign'))
    template = _mapping(context.get('template'))
    validation = _mapping(context.get('validation'))
    audience = _mapping(context.get('audience_preview'))
    analytics = _mapping(context.get('analytics'))
    latest_send_record = _mapping(context.get('latest_send_record'))
    recommendations: list[AICampaignRecommendationRead] = []

    def add(
        code: str,
        category: str,
        priority: str,
        title: str,
        detail: str,
        suggested_instruction: str,
        confidence: float,
    ) -> None:
        recommendations.append(
            AICampaignRecommendationRead(
                code=code,
                category=category,
                priority=priority,
                title=title,
                detail=detail,
                suggested_instruction=suggested_instruction,
                confidence=confidence,
            )
        )

    errors = [str(item) for item in _list(validation.get('errors'))]
    warnings = [str(item) for item in _list(validation.get('warnings'))]
    missing_variables = [str(item) for item in _list(validation.get('missing_variables'))]
    estimated_count = int(_number(audience.get('estimated_count')))
    sent_count = int(_number(analytics.get('sent_count')))
    opened_count = int(_number(analytics.get('opened_count')))
    clicked_count = int(_number(analytics.get('clicked_count')))
    failed_count = int(_number(analytics.get('failed_count')))
    open_rate = _number(analytics.get('open_rate'))
    click_rate = _number(analytics.get('click_rate'))
    bounce_rate = _number(analytics.get('bounce_rate'))

    if not template:
        add(
            'select_template',
            'setup',
            'high',
            'Select a campaign template',
            'The campaign context does not include a usable template.',
            'Choose a template before previewing, testing, or launching this campaign.',
            0.98,
        )
    if errors or missing_variables:
        add(
            'fix_launch_validation',
            'readiness',
            'high',
            'Fix launch validation blockers',
            '; '.join([*errors, *[f'Missing variable: {name}' for name in missing_variables]][:4])
            or 'Campaign validation is not ready.',
            'Resolve validation errors and provide missing launch variables before approving or launching.',
            0.96,
        )
    if estimated_count <= 0:
        add(
            'repair_audience_targeting',
            'audience',
            'high',
            'Repair audience targeting',
            'The campaign audience preview returned no matched contacts.',
            'Open Audience Builder, preview contacts, and adjust constraints until matched contacts are visible.',
            0.94,
        )
    if not latest_send_record:
        add(
            'send_test_email',
            'testing',
            'medium',
            'Send a real test email',
            'No latest send record is present for this campaign workflow.',
            'Use Test Send with a controlled recipient and inspect delivery, rendered variables, open, and click tracking.',
            0.86,
        )
    if warnings:
        add(
            'review_validation_warnings',
            'readiness',
            'medium',
            'Review validation warnings',
            '; '.join(warnings[:4]),
            'Address warnings where practical before scaling beyond test mode.',
            0.78,
        )
    if failed_count > 0 or bounce_rate > 0:
        add(
            'triage_delivery_risk',
            'delivery',
            'high' if failed_count > 0 else 'medium',
            'Triage delivery risk',
            f'Analytics show {failed_count} failed send(s) and {round(bounce_rate * 100, 1)}% bounce rate.',
            'Open Delivery Manager and Domain Deliverability to inspect failed records and suppression opportunities.',
            0.9,
        )
    if sent_count > 0 and open_rate < 0.15:
        add(
            'test_subject_variant',
            'optimization',
            'medium',
            'Test a stronger subject line',
            f'Open rate is {round(open_rate * 100, 1)}% for this campaign context.',
            'Use Template Editor AI to create a subject/body variant and compare it with this campaign baseline.',
            0.74,
        )
    if sent_count > 0 and click_rate < 0.03:
        add(
            'improve_campaign_cta',
            'optimization',
            'medium',
            'Improve the primary CTA',
            f'Click rate is {round(click_rate * 100, 1)}% for this campaign context.',
            'Use Template Editor AI to clarify the offer, move the CTA higher, and keep one primary action.',
            0.78,
        )
    if not recommendations:
        add(
            'ready_for_controlled_launch',
            'readiness',
            'low',
            'Ready for controlled launch',
            'No major campaign workflow blocker is visible in the selected context.',
            'Approve the campaign, run a dry run, then launch to a controlled audience before broad rollout.',
            0.7,
        )

    priority_order = {'high': 0, 'medium': 1, 'low': 2}
    recommendations = sorted(
        recommendations,
        key=lambda item: (priority_order.get(item.priority, 9), -item.confidence, item.code),
    )[:8]
    summary = [
        f'Campaign: {campaign.get("name") or campaign.get("id") or "selected campaign"}.',
        f'Audience matched contacts: {estimated_count}.',
        f'Analytics: {sent_count} sent, {opened_count} opened, {clicked_count} clicked, {failed_count} failed.',
        f'{len(recommendations)} recommendation(s) generated.',
    ]
    if payload.goals:
        summary.append(f'Goal focus: {"; ".join(payload.goals[:3])}.')
    return AICampaignAnalysisRead(
        summary=summary,
        recommendations=recommendations,
        validation=dict(validation),
    )


def _audience_rules(rule_tree: Mapping[str, object]) -> list[Mapping[str, object]]:
    rules: list[Mapping[str, object]] = []
    for item in _list(rule_tree.get('rules')):
        if not isinstance(item, Mapping):
            continue
        if 'rules' in item:
            rules.extend(_audience_rules(item))
        elif item.get('field'):
            rules.append(item)
    return rules


def _deterministic_audience_analysis(
    payload: AIAudienceAnalysisRequest,
) -> AIAudienceAnalysisRead:
    context = payload.audience_context or {}
    audience = _mapping(context.get('audience'))
    rule_tree = _mapping(context.get('rule_tree') or audience.get('rule_tree'))
    preview = _mapping(context.get('preview'))
    contact_meta = _mapping(context.get('contact_meta'))
    rules = _audience_rules(rule_tree)
    estimated_count = int(_number(preview.get('estimated_count')))
    sample_contacts = _list(preview.get('sample_contacts'))
    fields = {str(field) for field in _list(contact_meta.get('fields'))}
    attribute_fields = {f'attributes.{key}' for key in _list(contact_meta.get('attribute_keys'))}
    known_fields = fields | attribute_fields
    recommendations: list[AIAudienceRecommendationRead] = []

    def add(
        code: str,
        category: str,
        priority: str,
        title: str,
        detail: str,
        suggested_action: str,
        confidence: float,
    ) -> None:
        recommendations.append(
            AIAudienceRecommendationRead(
                code=code,
                category=category,
                priority=priority,
                title=title,
                detail=detail,
                suggested_action=suggested_action,
                confidence=confidence,
            )
        )

    unknown_fields = sorted({
        str(rule.get('field'))
        for rule in rules
        if known_fields and str(rule.get('field')) not in known_fields
    })
    if not rules:
        add(
            'add_audience_constraints',
            'targeting',
            'high',
            'Add audience constraints',
            'The audience rule tree does not contain any field rules.',
            'Use contact samples and attribute fields to add at least one meaningful rule before campaign launch.',
            0.94,
        )
    if unknown_fields:
        add(
            'fix_unknown_fields',
            'schema',
            'high',
            'Fix unknown audience fields',
            f'Rules reference fields not found in contact metadata: {", ".join(unknown_fields[:5])}.',
            'Click a known Core Field or Attribute Field chip and replace unknown field paths.',
            0.92,
        )
    if estimated_count <= 0:
        add(
            'broaden_zero_match_audience',
            'targeting',
            'high',
            'Broaden zero-match audience',
            'Preview returned zero matched contacts.',
            'Relax the most restrictive comparator, verify values against Contact Samples, then preview again.',
            0.96,
        )
    elif estimated_count < 5:
        add(
            'validate_small_audience',
            'targeting',
            'medium',
            'Validate very small audience',
            f'Preview estimates only {estimated_count} matched contact(s).',
            'Confirm this is intentional for testing; otherwise relax one rule or switch AND to OR.',
            0.78,
        )
    elif estimated_count > 50000 and len(rules) < 2:
        add(
            'narrow_broad_audience',
            'targeting',
            'medium',
            'Narrow broad audience before scaling',
            f'Preview estimates {estimated_count} contacts with limited constraints.',
            'Add behavior, source, plan, lifecycle, or recency constraints before a production campaign.',
            0.72,
        )
    if sample_contacts and not any(_mapping(contact).get('attributes') for contact in sample_contacts):
        add(
            'enrich_contact_attributes',
            'data_quality',
            'medium',
            'Enrich contact attributes',
            'Sample contacts do not expose attribute data for richer segmentation.',
            'Use Data Sources or import mappings to populate attributes such as plan, lifecycle, product, or source.',
            0.7,
        )
    if not recommendations:
        add(
            'audience_ready_for_testing',
            'readiness',
            'low',
            'Audience ready for test campaign',
            'No major audience rule or data-quality issue is visible in this context.',
            'Create a snapshot, attach the audience to a campaign, and validate send count with a dry run.',
            0.68,
        )

    priority_order = {'high': 0, 'medium': 1, 'low': 2}
    recommendations = sorted(
        recommendations,
        key=lambda item: (priority_order.get(item.priority, 9), -item.confidence, item.code),
    )[:8]
    summary = [
        f'Audience: {audience.get("name") or "current rule tree"}.',
        f'{len(rules)} rule(s), operator {rule_tree.get("operator") or "and"}.',
        f'Estimated matched contacts: {estimated_count}.',
        f'{len(recommendations)} recommendation(s) generated.',
    ]
    if payload.goals:
        summary.append(f'Goal focus: {"; ".join(payload.goals[:3])}.')
    return AIAudienceAnalysisRead(summary=summary, recommendations=recommendations)


def _deterministic_delivery_analysis(
    payload: AIDeliveryAnalysisRequest,
) -> AIDeliveryAnalysisRead:
    context = payload.delivery_context or {}
    jobs = [
        item for item in _list(_mapping(context.get('jobs')).get('items'))
        if isinstance(item, Mapping)
    ]
    records = [
        item for item in _list(_mapping(context.get('records')).get('items'))
        if isinstance(item, Mapping)
    ]
    run = _mapping(context.get('last_run'))
    recommendations: list[AIDeliveryRecommendationRead] = []

    def add(
        code: str,
        category: str,
        priority: str,
        title: str,
        detail: str,
        suggested_action: str,
        confidence: float,
    ) -> None:
        recommendations.append(
            AIDeliveryRecommendationRead(
                code=code,
                category=category,
                priority=priority,
                title=title,
                detail=detail,
                suggested_action=suggested_action,
                confidence=confidence,
            )
        )

    status_counts: dict[str, int] = {}
    provider_counts: dict[str, int] = {}
    failed_errors: dict[str, int] = {}
    retry_exhausted = 0
    for record in records:
        status = str(record.get('status') or 'unknown')
        status_counts[status] = status_counts.get(status, 0) + 1
        provider = str(record.get('provider') or 'unknown')
        provider_counts[provider] = provider_counts.get(provider, 0) + 1
        if status == 'failed':
            error = str(record.get('error_message') or 'unknown error')[:120]
            failed_errors[error] = failed_errors.get(error, 0) + 1
        if _number(record.get('attempt_count')) >= _number(record.get('max_attempts') or 3):
            retry_exhausted += 1
    queued_records = status_counts.get('queued', 0)
    sending_records = status_counts.get('sending', 0)
    failed_records = status_counts.get('failed', 0)
    suppressed_records = status_counts.get('suppressed', 0)
    stuck_jobs = [
        job for job in jobs
        if str(job.get('status')) in {'queued', 'sending'} and _number(job.get('queued_count')) > 0
    ]

    if queued_records or stuck_jobs:
        add(
            'process_queued_delivery',
            'queue',
            'high',
            'Process queued delivery',
            f'{queued_records} queued record(s) and {len(stuck_jobs)} active queued job(s) are visible.',
            'Run Process Queued for this campaign or send job, then reload records and verify progress.',
            0.94,
        )
    if sending_records:
        add(
            'watch_sending_records',
            'queue',
            'medium',
            'Watch in-flight records',
            f'{sending_records} record(s) are currently marked sending.',
            'Continue polling delivery progress before requeueing to avoid duplicate send attempts.',
            0.76,
        )
    if failed_records:
        top_error = max(failed_errors.items(), key=lambda item: item[1])[0] if failed_errors else 'unknown error'
        add(
            'triage_failed_records',
            'failure',
            'high',
            'Triage failed records',
            f'{failed_records} failed record(s) are visible. Most common error: {top_error}.',
            'Inspect provider error messages, fix configuration or recipient data, then requeue only records that are safe to retry.',
            0.95,
        )
    if retry_exhausted:
        add(
            'avoid_blind_retries',
            'failure',
            'high',
            'Avoid blind retries',
            f'{retry_exhausted} record(s) have reached max attempts.',
            'Review and fix root cause before requeueing max-attempt records.',
            0.9,
        )
    if suppressed_records:
        add(
            'review_suppression_volume',
            'suppression',
            'medium',
            'Review suppression volume',
            f'{suppressed_records} suppressed record(s) are visible.',
            'Open Suppressions and confirm unsubscribes, bounces, and manual suppressions are expected.',
            0.82,
        )
    if _number(run.get('failed_count')) > 0:
        add(
            'inspect_latest_delivery_run',
            'delivery_run',
            'medium',
            'Inspect latest delivery run failures',
            f'Last delivery run reported {int(_number(run.get("failed_count")))} failed record(s).',
            'Reload records, filter failed statuses, and inspect provider errors before the next run.',
            0.8,
        )
    if not recommendations:
        add(
            'delivery_state_clear',
            'readiness',
            'low',
            'Delivery state looks clear',
            'No major queue, retry, suppression, or failure risk is visible in the selected context.',
            'Continue monitoring send records and analytics after each campaign launch.',
            0.68,
        )

    priority_order = {'high': 0, 'medium': 1, 'low': 2}
    recommendations = sorted(
        recommendations,
        key=lambda item: (priority_order.get(item.priority, 9), -item.confidence, item.code),
    )[:8]
    provider_summary = ', '.join(
        f'{provider}: {count}' for provider, count in sorted(provider_counts.items())
    ) or 'none'
    summary = [
        f'Analyzed {len(jobs)} job(s) and {len(records)} send record(s).',
        f'Status counts: {status_counts or {}}.',
        f'Provider counts: {provider_summary}.',
        f'{len(recommendations)} recommendation(s) generated.',
    ]
    if payload.goals:
        summary.append(f'Goal focus: {"; ".join(payload.goals[:3])}.')
    return AIDeliveryAnalysisRead(summary=summary, recommendations=recommendations)


def _deterministic_journey_analysis(
    payload: AIJourneyAnalysisRequest,
) -> AIJourneyAnalysisRead:
    context = payload.journey_context or {}
    journey = _mapping(context.get('journey'))
    graph = _mapping(context.get('graph'))
    enrollments = _mapping(context.get('enrollments'))
    executions = _mapping(context.get('executions'))
    nodes = [item for item in _list(graph.get('nodes')) if isinstance(item, Mapping)]
    edges = [item for item in _list(graph.get('edges')) if isinstance(item, Mapping)]
    enrollment_items = [
        item for item in _list(enrollments.get('items')) if isinstance(item, Mapping)
    ]
    execution_items = [
        item for item in _list(executions.get('items')) if isinstance(item, Mapping)
    ]
    recommendations: list[AIJourneyRecommendationRead] = []

    def add(
        code: str,
        category: str,
        priority: str,
        title: str,
        detail: str,
        suggested_action: str,
        confidence: float,
    ) -> None:
        recommendations.append(
            AIJourneyRecommendationRead(
                code=code,
                category=category,
                priority=priority,
                title=title,
                detail=detail,
                suggested_action=suggested_action,
                confidence=confidence,
            )
        )

    status = str(journey.get('status') or 'draft')
    step_count = len(_list(journey.get('steps'))) or len(nodes)
    failed_nodes = [node for node in nodes if str(node.get('state')) == 'failed']
    active_nodes = [node for node in nodes if str(node.get('state')) == 'active']
    queued_send_nodes = [
        node for node in nodes
        if _number(_mapping(node.get('counts')).get('queued_send_count')) > 0
    ]
    send_email_nodes = [
        node for node in nodes
        if str(node.get('step_type')) == 'send_email'
    ]
    branch_nodes = [
        node for node in nodes
        if str(node.get('step_type')) == 'branch'
    ]
    source_ids = {str(edge.get('source')) for edge in edges}
    target_ids = {str(edge.get('target')) for edge in edges}
    node_ids = {str(node.get('id')) for node in nodes}
    dangling_edges = [
        edge for edge in edges
        if str(edge.get('source')) not in node_ids or str(edge.get('target')) not in node_ids
    ]
    terminal_non_action_nodes = [
        node for node in nodes
        if str(node.get('id')) not in source_ids and str(node.get('step_type')) in {'branch', 'wait'}
    ]
    unreachable_nodes = [
        node for node in nodes[1:]
        if str(node.get('id')) not in target_ids
    ]
    failed_executions = [
        item for item in execution_items
        if str(item.get('status')) == 'failed' or item.get('error_message')
    ]
    active_enrollments = [
        item for item in enrollment_items
        if str(item.get('status')) == 'active'
    ]

    if step_count == 0:
        add(
            'add_journey_steps',
            'structure',
            'high',
            'Add journey steps',
            'The journey has no steps, so contacts cannot progress.',
            'Add at least one send, wait, branch, update, or webhook step before activation.',
            0.98,
        )
    if status == 'active' and step_count == 0:
        add(
            'pause_empty_active_journey',
            'readiness',
            'high',
            'Pause empty active journey',
            'The journey is active but has no steps.',
            'Pause the journey until the path is built and reviewed.',
            0.96,
        )
    if send_email_nodes and any(not _mapping(node.get('config')).get('template_id') for node in send_email_nodes):
        add(
            'configure_send_templates',
            'content',
            'high',
            'Configure send-email templates',
            'One or more send_email steps do not expose a template_id in their config.',
            'Select each send_email step and set a template_id before enrolling contacts.',
            0.9,
        )
    if branch_nodes and not any(str(edge.get('edge_type')) == 'branch' for edge in edges):
        add(
            'connect_branch_outcomes',
            'structure',
            'high',
            'Connect branch outcomes',
            'A branch step exists but no branch edges are visible in the graph.',
            'Configure branch next_step_id values for matched/default outcomes and reload the graph.',
            0.88,
        )
    if dangling_edges:
        add(
            'fix_dangling_edges',
            'structure',
            'high',
            'Fix dangling graph edges',
            f'{len(dangling_edges)} edge(s) reference missing source or target nodes.',
            'Open affected step configs and replace stale next_step_id values.',
            0.86,
        )
    if terminal_non_action_nodes:
        add(
            'review_terminal_steps',
            'structure',
            'medium',
            'Review terminal wait or branch steps',
            f'{len(terminal_non_action_nodes)} wait/branch step(s) end the path.',
            'Confirm those are intentional exits, or connect them to a next step.',
            0.74,
        )
    if unreachable_nodes:
        add(
            'review_unreachable_steps',
            'structure',
            'medium',
            'Review unreachable steps',
            f'{len(unreachable_nodes)} step(s) are not targeted by another graph edge.',
            'Confirm they are entry steps or wire them into the journey path.',
            0.72,
        )
    if failed_nodes or failed_executions:
        add(
            'triage_failed_journey_steps',
            'execution',
            'high',
            'Triage failed journey steps',
            f'{len(failed_nodes)} failed graph node(s) and {len(failed_executions)} failed execution(s) are visible.',
            'Inspect recent errors, fix step config, then process due work after confirming retry behavior.',
            0.92,
        )
    if queued_send_nodes:
        add(
            'process_queued_journey_sends',
            'delivery',
            'medium',
            'Process queued journey sends',
            f'{len(queued_send_nodes)} step node(s) have queued send records.',
            'Open Delivery Manager or run delivery processing for queued sends generated by this journey.',
            0.8,
        )
    if active_enrollments and not active_nodes:
        add(
            'process_due_enrollments',
            'execution',
            'medium',
            'Process due enrollments',
            f'{len(active_enrollments)} active enrollment(s) exist but no active graph node is shown.',
            'Run Process Due and reload graph/enrollments to verify current state.',
            0.76,
        )
    if not recommendations:
        add(
            'journey_ready_for_testing',
            'readiness',
            'low',
            'Journey ready for controlled testing',
            'No major structural or execution risk is visible in the selected context.',
            'Enroll one test contact, process due steps, and verify sends/events before production activation.',
            0.68,
        )

    priority_order = {'high': 0, 'medium': 1, 'low': 2}
    recommendations = sorted(
        recommendations,
        key=lambda item: (priority_order.get(item.priority, 9), -item.confidence, item.code),
    )[:8]
    summary = [
        f'Journey: {journey.get("name") or journey.get("id") or "selected journey"}.',
        f'Status {status}, {step_count} step(s), {len(edges)} edge(s).',
        f'{len(enrollment_items)} enrollment row(s), {len(execution_items)} execution row(s) in context.',
        f'{len(recommendations)} recommendation(s) generated.',
    ]
    if payload.goals:
        summary.append(f'Goal focus: {"; ".join(payload.goals[:3])}.')
    return AIJourneyAnalysisRead(summary=summary, recommendations=recommendations)


@router.post('/ai/templates/draft', response_model=AITemplateDraftRead)
def draft_template_with_ai(
    payload: AITemplateDraftRequest,
    db: DbSession,
    settings: SettingsDep,
) -> AITemplateDraftRead:
    draft = _template_draft_payload(payload, settings)
    template_request = TemplateValidationRequest(
        subject=draft['subject'],
        html_body=draft['html_body'],
        css_body=cast(str | None, draft.get('css_body')),
        text_body=cast(str | None, draft.get('text_body')),
        variables={},
    )
    template_service = TemplateService(db)
    variables = template_service.variables(template_request)
    validation = template_service.validate(
        TemplateValidationRequest(
            subject=template_request.subject,
            html_body=template_request.html_body,
            css_body=template_request.css_body,
            text_body=template_request.text_body,
            variables=variables.sample_variables,
        )
    )
    return AITemplateDraftRead(
        subject=cast(str, draft['subject']),
        html_body=cast(str, draft['html_body']),
        css_body=cast(str | None, draft.get('css_body')),
        text_body=cast(str | None, draft.get('text_body')),
        sample_variables=variables.sample_variables,
        notes=cast(list[str], draft['notes']),
        validation=validation,
        template_variables=variables,
        provider=cast(str, draft.get('provider', 'email-engine')),
        model=cast(str, draft.get('model', 'deterministic-template-draft-v1')),
    )


@router.post('/ai/templates/edit', response_model=AITemplateDraftRead)
def edit_template_with_ai(
    payload: AITemplateEditRequest,
    db: DbSession,
    settings: SettingsDep,
) -> AITemplateDraftRead:
    draft = _template_edit_payload(payload, settings)
    changed_fields, change_summary = _ai_edit_change_metadata(payload, draft)
    template_request = TemplateValidationRequest(
        subject=draft['subject'],
        html_body=draft['html_body'],
        css_body=cast(str | None, draft.get('css_body')),
        text_body=cast(str | None, draft.get('text_body')),
        variables=payload.sample_variables,
    )
    template_service = TemplateService(db)
    variables = template_service.variables(template_request)
    render_variables = {**variables.sample_variables, **payload.sample_variables}
    validation = template_service.validate(
        TemplateValidationRequest(
            subject=template_request.subject,
            html_body=template_request.html_body,
            css_body=template_request.css_body,
            text_body=template_request.text_body,
            variables=render_variables,
        )
    )
    return AITemplateDraftRead(
        subject=cast(str, draft['subject']),
        html_body=cast(str, draft['html_body']),
        css_body=cast(str | None, draft.get('css_body')),
        text_body=cast(str | None, draft.get('text_body')),
        changed_fields=changed_fields,
        change_summary=change_summary,
        sample_variables=render_variables,
        notes=cast(list[str], draft['notes']),
        validation=validation,
        template_variables=variables,
        provider=cast(str, draft.get('provider', 'email-engine')),
        model=cast(str, draft.get('model', 'deterministic-template-edit-v1')),
    )


@router.post('/ai/templates/recommend', response_model=AITemplateRecommendationsRead)
def recommend_template_improvements(
    payload: AITemplateRecommendRequest,
    db: DbSession,
    settings: SettingsDep,
) -> AITemplateRecommendationsRead:
    template_request = TemplateValidationRequest(
        subject=payload.current_subject,
        html_body=payload.current_html,
        css_body=payload.current_css,
        text_body=payload.current_text,
        variables=payload.sample_variables,
    )
    template_service = TemplateService(db)
    variables = template_service.variables(template_request)
    render_variables = {**variables.sample_variables, **payload.sample_variables}
    validation = template_service.validate(
        TemplateValidationRequest(
            subject=payload.current_subject,
            html_body=payload.current_html,
            css_body=payload.current_css,
            text_body=payload.current_text,
            variables=render_variables,
        )
    )
    recommendations, summary, provider, model = _template_recommendation_payload(
        payload,
        validation,
        variables,
        settings,
    )
    return AITemplateRecommendationsRead(
        recommendations=recommendations,
        summary=summary,
        sample_variables=render_variables,
        validation=validation,
        template_variables=variables,
        provider=provider,
        model=model,
    )


@router.post('/ai/analytics/analyze', response_model=AIAnalyticsAnalysisRead)
def analyze_analytics_with_ai(
    payload: AIAnalyticsAnalysisRequest,
) -> AIAnalyticsAnalysisRead:
    return _deterministic_analytics_analysis(payload)


@router.post('/ai/campaigns/analyze', response_model=AICampaignAnalysisRead)
def analyze_campaign_with_ai(
    payload: AICampaignAnalysisRequest,
) -> AICampaignAnalysisRead:
    return _deterministic_campaign_analysis(payload)


@router.post('/ai/audiences/analyze', response_model=AIAudienceAnalysisRead)
def analyze_audience_with_ai(
    payload: AIAudienceAnalysisRequest,
) -> AIAudienceAnalysisRead:
    return _deterministic_audience_analysis(payload)


@router.post('/ai/delivery/analyze', response_model=AIDeliveryAnalysisRead)
def analyze_delivery_with_ai(
    payload: AIDeliveryAnalysisRequest,
) -> AIDeliveryAnalysisRead:
    return _deterministic_delivery_analysis(payload)


@router.post('/ai/journeys/analyze', response_model=AIJourneyAnalysisRead)
def analyze_journey_with_ai(
    payload: AIJourneyAnalysisRequest,
) -> AIJourneyAnalysisRead:
    return _deterministic_journey_analysis(payload)


def _tracking_request_metadata(request: Request) -> JsonObject:
    client_host = request.client.host if request.client else None
    return {
        'ip': client_host,
        'user_agent': request.headers.get('user-agent'),
        'referer': request.headers.get('referer'),
    }


def _is_http_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {'http', 'https'} and bool(parsed.netloc)


@router.get('/templates', response_model=list[TemplateRead])
def list_templates(
    db: DbSession,
    limit: Limit = 100,
    offset: Offset = 0,
) -> list[EmailTemplate]:
    return TemplateService(db).list(limit=limit, offset=offset)


@router.get('/templates/list', response_model=ListResponse[TemplateRead])
def list_templates_enveloped(
    db: DbSession,
    limit: Limit = 100,
    offset: Offset = 0,
) -> dict[str, object]:
    service = TemplateService(db)
    return {
        'items': service.list(limit=limit, offset=offset),
        'limit': limit,
        'offset': offset,
        'total': service.count(),
    }


@router.post('/templates', response_model=TemplateRead)
def create_template(payload: TemplateCreate, db: DbSession) -> EmailTemplate:
    return TemplateService(db).create(payload)


@router.post('/templates/samples', response_model=list[TemplateRead])
def create_sample_templates(db: DbSession, reset: bool = False) -> list[EmailTemplate]:
    return TemplateService(db).ensure_sample_templates(reset=reset)


@router.get('/templates/{template_id}/versions', response_model=list[TemplateVersionRead])
def list_template_versions(template_id: UUID, db: DbSession) -> list[EmailTemplateVersion]:
    service = TemplateService(db)
    if not service.get(template_id):
        raise HTTPException(status_code=404, detail='Template not found')
    return service.list_versions(template_id)


@router.post('/templates/{template_id}/versions', response_model=TemplateVersionRead)
def create_template_version(
    template_id: UUID, payload: TemplateVersionCreate, db: DbSession
) -> object:
    version = TemplateService(db).create_version(template_id, payload)
    if not version:
        raise HTTPException(status_code=404, detail='Template not found')
    return version


@router.get('/templates/{template_id}/document', response_model=TemplateDocumentRead)
def get_template_document(template_id: UUID, db: DbSession) -> TemplateDocumentRead:
    document = TemplateService(db).current_document(template_id)
    if not document:
        raise HTTPException(status_code=404, detail='Template not found')
    return document


@router.put('/templates/{template_id}/document', response_model=TemplateDocumentRead)
def update_template_document(
    template_id: UUID, payload: TemplateDocumentUpdate, db: DbSession
) -> TemplateDocumentRead:
    document = TemplateService(db).update_document(template_id, payload)
    if not document:
        raise HTTPException(status_code=404, detail='Template not found')
    return document


@router.post('/templates/document/render', response_model=TemplatePreviewRead)
def render_template_document(
    payload: TemplateDocumentRenderRequest, db: DbSession
) -> TemplatePreviewRead:
    return TemplateService(db).preview(_document_preview_request(payload))


@router.post('/templates/document/import-html', response_model=TemplateDocumentImportRead)
def import_template_document_html(
    payload: TemplateDocumentImportRequest,
) -> TemplateDocumentImportRead:
    document = html_to_document(payload.html_body)
    blocks = document.get('blocks')
    block_list = blocks if isinstance(blocks, list) else []
    raw_count = sum(
        1
        for block in block_list
        if isinstance(block, dict) and block.get('type') in {'html', 'raw'}
    )
    return TemplateDocumentImportRead(
        document_json=document,
        block_count=len(block_list),
        raw_block_count=raw_count,
    )


@router.post('/templates/document/variables', response_model=TemplateVariablesRead)
def inspect_template_document_variables(
    payload: TemplateDocumentRenderRequest, db: DbSession
) -> TemplateVariablesRead:
    return TemplateService(db).variables(_document_preview_request(payload))


@router.post('/templates/document/validate', response_model=TemplateValidationRead)
def validate_template_document(
    payload: TemplateDocumentRenderRequest, db: DbSession
) -> TemplateValidationRead:
    return TemplateService(db).validate(_document_preview_request(payload))


def _document_preview_request(payload: TemplateDocumentRenderRequest) -> TemplatePreviewRequest:
    return TemplatePreviewRequest(
        subject=payload.subject,
        html_body=document_to_html(payload.document_json),
        css_body=payload.css_body,
        text_body=payload.text_body,
        variables=payload.variables,
    )


@router.post('/templates/preview', response_model=TemplatePreviewRead)
def preview_template(payload: TemplatePreviewRequest, db: DbSession) -> TemplatePreviewRead:
    return TemplateService(db).preview(payload)


@router.post('/templates/lint', response_model=TemplateLintRead)
def lint_template(payload: TemplateValidationRequest, db: DbSession) -> TemplateLintRead:
    return TemplateService(db).lint(payload)


@router.post('/templates/validate', response_model=TemplateValidationRead)
def validate_template(
    payload: TemplateValidationRequest, db: DbSession
) -> TemplateValidationRead:
    return TemplateService(db).validate(payload)


@router.post('/templates/variables', response_model=TemplateVariablesRead)
def inspect_template_variables(
    payload: TemplateValidationRequest, db: DbSession
) -> TemplateVariablesRead:
    return TemplateService(db).variables(payload)


@router.get('/templates/{template_id}/variables', response_model=TemplateVariablesRead)
def inspect_stored_template_variables(
    template_id: UUID, db: DbSession
) -> TemplateVariablesRead:
    variables = TemplateService(db).variables_for_template(template_id)
    if not variables:
        raise HTTPException(status_code=404, detail='Template not found')
    return variables


@router.get('/templates/{template_id}/preview-sample', response_model=TemplatePreviewRead)
def preview_stored_template_sample(
    template_id: UUID, db: DbSession
) -> TemplatePreviewRead:
    preview = TemplateService(db).preview_sample(template_id)
    if not preview:
        raise HTTPException(status_code=404, detail='Template not found')
    return preview


@router.get('/templates/{template_id}', response_model=TemplateRead)
def get_template(template_id: UUID, db: DbSession) -> EmailTemplate:
    template = TemplateService(db).get(template_id)
    if not template:
        raise HTTPException(status_code=404, detail='Template not found')
    return template


@router.patch('/templates/{template_id}', response_model=TemplateRead)
def update_template(
    template_id: UUID, payload: TemplateUpdate, db: DbSession
) -> EmailTemplate:
    template = TemplateService(db).update(template_id, payload)
    if not template:
        raise HTTPException(status_code=404, detail='Template not found')
    return template


@router.delete('/templates/{template_id}', response_model=DeleteResponse)
def delete_template(template_id: UUID, db: DbSession) -> dict[str, UUID]:
    if not TemplateService(db).delete(template_id):
        raise HTTPException(status_code=404, detail='Template not found')
    return {'id': template_id}


@router.get('/campaigns', response_model=list[CampaignRead])
def list_campaigns(
    db: DbSession,
    limit: Limit = 100,
    offset: Offset = 0,
) -> list[Campaign]:
    return CampaignService(db).list_items(limit=limit, offset=offset)


@router.get('/campaigns/list', response_model=ListResponse[CampaignRead])
def list_campaigns_enveloped(
    db: DbSession,
    limit: Limit = 100,
    offset: Offset = 0,
) -> dict[str, object]:
    service = CampaignService(db)
    return {
        'items': service.list_items(limit=limit, offset=offset),
        'limit': limit,
        'offset': offset,
        'total': service.count(),
    }


@router.post('/campaigns', response_model=CampaignRead)
def create_campaign(payload: CampaignCreate, db: DbSession) -> Campaign:
    return CampaignService(db).create(payload)


@router.post('/campaigns/process-due', response_model=CampaignProcessDueRead)
def process_due_campaigns(db: DbSession, limit: Limit = 25) -> CampaignProcessDueRead:
    return CampaignService(db).process_due(limit=limit)


@router.get('/campaigns/{campaign_id}', response_model=CampaignRead)
def get_campaign(campaign_id: UUID, db: DbSession) -> Campaign:
    campaign = CampaignService(db).get(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail='Campaign not found')
    return campaign


@router.patch('/campaigns/{campaign_id}', response_model=CampaignRead)
def update_campaign(
    campaign_id: UUID, payload: CampaignUpdate, db: DbSession
) -> Campaign:
    try:
        campaign = CampaignService(db).update(campaign_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not campaign:
        raise HTTPException(status_code=404, detail='Campaign not found')
    return campaign


@router.post('/campaigns/{campaign_id}/clone', response_model=CampaignRead)
def clone_campaign(
    campaign_id: UUID, payload: CampaignCloneRequest, db: DbSession
) -> Campaign:
    campaign = CampaignService(db).clone(campaign_id, payload)
    if not campaign:
        raise HTTPException(status_code=404, detail='Campaign not found')
    return campaign


@router.delete('/campaigns/{campaign_id}', response_model=DeleteResponse)
def delete_campaign(campaign_id: UUID, db: DbSession) -> dict[str, UUID]:
    if not CampaignService(db).delete(campaign_id):
        raise HTTPException(status_code=404, detail='Campaign not found')
    return {'id': campaign_id}


@router.post('/campaigns/{campaign_id}/validate', response_model=CampaignValidationRead)
def validate_campaign(
    campaign_id: UUID, payload: CampaignLaunchRequest, db: DbSession
) -> CampaignValidationRead:
    validation = CampaignService(db).validate(campaign_id, payload=payload)
    if not validation:
        raise HTTPException(status_code=404, detail='Campaign not found')
    return validation


@router.post('/campaigns/{campaign_id}/approve', response_model=CampaignValidationRead)
def approve_campaign(
    campaign_id: UUID, payload: CampaignLaunchRequest, db: DbSession
) -> CampaignValidationRead:
    validation = CampaignService(db).approve(campaign_id, payload=payload)
    if not validation:
        raise HTTPException(status_code=404, detail='Campaign not found')
    if not validation.ok:
        raise HTTPException(status_code=400, detail=validation.errors or validation.warnings)
    return validation


@router.post('/campaigns/{campaign_id}/launch', response_model=CampaignLaunchRead)
def launch_campaign(
    campaign_id: UUID, payload: CampaignLaunchRequest, db: DbSession
) -> CampaignLaunchRead:
    try:
        launch = CampaignService(db).launch(campaign_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not launch:
        raise HTTPException(status_code=404, detail='Campaign not found')
    return launch


@router.post('/campaigns/{campaign_id}/test-send', response_model=CampaignTestSendResponse)
def send_campaign_test_email(
    campaign_id: UUID,
    payload: CampaignTestSendRequest,
    db: DbSession,
    settings: SettingsDep,
) -> dict[str, object]:
    try:
        return SendingService(db, settings).send_campaign_test(
            campaign_id=campaign_id,
            to_email=str(payload.to_email),
            variables=payload.variables,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post('/campaigns/{campaign_id}/test-preview', response_model=CampaignTestPreviewRead)
def preview_campaign_test_email(
    campaign_id: UUID,
    payload: CampaignTestPreviewRequest,
    db: DbSession,
    settings: SettingsDep,
) -> dict[str, object]:
    try:
        return SendingService(db, settings).preview_campaign_test(
            campaign_id=campaign_id,
            variables=payload.variables,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get('/campaigns/{campaign_id}/workflow-status', response_model=CampaignWorkflowStatusRead)
def get_campaign_workflow_status(
    campaign_id: UUID,
    db: DbSession,
) -> CampaignWorkflowStatusRead:
    campaign_service = CampaignService(db)
    campaign = campaign_service.get(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail='Campaign not found')

    template_service = TemplateService(db)
    template = template_service.get(campaign.template_id)
    template_variables = template_service.variables_for_template(campaign.template_id)
    validation_variables = template_variables.sample_variables if template_variables else {}
    validation = campaign_service.validate(
        campaign_id,
        CampaignLaunchRequest(variables=validation_variables),
    )
    if not validation:
        raise HTTPException(status_code=404, detail='Campaign not found')

    audience_preview = None
    try:
        estimated_count, sample_contacts = AudienceService(db).preview(
            campaign.audience_query,
            limit=25,
        )
        audience_preview = AudiencePreviewRead(
            estimated_count=estimated_count,
            sample_contacts=sample_contacts,
        )
    except ValueError:
        audience_preview = None

    latest_send_job = next(
        iter(campaign_service.list_send_jobs(campaign_id=campaign_id, limit=1, offset=0)),
        None,
    )
    latest_send_record = next(
        iter(campaign_service.list_send_records(campaign_id=campaign_id, limit=1, offset=0)),
        None,
    )
    latest_proof_attempt = campaign_service._latest_campaign_test_attempt(campaign_id)
    latest_proof_route = None
    if latest_proof_attempt:
        proof_metadata = latest_proof_attempt.metadata_json or {}
        route_resolved = proof_metadata.get('mta_route_resolved')
        if route_resolved is True:
            proof_route_status = 'resolved'
        elif route_resolved is False:
            proof_route_status = 'blocked'
        elif latest_proof_attempt.status == 'failed':
            proof_route_status = 'blocked'
        else:
            proof_route_status = 'attempted'
        latest_proof_route = CampaignProofRouteRead(
            delivery_attempt_id=latest_proof_attempt.id,
            send_record_id=latest_proof_attempt.send_record_id,
            status=latest_proof_attempt.status,
            route_type=latest_proof_attempt.route_type,
            route_key=latest_proof_attempt.route_key,
            mta_route_status=proof_route_status,
            mta_provider=(
                str(proof_metadata.get('mta_provider'))
                if proof_metadata.get('mta_provider') is not None
                else None
            ),
            mta_route_send_type=(
                str(proof_metadata.get('mta_route_send_type'))
                if proof_metadata.get('mta_route_send_type') is not None
                else None
            ),
            mta_rule_hit_send_type=(
                str(proof_metadata.get('mta_rule_hit_send_type'))
                if proof_metadata.get('mta_rule_hit_send_type') is not None
                else None
            ),
            mta_rule_hit_sender_domain=(
                str(proof_metadata.get('mta_rule_hit_sender_domain'))
                if proof_metadata.get('mta_rule_hit_sender_domain') is not None
                else None
            ),
            mta_rule_hit_recipient_domain=(
                str(proof_metadata.get('mta_rule_hit_recipient_domain'))
                if proof_metadata.get('mta_rule_hit_recipient_domain') is not None
                else None
            ),
            mta_rule_hit_name=(
                str(proof_metadata.get('mta_rule_hit_name'))
                if proof_metadata.get('mta_rule_hit_name') is not None
                else None
            ),
            mta_rule_hit_source=(
                str(proof_metadata.get('mta_rule_hit_source'))
                if proof_metadata.get('mta_rule_hit_source') is not None
                else None
            ),
            mta_rule_hit_pool_source=(
                str(proof_metadata.get('mta_rule_hit_pool_source'))
                if proof_metadata.get('mta_rule_hit_pool_source') is not None
                else None
            ),
            mta_rule_hit_provider_preference=(
                list(proof_metadata.get('mta_rule_hit_provider_preference'))
                if isinstance(proof_metadata.get('mta_rule_hit_provider_preference'), list)
                else None
            ),
            mta_submission_host=(
                str(proof_metadata.get('mta_submission_host'))
                if proof_metadata.get('mta_submission_host') is not None
                else None
            ),
            mta_hostname=(
                str(proof_metadata.get('mta_hostname'))
                if proof_metadata.get('mta_hostname') is not None
                else None
            ),
            smtp_response_code=latest_proof_attempt.smtp_response_code,
            smtp_response=latest_proof_attempt.smtp_response,
            error_message=latest_proof_attempt.error_message,
        )
    analytics = AnalyticsService(db).campaign_metrics(campaign_id)

    return CampaignWorkflowStatusRead(
        campaign=campaign,
        template=template,
        template_variables=template_variables,
        validation=validation,
        audience_preview=audience_preview,
        analytics=analytics,
        latest_send_job=latest_send_job,
        latest_send_record=latest_send_record,
        latest_proof_route=latest_proof_route,
    )


@router.get('/campaigns/{campaign_id}/analytics', response_model=CampaignAnalyticsRead)
def get_campaign_analytics(
    campaign_id: UUID,
    db: DbSession,
    send_job_id: UUID | None = None,
) -> CampaignAnalyticsRead:
    metrics = AnalyticsService(db).campaign_metrics(campaign_id, send_job_id)
    if not metrics:
        raise HTTPException(status_code=404, detail='Campaign or send job not found')
    return metrics


@router.get('/campaigns/{campaign_id}/analytics/timeline', response_model=CampaignTimelineRead)
def get_campaign_analytics_timeline(
    campaign_id: UUID,
    db: DbSession,
    days: Annotated[int, Query(ge=1, le=365)] = 30,
    send_job_id: UUID | None = None,
) -> CampaignTimelineRead:
    timeline = AnalyticsService(db).campaign_timeline(
        campaign_id=campaign_id,
        days=days,
        send_job_id=send_job_id,
    )
    if not timeline:
        raise HTTPException(status_code=404, detail='Campaign or send job not found')
    return timeline


@router.get('/analytics/overview', response_model=AnalyticsOverviewRead)
def get_analytics_overview(
    db: DbSession, recent_event_limit: RecentEventLimit = 25
) -> AnalyticsOverviewRead:
    return AnalyticsService(db).overview(recent_event_limit=recent_event_limit)


@router.get('/analytics/campaigns', response_model=ListResponse[CampaignPerformanceRead])
def list_campaign_performance(
    db: DbSession,
    limit: Limit = 100,
    offset: Offset = 0,
) -> dict[str, object]:
    items, total = AnalyticsService(db).campaign_performance(limit=limit, offset=offset)
    return {'items': items, 'limit': limit, 'offset': offset, 'total': total}


@router.get('/analytics/campaign-summaries', response_model=ListResponse[CampaignListSummaryRead])
def list_campaign_summaries(
    db: DbSession,
    campaign_id: Annotated[list[UUID] | None, Query()] = None,
    limit: Limit = 100,
    offset: Offset = 0,
) -> dict[str, object]:
    analytics = AnalyticsService(db)
    campaign_service = CampaignService(db)
    if campaign_id:
        page_ids = campaign_id[offset : offset + limit]
        items = [
            item
            for item in (
                _campaign_performance_for_id(db, analytics, selected_id)
                for selected_id in page_ids
            )
            if item
        ]
        total = len(campaign_id)
    else:
        items, total = analytics.campaign_performance(limit=limit, offset=offset)
    summaries = []
    for item in items:
        latest_send_job = next(
            iter(
                campaign_service.list_send_jobs(
                    campaign_id=item.campaign_id,
                    limit=1,
                    offset=0,
                )
            ),
            None,
        )
        summaries.append(
            CampaignListSummaryRead(
                campaign=item,
                latest_send_job=latest_send_job,
                progress=_send_job_progress(db, latest_send_job) if latest_send_job else None,
            )
        )
    return {'items': summaries, 'limit': limit, 'offset': offset, 'total': total}


def _campaign_performance_for_id(
    db: Session,
    analytics: AnalyticsService,
    campaign_id: UUID,
) -> CampaignPerformanceRead | None:
    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        return None
    metrics = analytics.campaign_metrics(campaign_id)
    if not metrics:
        return None
    return CampaignPerformanceRead(
        campaign_id=campaign.id,
        name=campaign.name,
        status=campaign.status,
        requested_count=metrics.requested_count,
        queued_count=metrics.queued_count,
        sent_count=metrics.sent_count,
        failed_count=metrics.failed_count,
        suppressed_count=metrics.suppressed_count,
        delivered_count=metrics.delivered_count,
        opened_count=metrics.opened_count,
        clicked_count=metrics.clicked_count,
        bounced_count=metrics.bounced_count,
        complained_count=metrics.complained_count,
        unsubscribed_count=metrics.unsubscribed_count,
        open_rate=metrics.open_rate,
        click_rate=metrics.click_rate,
        bounce_rate=metrics.bounce_rate,
    )


@router.get('/analytics/audiences', response_model=ListResponse[AudiencePerformanceRead])
def list_audience_performance(
    db: DbSession,
    limit: Limit = 100,
    offset: Offset = 0,
    audience_id: UUID | None = None,
) -> dict[str, object]:
    items, total = AnalyticsService(db).audience_performance(
        limit=limit,
        offset=offset,
        audience_id=audience_id,
    )
    return {'items': items, 'limit': limit, 'offset': offset, 'total': total}


@router.get('/analytics/domains', response_model=ListResponse[DomainDeliverabilityRead])
def list_domain_deliverability(
    db: DbSession,
    limit: Limit = 100,
    offset: Offset = 0,
    campaign_id: UUID | None = None,
    send_job_id: UUID | None = None,
    provider: str | None = None,
) -> dict[str, object]:
    items, total = AnalyticsService(db).domain_deliverability(
        limit=limit,
        offset=offset,
        campaign_id=campaign_id,
        send_job_id=send_job_id,
        provider=provider,
    )
    return {'items': items, 'limit': limit, 'offset': offset, 'total': total}


@router.get('/analytics/journeys', response_model=ListResponse[JourneyPerformanceRead])
def list_journey_performance(
    db: DbSession,
    limit: Limit = 100,
    offset: Offset = 0,
    journey_id: UUID | None = None,
) -> dict[str, object]:
    items, total = AnalyticsService(db).journey_performance(
        limit=limit,
        offset=offset,
        journey_id=journey_id,
    )
    return {'items': items, 'limit': limit, 'offset': offset, 'total': total}


@router.get('/journeys', response_model=list[JourneyRead])
def list_journeys(
    db: DbSession,
    limit: Limit = 100,
    offset: Offset = 0,
) -> list[Journey]:
    return JourneyService(db).list_items(limit=limit, offset=offset)


@router.get('/journeys/list', response_model=ListResponse[JourneyRead])
def list_journeys_enveloped(
    db: DbSession,
    limit: Limit = 100,
    offset: Offset = 0,
) -> dict[str, object]:
    service = JourneyService(db)
    return {
        'items': service.list_items(limit=limit, offset=offset),
        'limit': limit,
        'offset': offset,
        'total': service.count(),
    }


@router.post('/journeys', response_model=JourneyRead)
def create_journey(payload: JourneyCreate, db: DbSession) -> Journey:
    return JourneyService(db).create(payload)


@router.get('/journeys/{journey_id}', response_model=JourneyRead)
def get_journey(journey_id: UUID, db: DbSession) -> Journey:
    journey = JourneyService(db).get(journey_id)
    if not journey:
        raise HTTPException(status_code=404, detail='Journey not found')
    return journey


@router.get('/journeys/{journey_id}/graph', response_model=JourneyGraphRead)
def get_journey_graph(journey_id: UUID, db: DbSession) -> JourneyGraphRead:
    graph = JourneyService(db).graph(journey_id)
    if not graph:
        raise HTTPException(status_code=404, detail='Journey not found')
    return graph


@router.patch('/journeys/{journey_id}', response_model=JourneyRead)
def update_journey(journey_id: UUID, payload: JourneyUpdate, db: DbSession) -> Journey:
    journey = JourneyService(db).update(journey_id, payload)
    if not journey:
        raise HTTPException(status_code=404, detail='Journey not found')
    return journey


@router.delete('/journeys/{journey_id}', response_model=DeleteResponse)
def delete_journey(journey_id: UUID, db: DbSession) -> DeleteResponse:
    deleted = JourneyService(db).delete(journey_id)
    if not deleted:
        raise HTTPException(status_code=404, detail='Journey not found')
    return DeleteResponse(id=journey_id)


@router.post('/journeys/{journey_id}/steps', response_model=JourneyStepRead)
def create_journey_step(
    journey_id: UUID,
    payload: JourneyStepCreate,
    db: DbSession,
) -> JourneyStep:
    step = JourneyService(db).create_step(journey_id, payload)
    if not step:
        raise HTTPException(status_code=404, detail='Journey not found')
    return step


@router.patch('/journey-steps/{step_id}', response_model=JourneyStepRead)
def update_journey_step(
    step_id: UUID,
    payload: JourneyStepUpdate,
    db: DbSession,
) -> JourneyStep:
    step = JourneyService(db).update_step(step_id, payload)
    if not step:
        raise HTTPException(status_code=404, detail='Journey step not found')
    return step


@router.delete('/journey-steps/{step_id}', response_model=DeleteResponse)
def delete_journey_step(step_id: UUID, db: DbSession) -> DeleteResponse:
    deleted = JourneyService(db).delete_step(step_id)
    if not deleted:
        raise HTTPException(status_code=404, detail='Journey step not found')
    return DeleteResponse(id=step_id)


@router.post('/journeys/{journey_id}/enrollments', response_model=JourneyEnrollmentRead)
def enroll_contact_in_journey(
    journey_id: UUID,
    payload: JourneyEnrollmentCreate,
    db: DbSession,
) -> JourneyEnrollment:
    enrollment = JourneyService(db).enroll(journey_id, payload)
    if not enrollment:
        raise HTTPException(status_code=404, detail='Journey or contact not found')
    return enrollment


@router.get('/journey-enrollments/list', response_model=ListResponse[JourneyEnrollmentRead])
def list_journey_enrollments(
    db: DbSession,
    journey_id: UUID | None = None,
    status: JourneyEnrollmentStatus | None = None,
    limit: Limit = 100,
    offset: Offset = 0,
) -> dict[str, object]:
    service = JourneyService(db)
    return {
        'items': service.list_enrollments(
            journey_id=journey_id,
            status=status,
            limit=limit,
            offset=offset,
        ),
        'limit': limit,
        'offset': offset,
        'total': service.count_enrollments(journey_id=journey_id, status=status),
    }


@router.get(
    '/journey-step-executions/list',
    response_model=ListResponse[JourneyStepExecutionRead],
)
def list_journey_step_executions(
    db: DbSession,
    enrollment_id: UUID | None = None,
    journey_id: UUID | None = None,
    limit: Limit = 100,
    offset: Offset = 0,
) -> dict[str, object]:
    service = JourneyService(db)
    return {
        'items': service.list_executions(
            enrollment_id=enrollment_id,
            journey_id=journey_id,
            limit=limit,
            offset=offset,
        ),
        'limit': limit,
        'offset': offset,
        'total': service.count_executions(enrollment_id=enrollment_id, journey_id=journey_id),
    }


@router.post('/journeys/process', response_model=JourneyProcessRead)
def process_due_journeys(
    db: DbSession,
    limit: Limit = 25,
    journey_id: UUID | None = None,
) -> JourneyProcessRead:
    return JourneyService(db).process_due(limit=limit, journey_id=journey_id)


@router.get('/campaign-send-jobs/list', response_model=ListResponse[CampaignSendJobRead])
def list_campaign_send_jobs(
    db: DbSession,
    campaign_id: UUID | None = None,
    limit: Limit = 100,
    offset: Offset = 0,
) -> dict[str, object]:
    service = CampaignService(db)
    return {
        'items': service.list_send_jobs(campaign_id=campaign_id, limit=limit, offset=offset),
        'limit': limit,
        'offset': offset,
        'total': service.count_send_jobs(campaign_id=campaign_id),
    }


@router.get(
    '/campaign-send-jobs/{send_job_id}/progress',
    response_model=CampaignSendJobProgressRead,
)
def get_campaign_send_job_progress(send_job_id: UUID, db: DbSession) -> CampaignSendJobProgressRead:
    send_job = db.get(CampaignSendJob, send_job_id)
    if not send_job:
        raise HTTPException(status_code=404, detail='Send job not found')
    return _send_job_progress(db, send_job)


def _send_job_progress(db: Session, send_job: CampaignSendJob) -> CampaignSendJobProgressRead:
    rows = db.execute(
        select(EmailSendRecord.status, func.count())
        .where(EmailSendRecord.send_job_id == send_job.id)
        .group_by(EmailSendRecord.status)
    ).all()
    counts = {status.value: int(count) for status, count in rows}
    queued_count = counts.get('queued', 0) + counts.get('deferred', 0)
    sending_count = counts.get('sending', 0)
    sent_count = counts.get('sent', 0) + counts.get('submitted', 0) + counts.get('delivered', 0)
    failed_count = counts.get('failed', 0) + counts.get('bounced', 0)
    suppressed_count = (
        counts.get('suppressed', 0)
        + counts.get('complained', 0)
        + counts.get('unsubscribed', 0)
    )
    skipped_count = counts.get('skipped', 0)
    dead_lettered_count = counts.get('dead_lettered', 0)
    processed_count = (
        sent_count + failed_count + suppressed_count + skipped_count + dead_lettered_count
    )
    active_count = queued_count + sending_count
    denominator = max(send_job.requested_count, processed_count + active_count, 1)
    remaining_count = max(denominator - processed_count, 0)
    return CampaignSendJobProgressRead(
        send_job_id=send_job.id,
        campaign_id=send_job.campaign_id,
        status=send_job.status,
        requested_count=send_job.requested_count,
        queued_count=queued_count,
        sending_count=sending_count,
        sent_count=sent_count,
        failed_count=failed_count,
        suppressed_count=suppressed_count,
        skipped_count=skipped_count,
        dead_lettered_count=dead_lettered_count,
        processed_count=processed_count,
        remaining_count=remaining_count,
        active_count=active_count,
        percent_complete=round(processed_count / denominator, 4),
    )


@router.get('/email-send-records/list', response_model=ListResponse[EmailSendRecordRead])
def list_email_send_records(
    db: DbSession,
    campaign_id: UUID | None = None,
    send_job_id: UUID | None = None,
    limit: Limit = 100,
    offset: Offset = 0,
) -> dict[str, object]:
    service = CampaignService(db)
    return {
        'items': service.list_send_records(
            campaign_id=campaign_id, send_job_id=send_job_id, limit=limit, offset=offset
        ),
        'limit': limit,
        'offset': offset,
        'total': service.count_send_records(campaign_id=campaign_id, send_job_id=send_job_id),
    }


@router.get('/delivery-attempts/list', response_model=ListResponse[DeliveryAttemptRead])
def list_delivery_attempts(
    db: DbSession,
    campaign_id: UUID | None = None,
    send_job_id: UUID | None = None,
    send_record_id: UUID | None = None,
    provider: str | None = None,
    status: str | None = None,
    mta_ip_pool_id: UUID | None = None,
    mta_node_id: UUID | None = None,
    mta_provider: str | None = None,
    mta_route_resolved: bool | None = None,
    mta_route_send_type: str | None = None,
    mta_route_sender_domain: str | None = None,
    mta_route_recipient_domain: str | None = None,
    mta_routing_rule_name: str | None = None,
    mta_routing_rule_source: str | None = None,
    mta_rule_hit_pool_source: str | None = None,
    mta_rule_hit_provider_preference: str | None = None,
    mta_route_block_code: str | None = None,
    limit: Limit = 100,
    offset: Offset = 0,
) -> dict[str, object]:
    filters = []
    if campaign_id:
        filters.append(DeliveryAttempt.campaign_id == campaign_id)
    if send_job_id:
        filters.append(DeliveryAttempt.send_job_id == send_job_id)
    if send_record_id:
        filters.append(DeliveryAttempt.send_record_id == send_record_id)
    if provider:
        filters.append(DeliveryAttempt.provider == provider)
    if status:
        filters.append(DeliveryAttempt.status == status)
    metadata_filters = {
        'mta_ip_pool_id': str(mta_ip_pool_id) if mta_ip_pool_id else None,
        'mta_node_id': str(mta_node_id) if mta_node_id else None,
        'mta_provider': mta_provider,
        'mta_route_send_type': mta_route_send_type,
        'mta_route_sender_domain': mta_route_sender_domain,
        'mta_route_recipient_domain': mta_route_recipient_domain,
        'mta_routing_rule_name': mta_routing_rule_name,
        'mta_routing_rule_source': mta_routing_rule_source,
        'mta_rule_hit_pool_source': mta_rule_hit_pool_source,
        'mta_route_block_code': mta_route_block_code,
    }
    if mta_route_resolved is not None:
        filters.append(DeliveryAttempt.metadata_json['mta_route_resolved'].astext == str(mta_route_resolved).lower())
    for metadata_key, metadata_value in metadata_filters.items():
        if metadata_value:
            filters.append(DeliveryAttempt.metadata_json[metadata_key].astext == metadata_value)
    if mta_rule_hit_provider_preference:
        filters.append(
            DeliveryAttempt.metadata_json['mta_rule_hit_provider_preference'].contains(
                [mta_rule_hit_provider_preference]
            )
        )

    statement = (
        select(DeliveryAttempt)
        .where(*filters)
        .order_by(DeliveryAttempt.started_at.desc())
        .limit(limit)
        .offset(offset)
    )
    count_statement = select(func.count()).select_from(DeliveryAttempt).where(*filters)
    return {
        'items': list(db.scalars(statement).all()),
        'limit': limit,
        'offset': offset,
        'total': int(db.scalar(count_statement) or 0),
    }


@router.get('/delivery-routes/list', response_model=ListResponse[DeliveryRouteRead])
def list_delivery_routes(
    db: DbSession,
    route_type: DeliveryRouteType | None = None,
    status: DeliveryRouteStatus | None = None,
    limit: Limit = 100,
    offset: Offset = 0,
) -> dict[str, object]:
    service = DeliveryRouteService(db)
    return {
        'items': service.list_items(
            route_type=route_type,
            status=status,
            limit=limit,
            offset=offset,
        ),
        'limit': limit,
        'offset': offset,
        'total': service.count(route_type=route_type, status=status),
    }


@router.post('/delivery-routes', response_model=DeliveryRouteRead)
def create_delivery_route(payload: DeliveryRouteCreate, db: DbSession) -> DeliveryRoute:
    return DeliveryRouteService(db).create(payload)


@router.get('/delivery-routes/{route_id}', response_model=DeliveryRouteRead)
def get_delivery_route(route_id: UUID, db: DbSession) -> DeliveryRoute:
    route = DeliveryRouteService(db).get(route_id)
    if not route:
        raise HTTPException(status_code=404, detail='Delivery route not found')
    return route


@router.patch('/delivery-routes/{route_id}', response_model=DeliveryRouteRead)
def update_delivery_route(
    route_id: UUID,
    payload: DeliveryRouteUpdate,
    db: DbSession,
) -> DeliveryRoute:
    route = DeliveryRouteService(db).update(route_id, payload)
    if not route:
        raise HTTPException(status_code=404, detail='Delivery route not found')
    return route


@router.delete('/delivery-routes/{route_id}', response_model=DeleteResponse)
def delete_delivery_route(route_id: UUID, db: DbSession) -> DeleteResponse:
    if not DeliveryRouteService(db).delete(route_id):
        raise HTTPException(status_code=404, detail='Delivery route not found')
    return DeleteResponse(id=route_id)


@router.post('/delivery-routes/{route_id}/pause', response_model=DeliveryRouteRead)
def pause_delivery_route(route_id: UUID, db: DbSession) -> DeliveryRoute:
    route = DeliveryRouteService(db).pause_route(route_id)
    if not route:
        raise HTTPException(status_code=404, detail='Delivery route not found')
    return route


@router.post('/delivery-routes/{route_id}/resume', response_model=DeliveryRouteRead)
def resume_delivery_route(route_id: UUID, db: DbSession) -> DeliveryRoute:
    route = DeliveryRouteService(db).resume_route(route_id)
    if not route:
        raise HTTPException(status_code=404, detail='Delivery route not found')
    return route


@router.get(
    '/delivery-routes/{route_id}/managed-smtp/routing-rules',
    response_model=ManagedSmtpRoutingRulesRead,
)
def get_managed_smtp_routing_rules(
    route_id: UUID,
    db: DbSession,
) -> ManagedSmtpRoutingRulesRead:
    result = DeliveryRouteService(db).managed_smtp_routing_rules(route_id)
    if not result:
        raise HTTPException(status_code=404, detail='Delivery route not found')
    return result


@router.post(
    '/delivery-routes/{route_id}/managed-smtp/routing-rules',
    response_model=ManagedSmtpRoutingRulesRead,
)
def upsert_managed_smtp_routing_rule(
    route_id: UUID,
    payload: ManagedSmtpRoutingRuleUpsert,
    db: DbSession,
) -> ManagedSmtpRoutingRulesRead:
    result = DeliveryRouteService(db).upsert_managed_smtp_routing_rule(route_id, payload)
    if not result:
        raise HTTPException(status_code=404, detail='Delivery route not found')
    return result


@router.post(
    '/delivery-routes/{route_id}/managed-smtp/routing-rules/{rule_name}/disable',
    response_model=ManagedSmtpRoutingRulesRead,
)
def disable_managed_smtp_routing_rule(
    route_id: UUID,
    rule_name: str,
    db: DbSession,
) -> ManagedSmtpRoutingRulesRead:
    result = DeliveryRouteService(db).set_managed_smtp_routing_rule_enabled(
        route_id,
        rule_name,
        enabled=False,
    )
    if not result:
        raise HTTPException(status_code=404, detail='Delivery route or routing rule not found')
    return result


@router.post(
    '/delivery-routes/{route_id}/managed-smtp/routing-rules/{rule_name}/enable',
    response_model=ManagedSmtpRoutingRulesRead,
)
def enable_managed_smtp_routing_rule(
    route_id: UUID,
    rule_name: str,
    db: DbSession,
) -> ManagedSmtpRoutingRulesRead:
    result = DeliveryRouteService(db).set_managed_smtp_routing_rule_enabled(
        route_id,
        rule_name,
        enabled=True,
    )
    if not result:
        raise HTTPException(status_code=404, detail='Delivery route or routing rule not found')
    return result


@router.delete(
    '/delivery-routes/{route_id}/managed-smtp/routing-rules/{rule_name}',
    response_model=ManagedSmtpRoutingRulesRead,
)
def delete_managed_smtp_routing_rule(
    route_id: UUID,
    rule_name: str,
    db: DbSession,
) -> ManagedSmtpRoutingRulesRead:
    result = DeliveryRouteService(db).delete_managed_smtp_routing_rule(route_id, rule_name)
    if not result:
        raise HTTPException(status_code=404, detail='Delivery route or routing rule not found')
    return result


@router.get(
    '/domain-delivery-policies/list',
    response_model=ListResponse[DomainDeliveryPolicyRead],
)
def list_domain_delivery_policies(
    db: DbSession,
    domain: str | None = None,
    route_id: UUID | None = None,
    limit: Limit = 100,
    offset: Offset = 0,
) -> dict[str, object]:
    service = DeliveryRouteService(db)
    return {
        'items': service.list_domain_policies(
            domain=domain,
            route_id=route_id,
            limit=limit,
            offset=offset,
        ),
        'limit': limit,
        'offset': offset,
        'total': service.count_domain_policies(domain=domain, route_id=route_id),
    }


@router.post(
    '/domain-delivery-policies/managed-smtp-maintenance',
    response_model=ManagedSmtpMaintenanceRead,
)
def run_managed_smtp_domain_maintenance(
    payload: ManagedSmtpMaintenanceRequest,
    db: DbSession,
) -> ManagedSmtpMaintenanceRead:
    domain_rows, _total = AnalyticsService(db).domain_deliverability(limit=1000)
    deliverability_by_domain = {row.domain.lower(): row for row in domain_rows}
    return DeliveryRouteService(db).run_managed_smtp_maintenance(
        payload,
        deliverability_by_domain=deliverability_by_domain,
    )


@router.post('/domain-delivery-policies', response_model=DomainDeliveryPolicyRead)
def create_domain_delivery_policy(
    payload: DomainDeliveryPolicyCreate,
    db: DbSession,
) -> DomainDeliveryPolicy:
    return DeliveryRouteService(db).create_domain_policy(payload)


@router.get('/domain-delivery-policies/{policy_id}', response_model=DomainDeliveryPolicyRead)
def get_domain_delivery_policy(policy_id: UUID, db: DbSession) -> DomainDeliveryPolicy:
    policy = DeliveryRouteService(db).get_domain_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail='Domain delivery policy not found')
    return policy


@router.patch('/domain-delivery-policies/{policy_id}', response_model=DomainDeliveryPolicyRead)
def update_domain_delivery_policy(
    policy_id: UUID,
    payload: DomainDeliveryPolicyUpdate,
    db: DbSession,
) -> DomainDeliveryPolicy:
    policy = DeliveryRouteService(db).update_domain_policy(policy_id, payload)
    if not policy:
        raise HTTPException(status_code=404, detail='Domain delivery policy not found')
    return policy


@router.delete('/domain-delivery-policies/{policy_id}', response_model=DeleteResponse)
def delete_domain_delivery_policy(policy_id: UUID, db: DbSession) -> DeleteResponse:
    if not DeliveryRouteService(db).delete_domain_policy(policy_id):
        raise HTTPException(status_code=404, detail='Domain delivery policy not found')
    return DeleteResponse(id=policy_id)


@router.post('/domain-delivery-policies/{policy_id}/pause', response_model=DomainDeliveryPolicyRead)
def pause_domain_delivery_policy(
    policy_id: UUID,
    db: DbSession,
    paused_until: datetime | None = None,
) -> DomainDeliveryPolicy:
    policy = DeliveryRouteService(db).pause_domain_policy(policy_id, paused_until=paused_until)
    if not policy:
        raise HTTPException(status_code=404, detail='Domain delivery policy not found')
    return policy


@router.post(
    '/domain-delivery-policies/{policy_id}/compliance-hold',
    response_model=DomainDeliveryPolicyRead,
)
def apply_domain_delivery_compliance_hold(
    policy_id: UUID,
    payload: DomainComplianceHoldRequest,
    db: DbSession,
) -> DomainDeliveryPolicy:
    policy = DeliveryRouteService(db).apply_domain_compliance_hold(policy_id, payload)
    if not policy:
        raise HTTPException(status_code=404, detail='Domain delivery policy not found')
    return policy


@router.post(
    '/domain-delivery-policies/{policy_id}/authentication-plan',
    response_model=DomainAuthenticationPlanRead,
)
def build_domain_delivery_authentication_plan(
    policy_id: UUID,
    payload: DomainAuthenticationPlanRequest,
    db: DbSession,
) -> DomainAuthenticationPlanRead:
    plan = DeliveryRouteService(db).build_domain_authentication_plan(policy_id, payload)
    if not plan:
        raise HTTPException(status_code=404, detail='Domain delivery policy not found')
    return plan


@router.post(
    '/domain-delivery-policies/{policy_id}/dkim-key',
    response_model=DomainDkimKeyCreateRead,
)
def create_domain_delivery_dkim_key(
    policy_id: UUID,
    payload: DomainDkimKeyCreateRequest,
    db: DbSession,
) -> DomainDkimKeyCreateRead:
    result = DeliveryRouteService(db).create_domain_dkim_key(policy_id, payload)
    if not result:
        raise HTTPException(status_code=404, detail='Domain delivery policy not found')
    return result


@router.post(
    '/domain-delivery-policies/{policy_id}/verify-authentication',
    response_model=DomainAuthenticationVerificationRead,
)
def verify_domain_delivery_authentication(
    policy_id: UUID,
    db: DbSession,
) -> DomainAuthenticationVerificationRead:
    result = DeliveryRouteService(db).verify_domain_authentication(policy_id)
    if not result:
        raise HTTPException(status_code=404, detail='Domain delivery policy not found')
    return result


@router.post(
    '/domain-delivery-policies/{policy_id}/blocklist-scan',
    response_model=DomainBlocklistScanRead,
)
def scan_domain_delivery_blocklists(
    policy_id: UUID,
    payload: DomainBlocklistScanRequest,
    db: DbSession,
) -> DomainBlocklistScanRead:
    result = DeliveryRouteService(db).scan_domain_blocklists(policy_id, payload)
    if not result:
        raise HTTPException(status_code=404, detail='Domain delivery policy not found')
    return result


@router.get(
    '/domain-delivery-policies/{policy_id}/reputation-dashboard',
    response_model=DomainReputationDashboardRead,
)
def get_domain_delivery_reputation_dashboard(
    policy_id: UUID,
    db: DbSession,
) -> DomainReputationDashboardRead:
    service = DeliveryRouteService(db)
    policy = service.get_domain_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail='Domain delivery policy not found')
    domain_rows, _total = AnalyticsService(db).domain_deliverability(limit=1000)
    deliverability = next((row for row in domain_rows if row.domain == policy.domain), None)
    result = service.domain_reputation_dashboard(policy_id, deliverability=deliverability)
    if not result:
        raise HTTPException(status_code=404, detail='Domain delivery policy not found')
    return result


@router.post(
    '/domain-delivery-policies/{policy_id}/warmup-progress',
    response_model=DomainWarmupProgressionRead,
)
def progress_domain_delivery_warmup(
    policy_id: UUID,
    payload: DomainWarmupProgressionRequest,
    db: DbSession,
) -> DomainWarmupProgressionRead:
    service = DeliveryRouteService(db)
    policy = service.get_domain_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail='Domain delivery policy not found')
    domain_rows, _total = AnalyticsService(db).domain_deliverability(limit=1000)
    deliverability = next((row for row in domain_rows if row.domain == policy.domain), None)
    result = service.progress_domain_warmup(
        policy_id,
        payload,
        deliverability=deliverability,
    )
    if not result:
        raise HTTPException(status_code=404, detail='Domain delivery policy not found')
    return result


@router.post(
    '/domain-delivery-policies/{policy_id}/resume',
    response_model=DomainDeliveryPolicyRead,
)
def resume_domain_delivery_policy(policy_id: UUID, db: DbSession) -> DomainDeliveryPolicy:
    policy = DeliveryRouteService(db).resume_domain_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail='Domain delivery policy not found')
    return policy


@router.post(
    '/domain-delivery-policies/{policy_id}/release-compliance-hold',
    response_model=DomainDeliveryPolicyRead,
)
def release_domain_delivery_compliance_hold(
    policy_id: UUID,
    payload: DomainComplianceReleaseRequest,
    db: DbSession,
) -> DomainDeliveryPolicy:
    policy = DeliveryRouteService(db).release_domain_compliance_hold(policy_id, payload)
    if not policy:
        raise HTTPException(status_code=404, detail='Domain delivery policy not found')
    return policy


def _mta_inventory_conflict(exc: MtaInventoryError) -> HTTPException:
    return HTTPException(status_code=409, detail=str(exc))


@router.post('/managed-smtp/bootstrap', response_model=ManagedSmtpBootstrapRead)
def bootstrap_managed_smtp(
    payload: ManagedSmtpBootstrapRequest,
    db: DbSession,
) -> ManagedSmtpBootstrapRead:
    return ManagedSmtpBootstrapService(db).bootstrap(payload)


@router.get(
    '/managed-smtp/bootstrap-profiles/list',
    response_model=ListResponse[ManagedSmtpBootstrapProfileRead],
)
def list_managed_smtp_bootstrap_profiles() -> dict[str, object]:
    profiles = list_bootstrap_profiles()
    return {
        'items': profiles,
        'limit': len(profiles),
        'offset': 0,
        'total': len(profiles),
    }


@router.post(
    '/managed-smtp/bootstrap-profiles/{profile_name}',
    response_model=ManagedSmtpBootstrapRead,
)
def bootstrap_managed_smtp_profile(
    profile_name: str,
    db: DbSession,
) -> ManagedSmtpBootstrapRead:
    payload = bootstrap_profile_payload(profile_name)
    if not payload:
        raise HTTPException(status_code=404, detail='Managed SMTP bootstrap profile not found')
    return ManagedSmtpBootstrapService(db).bootstrap(payload)


async def _verified_managed_smtp_body(request: Request, settings: SettingsDep) -> bytes:
    raw_body = await request.body()
    try:
        ManagedSmtpFeedbackVerifier(settings).verify(
            raw_body,
            request.headers.get(ManagedSmtpFeedbackVerifier.signature_header),
            request.headers.get(ManagedSmtpFeedbackVerifier.timestamp_header),
        )
    except WebhookSignatureError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return raw_body


@router.get(
    '/mta-agent/nodes/{node_id}/runtime-config',
    response_model=MtaNodeRuntimeConfigRead,
)
async def get_mta_agent_runtime_config(
    node_id: UUID,
    request: Request,
    db: DbSession,
    settings: SettingsDep,
) -> MtaNodeRuntimeConfigRead:
    await _verified_managed_smtp_body(request, settings)
    config = ManagedSmtpAgentService(db).runtime_config(node_id)
    if not config:
        raise HTTPException(status_code=404, detail='MTA node not found')
    return config


@router.post(
    '/mta-agent/nodes/{node_id}/heartbeat',
    response_model=ManagedSmtpReadinessCheckRead,
)
async def post_mta_agent_heartbeat(
    node_id: UUID,
    request: Request,
    db: DbSession,
    settings: SettingsDep,
) -> ManagedSmtpReadinessCheckRead:
    raw_body = await _verified_managed_smtp_body(request, settings)
    try:
        payload = MtaNodeHeartbeatRequest.model_validate_json(raw_body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    check = ManagedSmtpAgentService(db).heartbeat(node_id, payload)
    if not check:
        raise HTTPException(status_code=404, detail='MTA node not found')
    return check


@router.post('/mta-agent/nodes/{node_id}/events', response_model=MtaNodeEventRead)
async def post_mta_agent_event(
    node_id: UUID,
    request: Request,
    db: DbSession,
    settings: SettingsDep,
) -> MtaNodeEventRead:
    raw_body = await _verified_managed_smtp_body(request, settings)
    try:
        payload = MtaNodeEventCreate.model_validate_json(raw_body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    event = ManagedSmtpAgentService(db).create_event(node_id, payload)
    if not event:
        raise HTTPException(status_code=404, detail='MTA node not found')
    return event


@router.post('/managed-smtp/resolve-route', response_model=ManagedSmtpRouteResolutionRead)
def resolve_managed_smtp_route(
    payload: ManagedSmtpRouteResolveRequest,
    db: DbSession,
) -> ManagedSmtpRouteResolutionRead:
    return ManagedSmtpRoutingService(db).resolve(payload)


@router.post('/managed-smtp/resolve-route-matrix', response_model=ManagedSmtpRouteMatrixRead)
def resolve_managed_smtp_route_matrix(
    payload: ManagedSmtpRouteMatrixRequest,
    db: DbSession,
) -> ManagedSmtpRouteMatrixRead:
    service = ManagedSmtpRoutingService(db)
    results = [
        ManagedSmtpRouteMatrixResult(
            index=index,
            label=item.label,
            request=item.request,
            result=service.resolve(item.request),
        )
        for index, item in enumerate(payload.cases)
    ]
    ok_count = sum(1 for item in results if item.result.ok)
    return ManagedSmtpRouteMatrixRead(
        total=len(results),
        ok_count=ok_count,
        blocked_count=len(results) - ok_count,
        results=results,
    )


@router.get('/managed-smtp/deployment-summary', response_model=ManagedSmtpDeploymentSummaryRead)
def summarize_managed_smtp_deployment(
    db: DbSession,
    settings: SettingsDep,
    limit: Limit = 10,
) -> ManagedSmtpDeploymentSummaryRead:
    return MtaInventoryService(db).deployment_summary(limit=limit, settings=settings)


@router.get('/managed-smtp/first-send-readiness', response_model=ManagedSmtpFirstSendRead)
def summarize_managed_smtp_first_send(
    db: DbSession,
    settings: SettingsDep,
    limit: Limit = 10,
) -> ManagedSmtpFirstSendRead:
    return MtaInventoryService(db).first_send_readiness(limit=limit, settings=settings)


@router.get(
    '/managed-smtp/provider-accounts/list',
    response_model=ListResponse[MtaProviderAccountRead],
)
def list_mta_provider_accounts(
    db: DbSession,
    status: MtaOperationalStatus | None = None,
    limit: Limit = 100,
    offset: Offset = 0,
) -> dict[str, object]:
    service = MtaInventoryService(db)
    return {
        'items': service.list_provider_accounts(status=status, limit=limit, offset=offset),
        'limit': limit,
        'offset': offset,
        'total': service.count_provider_accounts(status=status),
    }


@router.post('/managed-smtp/provider-accounts', response_model=MtaProviderAccountRead)
def create_mta_provider_account(
    payload: MtaProviderAccountCreate,
    db: DbSession,
) -> MtaProviderAccount:
    return MtaInventoryService(db).create_provider_account(payload)


@router.get('/managed-smtp/provider-accounts/{account_id}', response_model=MtaProviderAccountRead)
def get_mta_provider_account(account_id: UUID, db: DbSession) -> MtaProviderAccount:
    account = MtaInventoryService(db).get_provider_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail='MTA provider account not found')
    return account


@router.patch(
    '/managed-smtp/provider-accounts/{account_id}',
    response_model=MtaProviderAccountRead,
)
def update_mta_provider_account(
    account_id: UUID,
    payload: MtaProviderAccountUpdate,
    db: DbSession,
) -> MtaProviderAccount:
    account = MtaInventoryService(db).update_provider_account(account_id, payload)
    if not account:
        raise HTTPException(status_code=404, detail='MTA provider account not found')
    return account


@router.post(
    '/managed-smtp/provider-accounts/{account_id}/pause',
    response_model=MtaProviderAccountRead,
)
def pause_mta_provider_account(account_id: UUID, db: DbSession) -> MtaProviderAccount:
    account = MtaInventoryService(db).set_provider_account_status(
        account_id,
        MtaOperationalStatus.paused,
    )
    if not account:
        raise HTTPException(status_code=404, detail='MTA provider account not found')
    return account


@router.post(
    '/managed-smtp/provider-accounts/{account_id}/resume',
    response_model=MtaProviderAccountRead,
)
def resume_mta_provider_account(account_id: UUID, db: DbSession) -> MtaProviderAccount:
    account = MtaInventoryService(db).set_provider_account_status(
        account_id,
        MtaOperationalStatus.active,
    )
    if not account:
        raise HTTPException(status_code=404, detail='MTA provider account not found')
    return account


@router.get('/managed-smtp/nodes/list', response_model=ListResponse[MtaNodeRead])
def list_mta_nodes(
    db: DbSession,
    status: MtaOperationalStatus | None = None,
    provider_account_id: UUID | None = None,
    limit: Limit = 100,
    offset: Offset = 0,
) -> dict[str, object]:
    service = MtaInventoryService(db)
    return {
        'items': service.list_nodes(
            status=status,
            provider_account_id=provider_account_id,
            limit=limit,
            offset=offset,
        ),
        'limit': limit,
        'offset': offset,
        'total': service.count_nodes(status=status, provider_account_id=provider_account_id),
    }


@router.get('/managed-smtp/node-events/list', response_model=ListResponse[MtaNodeEventRead])
def list_mta_node_events(
    db: DbSession,
    mta_node_id: UUID | None = None,
    event_type: str | None = None,
    severity: str | None = None,
    limit: Limit = 100,
    offset: Offset = 0,
) -> dict[str, object]:
    service = MtaInventoryService(db)
    return {
        'items': service.list_node_events(
            mta_node_id=mta_node_id,
            event_type=event_type,
            severity=severity,
            limit=limit,
            offset=offset,
        ),
        'limit': limit,
        'offset': offset,
        'total': service.count_node_events(
            mta_node_id=mta_node_id,
            event_type=event_type,
            severity=severity,
        ),
    }


@router.post('/managed-smtp/nodes', response_model=MtaNodeRead)
def create_mta_node(payload: MtaNodeCreate, db: DbSession) -> MtaNode:
    try:
        return MtaInventoryService(db).create_node(payload)
    except MtaInventoryError as exc:
        raise _mta_inventory_conflict(exc) from exc


@router.get('/managed-smtp/nodes/{node_id}', response_model=MtaNodeRead)
def get_mta_node(node_id: UUID, db: DbSession) -> MtaNode:
    node = MtaInventoryService(db).get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail='MTA node not found')
    return node


@router.patch('/managed-smtp/nodes/{node_id}', response_model=MtaNodeRead)
def update_mta_node(node_id: UUID, payload: MtaNodeUpdate, db: DbSession) -> MtaNode:
    try:
        node = MtaInventoryService(db).update_node(node_id, payload)
    except MtaInventoryError as exc:
        raise _mta_inventory_conflict(exc) from exc
    if not node:
        raise HTTPException(status_code=404, detail='MTA node not found')
    return node


@router.post('/managed-smtp/nodes/{node_id}/pause', response_model=MtaNodeRead)
def pause_mta_node(
    node_id: UUID,
    payload: MtaNodeStatusActionRequest,
    db: DbSession,
) -> MtaNode:
    node = MtaInventoryService(db).set_node_status(
        node_id,
        MtaOperationalStatus.paused,
        reason=payload.reason,
        operator=payload.operator,
    )
    if not node:
        raise HTTPException(status_code=404, detail='MTA node not found')
    return node


@router.post('/managed-smtp/nodes/{node_id}/resume', response_model=MtaNodeRead)
def resume_mta_node(
    node_id: UUID,
    payload: MtaNodeStatusActionRequest,
    db: DbSession,
) -> MtaNode:
    node = MtaInventoryService(db).set_node_status(
        node_id,
        MtaOperationalStatus.active,
        reason=payload.reason,
        operator=payload.operator,
    )
    if not node:
        raise HTTPException(status_code=404, detail='MTA node not found')
    return node


@router.get('/managed-smtp/ip-pools/list', response_model=ListResponse[MtaIpPoolRead])
def list_mta_ip_pools(
    db: DbSession,
    status: MtaOperationalStatus | None = None,
    limit: Limit = 100,
    offset: Offset = 0,
) -> dict[str, object]:
    service = MtaInventoryService(db)
    return {
        'items': service.list_ip_pools(status=status, limit=limit, offset=offset),
        'limit': limit,
        'offset': offset,
        'total': service.count_ip_pools(status=status),
    }


@router.post('/managed-smtp/ip-pools', response_model=MtaIpPoolRead)
def create_mta_ip_pool(payload: MtaIpPoolCreate, db: DbSession) -> MtaIpPool:
    return MtaInventoryService(db).create_ip_pool(payload)


@router.get('/managed-smtp/ip-pools/{pool_id}', response_model=MtaIpPoolRead)
def get_mta_ip_pool(pool_id: UUID, db: DbSession) -> MtaIpPool:
    pool = MtaInventoryService(db).get_ip_pool(pool_id)
    if not pool:
        raise HTTPException(status_code=404, detail='MTA IP pool not found')
    return pool


@router.patch('/managed-smtp/ip-pools/{pool_id}', response_model=MtaIpPoolRead)
def update_mta_ip_pool(
    pool_id: UUID,
    payload: MtaIpPoolUpdate,
    db: DbSession,
) -> MtaIpPool:
    pool = MtaInventoryService(db).update_ip_pool(pool_id, payload)
    if not pool:
        raise HTTPException(status_code=404, detail='MTA IP pool not found')
    return pool


@router.post('/managed-smtp/ip-pools/{pool_id}/pause', response_model=MtaIpPoolRead)
def pause_mta_ip_pool(pool_id: UUID, db: DbSession) -> MtaIpPool:
    pool = MtaInventoryService(db).set_ip_pool_status(pool_id, MtaOperationalStatus.paused)
    if not pool:
        raise HTTPException(status_code=404, detail='MTA IP pool not found')
    return pool


@router.post('/managed-smtp/ip-pools/{pool_id}/resume', response_model=MtaIpPoolRead)
def resume_mta_ip_pool(pool_id: UUID, db: DbSession) -> MtaIpPool:
    pool = MtaInventoryService(db).set_ip_pool_status(pool_id, MtaOperationalStatus.active)
    if not pool:
        raise HTTPException(status_code=404, detail='MTA IP pool not found')
    return pool


@router.get(
    '/managed-smtp/ip-pool-nodes/list',
    response_model=ListResponse[MtaIpPoolNodeRead],
)
def list_mta_ip_pool_nodes(
    db: DbSession,
    ip_pool_id: UUID | None = None,
    mta_node_id: UUID | None = None,
    status: MtaOperationalStatus | None = None,
    limit: Limit = 100,
    offset: Offset = 0,
) -> dict[str, object]:
    service = MtaInventoryService(db)
    return {
        'items': service.list_pool_nodes(
            ip_pool_id=ip_pool_id,
            mta_node_id=mta_node_id,
            status=status,
            limit=limit,
            offset=offset,
        ),
        'limit': limit,
        'offset': offset,
        'total': service.count_pool_nodes(
            ip_pool_id=ip_pool_id,
            mta_node_id=mta_node_id,
            status=status,
        ),
    }


@router.post('/managed-smtp/ip-pool-nodes', response_model=MtaIpPoolNodeRead)
def create_mta_ip_pool_node(
    payload: MtaIpPoolNodeCreate,
    db: DbSession,
) -> MtaIpPoolNode:
    try:
        return MtaInventoryService(db).create_pool_node(payload)
    except MtaInventoryError as exc:
        raise _mta_inventory_conflict(exc) from exc


@router.patch(
    '/managed-smtp/ip-pool-nodes/{pool_node_id}',
    response_model=MtaIpPoolNodeRead,
)
def update_mta_ip_pool_node(
    pool_node_id: UUID,
    payload: MtaIpPoolNodeUpdate,
    db: DbSession,
) -> MtaIpPoolNode:
    pool_node = MtaInventoryService(db).update_pool_node(pool_node_id, payload)
    if not pool_node:
        raise HTTPException(status_code=404, detail='MTA IP pool node not found')
    return pool_node


@router.post(
    '/managed-smtp/ip-pool-nodes/{pool_node_id}/pause',
    response_model=MtaIpPoolNodeRead,
)
def pause_mta_ip_pool_node(pool_node_id: UUID, db: DbSession) -> MtaIpPoolNode:
    pool_node = MtaInventoryService(db).set_pool_node_status(
        pool_node_id,
        MtaOperationalStatus.paused,
    )
    if not pool_node:
        raise HTTPException(status_code=404, detail='MTA IP pool node not found')
    return pool_node


@router.post(
    '/managed-smtp/ip-pool-nodes/{pool_node_id}/resume',
    response_model=MtaIpPoolNodeRead,
)
def resume_mta_ip_pool_node(pool_node_id: UUID, db: DbSession) -> MtaIpPoolNode:
    pool_node = MtaInventoryService(db).set_pool_node_status(
        pool_node_id,
        MtaOperationalStatus.active,
    )
    if not pool_node:
        raise HTTPException(status_code=404, detail='MTA IP pool node not found')
    return pool_node


@router.post('/email-send-records/{send_record_id}/requeue', response_model=EmailSendRecordRead)
def requeue_email_send_record(send_record_id: UUID, db: DbSession) -> EmailSendRecord:
    try:
        record = CampaignService(db).requeue_send_record(send_record_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not record:
        raise HTTPException(status_code=404, detail='Send record not found')
    return record


@router.post('/email-send-records/{send_record_id}/skip', response_model=EmailSendRecordRead)
def skip_email_send_record(send_record_id: UUID, db: DbSession) -> EmailSendRecord:
    try:
        record = CampaignService(db).skip_send_record(send_record_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not record:
        raise HTTPException(status_code=404, detail='Send record not found')
    return record


@router.post(
    '/email-send-records/{send_record_id}/dead-letter',
    response_model=EmailSendRecordRead,
)
def dead_letter_email_send_record(
    send_record_id: UUID,
    db: DbSession,
    reason: str | None = None,
) -> EmailSendRecord:
    try:
        record = CampaignService(db).dead_letter_send_record(send_record_id, reason=reason)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not record:
        raise HTTPException(status_code=404, detail='Send record not found')
    return record


@router.delete('/email-send-records/{send_record_id}', response_model=DeleteResponse)
def delete_email_send_record(send_record_id: UUID, db: DbSession) -> DeleteResponse:
    try:
        deleted = CampaignService(db).delete_send_record(send_record_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail='Send record not found')
    return DeleteResponse(id=send_record_id)


@router.get('/email-send-records/{send_record_id}/tracking-links', response_model=TrackingLinksRead)
def get_email_send_record_tracking_links(
    send_record_id: UUID,
    request: Request,
    db: DbSession,
    settings: SettingsDep,
    target_url: str | None = None,
) -> TrackingLinksRead:
    service = TrackingService(db, settings.unsubscribe_secret)
    send_record = service.get_send_record(send_record_id)
    if not send_record:
        raise HTTPException(status_code=404, detail='Send record not found')

    token = service.create_token(send_record_id)
    open_url = str(request.url_for('record_tracking_open', token=token))
    click_url_base = str(request.url_for('record_tracking_click', token=token))
    click_url_template = f'{click_url_base}?url={{target_url}}'
    click_url = (
        f'{click_url_base}?url={quote(target_url, safe="")}'
        if target_url
        else click_url_template
    )
    return TrackingLinksRead(
        send_record_id=send_record_id,
        token=token,
        open_url=open_url,
        click_url=click_url,
        click_url_template=click_url_template,
    )


@router.get('/tracking/open/{token}', include_in_schema=False)
def record_tracking_open(
    token: str,
    request: Request,
    db: DbSession,
    settings: SettingsDep,
) -> Response:
    try:
        TrackingService(db, settings.unsubscribe_secret).record_open(
            token, _tracking_request_metadata(request)
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(
        content=TRANSPARENT_GIF,
        media_type='image/gif',
        headers={'Cache-Control': 'no-store, max-age=0'},
    )


@router.get('/tracking/click/{token}', response_model=None)
def record_tracking_click(
    token: str,
    url: str,
    request: Request,
    db: DbSession,
    settings: SettingsDep,
) -> RedirectResponse:
    if not _is_http_url(url):
        raise HTTPException(status_code=400, detail='Click redirect URL must be http or https')
    try:
        TrackingService(db, settings.unsubscribe_secret).record_click(
            token, {**_tracking_request_metadata(request), 'target_url': url}
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return RedirectResponse(url, status_code=302)


@router.post('/tracking/open/{token}', response_model=TrackingEventRead)
def record_tracking_open_api(
    token: str,
    request: Request,
    db: DbSession,
    settings: SettingsDep,
) -> TrackingEventRead:
    try:
        event = TrackingService(db, settings.unsubscribe_secret).record_open(
            token, _tracking_request_metadata(request)
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    send_record_id = UUID(str(event.metadata_json['send_record_id']))
    return TrackingEventRead(
        event_id=event.id, send_record_id=send_record_id, event_type=event.event_type
    )


@router.post('/tracking/click/{token}', response_model=TrackingEventRead)
def record_tracking_click_api(
    token: str,
    request: Request,
    db: DbSession,
    settings: SettingsDep,
    target_url: str | None = None,
) -> TrackingEventRead:
    metadata = _tracking_request_metadata(request)
    if target_url:
        if not _is_http_url(target_url):
            raise HTTPException(status_code=400, detail='Click URL must be http or https')
        metadata['target_url'] = target_url
    try:
        event = TrackingService(db, settings.unsubscribe_secret).record_click(token, metadata)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    send_record_id = UUID(str(event.metadata_json['send_record_id']))
    return TrackingEventRead(
        event_id=event.id, send_record_id=send_record_id, event_type=event.event_type
    )


@router.post('/tests/email-send-records/{send_record_id}/open', response_model=TrackingEventRead)
def record_test_tracking_open(
    send_record_id: UUID,
    request: Request,
    db: DbSession,
    settings: SettingsDep,
) -> TrackingEventRead:
    service = TrackingService(db, settings.unsubscribe_secret)
    if not service.get_send_record(send_record_id):
        raise HTTPException(status_code=404, detail='Send record not found')
    token = service.create_token(send_record_id)
    event = service.record_open(
        token,
        {
            **_tracking_request_metadata(request),
            'source': 'manual_test_event',
        },
    )
    return TrackingEventRead(
        event_id=event.id, send_record_id=send_record_id, event_type=event.event_type
    )


@router.post('/tests/email-send-records/{send_record_id}/click', response_model=TrackingEventRead)
def record_test_tracking_click(
    send_record_id: UUID,
    request: Request,
    db: DbSession,
    settings: SettingsDep,
    target_url: str | None = None,
) -> TrackingEventRead:
    service = TrackingService(db, settings.unsubscribe_secret)
    if not service.get_send_record(send_record_id):
        raise HTTPException(status_code=404, detail='Send record not found')
    if target_url and not _is_http_url(target_url):
        raise HTTPException(status_code=400, detail='Click URL must be http or https')
    token = service.create_token(send_record_id)
    metadata = {
        **_tracking_request_metadata(request),
        'source': 'manual_test_event',
    }
    if target_url:
        metadata['target_url'] = target_url
    event = service.record_click(token, metadata)
    return TrackingEventRead(
        event_id=event.id, send_record_id=send_record_id, event_type=event.event_type
    )


@router.post('/delivery/process-queued', response_model=DeliveryRunRead)
def process_queued_delivery(
    db: DbSession,
    settings: SettingsDep,
    limit: Limit = 25,
    campaign_id: UUID | None = None,
    send_job_id: UUID | None = None,
) -> DeliveryRunRead:
    return DeliveryService(db, settings).process_queued(
        limit=limit, campaign_id=campaign_id, send_job_id=send_job_id
    )


@router.post('/provider-webhooks/sendgrid', response_model=ProviderWebhookIngestRead)
async def ingest_sendgrid_webhook(
    request: Request,
    db: DbSession,
    settings: SettingsDep,
) -> ProviderWebhookIngestRead:
    raw_body = await request.body()
    try:
        SendGridWebhookVerifier(settings).verify(
            raw_body,
            request.headers.get(SendGridWebhookVerifier.signature_header),
            request.headers.get(SendGridWebhookVerifier.timestamp_header),
        )
    except WebhookSignatureError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    try:
        raw_events = json.loads(raw_body)
        payload = [SendGridWebhookEvent.model_validate(item) for item in raw_events]
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail='Invalid SendGrid webhook payload') from exc
    return ProviderWebhookService(db).ingest_sendgrid(payload)


@router.post('/delivery/managed-smtp/feedback', response_model=ProviderWebhookIngestRead)
async def ingest_managed_smtp_feedback(
    request: Request,
    db: DbSession,
    settings: SettingsDep,
) -> ProviderWebhookIngestRead:
    raw_body = await request.body()
    try:
        ManagedSmtpFeedbackVerifier(settings).verify(
            raw_body,
            request.headers.get(ManagedSmtpFeedbackVerifier.signature_header),
            request.headers.get(ManagedSmtpFeedbackVerifier.timestamp_header),
        )
    except WebhookSignatureError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    try:
        raw_events = json.loads(raw_body)
        payload = [ManagedSmtpFeedbackEvent.model_validate(item) for item in raw_events]
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail='Invalid managed SMTP feedback payload') from exc
    return FeedbackIngestionService(db).ingest_managed_smtp(payload)


@router.get(
    '/provider-feedback-events/list',
    response_model=ListResponse[ProviderFeedbackEventRead],
)
def list_provider_feedback_events(
    db: DbSession,
    provider: str | None = None,
    source: str | None = None,
    event_name: str | None = None,
    email: str | None = None,
    provider_message_id: str | None = None,
    limit: Limit = 100,
    offset: Offset = 0,
) -> dict[str, object]:
    service = FeedbackIngestionService(db)
    return {
        'items': service.list_feedback_events(
            provider=provider,
            source=source,
            event_name=event_name,
            email=email,
            provider_message_id=provider_message_id,
            limit=limit,
            offset=offset,
        ),
        'limit': limit,
        'offset': offset,
        'total': service.count_feedback_events(
            provider=provider,
            source=source,
            event_name=event_name,
            email=email,
            provider_message_id=provider_message_id,
        ),
    }


@router.post(
    '/delivery/managed-smtp/readiness-checks',
    response_model=ManagedSmtpReadinessCheckRead,
)
async def create_managed_smtp_readiness_check(
    request: Request,
    db: DbSession,
    settings: SettingsDep,
) -> ManagedSmtpReadinessCheckRead:
    raw_body = await request.body()
    try:
        ManagedSmtpFeedbackVerifier(settings).verify(
            raw_body,
            request.headers.get(ManagedSmtpFeedbackVerifier.signature_header),
            request.headers.get(ManagedSmtpFeedbackVerifier.timestamp_header),
        )
    except WebhookSignatureError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    try:
        payload = ManagedSmtpReadinessCheckCreate.model_validate_json(raw_body)
        return ManagedSmtpReadinessService(db).create(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    '/managed-smtp/readiness-checks/list',
    response_model=ListResponse[ManagedSmtpReadinessCheckRead],
)
def list_managed_smtp_readiness_checks(
    db: DbSession,
    source: str | None = None,
    check_type: str | None = None,
    status: str | None = None,
    domain: str | None = None,
    host: str | None = None,
    limit: Limit = 100,
    offset: Offset = 0,
) -> dict[str, object]:
    service = ManagedSmtpReadinessService(db)
    return {
        'items': service.list_checks(
            source=source,
            check_type=check_type,
            status=status,
            domain=domain,
            host=host,
            limit=limit,
            offset=offset,
        ),
        'limit': limit,
        'offset': offset,
        'total': service.count_checks(
            source=source,
            check_type=check_type,
            status=status,
            domain=domain,
            host=host,
        ),
    }


@router.get(
    '/managed-smtp/readiness-checks/summary',
    response_model=ManagedSmtpReadinessSummaryRead,
)
def summarize_managed_smtp_readiness_checks(
    db: DbSession,
    source: str | None = None,
    check_type: str | None = None,
    domain: str | None = None,
    host: str | None = None,
) -> ManagedSmtpReadinessSummaryRead:
    return ManagedSmtpReadinessService(db).summary(
        source=source,
        check_type=check_type,
        domain=domain,
        host=host,
    )


@router.get(
    '/managed-smtp/readiness-checks/trend',
    response_model=ManagedSmtpReadinessTrendRead,
)
def trend_managed_smtp_readiness_checks(
    db: DbSession,
    source: str | None = None,
    check_type: str | None = None,
    domain: str | None = None,
    host: str | None = None,
    limit: Limit = 20,
) -> ManagedSmtpReadinessTrendRead:
    return ManagedSmtpReadinessService(db).trend(
        source=source,
        check_type=check_type,
        domain=domain,
        host=host,
        limit=limit,
    )


@router.get(
    '/managed-smtp/readiness-checks/alerts',
    response_model=ManagedSmtpReadinessAlertsRead,
)
def alert_managed_smtp_readiness_checks(
    db: DbSession,
    source: str | None = None,
    check_type: str | None = None,
    domain: str | None = None,
    host: str | None = None,
    limit: Limit = 20,
) -> ManagedSmtpReadinessAlertsRead:
    return ManagedSmtpReadinessService(db).alerts(
        source=source,
        check_type=check_type,
        domain=domain,
        host=host,
        limit=limit,
    )


@router.get(
    '/managed-smtp/readiness-checks/notification',
    response_model=ManagedSmtpReadinessNotificationRead,
)
def notify_managed_smtp_readiness_checks(
    db: DbSession,
    source: str | None = None,
    check_type: str | None = None,
    domain: str | None = None,
    host: str | None = None,
    limit: Limit = 20,
) -> ManagedSmtpReadinessNotificationRead:
    return ManagedSmtpReadinessService(db).notification(
        source=source,
        check_type=check_type,
        domain=domain,
        host=host,
        limit=limit,
    )


@router.get('/suppressions', response_model=list[SuppressionRead])
def list_suppressions(
    db: DbSession,
    limit: Limit = 100,
    offset: Offset = 0,
) -> list[Suppression]:
    return SuppressionService(db).list_items(limit=limit, offset=offset)


@router.get('/suppressions/list', response_model=ListResponse[SuppressionRead])
def list_suppressions_enveloped(
    db: DbSession,
    limit: Limit = 100,
    offset: Offset = 0,
) -> dict[str, object]:
    service = SuppressionService(db)
    return {
        'items': service.list_items(limit=limit, offset=offset),
        'limit': limit,
        'offset': offset,
        'total': service.count(),
    }


@router.post('/suppressions', response_model=SuppressionRead)
def create_suppression(payload: SuppressionCreate, db: DbSession) -> Suppression:
    return SuppressionService(db).create_manual(
        email=str(payload.email),
        reason=payload.reason,
        source=payload.source,
        provider_message_id=payload.provider_message_id,
        metadata_json=cast(dict[str, object], payload.metadata_json),
        contact_id=payload.contact_id,
    )


@router.delete('/suppressions/{suppression_id}', response_model=DeleteResponse)
def delete_suppression(suppression_id: UUID, db: DbSession) -> DeleteResponse:
    deleted = SuppressionService(db).delete(suppression_id)
    if not deleted:
        raise HTTPException(status_code=404, detail='Suppression not found')
    return DeleteResponse(id=suppression_id)


@router.get('/audiences/contacts', response_model=list[ContactRead])
def list_contacts(
    db: DbSession,
    limit: Limit = 100,
    offset: Offset = 0,
) -> list[Contact]:
    return ContactService(db).list(limit=limit, offset=offset)


@router.get('/audiences/contacts/list', response_model=ListResponse[ContactRead])
def list_contacts_enveloped(
    db: DbSession,
    limit: Limit = 100,
    offset: Offset = 0,
) -> dict[str, object]:
    service = ContactService(db)
    return {
        'items': service.list(limit=limit, offset=offset),
        'limit': limit,
        'offset': offset,
        'total': service.count(),
    }


@router.get('/audiences/contacts/meta')
def contacts_metadata(
    db: DbSession, sample_limit: Limit = 25, scan_limit: Limit = 500
) -> dict[str, object]:
    return ContactService(db).metadata(sample_limit=sample_limit, scan_limit=scan_limit)


@router.post('/audiences/contacts', response_model=ContactRead)
def upsert_contact(payload: ContactUpsert, db: DbSession) -> Contact:
    return ContactService(db).upsert(payload)


@router.get('/audiences/contacts/{contact_id}', response_model=ContactRead)
def get_contact(contact_id: UUID, db: DbSession) -> Contact:
    contact = ContactService(db).get(contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail='Contact not found')
    return contact


@router.patch('/audiences/contacts/{contact_id}', response_model=ContactRead)
def update_contact(contact_id: UUID, payload: ContactUpdate, db: DbSession) -> Contact:
    contact = ContactService(db).update(contact_id, payload)
    if not contact:
        raise HTTPException(status_code=404, detail='Contact not found')
    return contact


@router.delete('/audiences/contacts/{contact_id}', response_model=DeleteResponse)
def delete_contact(contact_id: UUID, db: DbSession) -> dict[str, UUID]:
    if not ContactService(db).delete(contact_id):
        raise HTTPException(status_code=404, detail='Contact not found')
    return {'id': contact_id}


@router.get('/data-sources', response_model=list[DataSourceRead])
def list_data_sources(
    db: DbSession,
    limit: Limit = 100,
    offset: Offset = 0,
) -> list[DataSource]:
    return DataSourceService(db).list_items(limit=limit, offset=offset)


@router.get('/data-sources/list', response_model=ListResponse[DataSourceRead])
def list_data_sources_enveloped(
    db: DbSession,
    limit: Limit = 100,
    offset: Offset = 0,
) -> dict[str, object]:
    service = DataSourceService(db)
    return {
        'items': service.list_items(limit=limit, offset=offset),
        'limit': limit,
        'offset': offset,
        'total': service.count(),
    }


@router.post('/data-sources', response_model=DataSourceRead)
def create_data_source(payload: DataSourceCreate, db: DbSession) -> DataSource:
    return DataSourceService(db).create(payload)


@router.get('/data-sources/{data_source_id}', response_model=DataSourceRead)
def get_data_source(data_source_id: UUID, db: DbSession) -> DataSource:
    data_source = DataSourceService(db).get(data_source_id)
    if not data_source:
        raise HTTPException(status_code=404, detail='Data source not found')
    return data_source


@router.patch('/data-sources/{data_source_id}', response_model=DataSourceRead)
def update_data_source(
    data_source_id: UUID, payload: DataSourceUpdate, db: DbSession
) -> DataSource:
    data_source = DataSourceService(db).update(data_source_id, payload)
    if not data_source:
        raise HTTPException(status_code=404, detail='Data source not found')
    return data_source


@router.delete('/data-sources/{data_source_id}', response_model=DeleteResponse)
def delete_data_source(data_source_id: UUID, db: DbSession) -> dict[str, UUID]:
    if not DataSourceService(db).delete(data_source_id):
        raise HTTPException(status_code=404, detail='Data source not found')
    return {'id': data_source_id}


@router.post('/data-sources/{data_source_id}/validate', response_model=DataSourceValidationRead)
def validate_data_source(data_source_id: UUID, db: DbSession) -> DataSourceValidationRead:
    validation = DataSourceService(db).validate_connection(data_source_id)
    if not validation:
        raise HTTPException(status_code=404, detail='Data source not found')
    return validation


@router.get('/data-sources/{data_source_id}/schema', response_model=DataSourceSchemaRead)
def discover_data_source_schema(data_source_id: UUID, db: DbSession) -> DataSourceSchemaRead:
    schema = DataSourceService(db).discover_schema(data_source_id)
    if not schema:
        raise HTTPException(status_code=404, detail='Data source not found')
    return schema


@router.get('/data-source-mappings', response_model=list[DataSourceMappingRead])
def list_data_source_mappings(
    db: DbSession,
    data_source_id: UUID | None = None,
    limit: Limit = 100,
    offset: Offset = 0,
) -> list[DataSourceMapping]:
    return DataSourceService(db).list_mappings(
        data_source_id=data_source_id, limit=limit, offset=offset
    )


@router.get('/data-source-mappings/list', response_model=ListResponse[DataSourceMappingRead])
def list_data_source_mappings_enveloped(
    db: DbSession,
    data_source_id: UUID | None = None,
    limit: Limit = 100,
    offset: Offset = 0,
) -> dict[str, object]:
    service = DataSourceService(db)
    return {
        'items': service.list_mappings(
            data_source_id=data_source_id, limit=limit, offset=offset
        ),
        'limit': limit,
        'offset': offset,
        'total': service.count_mappings(data_source_id=data_source_id),
    }


@router.post('/data-source-mappings', response_model=DataSourceMappingRead)
def create_data_source_mapping(
    payload: DataSourceMappingCreate, db: DbSession
) -> DataSourceMapping:
    data_source_service = DataSourceService(db)
    if not data_source_service.get(payload.data_source_id):
        raise HTTPException(status_code=404, detail='Data source not found')
    return data_source_service.create_mapping(payload)


@router.patch('/data-source-mappings/{mapping_id}', response_model=DataSourceMappingRead)
def update_data_source_mapping(
    mapping_id: UUID, payload: DataSourceMappingUpdate, db: DbSession
) -> DataSourceMapping:
    data_source_service = DataSourceService(db)
    if payload.data_source_id and not data_source_service.get(payload.data_source_id):
        raise HTTPException(status_code=404, detail='Data source not found')
    mapping = data_source_service.update_mapping(mapping_id, payload)
    if not mapping:
        raise HTTPException(status_code=404, detail='Data source mapping not found')
    return mapping


@router.delete('/data-source-mappings/{mapping_id}', response_model=DeleteResponse)
def delete_data_source_mapping(mapping_id: UUID, db: DbSession) -> dict[str, UUID]:
    if not DataSourceService(db).delete_mapping(mapping_id):
        raise HTTPException(status_code=404, detail='Data source mapping not found')
    return {'id': mapping_id}


@router.post('/data-sources/{data_source_id}/ingest', response_model=DataSourceImportJobRead)
def ingest_data_source_rows(
    data_source_id: UUID,
    payload: DataSourceIngestRequest,
    db: DbSession,
) -> object:
    job = DataSourceService(db).ingest_rows(data_source_id, payload)
    if not job:
        raise HTTPException(status_code=404, detail='Data source or mapping not found')
    return job


@router.get(
    '/data-source-import-jobs/list',
    response_model=ListResponse[DataSourceImportJobRead],
)
def list_data_source_import_jobs(
    db: DbSession,
    data_source_id: UUID | None = None,
    limit: Limit = 100,
    offset: Offset = 0,
) -> dict[str, object]:
    service = DataSourceService(db)
    return {
        'items': service.list_import_jobs(
            data_source_id=data_source_id,
            limit=limit,
            offset=offset,
        ),
        'limit': limit,
        'offset': offset,
        'total': service.count_import_jobs(data_source_id=data_source_id),
    }


@router.get('/audiences', response_model=list[AudienceRead])
def list_audiences(
    db: DbSession,
    limit: Limit = 100,
    offset: Offset = 0,
) -> list[Audience]:
    return AudienceService(db).list_items(limit=limit, offset=offset)


@router.get('/audiences/list', response_model=ListResponse[AudienceRead])
def list_audiences_enveloped(
    db: DbSession,
    limit: Limit = 100,
    offset: Offset = 0,
) -> dict[str, object]:
    service = AudienceService(db)
    return {
        'items': service.list_items(limit=limit, offset=offset),
        'limit': limit,
        'offset': offset,
        'total': service.count(),
    }


@router.post('/audiences', response_model=AudienceRead)
def create_audience(payload: AudienceCreate, db: DbSession) -> Audience:
    return AudienceService(db).create(payload)


@router.post('/audiences/import-csv', response_model=AudienceImportRead)
async def import_audience_csv(
    db: DbSession,
    file: Annotated[UploadFile, File()],
    audience_name: Annotated[str, Form()],
    description: Annotated[str | None, Form()] = None,
    source: Annotated[str, Form()] = 'csv_import',
    column_mapping: Annotated[str | None, Form()] = None,
) -> AudienceImportRead:
    if not (file.filename or '').lower().endswith('.csv'):
        raise HTTPException(status_code=400, detail='Upload must be a CSV file')
    try:
        parsed_mapping_raw = json.loads(column_mapping) if column_mapping else None
        if parsed_mapping_raw is not None and not isinstance(parsed_mapping_raw, dict):
            raise ValueError('column_mapping must be a JSON object')
        parsed_mapping = (
            {str(key): str(value) for key, value in parsed_mapping_raw.items()}
            if parsed_mapping_raw
            else None
        )
        result = AudienceImportService(db).import_csv(
            await file.read(),
            audience_name=audience_name,
            description=description,
            source=source,
            column_mapping=parsed_mapping,
        )
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AudienceImportRead(
        audience_id=result.audience.id,
        import_id=result.import_id,
        imported_count=result.imported_count,
        created_count=result.created_count,
        updated_count=result.updated_count,
        skipped_count=result.skipped_count,
        errors=result.errors,
    )


@router.post('/audiences/import-csv/preview', response_model=AudienceImportPreviewRead)
async def preview_audience_csv(
    db: DbSession,
    file: Annotated[UploadFile, File()],
    sample_limit: Annotated[int, Form(ge=1, le=25)] = 10,
) -> AudienceImportPreviewRead:
    if not (file.filename or '').lower().endswith('.csv'):
        raise HTTPException(status_code=400, detail='Upload must be a CSV file')
    try:
        preview = AudienceImportService(db).preview_csv(
            await file.read(), sample_limit=sample_limit
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AudienceImportPreviewRead(
        headers=preview.headers,
        row_count=preview.row_count,
        sample_rows=preview.sample_rows,
        inferred_mapping=preview.inferred_mapping,
        errors=preview.errors,
    )


@router.get('/audiences/{audience_id}', response_model=AudienceRead)
def get_audience(audience_id: UUID, db: DbSession) -> Audience:
    audience = AudienceService(db).get(audience_id)
    if not audience:
        raise HTTPException(status_code=404, detail='Audience not found')
    return audience


@router.patch('/audiences/{audience_id}', response_model=AudienceRead)
def update_audience(audience_id: UUID, payload: AudienceUpdate, db: DbSession) -> Audience:
    audience = AudienceService(db).update(audience_id, payload)
    if not audience:
        raise HTTPException(status_code=404, detail='Audience not found')
    return audience


@router.delete('/audiences/{audience_id}', response_model=DeleteResponse)
def delete_audience(audience_id: UUID, db: DbSession) -> dict[str, UUID]:
    if not AudienceService(db).delete(audience_id):
        raise HTTPException(status_code=404, detail='Audience not found')
    return {'id': audience_id}


@router.get('/audience-snapshots/list', response_model=ListResponse[AudienceSnapshotRead])
def list_audience_snapshots(
    db: DbSession,
    audience_id: UUID | None = None,
    limit: Limit = 100,
    offset: Offset = 0,
) -> dict[str, object]:
    service = AudienceService(db)
    return {
        'items': service.list_snapshots(audience_id=audience_id, limit=limit, offset=offset),
        'limit': limit,
        'offset': offset,
        'total': service.count_snapshots(audience_id=audience_id),
    }


@router.post('/audiences/{audience_id}/snapshots', response_model=AudienceSnapshotRead)
def create_audience_snapshot(
    audience_id: UUID,
    payload: AudienceSnapshotCreate,
    db: DbSession,
) -> object:
    snapshot = AudienceService(db).create_snapshot(audience_id, payload)
    if not snapshot:
        raise HTTPException(status_code=404, detail='Audience not found')
    return snapshot


@router.post('/audiences/preview', response_model=AudiencePreviewRead)
def preview_audience(payload: AudiencePreviewRequest, db: DbSession) -> dict[str, object]:
    count, sample_contacts = AudienceService(db).preview(payload.rule_tree, payload.limit)
    return {'estimated_count': count, 'sample_contacts': sample_contacts}


@router.post(
    '/audiences/contacts/{contact_id}/unsubscribe-token',
    response_model=UnsubscribeTokenRead,
)
def create_unsubscribe_token(
    contact_id: UUID,
    db: DbSession,
    settings: SettingsDep,
) -> dict[str, UUID | str]:
    contact_service = ContactService(db)
    contact = contact_service.get(contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail='Contact not found')
    return {
        'contact_id': contact.id,
        'token': contact_service.build_unsubscribe_token(contact.id, settings),
    }


@router.post('/tests/send-email', response_model=SendResponse)
def send_test_email(
    payload: TestEmailSendRequest,
    db: DbSession,
    settings: SettingsDep,
) -> dict[str, str | int | None]:
    try:
        return SendingService(db, settings).send_test(
            payload.template_id,
            str(payload.to_email),
            payload.variables,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post('/send/test', response_model=SendResponse, include_in_schema=False)
def send_test_email_legacy(
    payload: TestEmailSendRequest,
    db: DbSession,
    settings: SettingsDep,
) -> dict[str, str | int | None]:
    return send_test_email(payload, db, settings)


@router.post('/emails/send', response_model=EmailSendResponse)
def send_email(
    payload: EmailSendRequest,
    db: DbSession,
    settings: SettingsDep,
) -> dict[str, str | int | UUID | None]:
    try:
        return SendingService(db, settings).send_email_to_contact(
            payload.contact_id,
            payload.template_id,
            payload.variables,
            payload.campaign_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post('/send/contact', response_model=EmailSendResponse, include_in_schema=False)
def send_email_legacy(
    payload: EmailSendRequest,
    db: DbSession,
    settings: SettingsDep,
) -> dict[str, str | int | UUID | None]:
    return send_email(payload, db, settings)


@router.get('/events', response_model=list[EventRead])
def list_events(
    db: DbSession,
    limit: Limit = 100,
    offset: Offset = 0,
) -> list[EmailEvent]:
    return EventService(db).list(limit=limit, offset=offset)


@router.get('/events/list', response_model=ListResponse[EventRead])
def list_events_enveloped(
    db: DbSession,
    limit: Limit = 100,
    offset: Offset = 0,
    campaign_id: UUID | None = None,
    send_job_id: UUID | None = None,
    send_record_id: UUID | None = None,
    contact_id: UUID | None = None,
    event_type: EmailEventType | None = None,
) -> dict[str, object]:
    service = EventService(db)
    return {
        'items': service.list(
            limit=limit,
            offset=offset,
            campaign_id=campaign_id,
            send_job_id=send_job_id,
            send_record_id=send_record_id,
            contact_id=contact_id,
            event_type=event_type,
        ),
        'limit': limit,
        'offset': offset,
        'total': service.count(
            campaign_id=campaign_id,
            send_job_id=send_job_id,
            send_record_id=send_record_id,
            contact_id=contact_id,
            event_type=event_type,
        ),
    }


@router.get('/events/timeline', response_model=ListResponse[EventRead])
def list_event_timeline(
    db: DbSession,
    limit: Limit = 100,
    offset: Offset = 0,
    campaign_id: UUID | None = None,
    send_job_id: UUID | None = None,
    send_record_id: UUID | None = None,
    contact_id: UUID | None = None,
    event_type: EmailEventType | None = None,
) -> dict[str, object]:
    return list_events_enveloped(
        db=db,
        limit=limit,
        offset=offset,
        campaign_id=campaign_id,
        send_job_id=send_job_id,
        send_record_id=send_record_id,
        contact_id=contact_id,
        event_type=event_type,
    )


@router.post('/events')
def record_event(payload: EventCreate, db: DbSession) -> dict[str, UUID | str]:
    event = EventService(db).record(payload)
    return {'id': event.id, 'status': 'recorded'}


@router.get('/events/{event_id}', response_model=EventRead)
def get_event(event_id: UUID, db: DbSession) -> EmailEvent:
    event = EventService(db).get(event_id)
    if not event:
        raise HTTPException(status_code=404, detail='Event not found')
    return event


@router.get('/unsubscribe/{token}', response_model=UnsubscribeRead)
def unsubscribe(
    token: str,
    db: DbSession,
    settings: SettingsDep,
) -> dict[str, UUID | str]:
    contact_service = ContactService(db)
    contact_id = contact_service.verify_unsubscribe_token(token, settings)
    if not contact_id:
        raise HTTPException(status_code=400, detail='Invalid unsubscribe token')
    contact = contact_service.unsubscribe(contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail='Contact not found')
    return {'status': 'unsubscribed', 'contact_id': contact.id}
