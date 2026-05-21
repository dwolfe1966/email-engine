from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from email_platform.models.entities import DataSource, DataSourceMapping
from email_platform.schemas.contracts import (
    DataSourceCreate,
    DataSourceMappingCreate,
    DataSourceMappingUpdate,
    DataSourceUpdate,
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
        self.db.delete(data_source)
        self.db.commit()
        return True

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
        self.db.delete(mapping)
        self.db.commit()
        return True
