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
    available_count: int = 0


@dataclass
class MtaPoolSelection:
    pool: MtaIpPool | None
    source: str
    rule_name: str | None = None
    rule_source: str | None = None
    preferred_providers: list[str] | None = None
    provider_preference_mode: str = 'strict'


class ManagedSmtpRoutingService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def resolve(self, payload: ManagedSmtpRouteResolveRequest) -> ManagedSmtpRouteResolutionRead:
        sender_domain = self._normalized_domain(payload.from_domain)
        recipient_domain = self._normalized_domain(payload.recipient_domain)
        domain = sender_domain or recipient_domain
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

        pool_selection = self._selected_pool(
            payload.ip_pool_id,
            policy,
            route,
            sender_domain=sender_domain,
            recipient_domain=recipient_domain,
            send_type=payload.send_type,
        )
        pool = pool_selection.pool
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

        selection = self._healthy_node_for_pool(
            pool.id,
            preferred_providers=pool_selection.preferred_providers,
        )
        fallback_used = False
        fallback_provider = None
        fallback_node = None
        if (
            not selection.node
            and pool_selection.preferred_providers
            and pool_selection.provider_preference_mode == 'fallback_allowed'
        ):
            fallback_selection = self._healthy_node_for_pool(pool.id, preferred_providers=None)
            if fallback_selection.node and fallback_selection.provider:
                selection = fallback_selection
                fallback_used = True
                fallback_provider = fallback_selection.provider.provider.value
                fallback_node = fallback_selection.node.name
        capacity = self._pool_capacity(pool, selection)
        if not capacity['ok']:
            return self._blocked(
                'POOL_CAPACITY_EXHAUSTED',
                'The selected MTA IP pool does not have enough healthy node capacity.',
                domain=domain,
                ip_pool_id=str(pool.id),
                preferred_providers=pool_selection.preferred_providers or [],
                candidate_count=selection.candidate_count,
                available_node_count=selection.available_count,
                required_available_node_count=capacity['required_available_node_count'],
                skipped_nodes=selection.skipped,
            )
        node = selection.node
        provider = selection.provider
        if not node or not provider:
            preference_block_details = self._provider_preference_block_details(
                pool.id,
                pool_selection.preferred_providers,
                selection,
            )
            return self._blocked(
                'NO_HEALTHY_MTA_NODE',
                'No active MTA node with passing readiness is available for this pool.',
                domain=domain,
                ip_pool_id=str(pool.id),
                preferred_providers=pool_selection.preferred_providers or [],
                candidate_count=selection.candidate_count,
                skipped_nodes=selection.skipped,
                **preference_block_details,
            )

        metadata = policy.metadata_json or {}
        authentication = metadata.get('domain_authentication')
        dkim_key = metadata.get('dkim_key')
        route_read = ManagedSmtpResolvedRoute(
            domain=domain,
            send_type=payload.send_type,
            sender_domain=sender_domain,
            recipient_domain=recipient_domain,
            decision_basis='sender_domain_policy' if sender_domain else 'recipient_domain_policy',
            routing_rule_name=pool_selection.rule_name,
            routing_rule_source=pool_selection.rule_source,
            routing_rule_pool_source=pool_selection.source,
            routing_rule_provider_preference=pool_selection.preferred_providers or [],
            routing_rule_provider_preference_mode=pool_selection.provider_preference_mode,
            preferred_providers=pool_selection.preferred_providers or [],
            provider_preference_fallback_used=fallback_used,
            provider_preference_fallback_provider=fallback_provider,
            provider_preference_fallback_node_name=fallback_node,
            delivery_route_id=route.id,
            delivery_route_name=route.name,
            domain_policy_id=policy.id,
            ip_pool_id=pool.id,
            ip_pool_name=pool.name,
            ip_pool_type=pool.pool_type,
            ip_pool_selection_source=pool_selection.source,
            mta_node_id=node.id,
            mta_node_name=node.name,
            mta_node_selection_membership_id=selection.membership.id
            if selection.membership
            else None,
            mta_node_selection_priority=selection.membership.priority if selection.membership else None,
            mta_node_selection_weight=selection.membership.weight if selection.membership else None,
            mta_node_candidate_count=selection.candidate_count,
            mta_pool_available_node_count=selection.available_count,
            mta_pool_required_available_node_count=capacity['required_available_node_count'],
            mta_pool_capacity_status='ok',
            mta_node_skipped_count=len(selection.skipped),
            mta_node_skipped_nodes=selection.skipped,
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
                'decision_basis': 'sender_domain_policy' if sender_domain else 'recipient_domain_policy',
                'send_type': payload.send_type,
                'ip_pool_selection_source': pool_selection.source,
                'routing_rule_name': pool_selection.rule_name,
                'routing_rule_source': pool_selection.rule_source,
                'routing_rule_pool_source': pool_selection.source,
                'routing_rule_provider_preference': pool_selection.preferred_providers or [],
                'routing_rule_provider_preference_mode': pool_selection.provider_preference_mode,
                'preferred_providers': pool_selection.preferred_providers or [],
                'provider_preference_fallback_used': fallback_used,
                'provider_preference_fallback_provider': fallback_provider,
                'provider_preference_fallback_node_name': fallback_node,
                'selection': {
                    'candidate_count': selection.candidate_count,
                    'available_node_count': selection.available_count,
                    'required_available_node_count': capacity['required_available_node_count'],
                    'capacity_status': 'ok',
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
        sender_domain: str | None,
        recipient_domain: str | None,
        send_type: str | None,
    ) -> MtaPoolSelection:
        if requested_pool_id:
            return MtaPoolSelection(self.db.get(MtaIpPool, requested_pool_id), 'request')
        rule_selection = self._routing_rule_pool_selection(
            policy,
            route,
            sender_domain=sender_domain,
            recipient_domain=recipient_domain,
            send_type=send_type,
        )
        if rule_selection:
            return rule_selection
        policy_pool_id = self._metadata_uuid(policy.metadata_json, 'mta_ip_pool_id')
        route_pool_id = self._metadata_uuid(route.config, 'mta_ip_pool_id')
        pool_id = policy_pool_id or route_pool_id
        if pool_id:
            return MtaPoolSelection(
                self.db.get(MtaIpPool, pool_id),
                'domain_policy' if policy_pool_id else 'delivery_route',
            )
        pool_name = self._metadata_value(policy.metadata_json, 'ip_pool') or self._metadata_value(
            route.config,
            'ip_pool',
        )
        if not pool_name:
            return MtaPoolSelection(None, 'missing')
        pool = self.db.scalar(select(MtaIpPool).where(MtaIpPool.name == pool_name).limit(1))
        return MtaPoolSelection(
            pool,
            'domain_policy' if self._metadata_value(policy.metadata_json, 'ip_pool') else 'delivery_route',
        )

    def _healthy_node_for_pool(
        self,
        pool_id: UUID,
        preferred_providers: list[str] | None = None,
    ) -> MtaNodeSelection:
        provider_preference = [provider.lower() for provider in preferred_providers or []]
        memberships = list(
            self.db.scalars(
                select(MtaIpPoolNode)
                .where(MtaIpPoolNode.ip_pool_id == pool_id)
                .where(MtaIpPoolNode.status == MtaOperationalStatus.active)
                .order_by(MtaIpPoolNode.priority.asc(), MtaIpPoolNode.created_at.desc())
            ).all()
        )
        skipped: list[dict[str, object]] = []
        selected_node = None
        selected_provider = None
        selected_membership = None
        available_count = 0
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
            if provider_preference and provider.provider.value.lower() not in provider_preference:
                skipped.append({**candidate, 'reason': 'provider_not_preferred'})
                continue
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
            available_count += 1
            if not selected_node:
                selected_node = node
                selected_provider = provider
                selected_membership = membership
        return MtaNodeSelection(
            selected_node,
            selected_provider,
            selected_membership,
            len(memberships),
            skipped,
            available_count,
        )

    def _pool_capacity(self, pool: MtaIpPool, selection: MtaNodeSelection) -> dict[str, object]:
        required_available = self._metadata_int(
            pool.metadata_json,
            'min_available_nodes',
        ) or self._metadata_int(pool.metadata_json, 'required_available_nodes')
        if not required_available:
            return {'ok': True, 'required_available_node_count': None}
        return {
            'ok': selection.available_count >= required_available,
            'required_available_node_count': required_available,
        }

    def _provider_preference_block_details(
        self,
        pool_id: UUID,
        preferred_providers: list[str] | None,
        selection: MtaNodeSelection,
    ) -> dict[str, object]:
        if not preferred_providers:
            return {}
        provider_blocked = any(
            candidate.get('reason') == 'provider_not_preferred'
            for candidate in selection.skipped
        )
        if not provider_blocked:
            return {}
        fallback = self._healthy_node_for_pool(pool_id, preferred_providers=None)
        details: dict[str, object] = {
            'provider_preference_blocked': True,
            'provider_preference_fallback_available': bool(fallback.node and fallback.provider),
            'provider_preference_fallback_candidate_count': fallback.candidate_count,
            'provider_preference_fallback_skipped_nodes': fallback.skipped,
        }
        if fallback.node and fallback.provider:
            details.update(
                {
                    'provider_preference_fallback_provider': fallback.provider.provider.value,
                    'provider_preference_fallback_provider_account_id': str(fallback.provider.id),
                    'provider_preference_fallback_mta_node_id': str(fallback.node.id),
                    'provider_preference_fallback_mta_node_name': fallback.node.name,
                    'provider_preference_fallback_hostname': fallback.node.hostname,
                    'provider_preference_fallback_membership_id': str(fallback.membership.id)
                    if fallback.membership
                    else None,
                }
            )
        return details

    def _routing_rule_pool_selection(
        self,
        policy: DomainDeliveryPolicy,
        route: DeliveryRoute,
        sender_domain: str | None,
        recipient_domain: str | None,
        send_type: str | None,
    ) -> MtaPoolSelection | None:
        for source, metadata in (
            ('domain_policy_rule', policy.metadata_json),
            ('delivery_route_rule', route.config),
        ):
            for rule in self._routing_rules(metadata):
                if not self._routing_rule_matches(
                    rule,
                    sender_domain=sender_domain,
                    recipient_domain=recipient_domain,
                    send_type=send_type,
                ):
                    continue
                pool = self._pool_from_rule(rule)
                if not pool:
                    continue
                preferred_providers = self._string_list(
                    rule.get('preferred_providers') or rule.get('provider_preferences')
                )
                rule_name = self._rule_name(rule)
                return MtaPoolSelection(
                    pool=pool,
                    source=source,
                    rule_name=rule_name,
                    rule_source=source,
                    preferred_providers=preferred_providers,
                    provider_preference_mode=self._provider_preference_mode(
                        rule.get('provider_preference_mode')
                    ),
                )
        return None

    def _routing_rules(self, metadata: object) -> list[dict[str, object]]:
        if not isinstance(metadata, dict):
            return []
        rules = metadata.get('routing_rules')
        if not isinstance(rules, list):
            return []
        normalized_rules = [rule for rule in rules if isinstance(rule, dict)]
        return sorted(
            normalized_rules,
            key=lambda rule: int(rule.get('priority') or 100),
        )

    def _routing_rule_matches(
        self,
        rule: dict[str, object],
        sender_domain: str | None,
        recipient_domain: str | None,
        send_type: str | None,
    ) -> bool:
        if rule.get('enabled') is False:
            return False
        return (
            self._rule_value_matches(rule.get('send_types'), send_type)
            and self._rule_value_matches(rule.get('sender_domains'), sender_domain)
            and self._rule_value_matches(rule.get('recipient_domains'), recipient_domain)
        )

    def _pool_from_rule(self, rule: dict[str, object]) -> MtaIpPool | None:
        pool_id = (
            self._uuid_from_value(rule.get('mta_ip_pool_id'))
            or self._uuid_from_value(rule.get('ip_pool_id'))
        )
        if pool_id:
            return self.db.get(MtaIpPool, pool_id)
        pool_name = rule.get('ip_pool') or rule.get('ip_pool_name')
        if pool_name:
            return self.db.scalar(select(MtaIpPool).where(MtaIpPool.name == str(pool_name)).limit(1))
        return None

    def _rule_name(self, rule: dict[str, object]) -> str | None:
        value = rule.get('name') or rule.get('id')
        return str(value) if value else None

    def _uuid_from_value(self, value: object) -> UUID | None:
        if not value:
            return None
        try:
            return UUID(str(value))
        except ValueError:
            return None

    def _string_list(self, value: object) -> list[str]:
        if isinstance(value, str):
            return [value]
        if isinstance(value, list):
            return [str(item) for item in value if item]
        return []

    def _provider_preference_mode(self, value: object) -> str:
        mode = str(value or 'strict').strip().lower()
        if mode in {'fallback_allowed', 'allow_fallback', 'fallback'}:
            return 'fallback_allowed'
        return 'strict'

    def _rule_value_matches(self, configured: object, actual: str | None) -> bool:
        values = [value.lower() for value in self._string_list(configured)]
        if not values:
            return True
        if '*' in values:
            return True
        if not actual:
            return False
        return actual.lower() in values

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

    def _metadata_int(self, metadata: object, key: str) -> int | None:
        value = self._metadata_value(metadata, key)
        if value is None:
            return None
        try:
            return int(value)
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
