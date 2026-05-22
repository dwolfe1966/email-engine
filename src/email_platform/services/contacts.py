import hmac
from hashlib import sha256
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from email_platform.core.settings import Settings
from email_platform.models.entities import (
    Contact,
    EmailEvent,
    EmailSendRecord,
    JourneyEnrollment,
    JourneyStepExecution,
    Suppression,
    SuppressionReason,
)
from email_platform.schemas.contracts import ContactUpdate, ContactUpsert
from email_platform.services.suppressions import SuppressionService


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

    def metadata(self, sample_limit: int = 25, scan_limit: int = 500) -> dict[str, object]:
        sources = self.db.execute(
            select(Contact.source, func.count())
            .where(Contact.source.is_not(None))
            .group_by(Contact.source)
            .order_by(Contact.source)
        ).all()
        scanned_contacts = self.list(limit=scan_limit, offset=0)
        sample_contacts = scanned_contacts[:sample_limit]
        attribute_keys = sorted(
            {
                key
                for contact in scanned_contacts
                for key in contact.attributes.keys()
            }
        )
        return {
            'total': self.count(),
            'scanned_count': len(scanned_contacts),
            'fields': ['email', 'first_name', 'last_name', 'source', 'is_unsubscribed'],
            'attribute_keys': attribute_keys,
            'sources': [{'source': source, 'count': count} for source, count in sources],
            'sample_contacts': [
                {
                    'id': contact.id,
                    'email': contact.email,
                    'first_name': contact.first_name,
                    'last_name': contact.last_name,
                    'source': contact.source,
                    'is_unsubscribed': contact.is_unsubscribed,
                    'attributes': contact.attributes,
                }
                for contact in sample_contacts
            ],
        }

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
        send_record_ids = list(
            self.db.scalars(
                select(EmailSendRecord.id).where(EmailSendRecord.contact_id == contact_id)
            ).all()
        )
        if send_record_ids:
            self.db.execute(
                delete(JourneyStepExecution).where(
                    JourneyStepExecution.send_record_id.in_(send_record_ids)
                )
            )
            self.db.execute(
                delete(EmailEvent).where(EmailEvent.send_record_id.in_(send_record_ids))
            )
            self.db.execute(delete(EmailSendRecord).where(EmailSendRecord.id.in_(send_record_ids)))

        self.db.execute(
            delete(JourneyStepExecution).where(JourneyStepExecution.contact_id == contact_id)
        )
        self.db.execute(delete(JourneyEnrollment).where(JourneyEnrollment.contact_id == contact_id))
        self.db.execute(delete(EmailEvent).where(EmailEvent.contact_id == contact_id))
        self.db.execute(delete(Suppression).where(Suppression.contact_id == contact_id))
        self.db.delete(contact)
        self.db.commit()
        return True

    def unsubscribe(self, contact_id: UUID) -> Contact | None:
        contact = self.get(contact_id)
        if not contact:
            return None
        contact.is_unsubscribed = True
        SuppressionService(self.db).create_or_update(
            email=contact.email,
            reason=SuppressionReason.unsubscribe,
            source='unsubscribe_endpoint',
            contact_id=contact.id,
        )
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
