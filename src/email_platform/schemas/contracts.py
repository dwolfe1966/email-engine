from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from email_platform.models.entities import CampaignStatus, EmailEventType

JsonObject = dict[str, str | int | float | bool | None | list[object] | dict[str, object]]


class ContactUpsert(BaseModel):
    email: EmailStr
    first_name: str | None = None
    last_name: str | None = None
    source: str | None = None
    attributes: JsonObject = Field(default_factory=dict)


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
    audience_query: JsonObject = Field(default_factory=dict)


class CampaignRead(CampaignCreate):
    id: UUID
    status: CampaignStatus

    model_config = {'from_attributes': True}


class TestSendRequest(BaseModel):
    template_id: UUID
    to_email: EmailStr
    variables: JsonObject = Field(default_factory=dict)


class ContactSendRequest(BaseModel):
    contact_id: UUID
    template_id: UUID
    variables: JsonObject = Field(default_factory=dict)
    campaign_id: UUID | None = None


class SendResponse(BaseModel):
    provider: str
    provider_message_id: str | None = None
    status_code: int


class ContactSendResponse(SendResponse):
    contact_id: UUID
    template_id: UUID
    campaign_id: UUID | None = None


class EventCreate(BaseModel):
    contact_id: UUID | None = None
    campaign_id: UUID | None = None
    event_type: EmailEventType
    provider_message_id: str | None = None
    metadata_json: JsonObject = Field(default_factory=dict)


class EventRead(EventCreate):
    id: UUID

    model_config = {'from_attributes': True}


class UnsubscribeTokenRead(BaseModel):
    contact_id: UUID
    token: str


class UnsubscribeRead(BaseModel):
    status: str
    contact_id: UUID
