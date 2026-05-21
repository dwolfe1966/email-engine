from datetime import datetime
from enum import StrEnum
from uuid import UUID as PyUUID
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, UniqueConstraint, func
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
    text_body: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


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


class EmailEvent(Base):
    __tablename__ = 'email_events'

    id: Mapped[PyUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
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
