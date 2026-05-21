from collections.abc import Mapping
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from email_platform.models.entities import Audience, Contact
from email_platform.schemas.contracts import AudienceCreate


class AudienceService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: AudienceCreate) -> Audience:
        count, _ = self.preview(payload.rule_tree, limit=1)
        audience = Audience(**payload.model_dump(), estimated_count=count)
        self.db.add(audience)
        self.db.commit()
        self.db.refresh(audience)
        return audience

    def list_items(self, limit: int = 100, offset: int = 0) -> list[Audience]:
        statement = (
            select(Audience).order_by(Audience.created_at.desc()).limit(limit).offset(offset)
        )
        return list(self.db.scalars(statement).all())

    def get(self, audience_id: UUID) -> Audience | None:
        return self.db.get(Audience, audience_id)

    def preview(
        self, rule_tree: Mapping[str, object], limit: int = 25
    ) -> tuple[int, list[Contact]]:
        contacts = list(self.db.scalars(select(Contact).order_by(Contact.created_at.desc())).all())
        matched = [contact for contact in contacts if self._matches(contact, rule_tree)]
        return len(matched), matched[:limit]

    def _matches(self, contact: Contact, rule_tree: Mapping[str, object]) -> bool:
        if not rule_tree:
            return not contact.is_unsubscribed

        operator = str(rule_tree.get('operator', 'and')).lower()
        rules = rule_tree.get('rules')
        if isinstance(rules, list):
            results = [self._matches(contact, rule) for rule in rules if isinstance(rule, dict)]
            return any(results) if operator == 'or' else all(results)

        field = rule_tree.get('field')
        comparator = str(rule_tree.get('comparator', 'eq')).lower()
        expected = rule_tree.get('value')
        actual = self._contact_value(contact, field if isinstance(field, str) else '')
        return self._compare(actual, comparator, expected)

    def _contact_value(self, contact: Contact, field: str) -> object:
        if field.startswith('attributes.'):
            return contact.attributes.get(field.removeprefix('attributes.'))
        if field == 'email':
            return contact.email
        if field == 'first_name':
            return contact.first_name
        if field == 'last_name':
            return contact.last_name
        if field == 'source':
            return contact.source
        if field == 'is_unsubscribed':
            return contact.is_unsubscribed
        return contact.attributes.get(field)

    def _compare(self, actual: object, comparator: str, expected: object) -> bool:
        if comparator == 'eq':
            return actual == expected
        if comparator == 'ne':
            return actual != expected
        if comparator == 'contains':
            return str(expected).lower() in str(actual or '').lower()
        if comparator == 'in' and isinstance(expected, list):
            return actual in expected
        if comparator == 'exists':
            return actual is not None
        if comparator == 'not_exists':
            return actual is None
        return False
