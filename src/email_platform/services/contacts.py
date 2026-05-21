import hmac
from hashlib import sha256
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from email_platform.core.settings import Settings
from email_platform.models.entities import Contact
from email_platform.schemas.contracts import ContactUpdate, ContactUpsert


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

    def list(self, limit: int = 100, offset: int = 0) -> list[Contact]:
        statement = select(Contact).order_by(Contact.created_at.desc()).limit(limit).offset(offset)
        return list(self.db.scalars(statement).all())

    def count(self) -> int:
        return self.db.scalar(select(func.count()).select_from(Contact)) or 0

    def get(self, contact_id: UUID) -> Contact | None:
        return self.db.get(Contact, contact_id)

    def update(self, contact_id: UUID, payload: ContactUpdate) -> Contact | None:
        contact = self.get(contact_id)
        if not contact:
            return None
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(contact, key, value)
        self.db.commit()
        self.db.refresh(contact)
        return contact

    def delete(self, contact_id: UUID) -> bool:
        contact = self.get(contact_id)
        if not contact:
            return False
        self.db.delete(contact)
        self.db.commit()
        return True

    def unsubscribe(self, contact_id: UUID) -> Contact | None:
        contact = self.get(contact_id)
        if not contact:
            return None
        contact.is_unsubscribed = True
        self.db.commit()
        self.db.refresh(contact)
        return contact

    def build_unsubscribe_token(self, contact_id: UUID, settings: Settings) -> str:
        payload = contact_id.hex
        signature = hmac.new(
            settings.unsubscribe_secret.encode('utf-8'),
            payload.encode('utf-8'),
            sha256,
        ).hexdigest()
        return f'{payload}.{signature}'

    def verify_unsubscribe_token(self, token: str, settings: Settings) -> UUID | None:
        payload, separator, signature = token.partition('.')
        if not separator:
            return None
        expected = hmac.new(
            settings.unsubscribe_secret.encode('utf-8'),
            payload.encode('utf-8'),
            sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return None
        try:
            return UUID(hex=payload)
        except ValueError:
            return None
