from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
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
)
from email_platform.schemas.contracts import (
    AudienceCreate,
    AudiencePreviewRead,
    AudiencePreviewRequest,
    AudienceRead,
    CampaignCreate,
    CampaignRead,
    ContactRead,
    ContactUpsert,
    DataSourceCreate,
    DataSourceMappingCreate,
    DataSourceMappingRead,
    DataSourceRead,
    EmailSendRequest,
    EmailSendResponse,
    EventCreate,
    EventRead,
    SendResponse,
    TemplateCreate,
    TemplateRead,
    TestEmailSendRequest,
    UnsubscribeRead,
    UnsubscribeTokenRead,
)
from email_platform.services.audiences import AudienceService
from email_platform.services.campaigns import CampaignService
from email_platform.services.contacts import ContactService
from email_platform.services.data_sources import DataSourceService
from email_platform.services.events import EventService
from email_platform.services.sending import SendingService
from email_platform.services.templates import TemplateService

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


@router.post('/templates', response_model=TemplateRead)
def create_template(payload: TemplateCreate, db: DbSession) -> EmailTemplate:
    return TemplateService(db).create(payload)


@router.get('/templates/{template_id}', response_model=TemplateRead)
def get_template(template_id: UUID, db: DbSession) -> EmailTemplate:
    template = TemplateService(db).get(template_id)
    if not template:
        raise HTTPException(status_code=404, detail='Template not found')
    return template


@router.get('/campaigns', response_model=list[CampaignRead])
def list_campaigns(
    db: DbSession,
    limit: Limit = 100,
    offset: Offset = 0,
) -> list[Campaign]:
    return CampaignService(db).list(limit=limit, offset=offset)


@router.post('/campaigns', response_model=CampaignRead)
def create_campaign(payload: CampaignCreate, db: DbSession) -> Campaign:
    return CampaignService(db).create(payload)


@router.get('/campaigns/{campaign_id}', response_model=CampaignRead)
def get_campaign(campaign_id: UUID, db: DbSession) -> Campaign:
    campaign = CampaignService(db).get(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail='Campaign not found')
    return campaign


@router.get('/audiences/contacts', response_model=list[ContactRead])
def list_contacts(
    db: DbSession,
    limit: Limit = 100,
    offset: Offset = 0,
) -> list[Contact]:
    return ContactService(db).list(limit=limit, offset=offset)


@router.post('/audiences/contacts', response_model=ContactRead)
def upsert_contact(payload: ContactUpsert, db: DbSession) -> Contact:
    return ContactService(db).upsert(payload)


@router.get('/audiences/contacts/{contact_id}', response_model=ContactRead)
def get_contact(contact_id: UUID, db: DbSession) -> Contact:
    contact = ContactService(db).get(contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail='Contact not found')
    return contact


@router.get('/data-sources', response_model=list[DataSourceRead])
def list_data_sources(
    db: DbSession,
    limit: Limit = 100,
    offset: Offset = 0,
) -> list[DataSource]:
    return DataSourceService(db).list_items(limit=limit, offset=offset)


@router.post('/data-sources', response_model=DataSourceRead)
def create_data_source(payload: DataSourceCreate, db: DbSession) -> DataSource:
    return DataSourceService(db).create(payload)


@router.get('/data-sources/{data_source_id}', response_model=DataSourceRead)
def get_data_source(data_source_id: UUID, db: DbSession) -> DataSource:
    data_source = DataSourceService(db).get(data_source_id)
    if not data_source:
        raise HTTPException(status_code=404, detail='Data source not found')
    return data_source


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


@router.post('/data-source-mappings', response_model=DataSourceMappingRead)
def create_data_source_mapping(
    payload: DataSourceMappingCreate, db: DbSession
) -> DataSourceMapping:
    data_source_service = DataSourceService(db)
    if not data_source_service.get(payload.data_source_id):
        raise HTTPException(status_code=404, detail='Data source not found')
    return data_source_service.create_mapping(payload)


@router.get('/audiences', response_model=list[AudienceRead])
def list_audiences(
    db: DbSession,
    limit: Limit = 100,
    offset: Offset = 0,
) -> list[Audience]:
    return AudienceService(db).list_items(limit=limit, offset=offset)


@router.post('/audiences', response_model=AudienceRead)
def create_audience(payload: AudienceCreate, db: DbSession) -> Audience:
    return AudienceService(db).create(payload)


@router.get('/audiences/{audience_id}', response_model=AudienceRead)
def get_audience(audience_id: UUID, db: DbSession) -> Audience:
    audience = AudienceService(db).get(audience_id)
    if not audience:
        raise HTTPException(status_code=404, detail='Audience not found')
    return audience


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
