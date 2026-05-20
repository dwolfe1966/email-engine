from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from email_platform.models.entities import CampaignStatus, EmailEventType


class ContactUpsert(BaseModel):
    email: EmailStr
    first_name: str | None = None
    last_name: str | None = None
    source: str | None = None
    attributes: dict = Field(default_factory=dict)


class ContactRead(ContactUpsert):
    id: UUID
    is_unsubscribed: bool

    model_config = {'from_attributes': True}


class TemplateCreate(BaseModel):
    name: str
    subject: str
    html_body: str
    text_body: str | None = None


class TemplateRead(TemplateCreate):
    id: UUID

    model_config = {'from_attributes': True}


class CampaignCreate(BaseModel):
    name: str
    template_id: UUID
    audience_query: dict = Field(default_factory=dict)


class CampaignRead(CampaignCreate):
    id: UUID
    status: CampaignStatus

    model_config = {'from_attributes': True}


class TestSendRequest(BaseModel):
    template_id: UUID
    to_email: EmailStr
    variables: dict = Field(default_factory=dict)


class EventCreate(BaseModel):
    contact_id: UUID | None = None
    campaign_id: UUID | None = None
    event_type: EmailEventType
    provider_message_id: str | None = None
    metadata_json: dict = Field(default_factory=dict)
