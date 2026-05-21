from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from email_platform.models.entities import EmailEvent
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

    def list(self, limit: int = 100, offset: int = 0) -> list[EmailEvent]:
        statement = (
            select(EmailEvent).order_by(EmailEvent.occurred_at.desc()).limit(limit).offset(offset)
        )
        return list(self.db.scalars(statement).all())

    def get(self, event_id: UUID) -> EmailEvent | None:
        return self.db.get(EmailEvent, event_id)
