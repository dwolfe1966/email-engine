from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from email_platform.models.entities import (
    Campaign,
    CampaignSendJob,
    CampaignStatus,
    Contact,
    EmailSendRecord,
    EmailSendStatus,
    SendJobStatus,
)
from email_platform.schemas.contracts import (
    CampaignCreate,
    CampaignLaunchRead,
    CampaignLaunchRequest,
    CampaignUpdate,
)
from email_platform.services.audiences import AudienceService


class CampaignService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: CampaignCreate) -> Campaign:
        campaign = Campaign(**payload.model_dump())
        self.db.add(campaign)
        self.db.commit()
        self.db.refresh(campaign)
        return campaign

    def list_items(self, limit: int = 100, offset: int = 0) -> list[Campaign]:
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

    def launch(
        self, campaign_id: UUID, payload: CampaignLaunchRequest
    ) -> CampaignLaunchRead | None:
        campaign = self.get(campaign_id)
        if not campaign:
            return None

        rule_tree = payload.rule_tree or campaign.audience_query
        if payload.audience_id:
            audience = AudienceService(self.db).get(payload.audience_id)
            if not audience:
                raise ValueError('Audience not found')
            rule_tree = audience.rule_tree

        requested_count, contacts = AudienceService(self.db).preview(rule_tree, limit=500)
        job = CampaignSendJob(
            campaign_id=campaign.id,
            status=SendJobStatus.completed if payload.dry_run else SendJobStatus.queued,
            audience_rule_tree=rule_tree,
            requested_count=requested_count,
            queued_count=0,
            suppressed_count=0,
            metadata_json={'dry_run': payload.dry_run},
        )
        self.db.add(job)
        self.db.flush()

        queued_count = 0
        suppressed_count = 0
        if not payload.dry_run:
            for contact in contacts:
                if contact.is_unsubscribed:
                    suppressed_count += 1
                    self._add_send_record(
                        campaign, job, contact, payload, EmailSendStatus.suppressed
                    )
                    continue
                queued_count += 1
                self._add_send_record(campaign, job, contact, payload, EmailSendStatus.queued)

        job.queued_count = queued_count
        job.suppressed_count = suppressed_count
        campaign.status = CampaignStatus.sending if queued_count > 0 else CampaignStatus.sent
        self.db.commit()
        self.db.refresh(job)
        self.db.refresh(campaign)
        return CampaignLaunchRead(
            job_id=job.id,
            campaign_id=campaign.id,
            status=job.status,
            requested_count=job.requested_count,
            queued_count=job.queued_count,
            suppressed_count=job.suppressed_count,
            dry_run=payload.dry_run,
        )

    def list_send_jobs(
        self, campaign_id: UUID | None = None, limit: int = 100, offset: int = 0
    ) -> list[CampaignSendJob]:
        statement = select(CampaignSendJob).order_by(CampaignSendJob.created_at.desc())
        if campaign_id:
            statement = statement.where(CampaignSendJob.campaign_id == campaign_id)
        return list(self.db.scalars(statement.limit(limit).offset(offset)).all())

    def count_send_jobs(self, campaign_id: UUID | None = None) -> int:
        statement = select(func.count()).select_from(CampaignSendJob)
        if campaign_id:
            statement = statement.where(CampaignSendJob.campaign_id == campaign_id)
        return self.db.scalar(statement) or 0

    def list_send_records(
        self,
        campaign_id: UUID | None = None,
        send_job_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[EmailSendRecord]:
        statement = select(EmailSendRecord).order_by(EmailSendRecord.created_at.desc())
        if campaign_id:
            statement = statement.where(EmailSendRecord.campaign_id == campaign_id)
        if send_job_id:
            statement = statement.where(EmailSendRecord.send_job_id == send_job_id)
        return list(self.db.scalars(statement.limit(limit).offset(offset)).all())

    def count_send_records(
        self, campaign_id: UUID | None = None, send_job_id: UUID | None = None
    ) -> int:
        statement = select(func.count()).select_from(EmailSendRecord)
        if campaign_id:
            statement = statement.where(EmailSendRecord.campaign_id == campaign_id)
        if send_job_id:
            statement = statement.where(EmailSendRecord.send_job_id == send_job_id)
        return self.db.scalar(statement) or 0

    def _add_send_record(
        self,
        campaign: Campaign,
        job: CampaignSendJob,
        contact: Contact,
        payload: CampaignLaunchRequest,
        status: EmailSendStatus,
    ) -> None:
        variables = {
            'email': contact.email,
            'first_name': contact.first_name,
            'last_name': contact.last_name,
            'source': contact.source,
            'attributes': contact.attributes,
            **contact.attributes,
            **payload.variables,
        }
        self.db.add(
            EmailSendRecord(
                campaign_id=campaign.id,
                send_job_id=job.id,
                contact_id=contact.id,
                template_id=campaign.template_id,
                status=status,
                to_email=contact.email,
                variables=variables,
            )
        )
