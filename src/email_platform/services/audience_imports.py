import csv
import io
from dataclasses import dataclass, field
from uuid import UUID, uuid4

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from email_platform.models.entities import Audience, Contact
from email_platform.schemas.contracts import AudienceCreate, ContactUpsert, JsonObject
from email_platform.services.audiences import AudienceService

CORE_FIELD_ALIASES = {
    'email': 'email',
    'email_address': 'email',
    'e_mail': 'email',
    'first_name': 'first_name',
    'firstname': 'first_name',
    'given_name': 'first_name',
    'last_name': 'last_name',
    'lastname': 'last_name',
    'family_name': 'last_name',
    'source': 'source',
}


@dataclass
class AudienceImportPreview:
    headers: list[str]
    row_count: int
    sample_rows: list[dict[str, str]]
    inferred_mapping: dict[str, str]
    errors: list[str] = field(default_factory=list)


@dataclass
class AudienceImportResult:
    audience: Audience
    import_id: UUID
    imported_count: int
    created_count: int
    updated_count: int
    skipped_count: int
    errors: list[str] = field(default_factory=list)


class AudienceImportService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def import_csv(
        self,
        content: bytes,
        audience_name: str,
        description: str | None = None,
        source: str = 'csv_import',
        column_mapping: dict[str, str] | None = None,
    ) -> AudienceImportResult:
        if self.db.scalar(select(Audience).where(Audience.name == audience_name)):
            raise ValueError('Audience name already exists')

        import_id = uuid4()
        rows = self._read_rows(content)
        if not rows:
            raise ValueError('CSV file has no rows')

        created_count = 0
        updated_count = 0
        skipped_count = 0
        errors: list[str] = []

        for index, row in enumerate(rows, start=2):
            try:
                payload = self._row_to_contact(row, import_id, source, column_mapping)
            except ValueError as exc:
                skipped_count += 1
                errors.append(f'Row {index}: {exc}')
                continue
            except ValidationError as exc:
                skipped_count += 1
                errors.append(f'Row {index}: {exc.errors()[0]["msg"]}')
                continue

            existing = self.db.scalar(select(Contact).where(Contact.email == str(payload.email)))
            if existing:
                existing.first_name = payload.first_name
                existing.last_name = payload.last_name
                existing.source = payload.source
                existing.attributes = {**existing.attributes, **payload.attributes}
                updated_count += 1
            else:
                self.db.add(Contact(**payload.model_dump()))
                created_count += 1

        imported_count = created_count + updated_count
        if imported_count == 0:
            self.db.rollback()
            raise ValueError('CSV import did not contain any valid contacts')

        self.db.commit()

        try:
            audience = AudienceService(self.db).create(
                AudienceCreate(
                    name=audience_name,
                    description=description,
                    rule_tree={
                        'field': 'attributes.audience_import_id',
                        'comparator': 'eq',
                        'value': str(import_id),
                    },
                )
            )
        except IntegrityError as exc:
            self.db.rollback()
            raise ValueError('Audience name already exists') from exc

        return AudienceImportResult(
            audience=audience,
            import_id=import_id,
            imported_count=imported_count,
            created_count=created_count,
            updated_count=updated_count,
            skipped_count=skipped_count,
            errors=errors,
        )

    def preview_csv(self, content: bytes, sample_limit: int = 10) -> AudienceImportPreview:
        rows = self._read_rows(content)
        headers = list(rows[0].keys()) if rows else self._read_headers(content)
        inferred_mapping = {
            header: CORE_FIELD_ALIASES.get(self._normalize_key(header), 'attribute')
            for header in headers
        }
        errors: list[str] = []
        if 'email' not in inferred_mapping.values():
            errors.append(
                'No email column was inferred. Map one CSV column to email before import.'
            )
        return AudienceImportPreview(
            headers=headers,
            row_count=len(rows),
            sample_rows=rows[:sample_limit],
            inferred_mapping=inferred_mapping,
            errors=errors,
        )

    def _read_rows(self, content: bytes) -> list[dict[str, str]]:
        try:
            text = content.decode('utf-8-sig')
        except UnicodeDecodeError as exc:
            raise ValueError('CSV must be UTF-8 encoded') from exc

        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            raise ValueError('CSV header row is required')
        return list(reader)

    def _read_headers(self, content: bytes) -> list[str]:
        try:
            text = content.decode('utf-8-sig')
        except UnicodeDecodeError as exc:
            raise ValueError('CSV must be UTF-8 encoded') from exc

        reader = csv.reader(io.StringIO(text))
        try:
            return next(reader)
        except StopIteration as exc:
            raise ValueError('CSV header row is required') from exc

    def _row_to_contact(
        self,
        row: dict[str, str],
        import_id: UUID,
        default_source: str,
        column_mapping: dict[str, str] | None = None,
    ) -> ContactUpsert:
        values: dict[str, str | None] = {
            'email': None,
            'first_name': None,
            'last_name': None,
            'source': default_source,
        }
        attributes: JsonObject = {
            'audience_import_id': str(import_id),
            'audience_import_source': default_source,
        }

        for raw_key, raw_value in row.items():
            key = self._normalize_key(raw_key)
            value = raw_value.strip() if isinstance(raw_value, str) else ''
            if not key or not value:
                continue
            target = self._mapped_target(raw_key, key, column_mapping)
            if target == 'ignore':
                continue
            if target == 'attribute':
                attributes[key] = value
                continue
            if target in values:
                values[target] = value

        if not values['email']:
            raise ValueError('missing email')

        return ContactUpsert(
            email=values['email'],
            first_name=values['first_name'],
            last_name=values['last_name'],
            source=values['source'],
            attributes=attributes,
        )

    def _normalize_key(self, key: str | None) -> str:
        if not key:
            return ''
        return '_'.join(key.strip().lower().replace('-', '_').split())

    def _mapped_target(
        self,
        raw_key: str | None,
        normalized_key: str,
        column_mapping: dict[str, str] | None,
    ) -> str:
        if column_mapping:
            mapped = column_mapping.get(raw_key or '') or column_mapping.get(normalized_key)
            if mapped in {'email', 'first_name', 'last_name', 'source', 'attribute', 'ignore'}:
                return mapped
        return CORE_FIELD_ALIASES.get(normalized_key, 'attribute')
