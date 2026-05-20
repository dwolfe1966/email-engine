from sqlalchemy.orm import Session

from email_platform.models.entities import EmailEvent
from email_platform.schemas.contracts import EventCreate


class EventService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def record(self, payload: EventCreate) -> EmailEvent:
        event = EmailEvent(**payload.model_dump())
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event
