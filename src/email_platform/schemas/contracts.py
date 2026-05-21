from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from email_platform.models.entities import (
    AudienceStatus,
    CampaignStatus,
    DataSourceStatus,
    DataSourceType,
    EmailEventType,
)

JsonObject = dict[str, str | int | float | bool | None | list[object] | dict[str, object]]
T = TypeVar('T')


class ListResponse(BaseModel, Generic[T]):
    items: list[T]
    limit: int
    offset: int
    total: int


class DeleteResponse(BaseModel):
    status: str = 'deleted'
    id: UUID


class ContactUpsert(BaseModel):
    email: EmailStr
    first_name: str | None = None
    last_name: str | None = None
    source: str | None = None
    attributes: JsonObject = Field(default_factory=dict)


class ContactUpdate(BaseModel):
    email: EmailStr | None = None
    first_name: str | None = None
    last_name: str | None = None
    source: str | None = None
    attributes: JsonObject | None = None
    is_unsubscribed: bool | None = None


class ContactRead(ContactUpsert):
    id: UUID
    is_unsubscribed: bool

    model_config = {'from_attributes': True}


class TemplateCreate(BaseModel):
    name: str
    subject: str
    html_body: str
    text_body: str | None = None


class TemplateUpdate(BaseModel):
    name: str | None = None
    subject: str | None = None
    html_body: str | None = None
    text_body: str | None = None


class TemplateRead(TemplateCreate):
    id: UUID

    model_config = {'from_attributes': True}


class CampaignCreate(BaseModel):
    name: str
    template_id: UUID
    audience_query: JsonObject = Field(default_factory=dict)


class CampaignUpdate(BaseModel):
    name: str | None = None
    template_id: UUID | None = None
    audience_query: JsonObject | None = None
    status: CampaignStatus | None = None


class CampaignRead(CampaignCreate):
    id: UUID
    status: CampaignStatus

    model_config = {'from_attributes': True}


class DataSourceCreate(BaseModel):
    name: str
    source_type: DataSourceType
    config: JsonObject = Field(default_factory=dict)
    secret_ref: str | None = None


class DataSourceUpdate(BaseModel):
    name: str | None = None
    source_type: DataSourceType | None = None
    status: DataSourceStatus | None = None
    config: JsonObject | None = None
    secret_ref: str | None = None


class DataSourceRead(DataSourceCreate):
    id: UUID
    status: DataSourceStatus

    model_config = {'from_attributes': True}


class DataSourceMappingCreate(BaseModel):
    data_source_id: UUID
    name: str
    object_type: str
    mapping: JsonObject = Field(default_factory=dict)
    extraction_plan: JsonObject = Field(default_factory=dict)


class DataSourceMappingUpdate(BaseModel):
    data_source_id: UUID | None = None
    name: str | None = None
    object_type: str | None = None
    mapping: JsonObject | None = None
    extraction_plan: JsonObject | None = None


class DataSourceMappingRead(DataSourceMappingCreate):
    id: UUID

    model_config = {'from_attributes': True}


class AudienceCreate(BaseModel):
    name: str
    description: str | None = None
    rule_tree: JsonObject = Field(default_factory=dict)


class AudienceUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: AudienceStatus | None = None
    rule_tree: JsonObject | None = None


class AudienceRead(AudienceCreate):
    id: UUID
    status: AudienceStatus
    estimated_count: int

    model_config = {'from_attributes': True}


class AudiencePreviewRequest(BaseModel):
    rule_tree: JsonObject
    limit: int = Field(default=25, ge=1, le=100)


class AudiencePreviewRead(BaseModel):
    estimated_count: int
    sample_contacts: list[ContactRead]


class TestEmailSendRequest(BaseModel):
    template_id: UUID
    to_email: EmailStr
    variables: JsonObject = Field(default_factory=dict)


class EmailSendRequest(BaseModel):
    contact_id: UUID
    template_id: UUID
    variables: JsonObject = Field(default_factory=dict)
    campaign_id: UUID | None = None


class SendResponse(BaseModel):
    provider: str
    provider_message_id: str | None = None
    status_code: int


class EmailSendResponse(SendResponse):
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
