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
    CampaignPerformanceRead,
    DomainDeliverabilityRead,
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

    def campaign_performance(
        self, limit: int = 100, offset: int = 0
    ) -> tuple[list[CampaignPerformanceRead], int]:
        campaigns = list(
            self.db.scalars(
                select(Campaign)
                .order_by(Campaign.created_at.desc())
                .limit(limit)
                .offset(offset)
            ).all()
        )
        rows = []
        for campaign in campaigns:
            metrics = self.campaign_metrics(campaign.id)
            if not metrics:
                continue
            rows.append(
                CampaignPerformanceRead(
                    campaign_id=campaign.id,
                    name=campaign.name,
                    status=campaign.status,
                    requested_count=metrics.requested_count,
                    queued_count=metrics.queued_count,
                    sent_count=metrics.sent_count,
                    failed_count=metrics.failed_count,
                    suppressed_count=metrics.suppressed_count,
                    delivered_count=metrics.delivered_count,
                    opened_count=metrics.opened_count,
                    clicked_count=metrics.clicked_count,
                    bounced_count=metrics.bounced_count,
                    complained_count=metrics.complained_count,
                    unsubscribed_count=metrics.unsubscribed_count,
                    open_rate=metrics.open_rate,
                    click_rate=metrics.click_rate,
                    bounce_rate=metrics.bounce_rate,
                )
            )
        return rows, self._row_count(Campaign)

    def domain_deliverability(
        self,
        limit: int = 100,
        offset: int = 0,
        campaign_id: UUID | None = None,
        send_job_id: UUID | None = None,
        provider: str | None = None,
    ) -> tuple[list[DomainDeliverabilityRead], int]:
        statement = select(EmailSendRecord)
        if campaign_id:
            statement = statement.where(EmailSendRecord.campaign_id == campaign_id)
        if send_job_id:
            statement = statement.where(EmailSendRecord.send_job_id == send_job_id)
        if provider:
            statement = statement.where(EmailSendRecord.provider == provider)
        records = list(self.db.scalars(statement).all())

        buckets: dict[tuple[str, str | None], dict[str, int]] = {}
        record_bucket_keys: dict[UUID, tuple[str, str | None]] = {}
        for record in records:
            domain = self._email_domain(record.to_email)
            key = (domain, record.provider)
            bucket = buckets.setdefault(key, self._empty_domain_bucket())
            record_bucket_keys[record.id] = key
            bucket['send_record_count'] += 1
            bucket[f'{record.status.value}_count'] = bucket.get(
                f'{record.status.value}_count', 0
            ) + 1

        if record_bucket_keys:
            event_statement = select(EmailEvent).where(
                EmailEvent.send_record_id.in_(record_bucket_keys.keys())
            )
            for event in self.db.scalars(event_statement).all():
                if not event.send_record_id:
                    continue
                event_key = record_bucket_keys.get(event.send_record_id)
                if not event_key:
                    continue
                buckets[event_key][f'{event.event_type.value}_count'] = buckets[event_key].get(
                    f'{event.event_type.value}_count', 0
                ) + 1

        rows = [
            self._domain_row(domain=domain, provider=provider_name, counts=counts)
            for (domain, provider_name), counts in buckets.items()
        ]
        rows.sort(key=lambda row: row.send_record_count, reverse=True)
        return rows[offset : offset + limit], len(rows)

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

    def _email_domain(self, email: str) -> str:
        if '@' not in email:
            return 'unknown'
        return email.rsplit('@', 1)[1].lower()

    def _empty_domain_bucket(self) -> dict[str, int]:
        return {
            'send_record_count': 0,
            'queued_count': 0,
            'sent_count': 0,
            'failed_count': 0,
            'suppressed_count': 0,
            'delivered_count': 0,
            'opened_count': 0,
            'clicked_count': 0,
            'bounced_count': 0,
            'complained_count': 0,
            'unsubscribed_count': 0,
        }

    def _domain_row(
        self, domain: str, provider: str | None, counts: dict[str, int]
    ) -> DomainDeliverabilityRead:
        rate_base = max(counts['sent_count'], counts['delivered_count'])
        return DomainDeliverabilityRead(
            domain=domain,
            provider=provider,
            send_record_count=counts['send_record_count'],
            queued_count=counts['queued_count'],
            sent_count=counts['sent_count'],
            failed_count=counts['failed_count'],
            suppressed_count=counts['suppressed_count'],
            delivered_count=counts['delivered_count'],
            opened_count=counts['opened_count'],
            clicked_count=counts['clicked_count'],
            bounced_count=counts['bounced_count'],
            complained_count=counts['complained_count'],
            unsubscribed_count=counts['unsubscribed_count'],
            open_rate=self._rate(counts['opened_count'], rate_base),
            click_rate=self._rate(counts['clicked_count'], rate_base),
            bounce_rate=self._rate(
                counts['bounced_count'],
                max(counts['sent_count'], counts['send_record_count']),
            ),
        )

    def _rate(self, numerator: int, denominator: int) -> float:
        if denominator <= 0:
            return 0.0
        return round(numerator / denominator, 4)
