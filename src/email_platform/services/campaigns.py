from datetime import datetime
from typing import cast
from uuid import UUID

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from email_platform.models.entities import (
    Campaign,
    CampaignSendJob,
    CampaignStatus,
    Contact,
    EmailEvent,
    EmailSendRecord,
    EmailSendStatus,
    JourneyStepExecution,
    SendJobStatus,
)
from email_platform.schemas.contracts import (
    CampaignCloneRequest,
    CampaignCreate,
    CampaignLaunchRead,
    CampaignLaunchRequest,
    CampaignProcessDueRead,
    CampaignUpdate,
    CampaignValidationRead,
    JsonObject,
    TemplateValidationRequest,
)
from email_platform.services.audiences import AudienceService
from email_platform.services.suppressions import SuppressionService
from email_platform.services.templates import TemplateService


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
        updates = payload.model_dump(exclude_unset=True)
        if updates.get('status') == CampaignStatus.scheduled:
            raise ValueError('Use the approve endpoint to move a campaign to scheduled.')
        content_fields = {'name', 'template_id', 'audience_query'} & updates.keys()
        for key, value in updates.items():
            setattr(campaign, key, value)
        if content_fields:
            campaign.status = CampaignStatus.draft
            campaign.scheduled_at = None
        self.db.commit()
        self.db.refresh(campaign)
        return campaign

    def clone(self, campaign_id: UUID, payload: CampaignCloneRequest) -> Campaign | None:
        campaign = self.get(campaign_id)
        if not campaign:
            return None
        clone = Campaign(
            name=payload.name or f'{campaign.name} copy',
            template_id=campaign.template_id,
            audience_query=campaign.audience_query,
            scheduled_at=None,
            status=CampaignStatus.draft,
        )
        self.db.add(clone)
        self.db.commit()
        self.db.refresh(clone)
        return clone

    def delete(self, campaign_id: UUID) -> bool:
        campaign = self.get(campaign_id)
        if not campaign:
            return False
        self._delete_campaign_dependencies(campaign_id)
        self.db.delete(campaign)
        self.db.commit()
        return True

    def validate(
        self,
        campaign_id: UUID,
        payload: CampaignLaunchRequest | None = None,
    ) -> CampaignValidationRead | None:
        campaign = self.get(campaign_id)
        if not campaign:
            return None
        payload = payload or CampaignLaunchRequest()
        errors: list[str] = []
        warnings: list[str] = []
        requested_count = 0
        queued_count = 0
        suppressed_count = 0
        undeclared_variables: list[str] = []
        missing_variables: list[str] = []

        template = TemplateService(self.db).get(campaign.template_id)
        if not template:
            errors.append('Campaign template not found.')
        else:
            template_validation = TemplateService(self.db).validate(
                TemplateValidationRequest(
                    subject=template.subject,
                    html_body=template.html_body,
                    css_body=template.css_body,
                    text_body=template.text_body,
                    variables=self._sample_variables(payload.variables),
                )
            )
            undeclared_variables = template_validation.undeclared_variables
            missing_variables = template_validation.missing_variables
            errors.extend(template_validation.errors)
            errors.extend(template_validation.lint_errors)
            warnings.extend(template_validation.lint_warnings)
            if template_validation.missing_variables:
                errors.append(
                    'Template is missing launch variables: '
                    + ', '.join(template_validation.missing_variables)
                )

        try:
            rule_tree = self._rule_tree(campaign, payload)
            requested_count, contacts = AudienceService(self.db).preview(rule_tree, limit=500)
            suppression_service = SuppressionService(self.db)
            for contact in contacts:
                if contact.is_unsubscribed or suppression_service.is_suppressed(contact.email):
                    suppressed_count += 1
                else:
                    queued_count += 1
        except ValueError as exc:
            errors.append(str(exc))
        if requested_count == 0 and not errors:
            errors.append('Campaign audience currently matches no contacts.')
        elif queued_count == 0 and not errors:
            errors.append('Campaign has no deliverable contacts after suppression checks.')
        if requested_count > 500:
            warnings.append('Initial campaign fanout is capped at 500 contacts per launch.')

        return CampaignValidationRead(
            campaign_id=campaign.id,
            ok=not errors and queued_count > 0,
            status=campaign.status,
            requested_count=requested_count,
            queued_count=queued_count,
            suppressed_count=suppressed_count,
            errors=errors,
            warnings=warnings,
            undeclared_variables=undeclared_variables,
            missing_variables=missing_variables,
        )

    def approve(
        self,
        campaign_id: UUID,
        payload: CampaignLaunchRequest | None = None,
    ) -> CampaignValidationRead | None:
        validation = self.validate(campaign_id, payload=payload)
        if not validation:
            return None
        if not validation.ok:
            return validation
        campaign = self.get(campaign_id)
        if not campaign:
            return None
        campaign.status = CampaignStatus.scheduled
        campaign.scheduled_at = payload.scheduled_at if payload else datetime.utcnow()
        self.db.commit()
        validation.status = campaign.status
        return validation

    def process_due(self, limit: int = 25) -> CampaignProcessDueRead:
        now = datetime.utcnow()
        campaigns = list(
            self.db.scalars(
                select(Campaign)
                .where(Campaign.status == CampaignStatus.scheduled)
                .where(Campaign.scheduled_at.is_not(None))
                .where(Campaign.scheduled_at <= now)
                .order_by(Campaign.scheduled_at.asc())
                .limit(limit)
            ).all()
        )
        job_ids: list[str] = []
        errors: list[str] = []
        failed_count = 0
        for campaign in campaigns:
            try:
                launch = self.launch(campaign.id, CampaignLaunchRequest())
                if launch:
                    job_ids.append(str(launch.job_id))
                else:
                    failed_count += 1
                    errors.append(f'{campaign.id}: campaign not found during due processing')
            except ValueError as exc:
                failed_count += 1
                errors.append(f'{campaign.id}: {exc}')
        return CampaignProcessDueRead(
            claimed_count=len(campaigns),
            launched_count=len(job_ids),
            failed_count=failed_count,
            job_ids=job_ids,
            errors=errors,
        )

    def launch(
        self, campaign_id: UUID, payload: CampaignLaunchRequest
    ) -> CampaignLaunchRead | None:
        campaign = self.get(campaign_id)
        if not campaign:
            return None
        validation = self.validate(campaign_id, payload=payload)
        if not validation:
            return None
        if not validation.ok:
            raise ValueError('; '.join(validation.errors or validation.warnings))
        if not payload.dry_run and campaign.status != CampaignStatus.scheduled:
            raise ValueError('Campaign must be approved before queue launch.')

        rule_tree = self._rule_tree(campaign, payload)
        audience_snapshot_id: UUID | None = None
        if payload.audience_id:
            snapshot = AudienceService(self.db).create_snapshot(
                payload.audience_id,
                commit=False,
            )
            audience_snapshot_id = snapshot.id if snapshot else None

        requested_count, contacts = AudienceService(self.db).preview(rule_tree, limit=500)
        job = CampaignSendJob(
            campaign_id=campaign.id,
            audience_snapshot_id=audience_snapshot_id,
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
            suppression_service = SuppressionService(self.db)
            for contact in contacts:
                if contact.is_unsubscribed or suppression_service.is_suppressed(contact.email):
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
        campaign.scheduled_at = None
        self.db.commit()
        self.db.refresh(job)
        self.db.refresh(campaign)
        return CampaignLaunchRead(
            job_id=job.id,
            campaign_id=campaign.id,
            audience_snapshot_id=audience_snapshot_id,
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

    def get_send_record(self, send_record_id: UUID) -> EmailSendRecord | None:
        return self.db.get(EmailSendRecord, send_record_id)

    def requeue_send_record(self, send_record_id: UUID) -> EmailSendRecord | None:
        record = self.get_send_record(send_record_id)
        if not record:
            return None
        if record.status == EmailSendStatus.sent:
            raise ValueError('Sent records cannot be requeued')
        record.status = EmailSendStatus.queued
        record.error_message = None
        record.next_attempt_at = None
        record.provider = None
        record.provider_message_id = None
        self.db.commit()
        self.db.refresh(record)
        return record

    def skip_send_record(self, send_record_id: UUID) -> EmailSendRecord | None:
        record = self.get_send_record(send_record_id)
        if not record:
            return None
        if record.status in {EmailSendStatus.sent, EmailSendStatus.sending}:
            raise ValueError('Sent or sending records cannot be skipped')
        record.status = EmailSendStatus.skipped
        record.next_attempt_at = None
        record.error_message = None
        self.db.commit()
        self.db.refresh(record)
        return record

    def delete_send_record(self, send_record_id: UUID) -> bool:
        record = self.get_send_record(send_record_id)
        if not record:
            return False
        if record.status in {EmailSendStatus.sent, EmailSendStatus.sending}:
            raise ValueError('Sent or sending records cannot be deleted')
        self.db.execute(
            delete(JourneyStepExecution).where(
                JourneyStepExecution.send_record_id == send_record_id
            )
        )
        self.db.execute(delete(EmailEvent).where(EmailEvent.send_record_id == send_record_id))
        self.db.delete(record)
        self.db.commit()
        return True

    def _delete_campaign_dependencies(self, campaign_id: UUID) -> None:
        send_job_ids = list(
            self.db.scalars(
                select(CampaignSendJob.id).where(CampaignSendJob.campaign_id == campaign_id)
            ).all()
        )
        send_record_filters = [EmailSendRecord.campaign_id == campaign_id]
        if send_job_ids:
            send_record_filters.append(EmailSendRecord.send_job_id.in_(send_job_ids))
        send_record_ids = list(
            self.db.scalars(
                select(EmailSendRecord.id).where(or_(*send_record_filters))
            ).all()
        )

        if send_record_ids:
            self.db.execute(
                delete(JourneyStepExecution).where(
                    JourneyStepExecution.send_record_id.in_(send_record_ids)
                )
            )
            self.db.execute(
                delete(EmailEvent).where(EmailEvent.send_record_id.in_(send_record_ids))
            )
            self.db.execute(delete(EmailSendRecord).where(EmailSendRecord.id.in_(send_record_ids)))

        if send_job_ids:
            self.db.execute(delete(EmailEvent).where(EmailEvent.send_job_id.in_(send_job_ids)))
            self.db.execute(delete(CampaignSendJob).where(CampaignSendJob.id.in_(send_job_ids)))

        self.db.execute(delete(EmailEvent).where(EmailEvent.campaign_id == campaign_id))

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

    def _rule_tree(self, campaign: Campaign, payload: CampaignLaunchRequest) -> dict[str, object]:
        rule_tree = payload.rule_tree or campaign.audience_query
        if payload.audience_id:
            audience = AudienceService(self.db).get(payload.audience_id)
            if not audience:
                raise ValueError('Audience not found.')
            rule_tree = audience.rule_tree
        return cast(dict[str, object], rule_tree)

    def _sample_variables(self, variables: JsonObject) -> JsonObject:
        return {
            'email': 'person@example.com',
            'first_name': 'First',
            'last_name': 'Last',
            'source': 'sample',
            'attributes': {},
            **variables,
        }
