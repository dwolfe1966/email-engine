from datetime import date, datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from email_platform.models.entities import (
    AudienceStatus,
    CampaignStatus,
    DataSourceImportStatus,
    DataSourceStatus,
    DataSourceType,
    DeliveryRouteStatus,
    DeliveryRouteType,
    EmailEventType,
    EmailSendStatus,
    JourneyEnrollmentStatus,
    JourneyStatus,
    JourneyStepExecutionStatus,
    JourneyStepType,
    MtaIpPoolType,
    MtaOperationalStatus,
    MtaProviderType,
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
    document_json: JsonObject = Field(default_factory=dict)


class TemplateUpdate(BaseModel):
    name: str | None = None
    subject: str | None = None
    html_body: str | None = None
    css_body: str | None = None
    text_body: str | None = None
    document_json: JsonObject | None = None


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


class TemplateDocumentRead(BaseModel):
    template_id: UUID
    version_id: UUID | None = None
    version_number: int | None = None
    document_json: JsonObject = Field(default_factory=dict)


class TemplateDocumentUpdate(BaseModel):
    document_json: JsonObject = Field(default_factory=dict)
    set_current: bool = True


class TemplateDocumentRenderRequest(BaseModel):
    document_json: JsonObject = Field(default_factory=dict)
    subject: str = ''
    css_body: str | None = None
    text_body: str | None = None
    variables: JsonObject = Field(default_factory=dict)


class TemplateDocumentImportRequest(BaseModel):
    html_body: str


class TemplateDocumentImportRead(BaseModel):
    document_json: JsonObject = Field(default_factory=dict)
    block_count: int = 0
    raw_block_count: int = 0


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
    lint_errors: list[str] = Field(default_factory=list)
    lint_warnings: list[str] = Field(default_factory=list)


class TemplateVariableRead(BaseModel):
    name: str
    required: bool = True
    native: bool = False
    sources: list[str] = Field(default_factory=list)
    sample_value: object = None


class TemplateVariablesRead(BaseModel):
    ok: bool
    variables: list[TemplateVariableRead] = Field(default_factory=list)
    native_variables: list[TemplateVariableRead] = Field(default_factory=list)
    sample_variables: JsonObject = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)


class TemplateLintRead(BaseModel):
    ok: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class TemplateRead(TemplateCreate):
    id: UUID

    model_config = {'from_attributes': True}


class AITemplateDraftRequest(BaseModel):
    brief: str
    brand: JsonObject = Field(default_factory=dict)
    required_variables: list[str] = Field(default_factory=list)
    audience_summary: str | None = None


class AITemplateEditRequest(BaseModel):
    instruction: str
    current_subject: str
    current_html: str
    current_css: str | None = None
    current_text: str | None = None
    brand: JsonObject = Field(default_factory=dict)
    required_variables: list[str] = Field(default_factory=list)
    sample_variables: JsonObject = Field(default_factory=dict)
    audience_summary: str | None = None


class AITemplateRecommendRequest(BaseModel):
    current_subject: str
    current_html: str
    current_css: str | None = None
    current_text: str | None = None
    sample_variables: JsonObject = Field(default_factory=dict)
    goals: list[str] = Field(default_factory=list)
    audience_summary: str | None = None


class AITemplateRecommendationRead(BaseModel):
    code: str
    category: str
    priority: str
    title: str
    detail: str
    suggested_instruction: str
    confidence: float = Field(ge=0, le=1)


class AITemplateRecommendationsRead(BaseModel):
    recommendations: list[AITemplateRecommendationRead] = Field(default_factory=list)
    summary: list[str] = Field(default_factory=list)
    sample_variables: JsonObject = Field(default_factory=dict)
    validation: TemplateValidationRead
    template_variables: TemplateVariablesRead
    provider: str = 'email-engine'
    model: str = 'deterministic-template-recommend-v1'


class AITemplateDraftRead(BaseModel):
    subject: str
    html_body: str
    css_body: str | None = None
    text_body: str | None = None
    changed_fields: list[str] = Field(default_factory=list)
    change_summary: list[str] = Field(default_factory=list)
    sample_variables: JsonObject = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
    validation: TemplateValidationRead
    template_variables: TemplateVariablesRead
    provider: str = 'email-engine'
    model: str = 'deterministic-template-draft-v1'


class AIAnalyticsAnalysisRequest(BaseModel):
    report_type: str = 'analytics'
    report_context: JsonObject = Field(default_factory=dict)
    goals: list[str] = Field(default_factory=list)


class AIAnalyticsRecommendationRead(BaseModel):
    code: str
    category: str
    priority: str
    title: str
    detail: str
    suggested_action: str
    confidence: float = Field(ge=0, le=1)


class AIAnalyticsAnalysisRead(BaseModel):
    summary: list[str] = Field(default_factory=list)
    recommendations: list[AIAnalyticsRecommendationRead] = Field(default_factory=list)
    provider: str = 'email-engine'
    model: str = 'deterministic-analytics-analysis-v1'


class AICampaignAnalysisRequest(BaseModel):
    campaign_context: JsonObject = Field(default_factory=dict)
    goals: list[str] = Field(default_factory=list)


class AICampaignRecommendationRead(BaseModel):
    code: str
    category: str
    priority: str
    title: str
    detail: str
    suggested_instruction: str
    confidence: float = Field(ge=0, le=1)


class AICampaignAnalysisRead(BaseModel):
    summary: list[str] = Field(default_factory=list)
    recommendations: list[AICampaignRecommendationRead] = Field(default_factory=list)
    validation: JsonObject = Field(default_factory=dict)
    provider: str = 'email-engine'
    model: str = 'deterministic-campaign-analysis-v1'


class AIAudienceAnalysisRequest(BaseModel):
    audience_context: JsonObject = Field(default_factory=dict)
    goals: list[str] = Field(default_factory=list)


class AIAudienceRecommendationRead(BaseModel):
    code: str
    category: str
    priority: str
    title: str
    detail: str
    suggested_action: str
    confidence: float = Field(ge=0, le=1)


class AIAudienceAnalysisRead(BaseModel):
    summary: list[str] = Field(default_factory=list)
    recommendations: list[AIAudienceRecommendationRead] = Field(default_factory=list)
    provider: str = 'email-engine'
    model: str = 'deterministic-audience-analysis-v1'


class AIDeliveryAnalysisRequest(BaseModel):
    delivery_context: JsonObject = Field(default_factory=dict)
    goals: list[str] = Field(default_factory=list)


class AIDeliveryRecommendationRead(BaseModel):
    code: str
    category: str
    priority: str
    title: str
    detail: str
    suggested_action: str
    confidence: float = Field(ge=0, le=1)


class AIDeliveryAnalysisRead(BaseModel):
    summary: list[str] = Field(default_factory=list)
    recommendations: list[AIDeliveryRecommendationRead] = Field(default_factory=list)
    provider: str = 'email-engine'
    model: str = 'deterministic-delivery-analysis-v1'


class AIJourneyAnalysisRequest(BaseModel):
    journey_context: JsonObject = Field(default_factory=dict)
    goals: list[str] = Field(default_factory=list)


class AIJourneyRecommendationRead(BaseModel):
    code: str
    category: str
    priority: str
    title: str
    detail: str
    suggested_action: str
    confidence: float = Field(ge=0, le=1)


class AIJourneyAnalysisRead(BaseModel):
    summary: list[str] = Field(default_factory=list)
    recommendations: list[AIJourneyRecommendationRead] = Field(default_factory=list)
    provider: str = 'email-engine'
    model: str = 'deterministic-journey-analysis-v1'


class CampaignCreate(BaseModel):
    name: str
    template_id: UUID
    audience_query: JsonObject = Field(default_factory=dict)
    scheduled_at: datetime | None = None


class CampaignUpdate(BaseModel):
    name: str | None = None
    template_id: UUID | None = None
    audience_query: JsonObject | None = None
    status: CampaignStatus | None = None
    scheduled_at: datetime | None = None


class CampaignCloneRequest(BaseModel):
    name: str | None = None


class CampaignRead(CampaignCreate):
    id: UUID
    status: CampaignStatus

    model_config = {'from_attributes': True}


class CampaignLaunchRequest(BaseModel):
    audience_id: UUID | None = None
    rule_tree: JsonObject | None = None
    variables: JsonObject = Field(default_factory=dict)
    scheduled_at: datetime | None = None
    dry_run: bool = False


class CampaignTestSendRequest(BaseModel):
    to_email: EmailStr
    variables: JsonObject = Field(default_factory=dict)


class CampaignTestPreviewRequest(BaseModel):
    variables: JsonObject = Field(default_factory=dict)


class CampaignLaunchRead(BaseModel):
    job_id: UUID
    campaign_id: UUID
    audience_snapshot_id: UUID | None = None
    status: SendJobStatus
    requested_count: int
    queued_count: int
    suppressed_count: int
    dry_run: bool


class CampaignValidationRead(BaseModel):
    campaign_id: UUID
    ok: bool
    status: CampaignStatus
    requested_count: int = 0
    queued_count: int = 0
    suppressed_count: int = 0
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    undeclared_variables: list[str] = Field(default_factory=list)
    missing_variables: list[str] = Field(default_factory=list)


class CampaignProcessDueRead(BaseModel):
    claimed_count: int
    launched_count: int
    failed_count: int
    job_ids: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class JourneyStepCreate(BaseModel):
    name: str
    step_type: JourneyStepType
    position: int = 0
    config: JsonObject = Field(default_factory=dict)


class JourneyStepUpdate(BaseModel):
    name: str | None = None
    step_type: JourneyStepType | None = None
    position: int | None = None
    config: JsonObject | None = None


class JourneyStepRead(JourneyStepCreate):
    id: UUID
    journey_id: UUID

    model_config = {'from_attributes': True}


class JourneyCreate(BaseModel):
    name: str
    description: str | None = None
    entry_rule_tree: JsonObject = Field(default_factory=dict)
    exit_rule_tree: JsonObject = Field(default_factory=dict)
    metadata_json: JsonObject = Field(default_factory=dict)


class JourneyUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: JourneyStatus | None = None
    entry_rule_tree: JsonObject | None = None
    exit_rule_tree: JsonObject | None = None
    metadata_json: JsonObject | None = None


class JourneyRead(JourneyCreate):
    id: UUID
    status: JourneyStatus
    steps: list[JourneyStepRead] = Field(default_factory=list)

    model_config = {'from_attributes': True}


class JourneyGraphNodeCounts(BaseModel):
    active_count: int = 0
    completed_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    queued_send_count: int = 0


class JourneyGraphNodeRead(BaseModel):
    id: str
    step_id: UUID
    label: str
    step_type: JourneyStepType
    position: int
    state: str
    x: int
    y: int
    config: JsonObject
    counts: JourneyGraphNodeCounts
    recent_error: str | None = None


class JourneyGraphEdgeRead(BaseModel):
    id: str
    source: str
    target: str
    label: str | None = None
    condition: object | None = None
    edge_type: str = 'sequence'


class JourneyGraphRead(BaseModel):
    journey_id: UUID
    name: str
    status: JourneyStatus
    nodes: list[JourneyGraphNodeRead]
    edges: list[JourneyGraphEdgeRead]


class JourneyEnrollmentCreate(BaseModel):
    contact_id: UUID
    variables: JsonObject = Field(default_factory=dict)


class JourneyEnrollmentRead(BaseModel):
    id: UUID
    journey_id: UUID
    contact_id: UUID
    current_step_id: UUID | None = None
    status: JourneyEnrollmentStatus
    variables: JsonObject
    due_at: datetime | None = None
    entered_at: datetime
    exited_at: datetime | None = None
    last_error: str | None = None

    model_config = {'from_attributes': True}


class JourneyStepExecutionRead(BaseModel):
    id: UUID
    enrollment_id: UUID
    journey_id: UUID
    step_id: UUID
    contact_id: UUID
    status: JourneyStepExecutionStatus
    send_record_id: UUID | None = None
    metadata_json: JsonObject
    error_message: str | None = None
    executed_at: datetime

    model_config = {'from_attributes': True}


class JourneyProcessRead(BaseModel):
    claimed_count: int
    completed_count: int
    failed_count: int
    queued_send_count: int
    enrollment_ids: list[str]


class CampaignSendJobRead(BaseModel):
    id: UUID
    campaign_id: UUID | None = None
    audience_snapshot_id: UUID | None = None
    status: SendJobStatus
    requested_count: int
    queued_count: int
    suppressed_count: int
    metadata_json: JsonObject

    model_config = {'from_attributes': True}


class CampaignSendJobProgressRead(BaseModel):
    send_job_id: UUID
    campaign_id: UUID | None = None
    status: SendJobStatus
    requested_count: int
    queued_count: int
    sending_count: int
    sent_count: int
    failed_count: int
    suppressed_count: int
    skipped_count: int
    dead_lettered_count: int = 0
    processed_count: int
    remaining_count: int
    active_count: int
    percent_complete: float


class EmailSendRecordRead(BaseModel):
    id: UUID
    campaign_id: UUID | None = None
    send_job_id: UUID
    contact_id: UUID
    template_id: UUID
    status: EmailSendStatus
    to_email: EmailStr
    variables: JsonObject
    provider: str | None = None
    provider_message_id: str | None = None
    error_message: str | None = None
    attempt_count: int = 0
    max_attempts: int = 3
    next_attempt_at: datetime | None = None

    model_config = {'from_attributes': True}


class DeliveryAttemptRead(BaseModel):
    id: UUID
    send_record_id: UUID
    send_job_id: UUID | None = None
    campaign_id: UUID | None = None
    attempt_number: int
    provider: str | None = None
    route_type: str | None = None
    route_key: str | None = None
    status: str
    provider_message_id: str | None = None
    smtp_response_code: int | None = None
    smtp_response: str | None = None
    error_message: str | None = None
    metadata_json: JsonObject
    started_at: datetime
    completed_at: datetime | None = None

    model_config = {'from_attributes': True}


class DeliveryRouteCreate(BaseModel):
    name: str
    route_type: DeliveryRouteType
    priority: int = 100
    config: JsonObject = Field(default_factory=dict)
    secret_ref: str | None = None
    metadata_json: JsonObject = Field(default_factory=dict)


class DeliveryRouteUpdate(BaseModel):
    name: str | None = None
    route_type: DeliveryRouteType | None = None
    status: DeliveryRouteStatus | None = None
    priority: int | None = None
    config: JsonObject | None = None
    secret_ref: str | None = None
    metadata_json: JsonObject | None = None


class DeliveryRouteRead(DeliveryRouteCreate):
    id: UUID
    status: DeliveryRouteStatus

    model_config = {'from_attributes': True}


class DomainDeliveryPolicyCreate(BaseModel):
    domain: str
    route_id: UUID | None = None
    max_per_minute: int | None = None
    max_concurrent: int | None = None
    warmup_stage: str | None = None
    paused_until: datetime | None = None
    metadata_json: JsonObject = Field(default_factory=dict)


class DomainDeliveryPolicyUpdate(BaseModel):
    domain: str | None = None
    route_id: UUID | None = None
    max_per_minute: int | None = None
    max_concurrent: int | None = None
    warmup_stage: str | None = None
    paused_until: datetime | None = None
    metadata_json: JsonObject | None = None


class DomainComplianceHoldRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)
    abuse_type: str = Field(default='manual_review', min_length=1, max_length=100)
    operator: str | None = Field(default=None, max_length=200)
    paused_hours: int = Field(default=24, ge=1, le=24 * 30)


class DomainComplianceReleaseRequest(BaseModel):
    reason: str = Field(default='review_cleared', min_length=1, max_length=500)
    operator: str | None = Field(default=None, max_length=200)


class DomainAuthenticationPlanRequest(BaseModel):
    dkim_selector: str = 'ee1'
    bounce_subdomain: str = 'bounces'
    mta_hostname: str | None = None
    dkim_public_key: str | None = None
    dmarc_policy: str = 'none'


class DomainAuthenticationDnsRecord(BaseModel):
    record_type: str
    name: str
    value: str
    purpose: str
    required: bool = True


class DomainAuthenticationPlanRead(BaseModel):
    domain: str
    dkim_selector: str
    bounce_domain: str
    mta_hostname: str | None = None
    dmarc_policy: str
    dns_records: list[DomainAuthenticationDnsRecord]
    next_steps: list[str]


class DomainDkimKeyCreateRequest(BaseModel):
    dkim_selector: str = 'ee1'
    key_ref: str | None = None
    key_size: int = 2048


class DomainDkimKeyCreateRead(BaseModel):
    domain: str
    dkim_selector: str
    key_ref: str
    public_key: str
    private_key_pem: str
    dns_record: DomainAuthenticationDnsRecord


class DomainBlocklistScanRequest(BaseModel):
    zones: list[str] = Field(
        default_factory=lambda: [
            'zen.spamhaus.org',
            'bl.spamcop.net',
            'b.barracudacentral.org',
        ]
    )
    ip_addresses: list[str] | None = None
    update_metadata: bool = True


class DomainBlocklistScanRecord(BaseModel):
    ip_address: str
    zone: str
    query: str
    observed_values: list[str] = Field(default_factory=list)
    status: str
    message: str


class DomainBlocklistScanRead(BaseModel):
    domain: str
    checked_at: str
    ip_addresses: list[str] = Field(default_factory=list)
    status: str
    hits: list[str] = Field(default_factory=list)
    records: list[DomainBlocklistScanRecord] = Field(default_factory=list)


class DomainWarmupProgressionRequest(BaseModel):
    advance: bool = True
    next_stage: str | None = None
    next_daily_limit: int | None = Field(default=None, ge=1)
    max_bounce_rate: float = Field(default=0.02, ge=0, le=1)
    max_complaint_rate: float = Field(default=0.001, ge=0, le=1)
    min_sent_count: int = Field(default=25, ge=0)
    operator: str | None = Field(default=None, max_length=200)


class DomainWarmupProgressionRead(BaseModel):
    domain: str
    previous_stage: str | None = None
    current_stage: str | None = None
    previous_daily_limit: int | None = None
    current_daily_limit: int | None = None
    previous_stage_order: int | None = None
    current_stage_order: int | None = None
    action: str
    status: str
    reason: str
    evaluated_at: str
    sent_count: int = 0
    bounce_rate: float = 0.0
    complaint_rate: float = 0.0


class ManagedSmtpMaintenanceRequest(BaseModel):
    scan_blocklists: bool = True
    progress_warmup: bool = True
    advance_warmup: bool = True
    include_all_route_types: bool = False
    zones: list[str] = Field(
        default_factory=lambda: [
            'zen.spamhaus.org',
            'bl.spamcop.net',
            'b.barracudacentral.org',
        ]
    )
    max_bounce_rate: float = Field(default=0.02, ge=0, le=1)
    max_complaint_rate: float = Field(default=0.001, ge=0, le=1)
    min_sent_count: int = Field(default=25, ge=0)
    limit: int = Field(default=100, ge=1, le=1000)
    operator: str | None = Field(default='managed_smtp_maintenance', max_length=200)


class ManagedSmtpMaintenancePolicyRead(BaseModel):
    policy_id: UUID
    domain: str
    route_type: DeliveryRouteType | None = None
    skipped_reason: str | None = None
    blocklist_status: str | None = None
    blocklist_hits: list[str] = Field(default_factory=list)
    warmup_action: str | None = None
    warmup_status: str | None = None
    warmup_stage: str | None = None
    warmup_daily_limit: int | None = None


class ManagedSmtpMaintenanceRead(BaseModel):
    processed_count: int
    blocklist_scan_count: int
    warmup_progression_count: int
    skipped_count: int
    results: list[ManagedSmtpMaintenancePolicyRead] = Field(default_factory=list)


class DomainAuthenticationVerificationRecord(BaseModel):
    record_type: str
    name: str
    expected_value: str
    observed_values: list[str] = Field(default_factory=list)
    status: str
    message: str
    required: bool = True


class DomainAuthenticationVerificationRead(BaseModel):
    domain: str
    verified: bool
    records: list[DomainAuthenticationVerificationRecord]


class DomainDeliveryPolicyRead(DomainDeliveryPolicyCreate):
    id: UUID

    model_config = {'from_attributes': True}


class MtaProviderAccountCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    provider: MtaProviderType
    account_ref: str | None = Field(default=None, max_length=255)
    region: str | None = Field(default=None, max_length=100)
    abuse_contact_email: str | None = Field(default=None, max_length=320)
    support_case_ref: str | None = Field(default=None, max_length=255)
    port25_status: str = Field(default='unknown', max_length=40)
    rdns_status: str = Field(default='unknown', max_length=40)
    secret_ref: str | None = Field(default=None, max_length=255)
    metadata_json: JsonObject = Field(default_factory=dict)


class MtaProviderAccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    provider: MtaProviderType | None = None
    status: MtaOperationalStatus | None = None
    account_ref: str | None = Field(default=None, max_length=255)
    region: str | None = Field(default=None, max_length=100)
    abuse_contact_email: str | None = Field(default=None, max_length=320)
    support_case_ref: str | None = Field(default=None, max_length=255)
    port25_status: str | None = Field(default=None, max_length=40)
    rdns_status: str | None = Field(default=None, max_length=40)
    secret_ref: str | None = Field(default=None, max_length=255)
    metadata_json: JsonObject | None = None


class MtaProviderAccountRead(MtaProviderAccountCreate):
    id: UUID
    status: MtaOperationalStatus
    created_at: datetime
    updated_at: datetime

    model_config = {'from_attributes': True}


class MtaNodeCreate(BaseModel):
    provider_account_id: UUID
    name: str = Field(..., min_length=1, max_length=200)
    hostname: str = Field(..., min_length=1, max_length=255)
    public_ipv4: str | None = Field(default=None, max_length=64)
    submission_host: str | None = Field(default=None, max_length=255)
    submission_port: int = Field(default=587, ge=1, le=65535)
    auth_secret_ref: str | None = Field(default=None, max_length=255)
    metadata_json: JsonObject = Field(default_factory=dict)


class MtaNodeUpdate(BaseModel):
    provider_account_id: UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=200)
    hostname: str | None = Field(default=None, min_length=1, max_length=255)
    public_ipv4: str | None = Field(default=None, max_length=64)
    status: MtaOperationalStatus | None = None
    submission_host: str | None = Field(default=None, max_length=255)
    submission_port: int | None = Field(default=None, ge=1, le=65535)
    auth_secret_ref: str | None = Field(default=None, max_length=255)
    last_readiness_at: datetime | None = None
    metadata_json: JsonObject | None = None


class MtaNodeStatusActionRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)
    operator: str | None = Field(default=None, max_length=200)


class MtaNodeRead(MtaNodeCreate):
    id: UUID
    status: MtaOperationalStatus
    last_readiness_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {'from_attributes': True}


class MtaIpPoolCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    pool_type: MtaIpPoolType
    description: str | None = None
    metadata_json: JsonObject = Field(default_factory=dict)


class MtaIpPoolUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    pool_type: MtaIpPoolType | None = None
    status: MtaOperationalStatus | None = None
    description: str | None = None
    metadata_json: JsonObject | None = None


class MtaIpPoolRead(MtaIpPoolCreate):
    id: UUID
    status: MtaOperationalStatus
    created_at: datetime
    updated_at: datetime

    model_config = {'from_attributes': True}


class MtaIpPoolNodeCreate(BaseModel):
    ip_pool_id: UUID
    mta_node_id: UUID
    priority: int = Field(default=100, ge=0)
    weight: int = Field(default=100, ge=0)
    metadata_json: JsonObject = Field(default_factory=dict)


class MtaIpPoolNodeUpdate(BaseModel):
    priority: int | None = Field(default=None, ge=0)
    weight: int | None = Field(default=None, ge=0)
    status: MtaOperationalStatus | None = None
    metadata_json: JsonObject | None = None


class MtaIpPoolNodeRead(MtaIpPoolNodeCreate):
    id: UUID
    status: MtaOperationalStatus
    created_at: datetime
    updated_at: datetime

    model_config = {'from_attributes': True}


class ManagedSmtpRouteResolveRequest(BaseModel):
    from_domain: str | None = Field(default=None, max_length=255)
    recipient_domain: str | None = Field(default=None, max_length=255)
    send_type: str = Field(default='internal_test', max_length=100)
    route_id: UUID | None = None
    ip_pool_id: UUID | None = None


class ManagedSmtpRouteBlockReason(BaseModel):
    code: str
    message: str
    details: JsonObject = Field(default_factory=dict)


class ManagedSmtpResolvedRoute(BaseModel):
    domain: str
    delivery_route_id: UUID
    delivery_route_name: str
    domain_policy_id: UUID
    ip_pool_id: UUID
    ip_pool_name: str
    ip_pool_type: MtaIpPoolType
    mta_node_id: UUID
    mta_node_name: str
    provider_account_id: UUID
    provider: MtaProviderType
    hostname: str
    public_ipv4: str | None = None
    submission_host: str
    submission_port: int
    auth_secret_ref: str | None = None
    envelope_sender_domain: str | None = None
    dkim_selector: str | None = None
    telemetry_tags: JsonObject = Field(default_factory=dict)


class ManagedSmtpRouteResolutionRead(BaseModel):
    ok: bool
    route: ManagedSmtpResolvedRoute | None = None
    reason: ManagedSmtpRouteBlockReason | None = None


class ManagedSmtpBootstrapRequest(BaseModel):
    provider_account_name: str = Field(..., min_length=1, max_length=200)
    provider: MtaProviderType
    provider_account_ref: str | None = Field(default=None, max_length=255)
    region: str | None = Field(default=None, max_length=100)
    abuse_contact_email: str | None = Field(default=None, max_length=320)
    support_case_ref: str | None = Field(default=None, max_length=255)
    port25_status: str = Field(default='unknown', max_length=40)
    rdns_status: str = Field(default='unknown', max_length=40)
    provider_secret_ref: str | None = Field(default=None, max_length=255)
    node_name: str = Field(..., min_length=1, max_length=200)
    hostname: str = Field(..., min_length=1, max_length=255)
    public_ipv4: str | None = Field(default=None, max_length=64)
    submission_host: str | None = Field(default=None, max_length=255)
    submission_port: int = Field(default=587, ge=1, le=65535)
    auth_secret_ref: str | None = Field(default=None, max_length=255)
    ip_pool_name: str = Field(..., min_length=1, max_length=200)
    ip_pool_type: MtaIpPoolType = MtaIpPoolType.internal_test
    route_name: str = Field(default='managed-smtp-primary', min_length=1, max_length=200)
    domain: str = Field(..., min_length=1, max_length=255)
    bounce_domain: str | None = Field(default=None, max_length=255)
    dkim_selector: str | None = Field(default=None, max_length=100)
    dkim_key_ref: str | None = Field(default=None, max_length=255)
    warmup_stage: str | None = Field(default='stage_1', max_length=100)
    max_per_minute: int | None = Field(default=25, ge=1)
    max_concurrent: int | None = Field(default=2, ge=1)
    activate_inventory: bool = False
    mark_domain_verified: bool = False
    metadata_json: JsonObject = Field(default_factory=dict)


class ManagedSmtpBootstrapProfileRead(BaseModel):
    name: str
    provider: MtaProviderType
    provider_account_name: str
    node_name: str
    hostname: str
    public_ipv4: str | None = None
    route_name: str
    ip_pool_name: str
    domain: str
    bounce_domain: str | None = None
    dkim_selector: str | None = None
    port25_status: str
    rdns_status: str
    activate_inventory: bool
    mark_domain_verified: bool
    metadata_json: JsonObject = Field(default_factory=dict)


class ManagedSmtpBootstrapRead(BaseModel):
    provider_account: MtaProviderAccountRead
    node: MtaNodeRead
    ip_pool: MtaIpPoolRead
    pool_node: MtaIpPoolNodeRead
    delivery_route: DeliveryRouteRead
    domain_policy: DomainDeliveryPolicyRead
    route_resolution: ManagedSmtpRouteResolutionRead
    next_steps: list[str] = Field(default_factory=list)


class DeliveryRunRead(BaseModel):
    claimed_count: int
    sent_count: int
    failed_count: int
    processed_record_ids: list[str]
    skipped_count: int = 0
    skipped_record_ids: list[str] = Field(default_factory=list)


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


class CampaignTimelinePointRead(BaseModel):
    date: date
    requested_count: int = 0
    queued_count: int = 0
    sent_count: int = 0
    failed_count: int = 0
    suppressed_count: int = 0
    delivered_count: int = 0
    opened_count: int = 0
    clicked_count: int = 0
    bounced_count: int = 0
    complained_count: int = 0
    unsubscribed_count: int = 0
    open_rate: float = 0
    click_rate: float = 0
    bounce_rate: float = 0


class CampaignTimelineRead(BaseModel):
    campaign_id: UUID
    send_job_id: UUID | None = None
    days: int
    points: list[CampaignTimelinePointRead]


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


class SuppressionCreate(BaseModel):
    email: EmailStr
    reason: SuppressionReason = SuppressionReason.manual
    source: str = 'manual_admin'
    provider_message_id: str | None = None
    metadata_json: JsonObject = Field(default_factory=dict)
    contact_id: UUID | None = None


class SendGridWebhookEvent(BaseModel):
    email: EmailStr
    event: str
    sg_message_id: str | None = None
    smtp_id: str | None = None
    reason: str | None = None
    url: str | None = None
    timestamp: int | None = None

    model_config = {'extra': 'allow'}


class ManagedSmtpFeedbackEvent(BaseModel):
    email: EmailStr
    event: str
    provider_message_id: str | None = None
    smtp_response_code: int | None = None
    smtp_response: str | None = None
    diagnostic_code: str | None = None
    source: str = 'managed_smtp_feedback'
    timestamp: int | None = None
    metadata_json: JsonObject = Field(default_factory=dict)

    model_config = {'extra': 'allow'}


class ProviderWebhookIngestRead(BaseModel):
    processed_count: int
    suppressed_count: int
    updated_send_records: int
    duplicate_count: int = 0


class ProviderFeedbackEventRead(BaseModel):
    id: UUID
    provider: str
    source: str
    event_name: str
    email: EmailStr
    provider_message_id: str | None = None
    idempotency_key: str
    payload_json: JsonObject
    metadata_json: JsonObject
    received_at: datetime

    model_config = {'from_attributes': True}


class ManagedSmtpReadinessCheckCreate(BaseModel):
    source: str = 'managed_smtp_mta_smoke'
    check_type: str = 'mta_smoke'
    status: str
    domain: str | None = None
    host: str | None = None
    summary: str | None = None
    result_json: JsonObject = Field(default_factory=dict)


class ManagedSmtpReadinessCheckRead(ManagedSmtpReadinessCheckCreate):
    id: UUID
    created_at: datetime

    model_config = {'from_attributes': True}


class ManagedSmtpReadinessSummaryRead(BaseModel):
    total_count: int
    ok_count: int
    warning_count: int
    failed_count: int
    latest_check: ManagedSmtpReadinessCheckRead | None = None
    latest_success: ManagedSmtpReadinessCheckRead | None = None


class ManagedSmtpReadinessTrendRead(BaseModel):
    sample_size: int
    ok_count: int
    warning_count: int
    failed_count: int
    ok_rate: float
    failure_rate: float
    trend: str
    alert_status: str
    alert_reasons: list[str] = Field(default_factory=list)
    latest_window_failure_rate: float
    previous_window_failure_rate: float
    recent_checks: list[ManagedSmtpReadinessCheckRead] = Field(default_factory=list)


class ManagedSmtpReadinessAlertsRead(BaseModel):
    alert_status: str
    alert_reasons: list[str] = Field(default_factory=list)
    alert_count: int
    trend: ManagedSmtpReadinessTrendRead
    alert_checks: list[ManagedSmtpReadinessCheckRead] = Field(default_factory=list)


class ManagedSmtpReadinessNotificationRead(BaseModel):
    should_notify: bool
    severity: str
    title: str
    message: str
    dedupe_key: str
    alert_status: str
    alert_reasons: list[str] = Field(default_factory=list)
    alert_count: int
    latest_alert_check: ManagedSmtpReadinessCheckRead | None = None
    alerts: ManagedSmtpReadinessAlertsRead


class MtaInventoryCounts(BaseModel):
    total: int
    pending: int = 0
    active: int = 0
    paused: int = 0
    draining: int = 0
    failed: int = 0
    retired: int = 0
    suspended: int = 0


class ManagedSmtpDeploymentNodeSummary(BaseModel):
    node: MtaNodeRead
    provider_account: MtaProviderAccountRead | None = None
    pool_memberships: list[MtaIpPoolNodeRead] = Field(default_factory=list)
    readiness_summary: ManagedSmtpReadinessSummaryRead
    agent_heartbeat_status: str = 'missing'
    agent_last_heartbeat_at: datetime | None = None
    agent_heartbeat_age_seconds: int | None = None
    agent_heartbeat_stale_after_seconds: int = 180
    agent_queue_depth: int | None = None
    agent_deferred_count: int | None = None
    agent_active_count: int | None = None
    platform_config_version: str | None = None
    agent_config_version: str | None = None
    agent_applied_config_version: str | None = None
    agent_config_in_sync: bool = False
    agent_service_active_state: str | None = None
    agent_service_sub_state: str | None = None
    agent_timer_active_state: str | None = None
    agent_timer_sub_state: str | None = None
    agent_timer_next_elapse: str | None = None


class ManagedSmtpFleetHealthRead(BaseModel):
    status: str
    summary: str
    provider_count: int
    active_provider_count: int
    blocked_provider_count: int
    total_nodes: int
    active_nodes: int
    route_ready_nodes: int
    readiness_ok_nodes: int
    stale_agent_nodes: int
    missing_agent_nodes: int
    config_drift_nodes: int
    queue_depth: int
    deferred_count: int
    active_queue_count: int


class ManagedSmtpDeploymentSummaryRead(BaseModel):
    provider_accounts: MtaInventoryCounts
    nodes: MtaInventoryCounts
    ip_pools: MtaInventoryCounts
    pool_nodes: MtaInventoryCounts
    submission_credentials_configured: bool = False
    submission_tls_enabled: bool = True
    managed_smtp_route_count: int
    managed_smtp_domain_policy_count: int
    fleet_health: ManagedSmtpFleetHealthRead
    recent_nodes: list[ManagedSmtpDeploymentNodeSummary] = Field(default_factory=list)


class MtaNodeRuntimeDomainConfig(BaseModel):
    domain: str
    route_id: UUID | None = None
    ip_pool_id: UUID | None = None
    bounce_domain: str | None = None
    dkim_selector: str | None = None
    dkim_key_ref: str | None = None
    warmup_stage: str | None = None
    max_per_minute: int | None = None
    max_concurrent: int | None = None
    verified: bool = False


class MtaNodeRuntimePoolConfig(BaseModel):
    ip_pool_id: UUID
    name: str
    pool_type: MtaIpPoolType
    status: MtaOperationalStatus
    membership_id: UUID
    membership_status: MtaOperationalStatus
    priority: int
    weight: int


class MtaNodeRuntimeConfigRead(BaseModel):
    node: MtaNodeRead
    provider_account: MtaProviderAccountRead
    config_version: str
    submission_host: str
    submission_port: int
    auth_secret_ref: str | None = None
    pools: list[MtaNodeRuntimePoolConfig] = Field(default_factory=list)
    domains: list[MtaNodeRuntimeDomainConfig] = Field(default_factory=list)
    status: MtaOperationalStatus
    generated_at: datetime


class MtaNodeHeartbeatRequest(BaseModel):
    status: str = Field(default='ok', max_length=40)
    summary: str | None = Field(default=None, max_length=500)
    queue_depth: int | None = Field(default=None, ge=0)
    deferred_count: int | None = Field(default=None, ge=0)
    active_count: int | None = Field(default=None, ge=0)
    config_version: str | None = Field(default=None, max_length=128)
    applied_config_version: str | None = Field(default=None, max_length=128)
    payload_json: JsonObject = Field(default_factory=dict)


class MtaNodeEventCreate(BaseModel):
    event_type: str = Field(..., min_length=1, max_length=100)
    severity: str = Field(default='info', max_length=40)
    summary: str | None = Field(default=None, max_length=500)
    payload_json: JsonObject = Field(default_factory=dict)
    observed_at: datetime | None = None


class MtaNodeEventRead(MtaNodeEventCreate):
    id: UUID
    mta_node_id: UUID
    received_at: datetime

    model_config = {'from_attributes': True}


class ManagedSmtpFirstSendChecklistItem(BaseModel):
    key: str
    label: str
    status: str
    value: str
    detail: str
    blocking: bool = True


class ManagedSmtpFirstSendRead(BaseModel):
    ok: bool
    status: str
    blockers: list[str] = Field(default_factory=list)
    items: list[ManagedSmtpFirstSendChecklistItem] = Field(default_factory=list)
    deployment_summary: ManagedSmtpDeploymentSummaryRead


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


class DataSourceValidationRead(BaseModel):
    data_source_id: UUID
    source_type: DataSourceType
    ok: bool
    checks: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class DataSourceSchemaFieldRead(BaseModel):
    name: str
    field_type: str = 'unknown'
    sample_values: list[object] = Field(default_factory=list)


class DataSourceSchemaRead(BaseModel):
    data_source_id: UUID
    source_type: DataSourceType
    object_types: list[str] = Field(default_factory=list)
    fields: list[DataSourceSchemaFieldRead] = Field(default_factory=list)
    sample_rows: list[JsonObject] = Field(default_factory=list)


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


class DataSourceIngestRequest(BaseModel):
    mapping_id: UUID
    rows: list[JsonObject]
    dry_run: bool = False
    metadata_json: JsonObject = Field(default_factory=dict)


class DataSourceImportJobRead(BaseModel):
    id: UUID
    data_source_id: UUID
    mapping_id: UUID
    status: DataSourceImportStatus
    object_type: str
    received_count: int
    imported_count: int
    created_count: int
    updated_count: int
    skipped_count: int
    errors: list[object]
    metadata_json: JsonObject
    created_at: datetime

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


class AudienceSnapshotCreate(BaseModel):
    metadata_json: JsonObject = Field(default_factory=dict)


class AudienceSnapshotRead(BaseModel):
    id: UUID
    audience_id: UUID
    version_number: int
    name: str
    description: str | None = None
    rule_tree: JsonObject
    estimated_count: int
    contact_ids: list[str]
    metadata_json: JsonObject
    created_at: datetime

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
    subject: str | None = None
    html_body: str | None = None
    text_body: str | None = None
    variables: JsonObject | None = None


class EmailSendResponse(SendResponse):
    contact_id: UUID
    template_id: UUID
    campaign_id: UUID | None = None


class CampaignTestSendResponse(SendResponse):
    campaign_id: UUID
    template_id: UUID
    send_job_id: UUID
    send_record_id: UUID
    contact_id: UUID
    to_email: EmailStr
    subject: str
    html_body: str
    text_body: str | None = None
    variables: JsonObject = Field(default_factory=dict)
    tracking_open_url: str | None = None
    tracking_click_base: str | None = None
    unsubscribe_url: str | None = None


class CampaignTestPreviewRead(BaseModel):
    campaign_id: UUID
    template_id: UUID
    subject: str
    html_body: str
    text_body: str | None = None
    variables: JsonObject = Field(default_factory=dict)


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
    occurred_at: datetime

    model_config = {'from_attributes': True}


class AnalyticsOverviewRead(BaseModel):
    campaign_count: int
    contact_count: int
    send_job_count: int
    send_record_count: int
    event_count: int
    status_counts: list[MetricCount]
    event_counts: list[MetricCount]
    recent_events: list[EventRead]


class CampaignPerformanceRead(BaseModel):
    campaign_id: UUID
    name: str
    status: CampaignStatus
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


class CampaignListSummaryRead(BaseModel):
    campaign: CampaignPerformanceRead
    latest_send_job: CampaignSendJobRead | None = None
    progress: CampaignSendJobProgressRead | None = None


class AudiencePerformanceRead(BaseModel):
    audience_id: UUID
    name: str
    status: AudienceStatus
    estimated_count: int
    send_job_count: int
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


class DomainDeliverabilityRead(BaseModel):
    domain: str
    provider: str | None = None
    send_record_count: int
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


class DomainReputationDashboardRead(BaseModel):
    domain: str
    route_id: UUID | None = None
    route_name: str | None = None
    route_type: DeliveryRouteType | None = None
    warmup_stage: str | None = None
    warmup_status: str
    warmup_daily_limit: int | None = None
    warmup_stage_order: int | None = None
    ip_pool: str | None = None
    ip_addresses: list[str] = Field(default_factory=list)
    blocklist_status: str
    blocklist_hits: list[str] = Field(default_factory=list)
    blocklist_checked_at: str | None = None
    max_per_minute: int | None = None
    max_concurrent: int | None = None
    paused_until: datetime | None = None
    authentication_verified: bool = False
    authentication_status: str
    reputation_status: str
    throttle_status: str
    compliance_status: str = 'clear'
    compliance_reason: str | None = None
    send_record_count: int = 0
    sent_count: int = 0
    delivered_count: int = 0
    bounced_count: int = 0
    complained_count: int = 0
    bounce_rate: float = 0.0
    complaint_rate: float = 0.0
    recommendations: list[str] = Field(default_factory=list)


class JourneyStepPerformanceRead(BaseModel):
    step_id: UUID
    name: str
    step_type: JourneyStepType
    position: int
    execution_count: int
    completed_count: int
    failed_count: int
    skipped_count: int
    queued_send_count: int


class JourneyPerformanceRead(BaseModel):
    journey_id: UUID
    name: str
    status: JourneyStatus
    enrollment_count: int
    active_count: int
    completed_count: int
    exited_count: int
    paused_count: int
    failed_count: int
    execution_count: int
    step_completed_count: int
    step_failed_count: int
    step_skipped_count: int
    queued_send_count: int
    steps: list[JourneyStepPerformanceRead]


class UnsubscribeTokenRead(BaseModel):
    contact_id: UUID
    token: str


class UnsubscribeRead(BaseModel):
    status: str
    contact_id: UUID


class CampaignWorkflowStatusRead(BaseModel):
    campaign: CampaignRead
    template: TemplateRead | None = None
    template_variables: TemplateVariablesRead | None = None
    validation: CampaignValidationRead
    audience_preview: AudiencePreviewRead | None = None
    analytics: CampaignAnalyticsRead | None = None
    latest_send_job: CampaignSendJobRead | None = None
    latest_send_record: EmailSendRecordRead | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=200)


class AuthUserRead(BaseModel):
    id: UUID
    email: str
    display_name: str
    role: str

    model_config = {'from_attributes': True}


class LoginResponse(BaseModel):
    user: AuthUserRead


class MeResponse(BaseModel):
    user: AuthUserRead


class OperatorUserRead(BaseModel):
    id: UUID
    email: str
    display_name: str
    role: str
    is_active: bool
    last_login_at: datetime | None = None
    failed_login_count: int
    locked_until: datetime | None = None
    created_at: datetime

    model_config = {'from_attributes': True}


class OperatorUserCreate(BaseModel):
    email: EmailStr
    display_name: str = Field(..., min_length=1, max_length=200)
    role: str = Field(default='admin', min_length=1, max_length=40)
    password: str = Field(..., min_length=8, max_length=200)
    is_active: bool = True


class OperatorUserUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    role: str | None = Field(default=None, min_length=1, max_length=40)
    is_active: bool | None = None


class OperatorUserPasswordUpdate(BaseModel):
    password: str = Field(..., min_length=8, max_length=200)
