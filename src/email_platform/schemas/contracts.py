from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from email_platform.models.entities import (
    AudienceStatus,
    CampaignStatus,
    DataSourceStatus,
    DataSourceType,
    EmailEventType,
    EmailSendStatus,
    SendJobStatus,
    SuppressionReason,
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
    css_body: str | None = None
    text_body: str | None = None


class TemplateUpdate(BaseModel):
    name: str | None = None
    subject: str | None = None
    html_body: str | None = None
    css_body: str | None = None
    text_body: str | None = None


class TemplateVersionCreate(BaseModel):
    subject: str | None = None
    html_body: str | None = None
    css_body: str | None = None
    text_body: str | None = None
    document_json: JsonObject = Field(default_factory=dict)
    set_current: bool = True


class TemplateVersionRead(BaseModel):
    id: UUID
    template_id: UUID
    version_number: int
    subject: str
    html_body: str
    css_body: str | None = None
    text_body: str | None = None
    document_json: JsonObject
    is_current: bool

    model_config = {'from_attributes': True}


class TemplatePreviewRequest(BaseModel):
    subject: str
    html_body: str
    css_body: str | None = None
    text_body: str | None = None
    variables: JsonObject = Field(default_factory=dict)


class TemplatePreviewRead(BaseModel):
    ok: bool = True
    subject: str
    html_body: str
    css_body: str | None = None
    text_body: str | None = None
    errors: list[str] = Field(default_factory=list)
    undeclared_variables: list[str] = Field(default_factory=list)


class TemplateValidationRequest(BaseModel):
    subject: str
    html_body: str
    css_body: str | None = None
    text_body: str | None = None
    variables: JsonObject = Field(default_factory=dict)


class TemplateValidationRead(BaseModel):
    ok: bool
    errors: list[str] = Field(default_factory=list)
    undeclared_variables: list[str] = Field(default_factory=list)
    missing_variables: list[str] = Field(default_factory=list)


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


class CampaignLaunchRequest(BaseModel):
    audience_id: UUID | None = None
    rule_tree: JsonObject | None = None
    variables: JsonObject = Field(default_factory=dict)
    dry_run: bool = False


class CampaignLaunchRead(BaseModel):
    job_id: UUID
    campaign_id: UUID
    status: SendJobStatus
    requested_count: int
    queued_count: int
    suppressed_count: int
    dry_run: bool


class CampaignSendJobRead(BaseModel):
    id: UUID
    campaign_id: UUID
    status: SendJobStatus
    requested_count: int
    queued_count: int
    suppressed_count: int
    metadata_json: JsonObject

    model_config = {'from_attributes': True}


class EmailSendRecordRead(BaseModel):
    id: UUID
    campaign_id: UUID
    send_job_id: UUID
    contact_id: UUID
    template_id: UUID
    status: EmailSendStatus
    to_email: EmailStr
    variables: JsonObject
    provider: str | None = None
    provider_message_id: str | None = None
    error_message: str | None = None

    model_config = {'from_attributes': True}


class DeliveryRunRead(BaseModel):
    claimed_count: int
    sent_count: int
    failed_count: int
    processed_record_ids: list[str]


class MetricCount(BaseModel):
    name: str
    count: int


class CampaignAnalyticsRead(BaseModel):
    campaign_id: UUID
    send_job_id: UUID | None = None
    requested_count: int
    queued_count: int
    sent_count: int
    failed_count: int
    suppressed_count: int
    delivered_count: int
    opened_count: int
    clicked_count: int
    bounced_count: int
    complained_count: int
    unsubscribed_count: int
    open_rate: float
    click_rate: float
    bounce_rate: float
    status_counts: list[MetricCount]
    event_counts: list[MetricCount]


class TrackingLinksRead(BaseModel):
    send_record_id: UUID
    token: str
    open_url: str
    click_url: str
    click_url_template: str


class TrackingEventRead(BaseModel):
    status: str = 'recorded'
    event_id: UUID
    send_record_id: UUID
    event_type: EmailEventType


class SuppressionRead(BaseModel):
    id: UUID
    email: EmailStr
    contact_id: UUID | None = None
    reason: SuppressionReason
    source: str
    provider_message_id: str | None = None
    metadata_json: JsonObject

    model_config = {'from_attributes': True}


class SendGridWebhookEvent(BaseModel):
    email: EmailStr
    event: str
    sg_message_id: str | None = None
    smtp_id: str | None = None
    reason: str | None = None
    url: str | None = None
    timestamp: int | None = None

    model_config = {'extra': 'allow'}


class ProviderWebhookIngestRead(BaseModel):
    processed_count: int
    suppressed_count: int
    updated_send_records: int


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


class AudienceImportRead(BaseModel):
    audience_id: UUID
    import_id: UUID
    imported_count: int
    created_count: int
    updated_count: int
    skipped_count: int
    errors: list[str] = Field(default_factory=list)


class AudienceImportPreviewRead(BaseModel):
    headers: list[str]
    row_count: int
    sample_rows: list[dict[str, str]]
    inferred_mapping: dict[str, str]
    errors: list[str] = Field(default_factory=list)


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
    send_record_id: UUID | None = None
    send_job_id: UUID | None = None
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
