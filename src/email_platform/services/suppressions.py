from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from email_platform.models.entities import Contact, Suppression, SuppressionReason


class SuppressionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def is_suppressed(self, email: str) -> bool:
        return (
            self.db.scalar(
                select(Suppression.id).where(Suppression.email == email.lower()).limit(1)
            )
            is not None
        )

    def create_or_update(
        self,
        email: str,
        reason: SuppressionReason,
        source: str,
        provider_message_id: str | None = None,
        metadata_json: dict[str, object] | None = None,
        contact_id: UUID | None = None,
    ) -> Suppression:
        normalized_email = email.lower()
        contact = self.db.scalar(select(Contact).where(Contact.email == normalized_email))
        suppression = self.db.scalar(
            select(Suppression).where(
                Suppression.email == normalized_email,
                Suppression.reason == reason,
            )
        )
        if not suppression:
            suppression = Suppression(
                email=normalized_email,
                reason=reason,
                source=source,
                contact_id=contact_id or (contact.id if contact else None),
                metadata_json=metadata_json or {},
            )
            self.db.add(suppression)
        suppression.source = source
        suppression.provider_message_id = provider_message_id
        suppression.metadata_json = metadata_json or {}
        if contact and reason == SuppressionReason.unsubscribe:
            contact.is_unsubscribed = True
        return suppression

    def list_items(self, limit: int = 100, offset: int = 0) -> list[Suppression]:
        statement = (
            select(Suppression)
            .order_by(Suppression.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.scalars(statement).all())
