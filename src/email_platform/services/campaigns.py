from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from email_platform.models.entities import Campaign
from email_platform.schemas.contracts import CampaignCreate, CampaignUpdate


class CampaignService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: CampaignCreate) -> Campaign:
        campaign = Campaign(**payload.model_dump())
        self.db.add(campaign)
        self.db.commit()
        self.db.refresh(campaign)
        return campaign

    def list(self, limit: int = 100, offset: int = 0) -> list[Campaign]:
        statement = (
            select(Campaign).order_by(Campaign.created_at.desc()).limit(limit).offset(offset)
        )
        return list(self.db.scalars(statement).all())

    def count(self) -> int:
        return self.db.scalar(select(func.count()).select_from(Campaign)) or 0

    def get(self, campaign_id: UUID) -> Campaign | None:
        return self.db.get(Campaign, campaign_id)

    def update(self, campaign_id: UUID, payload: CampaignUpdate) -> Campaign | None:
        campaign = self.get(campaign_id)
        if not campaign:
            return None
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(campaign, key, value)
        self.db.commit()
        self.db.refresh(campaign)
        return campaign

    def delete(self, campaign_id: UUID) -> bool:
        campaign = self.get(campaign_id)
        if not campaign:
            return False
        self.db.delete(campaign)
        self.db.commit()
        return True
