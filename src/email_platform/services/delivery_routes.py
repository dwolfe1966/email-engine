from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from email_platform.core.settings import Settings
from email_platform.models.entities import (
    DeliveryRoute,
    DeliveryRouteStatus,
    DeliveryRouteType,
    DeliveryAttempt,
    DomainDeliveryPolicy,
    EmailSendRecord,
)
from email_platform.schemas.contracts import (
    DeliveryRouteCreate,
    DeliveryRouteUpdate,
    DomainAuthenticationDnsRecord,
    DomainAuthenticationPlanRead,
    DomainAuthenticationPlanRequest,
    DomainDeliveryPolicyCreate,
    DomainDeliveryPolicyUpdate,
)


@dataclass(frozen=True)
class SelectedDeliveryRoute:
    route_type: str
    route_key: str
    route_id: UUID | None = None
    domain_policy_id: UUID | None = None
    name: str | None = None
    domain: str | None = None
    warmup_stage: str | None = None
    max_per_minute: int | None = None
    max_concurrent: int | None = None
    source: str = 'fallback'


@dataclass(frozen=True)
class DeliveryClaimDecision:
    can_claim: bool
    reason: str | None = None
    domain: str | None = None
    domain_policy_id: UUID | None = None


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

    def pause_route(self, route_id: UUID) -> DeliveryRoute | None:
        route = self.get(route_id)
        if not route:
            return None
        route.status = DeliveryRouteStatus.paused
        self.db.commit()
        self.db.refresh(route)
        return route

    def resume_route(self, route_id: UUID) -> DeliveryRoute | None:
        route = self.get(route_id)
        if not route:
            return None
        route.status = DeliveryRouteStatus.active
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

    def create_domain_policy(
        self,
        payload: DomainDeliveryPolicyCreate,
    ) -> DomainDeliveryPolicy:
        policy = DomainDeliveryPolicy(
            **{
                **payload.model_dump(),
                'domain': payload.domain.lower(),
            }
        )
        self.db.add(policy)
        self.db.commit()
        self.db.refresh(policy)
        return policy

    def get_domain_policy(self, policy_id: UUID) -> DomainDeliveryPolicy | None:
        return self.db.get(DomainDeliveryPolicy, policy_id)

    def list_domain_policies(
        self,
        domain: str | None = None,
        route_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DomainDeliveryPolicy]:
        statement = select(DomainDeliveryPolicy).order_by(
            DomainDeliveryPolicy.domain.asc(),
            DomainDeliveryPolicy.created_at.desc(),
        )
        if domain:
            statement = statement.where(DomainDeliveryPolicy.domain == domain.lower())
        if route_id:
            statement = statement.where(DomainDeliveryPolicy.route_id == route_id)
        return list(self.db.scalars(statement.limit(limit).offset(offset)).all())

    def count_domain_policies(
        self,
        domain: str | None = None,
        route_id: UUID | None = None,
    ) -> int:
        statement = select(func.count()).select_from(DomainDeliveryPolicy)
        if domain:
            statement = statement.where(DomainDeliveryPolicy.domain == domain.lower())
        if route_id:
            statement = statement.where(DomainDeliveryPolicy.route_id == route_id)
        return self.db.scalar(statement) or 0

    def update_domain_policy(
        self,
        policy_id: UUID,
        payload: DomainDeliveryPolicyUpdate,
    ) -> DomainDeliveryPolicy | None:
        policy = self.get_domain_policy(policy_id)
        if not policy:
            return None
        values = payload.model_dump(exclude_unset=True)
        if 'domain' in values and values['domain']:
            values['domain'] = str(values['domain']).lower()
        for key, value in values.items():
            setattr(policy, key, value)
        self.db.commit()
        self.db.refresh(policy)
        return policy

    def pause_domain_policy(
        self,
        policy_id: UUID,
        paused_until: datetime | None = None,
    ) -> DomainDeliveryPolicy | None:
        policy = self.get_domain_policy(policy_id)
        if not policy:
            return None
        policy.paused_until = paused_until or datetime.utcnow() + timedelta(hours=1)
        self.db.commit()
        self.db.refresh(policy)
        return policy

    def resume_domain_policy(self, policy_id: UUID) -> DomainDeliveryPolicy | None:
        policy = self.get_domain_policy(policy_id)
        if not policy:
            return None
        policy.paused_until = None
        self.db.commit()
        self.db.refresh(policy)
        return policy

    def delete_domain_policy(self, policy_id: UUID) -> bool:
        policy = self.get_domain_policy(policy_id)
        if not policy:
            return False
        self.db.delete(policy)
        self.db.commit()
        return True

    def build_domain_authentication_plan(
        self,
        policy_id: UUID,
        payload: DomainAuthenticationPlanRequest,
    ) -> DomainAuthenticationPlanRead | None:
        policy = self.get_domain_policy(policy_id)
        if not policy:
            return None
        plan = self._domain_authentication_plan(policy.domain, payload)
        policy.metadata_json = {
            **(policy.metadata_json or {}),
            'domain_authentication': plan.model_dump(),
        }
        self.db.commit()
        self.db.refresh(policy)
        return plan

    def select_for_record(
        self,
        record: EmailSendRecord,
        settings: Settings,
    ) -> SelectedDeliveryRoute:
        domain = self._domain_for_record(record)
        if domain:
            policy = self._active_domain_policy(domain)
            if policy and policy.route_id:
                route = self.db.get(DeliveryRoute, policy.route_id)
                if route and route.status == DeliveryRouteStatus.active:
                    return SelectedDeliveryRoute(
                        route_type=route.route_type.value,
                        route_key=route.name,
                        route_id=route.id,
                        domain_policy_id=policy.id,
                        name=route.name,
                        domain=policy.domain,
                        warmup_stage=policy.warmup_stage,
                        max_per_minute=policy.max_per_minute,
                        max_concurrent=policy.max_concurrent,
                        source='domain_policy',
                    )

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
                    domain=domain,
                    source='delivery_routes',
                )

        route_type = configured_type.value if configured_type else settings.email_provider
        return SelectedDeliveryRoute(
            route_type=route_type,
            route_key=settings.email_provider,
            domain=domain,
            source='settings',
        )

    def claim_decision(
        self,
        record: EmailSendRecord,
        reserved_count: int = 0,
    ) -> DeliveryClaimDecision:
        domain = self._domain_for_record(record)
        if not domain:
            return DeliveryClaimDecision(can_claim=True)

        policy = self._domain_policy(domain)
        if not policy:
            return DeliveryClaimDecision(can_claim=True, domain=domain)
        if policy.paused_until and policy.paused_until > datetime.utcnow():
            return DeliveryClaimDecision(
                can_claim=False,
                reason='domain_policy_paused',
                domain=domain,
                domain_policy_id=policy.id,
            )
        if policy.max_per_minute is not None:
            recent_count = self._recent_domain_attempt_count(domain, seconds=60)
            if recent_count + reserved_count >= policy.max_per_minute:
                return DeliveryClaimDecision(
                    can_claim=False,
                    reason='domain_policy_max_per_minute',
                    domain=domain,
                    domain_policy_id=policy.id,
                )
        if policy.max_concurrent is not None:
            active_count = self._active_domain_attempt_count(domain)
            if active_count + reserved_count >= policy.max_concurrent:
                return DeliveryClaimDecision(
                    can_claim=False,
                    reason='domain_policy_max_concurrent',
                    domain=domain,
                    domain_policy_id=policy.id,
                )
        return DeliveryClaimDecision(
            can_claim=True,
            domain=domain,
            domain_policy_id=policy.id,
        )

    def _domain_policy(self, domain: str) -> DomainDeliveryPolicy | None:
        return self.db.scalar(
            select(DomainDeliveryPolicy)
            .where(DomainDeliveryPolicy.domain == domain)
            .limit(1)
        )

    def _active_domain_policy(self, domain: str) -> DomainDeliveryPolicy | None:
        policy = self._domain_policy(domain)
        if not policy:
            return None
        if policy.paused_until and policy.paused_until > datetime.utcnow():
            return None
        return policy

    def _configured_route_type(self, email_provider: str) -> DeliveryRouteType | None:
        if email_provider == 'smtp':
            return DeliveryRouteType.smtp_relay
        try:
            return DeliveryRouteType(email_provider)
        except ValueError:
            return None

    def _domain_authentication_plan(
        self,
        domain: str,
        payload: DomainAuthenticationPlanRequest,
    ) -> DomainAuthenticationPlanRead:
        normalized_domain = domain.lower()
        selector = payload.dkim_selector.strip().lower() or 'ee1'
        bounce_subdomain = payload.bounce_subdomain.strip().lower() or 'bounces'
        bounce_domain = f'{bounce_subdomain}.{normalized_domain}'
        dkim_public_key = payload.dkim_public_key or 'REPLACE_WITH_DKIM_PUBLIC_KEY'
        mta_hostname = payload.mta_hostname or f'smtp.{normalized_domain}'
        records = [
            DomainAuthenticationDnsRecord(
                record_type='TXT',
                name=f'{selector}._domainkey.{normalized_domain}',
                value=f'v=DKIM1; k=rsa; p={dkim_public_key}',
                purpose='Authorize Email Engine managed SMTP DKIM signing for this domain.',
            ),
            DomainAuthenticationDnsRecord(
                record_type='TXT',
                name=normalized_domain,
                value='v=spf1 mx -all',
                purpose='Authorize the domain MX path for managed SMTP staging sends.',
            ),
            DomainAuthenticationDnsRecord(
                record_type='TXT',
                name=f'_dmarc.{normalized_domain}',
                value=f'v=DMARC1; p={payload.dmarc_policy}; rua=mailto:dmarc@{normalized_domain}',
                purpose='Publish DMARC policy and aggregate-report destination.',
            ),
            DomainAuthenticationDnsRecord(
                record_type='MX',
                name=bounce_domain,
                value=f'10 {mta_hostname}',
                purpose='Route DSN and bounce handling traffic for the managed SMTP return path.',
            ),
            DomainAuthenticationDnsRecord(
                record_type='MX',
                name=normalized_domain,
                value=f'10 {mta_hostname}',
                purpose='Point staging-domain mail routing at the managed SMTP host.',
                required=False,
            ),
            DomainAuthenticationDnsRecord(
                record_type='A',
                name=mta_hostname,
                value='REPLACE_WITH_MTA_IPV4',
                purpose='Map the staging MTA hostname to its server IP.',
                required=False,
            ),
        ]
        return DomainAuthenticationPlanRead(
            domain=normalized_domain,
            dkim_selector=selector,
            bounce_domain=bounce_domain,
            mta_hostname=mta_hostname,
            dmarc_policy=payload.dmarc_policy,
            dns_records=records,
            next_steps=[
                'Publish required DNS records on the staging domain.',
                'Configure Postfix DKIM signing with the matching private key and selector.',
                'Send a low-volume seed message through the managed SMTP route.',
                'Post a signed managed-SMTP feedback smoke event and confirm analytics update.',
                'Move DMARC policy from none only after alignment and bounce handling are verified.',
            ],
        )

    def _domain_for_record(self, record: EmailSendRecord) -> str | None:
        if '@' not in record.to_email:
            return None
        return record.to_email.rsplit('@', 1)[-1].lower()

    def _recent_domain_attempt_count(self, domain: str, seconds: int) -> int:
        cutoff = datetime.utcnow() - timedelta(seconds=seconds)
        return self.db.scalar(
            select(func.count())
            .select_from(DeliveryAttempt)
            .join(EmailSendRecord, DeliveryAttempt.send_record_id == EmailSendRecord.id)
            .where(func.lower(EmailSendRecord.to_email).like(f'%@{domain}'))
            .where(DeliveryAttempt.started_at >= cutoff)
            .where(DeliveryAttempt.status.in_(['submitting', 'submitted']))
        ) or 0

    def _active_domain_attempt_count(self, domain: str) -> int:
        return self.db.scalar(
            select(func.count())
            .select_from(DeliveryAttempt)
            .join(EmailSendRecord, DeliveryAttempt.send_record_id == EmailSendRecord.id)
            .where(func.lower(EmailSendRecord.to_email).like(f'%@{domain}'))
            .where(DeliveryAttempt.status == 'submitting')
        ) or 0
