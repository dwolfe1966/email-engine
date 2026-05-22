from typing import cast
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from email_platform.models.entities import (
    Contact,
    DataSource,
    DataSourceImportJob,
    DataSourceImportStatus,
    DataSourceMapping,
)
from email_platform.schemas.contracts import (
    DataSourceCreate,
    DataSourceIngestRequest,
    DataSourceMappingCreate,
    DataSourceMappingUpdate,
    DataSourceSchemaFieldRead,
    DataSourceSchemaRead,
    DataSourceUpdate,
    DataSourceValidationRead,
    JsonObject,
)


class DataSourceService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: DataSourceCreate) -> DataSource:
        data_source = DataSource(**payload.model_dump())
        self.db.add(data_source)
        self.db.commit()
        self.db.refresh(data_source)
        return data_source

    def list_items(self, limit: int = 100, offset: int = 0) -> list[DataSource]:
        statement = (
            select(DataSource).order_by(DataSource.created_at.desc()).limit(limit).offset(offset)
        )
        return list(self.db.scalars(statement).all())

    def count(self) -> int:
        return self.db.scalar(select(func.count()).select_from(DataSource)) or 0

    def get(self, data_source_id: UUID) -> DataSource | None:
        return self.db.get(DataSource, data_source_id)

    def update(self, data_source_id: UUID, payload: DataSourceUpdate) -> DataSource | None:
        data_source = self.get(data_source_id)
        if not data_source:
            return None
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(data_source, key, value)
        self.db.commit()
        self.db.refresh(data_source)
        return data_source

    def delete(self, data_source_id: UUID) -> bool:
        data_source = self.get(data_source_id)
        if not data_source:
            return False
        self.db.execute(
            delete(DataSourceImportJob).where(DataSourceImportJob.data_source_id == data_source_id)
        )
        self.db.execute(
            delete(DataSourceMapping).where(DataSourceMapping.data_source_id == data_source_id)
        )
        self.db.delete(data_source)
        self.db.commit()
        return True

    def validate_connection(self, data_source_id: UUID) -> DataSourceValidationRead | None:
        data_source = self.get(data_source_id)
        if not data_source:
            return None
        checks: list[str] = []
        errors: list[str] = []
        config = data_source.config

        if data_source.source_type.value in {'manual', 'csv'}:
            checks.append('local_source_configuration_available')
            if self._configured_fields(config) or self._sample_rows(config):
                checks.append('schema_hints_available')
            else:
                errors.append('Add fields, headers, or sample_rows to config for schema discovery')
        elif data_source.source_type.value == 'rest_api':
            if config.get('base_url') or config.get('url'):
                checks.append('rest_endpoint_configured')
            else:
                errors.append('REST API sources require config.base_url or config.url')
            if data_source.secret_ref:
                checks.append('secret_ref_present')
        else:
            if data_source.secret_ref:
                checks.append('secret_ref_present')
            else:
                errors.append(f'{data_source.source_type.value} sources require secret_ref')
            if config.get('database') or config.get('dataset') or config.get('schema'):
                checks.append('namespace_configured')

        return DataSourceValidationRead(
            data_source_id=data_source.id,
            source_type=data_source.source_type,
            ok=not errors,
            checks=checks,
            errors=errors,
        )

    def discover_schema(self, data_source_id: UUID) -> DataSourceSchemaRead | None:
        data_source = self.get(data_source_id)
        if not data_source:
            return None
        mappings = self.list_mappings(data_source_id=data_source_id, limit=500, offset=0)
        sample_rows = self._sample_rows(data_source.config)
        field_names = set(self._configured_fields(data_source.config))
        for row in sample_rows:
            field_names.update(row.keys())
        for mapping in mappings:
            field_names.update(self._mapping_source_fields(mapping.mapping))

        fields = [
            DataSourceSchemaFieldRead(
                name=name,
                field_type=self._field_type(name, sample_rows),
                sample_values=self._sample_values(name, sample_rows),
            )
            for name in sorted(field_names)
        ]
        return DataSourceSchemaRead(
            data_source_id=data_source.id,
            source_type=data_source.source_type,
            object_types=sorted({mapping.object_type for mapping in mappings}),
            fields=fields,
            sample_rows=cast(list[JsonObject], sample_rows[:10]),
        )

    def create_mapping(self, payload: DataSourceMappingCreate) -> DataSourceMapping:
        mapping = DataSourceMapping(**payload.model_dump())
        self.db.add(mapping)
        self.db.commit()
        self.db.refresh(mapping)
        return mapping

    def get_mapping(self, mapping_id: UUID) -> DataSourceMapping | None:
        return self.db.get(DataSourceMapping, mapping_id)

    def list_mappings(
        self,
        data_source_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DataSourceMapping]:
        statement = select(DataSourceMapping).order_by(DataSourceMapping.created_at.desc())
        if data_source_id:
            statement = statement.where(DataSourceMapping.data_source_id == data_source_id)
        statement = statement.limit(limit).offset(offset)
        return list(self.db.scalars(statement).all())

    def count_mappings(self, data_source_id: UUID | None = None) -> int:
        statement = select(func.count()).select_from(DataSourceMapping)
        if data_source_id:
            statement = statement.where(DataSourceMapping.data_source_id == data_source_id)
        return self.db.scalar(statement) or 0

    def update_mapping(
        self, mapping_id: UUID, payload: DataSourceMappingUpdate
    ) -> DataSourceMapping | None:
        mapping = self.get_mapping(mapping_id)
        if not mapping:
            return None
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(mapping, key, value)
        self.db.commit()
        self.db.refresh(mapping)
        return mapping

    def delete_mapping(self, mapping_id: UUID) -> bool:
        mapping = self.get_mapping(mapping_id)
        if not mapping:
            return False
        self.db.execute(
            delete(DataSourceImportJob).where(DataSourceImportJob.mapping_id == mapping_id)
        )
        self.db.delete(mapping)
        self.db.commit()
        return True

    def ingest_rows(
        self,
        data_source_id: UUID,
        payload: DataSourceIngestRequest,
    ) -> DataSourceImportJob | None:
        data_source = self.get(data_source_id)
        mapping = self.get_mapping(payload.mapping_id)
        if not data_source or not mapping or mapping.data_source_id != data_source_id:
            return None

        errors: list[object] = []
        created_count = 0
        updated_count = 0
        skipped_count = 0
        object_type = mapping.object_type

        if object_type != 'contact':
            errors.append({'row': None, 'error': f'Unsupported object_type {object_type}'})
            return self._save_import_job(
                data_source_id=data_source_id,
                mapping=mapping,
                status=DataSourceImportStatus.failed,
                received_count=len(payload.rows),
                imported_count=0,
                created_count=0,
                updated_count=0,
                skipped_count=len(payload.rows),
                errors=errors,
                metadata_json=cast(dict[str, object], payload.metadata_json),
            )

        for index, row in enumerate(payload.rows, start=1):
            try:
                contact_values = self._map_contact_row(cast(dict[str, object], row), mapping)
            except ValueError as exc:
                skipped_count += 1
                errors.append({'row': index, 'error': str(exc)})
                continue
            if payload.dry_run:
                created_count += 1
                continue

            existing = self.db.scalar(
                select(Contact).where(Contact.email == contact_values['email'])
            )
            if existing:
                existing.first_name = cast(str | None, contact_values.get('first_name'))
                existing.last_name = cast(str | None, contact_values.get('last_name'))
                existing.source = cast(str | None, contact_values.get('source'))
                existing.attributes = {
                    **existing.attributes,
                    **cast(dict[str, object], contact_values['attributes']),
                }
                updated_count += 1
            else:
                self.db.add(Contact(**contact_values))
                created_count += 1

        imported_count = created_count + updated_count
        status = (
            DataSourceImportStatus.dry_run
            if payload.dry_run
            else DataSourceImportStatus.completed
        )
        return self._save_import_job(
            data_source_id=data_source_id,
            mapping=mapping,
            status=status,
            received_count=len(payload.rows),
            imported_count=imported_count,
            created_count=created_count,
            updated_count=updated_count,
            skipped_count=skipped_count,
            errors=errors,
            metadata_json=cast(dict[str, object], payload.metadata_json),
        )

    def list_import_jobs(
        self,
        data_source_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DataSourceImportJob]:
        statement = select(DataSourceImportJob).order_by(DataSourceImportJob.created_at.desc())
        if data_source_id:
            statement = statement.where(DataSourceImportJob.data_source_id == data_source_id)
        return list(self.db.scalars(statement.limit(limit).offset(offset)).all())

    def count_import_jobs(self, data_source_id: UUID | None = None) -> int:
        statement = select(func.count()).select_from(DataSourceImportJob)
        if data_source_id:
            statement = statement.where(DataSourceImportJob.data_source_id == data_source_id)
        return self.db.scalar(statement) or 0

    def _save_import_job(
        self,
        data_source_id: UUID,
        mapping: DataSourceMapping,
        status: DataSourceImportStatus,
        received_count: int,
        imported_count: int,
        created_count: int,
        updated_count: int,
        skipped_count: int,
        errors: list[object],
        metadata_json: dict[str, object],
    ) -> DataSourceImportJob:
        job = DataSourceImportJob(
            data_source_id=data_source_id,
            mapping_id=mapping.id,
            status=status,
            object_type=mapping.object_type,
            received_count=received_count,
            imported_count=imported_count,
            created_count=created_count,
            updated_count=updated_count,
            skipped_count=skipped_count,
            errors=errors,
            metadata_json=metadata_json,
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def _map_contact_row(
        self,
        row: dict[str, object],
        mapping: DataSourceMapping,
    ) -> dict[str, object]:
        spec = mapping.mapping
        email = self._mapped_value(row, spec.get('email'))
        if not email:
            raise ValueError('missing mapped email')
        attributes: dict[str, object] = {
            'data_source_id': str(mapping.data_source_id),
            'data_source_mapping_id': str(mapping.id),
        }
        raw_attributes = spec.get('attributes')
        if isinstance(raw_attributes, dict):
            for attribute_key, source_key in raw_attributes.items():
                if not isinstance(attribute_key, str):
                    continue
                value = self._mapped_value(row, source_key)
                if value is not None:
                    attributes[attribute_key] = value
        source = self._mapped_value(row, spec.get('source'))
        return {
            'email': str(email).lower(),
            'first_name': self._mapped_str(row, spec.get('first_name')),
            'last_name': self._mapped_str(row, spec.get('last_name')),
            'source': str(source) if source else 'data_source_import',
            'attributes': attributes,
        }

    def _mapped_str(self, row: dict[str, object], source: object) -> str | None:
        value = self._mapped_value(row, source)
        return str(value) if value is not None else None

    def _mapped_value(self, row: dict[str, object], source: object) -> object:
        if source is None:
            return None
        if isinstance(source, str):
            return row.get(source)
        return source

    def _configured_fields(self, config: dict[str, object]) -> list[str]:
        fields = config.get('fields', config.get('headers', []))
        if isinstance(fields, list):
            return [str(field) for field in fields if str(field)]
        return []

    def _sample_rows(self, config: dict[str, object]) -> list[dict[str, object]]:
        rows = config.get('sample_rows', [])
        if not isinstance(rows, list):
            return []
        return [cast(dict[str, object], row) for row in rows if isinstance(row, dict)]

    def _mapping_source_fields(self, mapping: dict[str, object]) -> set[str]:
        fields: set[str] = set()
        for key, value in mapping.items():
            if key == 'attributes' and isinstance(value, dict):
                fields.update(str(source) for source in value.values() if source)
            elif isinstance(value, str) and value:
                fields.add(value)
        return fields

    def _field_type(self, field: str, rows: list[dict[str, object]]) -> str:
        for row in rows:
            value = row.get(field)
            if value is not None:
                return type(value).__name__
        return 'unknown'

    def _sample_values(self, field: str, rows: list[dict[str, object]]) -> list[object]:
        values: list[object] = []
        for row in rows:
            if field not in row:
                continue
            value = row[field]
            if value not in values:
                values.append(value)
            if len(values) >= 5:
                break
        return values
