from sqlalchemy import select
from sqlalchemy.orm import Session

from email_platform.models.entities import Contact
from email_platform.schemas.contracts import ContactUpsert


class ContactService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def upsert(self, payload: ContactUpsert) -> Contact:
        existing = self.db.scalar(select(Contact).where(Contact.email == str(payload.email)))
        if existing:
            for key, value in payload.model_dump().items():
                setattr(existing, key, value)
            contact = existing
        else:
            contact = Contact(**payload.model_dump())
            self.db.add(contact)
        self.db.commit()
        self.db.refresh(contact)
        return contact
