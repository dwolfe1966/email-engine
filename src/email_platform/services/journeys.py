from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from email_platform.models.entities import Journey, JourneyStep
from email_platform.schemas.contracts import (
    JourneyCreate,
    JourneyStepCreate,
    JourneyStepUpdate,
    JourneyUpdate,
)


class JourneyService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: JourneyCreate) -> Journey:
        journey = Journey(**payload.model_dump())
        self.db.add(journey)
        self.db.commit()
        return self.get(journey.id) or journey

    def list_items(self, limit: int = 100, offset: int = 0) -> list[Journey]:
        statement = (
            select(Journey)
            .options(selectinload(Journey.steps))
            .order_by(Journey.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.scalars(statement).all())

    def count(self) -> int:
        return self.db.scalar(select(func.count()).select_from(Journey)) or 0

    def get(self, journey_id: UUID) -> Journey | None:
        statement = (
            select(Journey)
            .options(selectinload(Journey.steps))
            .where(Journey.id == journey_id)
        )
        return self.db.scalar(statement)

    def update(self, journey_id: UUID, payload: JourneyUpdate) -> Journey | None:
        journey = self.get(journey_id)
        if not journey:
            return None
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(journey, key, value)
        self.db.commit()
        return self.get(journey_id)

    def delete(self, journey_id: UUID) -> bool:
        journey = self.get(journey_id)
        if not journey:
            return False
        self.db.delete(journey)
        self.db.commit()
        return True

    def create_step(self, journey_id: UUID, payload: JourneyStepCreate) -> JourneyStep | None:
        if not self.get(journey_id):
            return None
        step = JourneyStep(journey_id=journey_id, **payload.model_dump())
        self.db.add(step)
        self.db.commit()
        self.db.refresh(step)
        return step

    def get_step(self, step_id: UUID) -> JourneyStep | None:
        return self.db.get(JourneyStep, step_id)

    def update_step(self, step_id: UUID, payload: JourneyStepUpdate) -> JourneyStep | None:
        step = self.get_step(step_id)
        if not step:
            return None
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(step, key, value)
        self.db.commit()
        self.db.refresh(step)
        return step

    def delete_step(self, step_id: UUID) -> bool:
        step = self.get_step(step_id)
        if not step:
            return False
        self.db.delete(step)
        self.db.commit()
        return True
