from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from email_platform.models.entities import DataSource, DataSourceMapping
from email_platform.schemas.contracts import DataSourceCreate, DataSourceMappingCreate


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

    def get(self, data_source_id: UUID) -> DataSource | None:
        return self.db.get(DataSource, data_source_id)

    def create_mapping(self, payload: DataSourceMappingCreate) -> DataSourceMapping:
        mapping = DataSourceMapping(**payload.model_dump())
        self.db.add(mapping)
        self.db.commit()
        self.db.refresh(mapping)
        return mapping

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
