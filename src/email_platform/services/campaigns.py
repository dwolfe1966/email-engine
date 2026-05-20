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
