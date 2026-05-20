from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from email_platform.core.settings import Settings, get_settings
from email_platform.db.session import get_db
from email_platform.schemas.contracts import (
    CampaignCreate,
    CampaignRead,
    ContactRead,
    ContactUpsert,
    EventCreate,
    TemplateCreate,
    TemplateRead,
    TestSendRequest,
)
from email_platform.services.campaigns import CampaignService
from email_platform.services.contacts import ContactService
from email_platform.services.events import EventService
from email_platform.services.sending import SendingService
from email_platform.services.templates import TemplateService

router = APIRouter(prefix='/api/v1')


@router.post('/templates', response_model=TemplateRead)
def create_template(payload: TemplateCreate, db: Session = Depends(get_db)):
    return TemplateService(db).create(payload)


@router.get('/templates/{template_id}', response_model=TemplateRead)
def get_template(template_id: UUID, db: Session = Depends(get_db)):
    template = TemplateService(db).get(template_id)
    if not template:
        raise HTTPException(status_code=404, detail='Template not found')
    return template


@router.post('/campaigns', response_model=CampaignRead)
def create_campaign(payload: CampaignCreate, db: Session = Depends(get_db)):
    return CampaignService(db).create(payload)


@router.post('/audiences/contacts', response_model=ContactRead)
def upsert_contact(payload: ContactUpsert, db: Session = Depends(get_db)):
    return ContactService(db).upsert(payload)


@router.post('/send/test')
def send_test(
    payload: TestSendRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    try:
        return SendingService(db, settings).send_test(payload.template_id, str(payload.to_email), payload.variables)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post('/events')
def record_event(payload: EventCreate, db: Session = Depends(get_db)):
    event = EventService(db).record(payload)
    return {'id': event.id, 'status': 'recorded'}


@router.get('/unsubscribe/{token}')
def unsubscribe(token: str):
    # TODO: verify signed token and mark contact unsubscribed.
    return {'status': 'received', 'token': token}
