from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from email_platform.core.settings import Settings
from email_platform.models.entities import (
    DeliveryRoute,
    DeliveryRouteStatus,
    DeliveryRouteType,
    EmailSendRecord,
)
from email_platform.schemas.contracts import DeliveryRouteCreate, DeliveryRouteUpdate


@dataclass(frozen=True)
class SelectedDeliveryRoute:
    route_type: str
    route_key: str
    route_id: UUID | None = None
    name: str | None = None
    source: str = 'fallback'


class DeliveryRouteService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: DeliveryRouteCreate) -> DeliveryRoute:
        route = DeliveryRoute(**payload.model_dump())
        self.db.add(route)
        self.db.commit()
        self.db.refresh(route)
        return route

    def get(self, route_id: UUID) -> DeliveryRoute | None:
        return self.db.get(DeliveryRoute, route_id)

    def list_items(
        self,
        route_type: DeliveryRouteType | None = None,
        status: DeliveryRouteStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DeliveryRoute]:
        statement = select(DeliveryRoute).order_by(
            DeliveryRoute.priority.asc(),
            DeliveryRoute.created_at.desc(),
        )
        if route_type:
            statement = statement.where(DeliveryRoute.route_type == route_type)
        if status:
            statement = statement.where(DeliveryRoute.status == status)
        return list(self.db.scalars(statement.limit(limit).offset(offset)).all())

    def count(
        self,
        route_type: DeliveryRouteType | None = None,
        status: DeliveryRouteStatus | None = None,
    ) -> int:
        statement = select(func.count()).select_from(DeliveryRoute)
        if route_type:
            statement = statement.where(DeliveryRoute.route_type == route_type)
        if status:
            statement = statement.where(DeliveryRoute.status == status)
        return self.db.scalar(statement) or 0

    def update(self, route_id: UUID, payload: DeliveryRouteUpdate) -> DeliveryRoute | None:
        route = self.get(route_id)
        if not route:
            return None
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(route, key, value)
        self.db.commit()
        self.db.refresh(route)
        return route

    def delete(self, route_id: UUID) -> bool:
        route = self.get(route_id)
        if not route:
            return False
        self.db.delete(route)
        self.db.commit()
        return True

    def select_for_record(
        self,
        record: EmailSendRecord,
        settings: Settings,
    ) -> SelectedDeliveryRoute:
        configured_type = self._configured_route_type(settings.email_provider)
        if configured_type:
            route = self.db.scalar(
                select(DeliveryRoute)
                .where(DeliveryRoute.status == DeliveryRouteStatus.active)
                .where(DeliveryRoute.route_type == configured_type)
                .order_by(DeliveryRoute.priority.asc(), DeliveryRoute.created_at.desc())
                .limit(1)
            )
            if route:
                return SelectedDeliveryRoute(
                    route_type=route.route_type.value,
                    route_key=route.name,
                    route_id=route.id,
                    name=route.name,
                    source='delivery_routes',
                )

        route_type = configured_type.value if configured_type else settings.email_provider
        return SelectedDeliveryRoute(
            route_type=route_type,
            route_key=settings.email_provider,
            source='settings',
        )

    def _configured_route_type(self, email_provider: str) -> DeliveryRouteType | None:
        if email_provider == 'smtp':
            return DeliveryRouteType.smtp_relay
        try:
            return DeliveryRouteType(email_provider)
        except ValueError:
            return None
