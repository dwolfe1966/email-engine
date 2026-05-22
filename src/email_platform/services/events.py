from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from email_platform.models.entities import EmailEvent, EmailEventType
from email_platform.schemas.contracts import EventCreate


class EventService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def record(self, payload: EventCreate) -> EmailEvent:
        event = self.record_no_commit(payload)
        self.db.commit()
        self.db.refresh(event)
        return event

    def record_no_commit(self, payload: EventCreate) -> EmailEvent:
        event = EmailEvent(**payload.model_dump())
        self.db.add(event)
        return event

    def list(
        self,
        limit: int = 100,
        offset: int = 0,
        *,
        campaign_id: UUID | None = None,
        send_job_id: UUID | None = None,
        send_record_id: UUID | None = None,
        contact_id: UUID | None = None,
        event_type: EmailEventType | None = None,
    ) -> list[EmailEvent]:
        statement = (
            self._filtered_statement(
                campaign_id=campaign_id,
                send_job_id=send_job_id,
                send_record_id=send_record_id,
                contact_id=contact_id,
                event_type=event_type,
            )
            .order_by(EmailEvent.occurred_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.scalars(statement).all())

    def count(
        self,
        *,
        campaign_id: UUID | None = None,
        send_job_id: UUID | None = None,
        send_record_id: UUID | None = None,
        contact_id: UUID | None = None,
        event_type: EmailEventType | None = None,
    ) -> int:
        statement = select(func.count()).select_from(
            self._filtered_statement(
                campaign_id=campaign_id,
                send_job_id=send_job_id,
                send_record_id=send_record_id,
                contact_id=contact_id,
                event_type=event_type,
            ).subquery()
        )
        return self.db.scalar(statement) or 0

    def get(self, event_id: UUID) -> EmailEvent | None:
        return self.db.get(EmailEvent, event_id)

    def _filtered_statement(
        self,
        *,
        campaign_id: UUID | None = None,
        send_job_id: UUID | None = None,
        send_record_id: UUID | None = None,
        contact_id: UUID | None = None,
        event_type: EmailEventType | None = None,
    ) -> Select[tuple[EmailEvent]]:
        statement = select(EmailEvent)
        if campaign_id:
            statement = statement.where(EmailEvent.campaign_id == campaign_id)
        if send_job_id:
            statement = statement.where(EmailEvent.send_job_id == send_job_id)
        if send_record_id:
            statement = statement.where(EmailEvent.send_record_id == send_record_id)
        if contact_id:
            statement = statement.where(EmailEvent.contact_id == contact_id)
        if event_type:
            statement = statement.where(EmailEvent.event_type == event_type)
        return statement
