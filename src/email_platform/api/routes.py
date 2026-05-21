import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
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
    Suppression,
)
from email_platform.schemas.contracts import (
    AudienceCreate,
    AudiencePreviewRead,
    AudiencePreviewRequest,
    AudienceRead,
    AudienceUpdate,
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
    ListResponse,
    ProviderWebhookIngestRead,
    SendGridWebhookEvent,
    SendResponse,
    SuppressionRead,
    TemplateCreate,
    TemplateRead,
    TemplateUpdate,
    TestEmailSendRequest,
    UnsubscribeRead,
    UnsubscribeTokenRead,
)
from email_platform.services.audiences import AudienceService
from email_platform.services.campaigns import CampaignService
from email_platform.services.contacts import ContactService
from email_platform.services.data_sources import DataSourceService
from email_platform.services.delivery import DeliveryService
from email_platform.services.events import EventService
from email_platform.services.provider_webhooks import ProviderWebhookService
from email_platform.services.sending import SendingService
from email_platform.services.suppressions import SuppressionService
from email_platform.services.templates import TemplateService
from email_platform.services.webhook_security import SendGridWebhookVerifier, WebhookSignatureError

router = APIRouter(prefix='/api/v1')
DbSession = Annotated[Session, Depends(get_db)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
Limit = Annotated[int, Query(ge=1, le=500)]
Offset = Annotated[int, Query(ge=0)]


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
