from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from email_platform.models.entities import (
    DeliveryRoute,
    DeliveryRouteStatus,
    DeliveryRouteType,
    DomainDeliveryPolicy,
    MtaIpPool,
    MtaIpPoolNode,
    MtaNode,
    MtaOperationalStatus,
    MtaProviderAccount,
)
from email_platform.schemas.contracts import (
    ManagedSmtpBootstrapProfileRead,
    ManagedSmtpBootstrapRead,
    ManagedSmtpBootstrapRequest,
    ManagedSmtpRouteResolveRequest,
)
from email_platform.services.managed_smtp_routing import ManagedSmtpRoutingService


BOOTSTRAP_PROFILES: dict[str, dict[str, object]] = {
    'scaleway-poc': {
        'provider_account_name': 'scaleway-poc',
        'provider': 'scaleway',
        'provider_account_ref': 'email-engine-mta-poc',
        'region': 'fr-par',
        'port25_status': 'approved',
        'rdns_status': 'configured',
        'node_name': 'mta-002',
        'hostname': 'mta-002.email-engine.app',
        'public_ipv4': '212.47.236.69',
        'submission_host': 'mta-002.email-engine.app',
        'submission_port': 587,
        'auth_secret_ref': 'secret/mta/scaleway/mta-002/submission',
        'ip_pool_name': 'scaleway-internal-test',
        'ip_pool_type': 'internal_test',
        'route_name': 'managed-smtp-scaleway-primary',
        'domain': 'email-engine.app',
        'bounce_domain': 'returns-scaleway.email-engine.app',
        'dkim_selector': 'ee2',
        'dkim_key_ref': 'mta://mta-002.email-engine.app/email-engine.app/ee2',
        'warmup_stage': 'stage_1',
        'max_per_minute': 10,
        'max_concurrent': 2,
        'activate_inventory': True,
        'mark_domain_verified': True,
        'metadata_json': {
            'bootstrap_profile': 'scaleway-poc',
            'provider_project': 'email-engine-mta-poc',
            'seed_mailbox': 'davidtesterwex@gmail.com',
            'first_seed_delivered': True,
            'first_seed_delivered_at': '2026-06-18T15:20:00-07:00',
        },
    },
}


def list_bootstrap_profiles() -> list[ManagedSmtpBootstrapProfileRead]:
    return [
        _profile_read(name, values)
        for name, values in sorted(BOOTSTRAP_PROFILES.items(), key=lambda item: item[0])
    ]


def bootstrap_profile_payload(name: str) -> ManagedSmtpBootstrapRequest | None:
    values = BOOTSTRAP_PROFILES.get(name)
    if not values:
        return None
    return ManagedSmtpBootstrapRequest(**values)


def _profile_read(name: str, values: dict[str, object]) -> ManagedSmtpBootstrapProfileRead:
    return ManagedSmtpBootstrapProfileRead(
        name=name,
        provider=values['provider'],
        provider_account_name=str(values['provider_account_name']),
        node_name=str(values['node_name']),
        hostname=str(values['hostname']),
        public_ipv4=values.get('public_ipv4'),
        route_name=str(values['route_name']),
        ip_pool_name=str(values['ip_pool_name']),
        domain=str(values['domain']),
        bounce_domain=values.get('bounce_domain'),
        dkim_selector=values.get('dkim_selector'),
        port25_status=str(values.get('port25_status') or 'unknown'),
        rdns_status=str(values.get('rdns_status') or 'unknown'),
        activate_inventory=bool(values.get('activate_inventory')),
        mark_domain_verified=bool(values.get('mark_domain_verified')),
        metadata_json=dict(values.get('metadata_json') or {}),
    )


class ManagedSmtpBootstrapService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def bootstrap(self, payload: ManagedSmtpBootstrapRequest) -> ManagedSmtpBootstrapRead:
        provider_account = self._provider_account(payload)
        node = self._node(payload, provider_account)
        ip_pool = self._ip_pool(payload)
        pool_node = self._pool_node(ip_pool, node, payload)
        self.db.flush()
        delivery_route = self._delivery_route(payload, ip_pool)
        domain_policy = self._domain_policy(payload, delivery_route, ip_pool)
        self.db.commit()
        for item in (provider_account, node, ip_pool, pool_node, delivery_route, domain_policy):
            self.db.refresh(item)

        route_resolution = ManagedSmtpRoutingService(self.db).resolve(
            ManagedSmtpRouteResolveRequest(
                from_domain=domain_policy.domain,
                route_id=delivery_route.id,
                ip_pool_id=ip_pool.id,
                send_type='internal_test',
            )
        )
        return ManagedSmtpBootstrapRead(
            provider_account=provider_account,
            node=node,
            ip_pool=ip_pool,
            pool_node=pool_node,
            delivery_route=delivery_route,
            domain_policy=domain_policy,
            route_resolution=route_resolution,
            next_steps=self._next_steps(payload, route_resolution.ok),
        )

    def _provider_account(self, payload: ManagedSmtpBootstrapRequest) -> MtaProviderAccount:
        account = self.db.scalar(
            select(MtaProviderAccount)
            .where(MtaProviderAccount.name == payload.provider_account_name)
            .limit(1)
        )
        if not account:
            account = MtaProviderAccount(
                name=payload.provider_account_name,
                provider=payload.provider,
            )
            self.db.add(account)
        account.provider = payload.provider
        account.account_ref = payload.provider_account_ref
        account.region = payload.region
        account.abuse_contact_email = payload.abuse_contact_email
        account.support_case_ref = payload.support_case_ref
        account.port25_status = payload.port25_status
        account.rdns_status = payload.rdns_status
        account.secret_ref = payload.provider_secret_ref
        account.status = (
            MtaOperationalStatus.active
            if payload.activate_inventory
            else MtaOperationalStatus.pending
        )
        account.metadata_json = {
            **(account.metadata_json or {}),
            **payload.metadata_json,
            'bootstrap_updated_at': datetime.utcnow().isoformat(),
        }
        return account

    def _node(
        self,
        payload: ManagedSmtpBootstrapRequest,
        provider_account: MtaProviderAccount,
    ) -> MtaNode:
        node = self.db.scalar(
            select(MtaNode).where(MtaNode.hostname == payload.hostname.lower()).limit(1)
        )
        if not node:
            node = MtaNode(
                provider_account_id=provider_account.id,
                name=payload.node_name,
                hostname=payload.hostname.lower(),
            )
            self.db.add(node)
        node.provider_account = provider_account
        node.name = payload.node_name
        node.hostname = payload.hostname.lower()
        node.public_ipv4 = payload.public_ipv4
        node.submission_host = payload.submission_host or payload.hostname.lower()
        node.submission_port = payload.submission_port
        node.auth_secret_ref = payload.auth_secret_ref
        node.status = (
            MtaOperationalStatus.active
            if payload.activate_inventory
            else MtaOperationalStatus.pending
        )
        node.metadata_json = {
            **(node.metadata_json or {}),
            'bootstrap_updated_at': datetime.utcnow().isoformat(),
        }
        return node

    def _ip_pool(self, payload: ManagedSmtpBootstrapRequest) -> MtaIpPool:
        pool = self.db.scalar(
            select(MtaIpPool).where(MtaIpPool.name == payload.ip_pool_name).limit(1)
        )
        if not pool:
            pool = MtaIpPool(name=payload.ip_pool_name, pool_type=payload.ip_pool_type)
            self.db.add(pool)
        pool.pool_type = payload.ip_pool_type
        pool.status = (
            MtaOperationalStatus.active
            if payload.activate_inventory
            else MtaOperationalStatus.paused
        )
        pool.description = 'First managed SMTP bootstrap pool'
        pool.metadata_json = {
            **(pool.metadata_json or {}),
            'bootstrap_updated_at': datetime.utcnow().isoformat(),
        }
        return pool

    def _pool_node(
        self,
        ip_pool: MtaIpPool,
        node: MtaNode,
        payload: ManagedSmtpBootstrapRequest,
    ) -> MtaIpPoolNode:
        pool_node = self.db.scalar(
            select(MtaIpPoolNode)
            .where(MtaIpPoolNode.ip_pool == ip_pool)
            .where(MtaIpPoolNode.mta_node == node)
            .limit(1)
        )
        if not pool_node:
            pool_node = MtaIpPoolNode(ip_pool=ip_pool, mta_node=node)
            self.db.add(pool_node)
        pool_node.priority = 100
        pool_node.weight = 100
        pool_node.status = (
            MtaOperationalStatus.active
            if payload.activate_inventory
            else MtaOperationalStatus.paused
        )
        pool_node.metadata_json = {
            **(pool_node.metadata_json or {}),
            'bootstrap_updated_at': datetime.utcnow().isoformat(),
        }
        return pool_node

    def _delivery_route(
        self,
        payload: ManagedSmtpBootstrapRequest,
        ip_pool: MtaIpPool,
    ) -> DeliveryRoute:
        route = self.db.scalar(
            select(DeliveryRoute).where(DeliveryRoute.name == payload.route_name).limit(1)
        )
        if not route:
            route = DeliveryRoute(
                name=payload.route_name,
                route_type=DeliveryRouteType.managed_smtp,
                priority=50,
                config={},
                metadata_json={},
            )
            self.db.add(route)
        route.route_type = DeliveryRouteType.managed_smtp
        route.status = DeliveryRouteStatus.active
        route.config = {
            **(route.config or {}),
            'mta_ip_pool_id': str(ip_pool.id),
            'ip_pool': ip_pool.name,
            'managed_smtp_bootstrap': True,
        }
        route.metadata_json = {
            **(route.metadata_json or {}),
            'bootstrap_updated_at': datetime.utcnow().isoformat(),
        }
        return route

    def _domain_policy(
        self,
        payload: ManagedSmtpBootstrapRequest,
        delivery_route: DeliveryRoute,
        ip_pool: MtaIpPool,
    ) -> DomainDeliveryPolicy:
        normalized_domain = payload.domain.lower()
        policy = self.db.scalar(
            select(DomainDeliveryPolicy)
            .where(DomainDeliveryPolicy.domain == normalized_domain)
            .limit(1)
        )
        if not policy:
            policy = DomainDeliveryPolicy(domain=normalized_domain, metadata_json={})
            self.db.add(policy)
        policy.route = delivery_route
        policy.max_per_minute = payload.max_per_minute
        policy.max_concurrent = payload.max_concurrent
        policy.warmup_stage = payload.warmup_stage
        metadata = {
            **(policy.metadata_json or {}),
            **payload.metadata_json,
            'mta_ip_pool_id': str(ip_pool.id),
            'ip_pool': ip_pool.name,
            'domain_authentication': {
                **self._mapping((policy.metadata_json or {}).get('domain_authentication')),
                'bounce_domain': payload.bounce_domain or f'bounces.{normalized_domain}',
                'mta_hostname': payload.hostname.lower(),
            },
            'bootstrap_updated_at': datetime.utcnow().isoformat(),
        }
        if payload.dkim_selector or payload.dkim_key_ref:
            metadata['dkim_key'] = {
                **self._mapping((policy.metadata_json or {}).get('dkim_key')),
                'selector': payload.dkim_selector,
                'key_ref': payload.dkim_key_ref,
            }
        if payload.mark_domain_verified:
            metadata['domain_authentication_verification'] = {
                'verified': True,
                'source': 'managed_smtp_bootstrap',
                'verified_at': datetime.utcnow().isoformat(),
            }
        policy.metadata_json = metadata
        return policy

    def _next_steps(self, payload: ManagedSmtpBootstrapRequest, route_ready: bool) -> list[str]:
        steps: list[str] = []
        if payload.port25_status != 'approved':
            steps.append('Verify provider outbound TCP port 25 approval.')
        if payload.rdns_status != 'configured':
            steps.append('Configure PTR/rDNS for the MTA public IPv4.')
        if not payload.mark_domain_verified:
            steps.append('Publish and verify SPF, DKIM, DMARC, and bounce-domain MX records.')
        if not payload.activate_inventory:
            steps.append(
                'Activate provider account, node, pool, and pool-node membership after deployment.'
            )
        if not route_ready:
            steps.append('Run MTA smoke/readiness checks until route resolution returns ok.')
        if route_ready:
            steps.append('Run the first managed SMTP seed send runbook.')
        return steps

    @staticmethod
    def _mapping(value: object) -> dict[str, object]:
        return dict(value) if isinstance(value, dict) else {}
