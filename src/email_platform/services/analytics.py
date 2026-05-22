from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from email_platform.models.entities import (
    Campaign,
    CampaignSendJob,
    Contact,
    EmailEvent,
    EmailEventType,
    EmailSendRecord,
    EmailSendStatus,
)
from email_platform.schemas.contracts import (
    AnalyticsOverviewRead,
    CampaignAnalyticsRead,
    EventRead,
    MetricCount,
)


class AnalyticsService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def campaign_metrics(
        self, campaign_id: UUID, send_job_id: UUID | None = None
    ) -> CampaignAnalyticsRead | None:
        if not self.db.get(Campaign, campaign_id):
            return None
        if send_job_id:
            send_job = self.db.get(CampaignSendJob, send_job_id)
            if not send_job or send_job.campaign_id != campaign_id:
                return None

        status_counts = self._status_counts(campaign_id, send_job_id)
        event_counts = self._event_counts(campaign_id, send_job_id)
        requested_count = self._requested_count(campaign_id, send_job_id)
        queued_count = status_counts.get(EmailSendStatus.queued.value, 0)
        sent_count = status_counts.get(EmailSendStatus.sent.value, 0)
        failed_count = status_counts.get(EmailSendStatus.failed.value, 0)
        suppressed_count = status_counts.get(EmailSendStatus.suppressed.value, 0)
        delivered_count = event_counts.get(EmailEventType.delivered.value, 0)
        opened_count = event_counts.get(EmailEventType.opened.value, 0)
        clicked_count = event_counts.get(EmailEventType.clicked.value, 0)
        bounced_count = event_counts.get(EmailEventType.bounced.value, 0)
        complained_count = event_counts.get(EmailEventType.complained.value, 0)
        unsubscribed_count = event_counts.get(EmailEventType.unsubscribed.value, 0)
        rate_base = max(sent_count, delivered_count)

        return CampaignAnalyticsRead(
            campaign_id=campaign_id,
            send_job_id=send_job_id,
            requested_count=requested_count,
            queued_count=queued_count,
            sent_count=sent_count,
            failed_count=failed_count,
            suppressed_count=suppressed_count,
            delivered_count=delivered_count,
            opened_count=opened_count,
            clicked_count=clicked_count,
            bounced_count=bounced_count,
            complained_count=complained_count,
            unsubscribed_count=unsubscribed_count,
            open_rate=self._rate(opened_count, rate_base),
            click_rate=self._rate(clicked_count, rate_base),
            bounce_rate=self._rate(bounced_count, max(sent_count, requested_count)),
            status_counts=[
                MetricCount(name=name, count=count) for name, count in sorted(status_counts.items())
            ],
            event_counts=[
                MetricCount(name=name, count=count) for name, count in sorted(event_counts.items())
            ],
        )

    def overview(self, recent_event_limit: int = 25) -> AnalyticsOverviewRead:
        status_counts = self._global_status_counts()
        event_counts = self._global_event_counts()
        recent_events = [
            EventRead.model_validate(event)
            for event in self.db.scalars(
                select(EmailEvent).order_by(EmailEvent.occurred_at.desc()).limit(
                    recent_event_limit
                )
            ).all()
        ]
        return AnalyticsOverviewRead(
            campaign_count=self._row_count(Campaign),
            contact_count=self._row_count(Contact),
            send_job_count=self._row_count(CampaignSendJob),
            send_record_count=self._row_count(EmailSendRecord),
            event_count=self._row_count(EmailEvent),
            status_counts=[
                MetricCount(name=name, count=count) for name, count in sorted(status_counts.items())
            ],
            event_counts=[
                MetricCount(name=name, count=count) for name, count in sorted(event_counts.items())
            ],
            recent_events=recent_events,
        )

    def _requested_count(self, campaign_id: UUID, send_job_id: UUID | None) -> int:
        if send_job_id:
            job = self.db.get(CampaignSendJob, send_job_id)
            return job.requested_count if job else 0
        total = self.db.scalar(
            select(func.coalesce(func.sum(CampaignSendJob.requested_count), 0)).where(
                CampaignSendJob.campaign_id == campaign_id
            )
        )
        if total:
            return int(total)
        record_count = self.db.scalar(
            select(func.count()).select_from(EmailSendRecord).where(
                EmailSendRecord.campaign_id == campaign_id
            )
        )
        return record_count or 0

    def _status_counts(
        self, campaign_id: UUID, send_job_id: UUID | None
    ) -> dict[str, int]:
        statement = (
            select(EmailSendRecord.status, func.count())
            .where(EmailSendRecord.campaign_id == campaign_id)
            .group_by(EmailSendRecord.status)
        )
        if send_job_id:
            statement = statement.where(EmailSendRecord.send_job_id == send_job_id)
        return {status.value: count for status, count in self.db.execute(statement).all()}

    def _event_counts(self, campaign_id: UUID, send_job_id: UUID | None) -> dict[str, int]:
        statement = (
            select(EmailEvent.event_type, func.count())
            .where(EmailEvent.campaign_id == campaign_id)
            .group_by(EmailEvent.event_type)
        )
        if send_job_id:
            statement = statement.where(EmailEvent.send_job_id == send_job_id)
        return {event_type.value: count for event_type, count in self.db.execute(statement).all()}

    def _global_status_counts(self) -> dict[str, int]:
        statement = select(EmailSendRecord.status, func.count()).group_by(EmailSendRecord.status)
        return {status.value: count for status, count in self.db.execute(statement).all()}

    def _global_event_counts(self) -> dict[str, int]:
        statement = select(EmailEvent.event_type, func.count()).group_by(EmailEvent.event_type)
        return {event_type.value: count for event_type, count in self.db.execute(statement).all()}

    def _row_count(self, model: type[object]) -> int:
        return self.db.scalar(select(func.count()).select_from(model)) or 0

    def _rate(self, numerator: int, denominator: int) -> float:
        if denominator <= 0:
            return 0.0
        return round(numerator / denominator, 4)
