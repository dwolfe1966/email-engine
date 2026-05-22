import json
from typing import Annotated, cast
from urllib.parse import quote, urlparse
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

from email_platform.core.settings import Settings, get_settings
from email_platform.db.session import get_db
from email_platform.models.entities import (
    Audience,
    Campaign,
    Contact,
    DataSource,
    DataSourceMapping,
    EmailEvent,
    EmailTemplate,
    EmailTemplateVersion,
    Journey,
    JourneyEnrollment,
    JourneyEnrollmentStatus,
    JourneyStep,
    Suppression,
)
from email_platform.schemas.contracts import (
    AudienceCreate,
    AudienceImportPreviewRead,
    AudienceImportRead,
    AudiencePreviewRead,
    AudiencePreviewRequest,
    AudienceRead,
    AudienceUpdate,
    CampaignAnalyticsRead,
    CampaignCreate,
    CampaignLaunchRead,
    CampaignLaunchRequest,
    CampaignRead,
    CampaignSendJobRead,
    CampaignUpdate,
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
    DataSourceUpdate,
    DeleteResponse,
    DeliveryRunRead,
    EmailSendRecordRead,
    EmailSendRequest,
    EmailSendResponse,
    EventCreate,
    EventRead,
    JourneyCreate,
    JourneyEnrollmentCreate,
    JourneyEnrollmentRead,
    JourneyProcessRead,
    JourneyRead,
    JourneyStepCreate,
    JourneyStepExecutionRead,
    JourneyStepRead,
    JourneyStepUpdate,
    JourneyUpdate,
    JsonObject,
    ListResponse,
    ProviderWebhookIngestRead,
    SendGridWebhookEvent,
    SendResponse,
    SuppressionCreate,
    SuppressionRead,
    TemplateCreate,
    TemplatePreviewRead,
    TemplatePreviewRequest,
    TemplateRead,
    TemplateUpdate,
    TemplateValidationRead,
    TemplateValidationRequest,
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
from email_platform.services.campaigns import CampaignService
from email_platform.services.contacts import ContactService
from email_platform.services.data_sources import DataSourceService
from email_platform.services.delivery import DeliveryService
from email_platform.services.events import EventService
from email_platform.services.journeys import JourneyService
from email_platform.services.provider_webhooks import ProviderWebhookService
from email_platform.services.sending import SendingService
from email_platform.services.suppressions import SuppressionService
from email_platform.services.templates import TemplateService
from email_platform.services.tracking import TrackingService
from email_platform.services.webhook_security import SendGridWebhookVerifier, WebhookSignatureError

router = APIRouter(prefix='/api/v1')
DbSession = Annotated[Session, Depends(get_db)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
Limit = Annotated[int, Query(ge=1, le=500)]
Offset = Annotated[int, Query(ge=0)]
TRANSPARENT_GIF = (
    b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!'
    b'\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00'
    b'\x01\x00\x00\x02\x02D\x01\x00;'
)


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


@router.post('/templates/preview', response_model=TemplatePreviewRead)
def preview_template(payload: TemplatePreviewRequest, db: DbSession) -> TemplatePreviewRead:
    return TemplateService(db).preview(payload)


@router.post('/templates/validate', response_model=TemplateValidationRead)
def validate_template(
    payload: TemplateValidationRequest, db: DbSession
) -> TemplateValidationRead:
    return TemplateService(db).validate(payload)


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
    campaign = CampaignService(db).update(campaign_id, payload)
    if not campaign:
        raise HTTPException(status_code=404, detail='Campaign not found')
    return campaign


@router.delete('/campaigns/{campaign_id}', response_model=DeleteResponse)
def delete_campaign(campaign_id: UUID, db: DbSession) -> dict[str, UUID]:
    if not CampaignService(db).delete(campaign_id):
        raise HTTPException(status_code=404, detail='Campaign not found')
    return {'id': campaign_id}


@router.post('/campaigns/{campaign_id}/launch', response_model=CampaignLaunchRead)
def launch_campaign(
    campaign_id: UUID, payload: CampaignLaunchRequest, db: DbSession
) -> CampaignLaunchRead:
    try:
        launch = CampaignService(db).launch(campaign_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if not launch:
        raise HTTPException(status_code=404, detail='Campaign not found')
    return launch


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
