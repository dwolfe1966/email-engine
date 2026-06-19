from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from email_platform.models.entities import (
    DeliveryRoute,
    DeliveryRouteStatus,
    DeliveryRouteType,
    DomainDeliveryPolicy,
    ManagedSmtpReadinessCheck,
    MtaIpPool,
    MtaIpPoolNode,
    MtaNode,
    MtaOperationalStatus,
    MtaProviderAccount,
)
from email_platform.schemas.contracts import (
    ManagedSmtpResolvedRoute,
    ManagedSmtpRouteBlockReason,
    ManagedSmtpRouteResolutionRead,
    ManagedSmtpRouteResolveRequest,
)


@dataclass
class MtaNodeSelection:
    node: MtaNode | None
    provider: MtaProviderAccount | None
    membership: MtaIpPoolNode | None
    candidate_count: int
    skipped: list[dict[str, object]]


class ManagedSmtpRoutingService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def resolve(self, payload: ManagedSmtpRouteResolveRequest) -> ManagedSmtpRouteResolutionRead:
        domain = self._normalized_domain(payload.from_domain or payload.recipient_domain)
        if not domain:
            return self._blocked(
                'DOMAIN_NOT_READY',
                'A from_domain or recipient_domain is required to resolve managed SMTP routing.',
            )

        policy = self._domain_policy(domain)
        if not policy:
            return self._blocked(
                'DOMAIN_NOT_READY',
                'No domain delivery policy exists for this domain.',
                domain=domain,
            )
        if policy.paused_until and policy.paused_until > datetime.utcnow():
            return self._blocked(
                'COMPLIANCE_HOLD',
                'The domain delivery policy is paused.',
                domain=domain,
                domain_policy_id=str(policy.id),
                paused_until=policy.paused_until.isoformat(),
            )
        if self._compliance_hold_active(policy):
            return self._blocked(
                'COMPLIANCE_HOLD',
                'The domain delivery policy has an active compliance hold.',
                domain=domain,
                domain_policy_id=str(policy.id),
            )
        if not self._domain_verified(policy):
            return self._blocked(
                'DOMAIN_NOT_READY',
                'Domain authentication has not been verified.',
                domain=domain,
                domain_policy_id=str(policy.id),
            )

        route = self._delivery_route(payload.route_id or policy.route_id)
        if not route or route.route_type != DeliveryRouteType.managed_smtp:
            return self._blocked(
                'ROUTE_PAUSED',
                'No managed SMTP delivery route is assigned to this domain.',
                domain=domain,
                domain_policy_id=str(policy.id),
            )
        if route.status != DeliveryRouteStatus.active:
            return self._blocked(
                'ROUTE_PAUSED',
                'The managed SMTP delivery route is not active.',
                domain=domain,
                route_id=str(route.id),
            )

        pool = self._selected_pool(payload.ip_pool_id, policy, route)
        if not pool:
            return self._blocked(
                'POOL_PAUSED',
                'No MTA IP pool is configured for this managed SMTP route.',
                domain=domain,
                route_id=str(route.id),
            )
        if pool.status != MtaOperationalStatus.active:
            return self._blocked(
                'POOL_PAUSED',
                'The selected MTA IP pool is not active.',
                domain=domain,
                ip_pool_id=str(pool.id),
                ip_pool_status=pool.status.value,
            )

        selection = self._healthy_node_for_pool(pool.id)
        node = selection.node
        provider = selection.provider
        if not node or not provider:
            return self._blocked(
                'NO_HEALTHY_MTA_NODE',
                'No active MTA node with passing readiness is available for this pool.',
                domain=domain,
                ip_pool_id=str(pool.id),
                candidate_count=selection.candidate_count,
                skipped_nodes=selection.skipped,
            )

        metadata = policy.metadata_json or {}
        authentication = metadata.get('domain_authentication')
        dkim_key = metadata.get('dkim_key')
        route_read = ManagedSmtpResolvedRoute(
            domain=domain,
            delivery_route_id=route.id,
            delivery_route_name=route.name,
            domain_policy_id=policy.id,
            ip_pool_id=pool.id,
            ip_pool_name=pool.name,
            ip_pool_type=pool.pool_type,
            mta_node_id=node.id,
            mta_node_name=node.name,
            provider_account_id=provider.id,
            provider=provider.provider,
            hostname=node.hostname,
            public_ipv4=node.public_ipv4,
            submission_host=node.submission_host or node.hostname,
            submission_port=node.submission_port,
            auth_secret_ref=node.auth_secret_ref,
            envelope_sender_domain=self._metadata_value(authentication, 'bounce_domain'),
            dkim_selector=self._metadata_value(dkim_key, 'selector'),
            telemetry_tags={
                'domain': domain,
                'route': route.name,
                'ip_pool': pool.name,
                'mta_node': node.name,
                'provider': provider.provider.value,
                'selection': {
                    'candidate_count': selection.candidate_count,
                    'membership_id': str(selection.membership.id) if selection.membership else None,
                    'priority': selection.membership.priority if selection.membership else None,
                    'weight': selection.membership.weight if selection.membership else None,
                    'skipped_nodes': selection.skipped,
                },
            },
        )
        return ManagedSmtpRouteResolutionRead(ok=True, route=route_read)

    def _domain_policy(self, domain: str) -> DomainDeliveryPolicy | None:
        return self.db.scalar(
            select(DomainDeliveryPolicy)
            .where(DomainDeliveryPolicy.domain == domain)
            .limit(1)
        )

    def _delivery_route(self, route_id: UUID | None) -> DeliveryRoute | None:
        if not route_id:
            return None
        return self.db.get(DeliveryRoute, route_id)

    def _selected_pool(
        self,
        requested_pool_id: UUID | None,
        policy: DomainDeliveryPolicy,
        route: DeliveryRoute,
    ) -> MtaIpPool | None:
        if requested_pool_id:
            return self.db.get(MtaIpPool, requested_pool_id)
        policy_pool_id = self._metadata_uuid(policy.metadata_json, 'mta_ip_pool_id')
        route_pool_id = self._metadata_uuid(route.config, 'mta_ip_pool_id')
        pool_id = policy_pool_id or route_pool_id
        if pool_id:
            return self.db.get(MtaIpPool, pool_id)
        pool_name = self._metadata_value(policy.metadata_json, 'ip_pool') or self._metadata_value(
            route.config,
            'ip_pool',
        )
        if not pool_name:
            return None
        return self.db.scalar(select(MtaIpPool).where(MtaIpPool.name == pool_name).limit(1))

    def _healthy_node_for_pool(
        self,
        pool_id: UUID,
    ) -> MtaNodeSelection:
        memberships = list(
            self.db.scalars(
                select(MtaIpPoolNode)
                .where(MtaIpPoolNode.ip_pool_id == pool_id)
                .where(MtaIpPoolNode.status == MtaOperationalStatus.active)
                .order_by(MtaIpPoolNode.priority.asc(), MtaIpPoolNode.created_at.desc())
            ).all()
        )
        skipped: list[dict[str, object]] = []
        for membership in memberships:
            node = self.db.get(MtaNode, membership.mta_node_id)
            candidate = {
                'membership_id': str(membership.id),
                'mta_node_id': str(membership.mta_node_id),
                'priority': membership.priority,
                'weight': membership.weight,
            }
            if not node:
                skipped.append({**candidate, 'reason': 'node_missing'})
                continue
            candidate.update({'node_name': node.name, 'hostname': node.hostname})
            if node.status != MtaOperationalStatus.active:
                skipped.append(
                    {**candidate, 'reason': 'node_not_active', 'node_status': node.status.value}
                )
                continue
            provider = self.db.get(MtaProviderAccount, node.provider_account_id)
            if not provider:
                skipped.append({**candidate, 'reason': 'provider_missing'})
                continue
            candidate.update({'provider': provider.provider.value, 'provider_account_id': str(provider.id)})
            if provider.status != MtaOperationalStatus.active:
                skipped.append(
                    {
                        **candidate,
                        'reason': 'provider_not_active',
                        'provider_status': provider.status.value,
                    }
                )
                continue
            if not self._latest_readiness_ok(node):
                skipped.append({**candidate, 'reason': 'readiness_not_ok'})
                continue
            return MtaNodeSelection(node, provider, membership, len(memberships), skipped)
        return MtaNodeSelection(None, None, None, len(memberships), skipped)

    def _latest_readiness_ok(self, node: MtaNode) -> bool:
        check = self.db.scalar(
            select(ManagedSmtpReadinessCheck)
            .where(ManagedSmtpReadinessCheck.host == node.hostname.lower())
            .order_by(ManagedSmtpReadinessCheck.created_at.desc())
            .limit(1)
        )
        return bool(check and check.status == 'ok')

    def _domain_verified(self, policy: DomainDeliveryPolicy) -> bool:
        metadata = policy.metadata_json or {}
        verification = metadata.get('domain_authentication_verification')
        return bool(isinstance(verification, dict) and verification.get('verified'))

    def _compliance_hold_active(self, policy: DomainDeliveryPolicy) -> bool:
        metadata = policy.metadata_json or {}
        hold = metadata.get('compliance_hold')
        return bool(isinstance(hold, dict) and hold.get('status') == 'active')

    def _metadata_uuid(self, metadata: object, key: str) -> UUID | None:
        value = self._metadata_value(metadata, key)
        if not value:
            return None
        try:
            return UUID(value)
        except ValueError:
            return None

    @staticmethod
    def _metadata_value(metadata: object, key: str) -> str | None:
        if not isinstance(metadata, dict):
            return None
        value = metadata.get(key)
        return str(value) if value else None

    @staticmethod
    def _normalized_domain(domain: str | None) -> str | None:
        if not domain:
            return None
        normalized = domain.strip().lower()
        if '@' in normalized:
            normalized = normalized.rsplit('@', 1)[-1]
        return normalized or None

    @staticmethod
    def _blocked(code: str, message: str, **details: object) -> ManagedSmtpRouteResolutionRead:
        return ManagedSmtpRouteResolutionRead(
            ok=False,
            reason=ManagedSmtpRouteBlockReason(
                code=code,
                message=message,
                details={key: value for key, value in details.items() if value is not None},
            ),
        )
