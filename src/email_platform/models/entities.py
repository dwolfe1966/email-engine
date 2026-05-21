from datetime import datetime
from enum import StrEnum
from uuid import UUID as PyUUID
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from email_platform.db.session import Base


class CampaignStatus(StrEnum):
    draft = 'draft'
    scheduled = 'scheduled'
    sending = 'sending'
    sent = 'sent'
    paused = 'paused'


class EmailEventType(StrEnum):
    queued = 'queued'
    sent = 'sent'
    delivered = 'delivered'
    opened = 'opened'
    clicked = 'clicked'
    bounced = 'bounced'
    complained = 'complained'
    unsubscribed = 'unsubscribed'


class DataSourceType(StrEnum):
    postgres = 'postgres'
    mysql = 'mysql'
    snowflake = 'snowflake'
    bigquery = 'bigquery'
    rest_api = 'rest_api'
    csv = 'csv'
    manual = 'manual'


class DataSourceStatus(StrEnum):
    draft = 'draft'
    active = 'active'
    paused = 'paused'


class AudienceStatus(StrEnum):
    draft = 'draft'
    active = 'active'
    archived = 'archived'


class SendJobStatus(StrEnum):
    queued = 'queued'
    processing = 'processing'
    completed = 'completed'
    failed = 'failed'


class EmailSendStatus(StrEnum):
    queued = 'queued'
    sending = 'sending'
    sent = 'sent'
    failed = 'failed'
    suppressed = 'suppressed'
    skipped = 'skipped'


class SuppressionReason(StrEnum):
    hard_bounce = 'hard_bounce'
    spam_complaint = 'spam_complaint'
    unsubscribe = 'unsubscribe'
    manual = 'manual'


class Contact(Base):
    __tablename__ = 'contacts'
    __table_args__ = (UniqueConstraint('email', name='uq_contacts_email'),)

    id: Mapped[PyUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), index=True)
    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))
    source: Mapped[str | None] = mapped_column(String(100))
    attributes: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    is_unsubscribed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=func.now()
    )


class EmailTemplate(Base):
    __tablename__ = 'email_templates'

    id: Mapped[PyUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    subject: Mapped[str] = mapped_column(String(300))
    html_body: Mapped[str] = mapped_column(Text)
    css_body: Mapped[str | None] = mapped_column(Text)
    text_body: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DataSource(Base):
    __tablename__ = 'data_sources'

    id: Mapped[PyUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    source_type: Mapped[DataSourceType] = mapped_column(Enum(DataSourceType), index=True)
    status: Mapped[DataSourceStatus] = mapped_column(
        Enum(DataSourceStatus), default=DataSourceStatus.draft
    )
    config: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    secret_ref: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=func.now()
    )


class DataSourceMapping(Base):
    __tablename__ = 'data_source_mappings'

    id: Mapped[PyUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    data_source_id: Mapped[PyUUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey('data_sources.id')
    )
    name: Mapped[str] = mapped_column(String(200), index=True)
    object_type: Mapped[str] = mapped_column(String(100), index=True)
    mapping: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    extraction_plan: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    data_source: Mapped[DataSource] = relationship()


class Audience(Base):
    __tablename__ = 'audiences'

    id: Mapped[PyUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[AudienceStatus] = mapped_column(
        Enum(AudienceStatus), default=AudienceStatus.draft
    )
    rule_tree: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    estimated_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=func.now()
    )


class Campaign(Base):
    __tablename__ = 'campaigns'

    id: Mapped[PyUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), index=True)
    status: Mapped[CampaignStatus] = mapped_column(
        Enum(CampaignStatus),
        default=CampaignStatus.draft,
    )
    template_id: Mapped[PyUUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey('email_templates.id')
    )
    audience_query: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    template: Mapped[EmailTemplate] = relationship()


class CampaignSendJob(Base):
    __tablename__ = 'campaign_send_jobs'

    id: Mapped[PyUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    campaign_id: Mapped[PyUUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey('campaigns.id'))
    status: Mapped[SendJobStatus] = mapped_column(Enum(SendJobStatus), default=SendJobStatus.queued)
    audience_rule_tree: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    requested_count: Mapped[int] = mapped_column(Integer, default=0)
    queued_count: Mapped[int] = mapped_column(Integer, default=0)
    suppressed_count: Mapped[int] = mapped_column(Integer, default=0)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=func.now()
    )

    campaign: Mapped[Campaign] = relationship()


class EmailSendRecord(Base):
    __tablename__ = 'email_send_records'

    id: Mapped[PyUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    campaign_id: Mapped[PyUUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey('campaigns.id'))
    send_job_id: Mapped[PyUUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey('campaign_send_jobs.id')
    )
    contact_id: Mapped[PyUUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey('contacts.id'))
    template_id: Mapped[PyUUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey('email_templates.id')
    )
    status: Mapped[EmailSendStatus] = mapped_column(
        Enum(EmailSendStatus), default=EmailSendStatus.queued, index=True
    )
    to_email: Mapped[str] = mapped_column(String(320), index=True)
    variables: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    provider: Mapped[str | None] = mapped_column(String(100))
    provider_message_id: Mapped[str | None] = mapped_column(String(255), index=True)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=func.now()
    )

    campaign: Mapped[Campaign] = relationship()
    contact: Mapped[Contact] = relationship()
    send_job: Mapped[CampaignSendJob] = relationship()
    template: Mapped[EmailTemplate] = relationship()


class Suppression(Base):
    __tablename__ = 'suppressions'
    __table_args__ = (UniqueConstraint('email', 'reason', name='uq_suppressions_email_reason'),)

    id: Mapped[PyUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), index=True)
    contact_id: Mapped[PyUUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey('contacts.id')
    )
    reason: Mapped[SuppressionReason] = mapped_column(Enum(SuppressionReason), index=True)
    source: Mapped[str] = mapped_column(String(100), default='system')
    provider_message_id: Mapped[str | None] = mapped_column(String(255), index=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    contact: Mapped[Contact | None] = relationship()


class EmailEvent(Base):
    __tablename__ = 'email_events'

    id: Mapped[PyUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    send_record_id: Mapped[PyUUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey('email_send_records.id'), index=True
    )
    send_job_id: Mapped[PyUUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey('campaign_send_jobs.id'), index=True
    )
    contact_id: Mapped[PyUUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey('contacts.id')
    )
    campaign_id: Mapped[PyUUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey('campaigns.id')
    )
    event_type: Mapped[EmailEventType] = mapped_column(Enum(EmailEventType), index=True)
    provider_message_id: Mapped[str | None] = mapped_column(String(255), index=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    send_record: Mapped[EmailSendRecord | None] = relationship()
    send_job: Mapped[CampaignSendJob | None] = relationship()
