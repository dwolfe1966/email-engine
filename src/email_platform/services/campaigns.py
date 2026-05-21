from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from email_platform.models.entities import Campaign
from email_platform.schemas.contracts import CampaignCreate


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

    def get(self, campaign_id: UUID) -> Campaign | None:
        return self.db.get(Campaign, campaign_id)
