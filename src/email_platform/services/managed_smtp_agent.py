import hashlib
import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from email_platform.models.entities import (
    DomainDeliveryPolicy,
    MtaIpPool,
    MtaIpPoolNode,
    MtaNode,
    MtaNodeEvent,
    MtaProviderAccount,
)
from email_platform.schemas.contracts import (
    ManagedSmtpReadinessCheckCreate,
    MtaNodeEventCreate,
    MtaNodeHeartbeatRequest,
    MtaNodeRuntimeConfigRead,
    MtaNodeRuntimeDomainConfig,
    MtaNodeRuntimePoolConfig,
)
from email_platform.services.managed_smtp_readiness import ManagedSmtpReadinessService


class ManagedSmtpAgentError(ValueError):
    pass


class ManagedSmtpAgentService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def runtime_config(self, node_id: UUID) -> MtaNodeRuntimeConfigRead | None:
        node = self.db.get(MtaNode, node_id)
        if not node:
            return None
        provider = self.db.get(MtaProviderAccount, node.provider_account_id)
        if not provider:
            raise ManagedSmtpAgentError('MTA provider account not found for node')
        pools = self._pool_configs(node)
        domains = self._domain_configs([pool.ip_pool_id for pool in pools])
        version = self._config_version(node, provider, pools, domains)
        return MtaNodeRuntimeConfigRead(
            node=node,
            provider_account=provider,
            config_version=version,
            submission_host=node.submission_host or node.hostname,
            submission_port=node.submission_port,
            auth_secret_ref=node.auth_secret_ref,
            pools=pools,
            domains=domains,
            status=node.status,
            generated_at=datetime.utcnow(),
        )

    def heartbeat(
        self,
        node_id: UUID,
        payload: MtaNodeHeartbeatRequest,
    ):
        node = self.db.get(MtaNode, node_id)
        if not node:
            return None
        normalized_status = self._readiness_status(payload.status)
        result_json = {
            **payload.payload_json,
            'queue_depth': payload.queue_depth,
            'deferred_count': payload.deferred_count,
            'active_count': payload.active_count,
            'config_version': payload.config_version,
            'applied_config_version': payload.applied_config_version,
        }
        check = ManagedSmtpReadinessService(self.db).create(
            ManagedSmtpReadinessCheckCreate(
                source='mta_agent',
                check_type='heartbeat',
                status=normalized_status,
                host=node.hostname,
                summary=payload.summary or f'MTA agent heartbeat {normalized_status}',
                result_json={key: value for key, value in result_json.items() if value is not None},
            )
        )
        node.last_readiness_at = check.created_at
        node.metadata_json = {
            **(node.metadata_json or {}),
            'agent_last_heartbeat_at': check.created_at.isoformat(),
            'agent_last_status': normalized_status,
            'agent_config_version': payload.config_version,
            'agent_applied_config_version': payload.applied_config_version,
        }
        self.db.commit()
        self.db.refresh(check)
        return check

    def create_event(self, node_id: UUID, payload: MtaNodeEventCreate) -> MtaNodeEvent | None:
        node = self.db.get(MtaNode, node_id)
        if not node:
            return None
        event = MtaNodeEvent(
            mta_node_id=node.id,
            event_type=payload.event_type.strip(),
            severity=self._event_severity(payload.severity),
            summary=payload.summary.strip()[:500] if payload.summary else None,
            payload_json=payload.payload_json,
            observed_at=payload.observed_at or datetime.utcnow(),
            received_at=datetime.utcnow(),
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def _pool_configs(self, node: MtaNode) -> list[MtaNodeRuntimePoolConfig]:
        memberships = list(
            self.db.scalars(
                select(MtaIpPoolNode)
                .where(MtaIpPoolNode.mta_node_id == node.id)
                .order_by(MtaIpPoolNode.priority.asc(), MtaIpPoolNode.created_at.desc())
            ).all()
        )
        configs: list[MtaNodeRuntimePoolConfig] = []
        for membership in memberships:
            pool = self.db.get(MtaIpPool, membership.ip_pool_id)
            if not pool:
                continue
            configs.append(
                MtaNodeRuntimePoolConfig(
                    ip_pool_id=pool.id,
                    name=pool.name,
                    pool_type=pool.pool_type,
                    status=pool.status,
                    membership_id=membership.id,
                    membership_status=membership.status,
                    priority=membership.priority,
                    weight=membership.weight,
                )
            )
        return configs

    def _domain_configs(self, pool_ids: list[UUID]) -> list[MtaNodeRuntimeDomainConfig]:
        pool_id_values = {str(pool_id) for pool_id in pool_ids}
        policies = list(self.db.scalars(select(DomainDeliveryPolicy)).all())
        configs: list[MtaNodeRuntimeDomainConfig] = []
        for policy in policies:
            metadata = policy.metadata_json or {}
            pool_id = str(metadata.get('mta_ip_pool_id') or '')
            if pool_id not in pool_id_values:
                continue
            authentication = self._mapping(metadata.get('domain_authentication'))
            dkim_key = self._mapping(metadata.get('dkim_key'))
            verification = self._mapping(metadata.get('domain_authentication_verification'))
            configs.append(
                MtaNodeRuntimeDomainConfig(
                    domain=policy.domain,
                    route_id=policy.route_id,
                    ip_pool_id=UUID(pool_id),
                    bounce_domain=self._str_or_none(authentication.get('bounce_domain')),
                    dkim_selector=self._str_or_none(dkim_key.get('selector')),
                    dkim_key_ref=self._str_or_none(dkim_key.get('key_ref')),
                    warmup_stage=policy.warmup_stage,
                    max_per_minute=policy.max_per_minute,
                    max_concurrent=policy.max_concurrent,
                    verified=bool(verification.get('verified')),
                )
            )
        return configs

    def _config_version(
        self,
        node: MtaNode,
        provider: MtaProviderAccount,
        pools: list[MtaNodeRuntimePoolConfig],
        domains: list[MtaNodeRuntimeDomainConfig],
    ) -> str:
        payload = {
            'node': {
                'id': str(node.id),
                'status': getattr(node.status, 'value', str(node.status)),
                'submission_host': node.submission_host or node.hostname,
                'submission_port': node.submission_port,
                'auth_secret_ref': node.auth_secret_ref,
                'updated_at': node.updated_at.isoformat() if node.updated_at else None,
            },
            'provider': {
                'id': str(provider.id),
                'status': getattr(provider.status, 'value', str(provider.status)),
                'updated_at': provider.updated_at.isoformat() if provider.updated_at else None,
            },
            'pools': [pool.model_dump(mode='json') for pool in pools],
            'domains': [domain.model_dump(mode='json') for domain in domains],
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode('utf-8')
        return hashlib.sha256(encoded).hexdigest()[:24]

    @staticmethod
    def _readiness_status(status: str) -> str:
        normalized = status.strip().lower()
        if normalized in {'ok', 'healthy', 'ready'}:
            return 'ok'
        if normalized in {'warning', 'degraded'}:
            return 'warning'
        return 'failed'

    @staticmethod
    def _event_severity(severity: str) -> str:
        normalized = severity.strip().lower()
        return normalized if normalized in {'debug', 'info', 'warning', 'error', 'critical'} else 'info'

    @staticmethod
    def _mapping(value: object) -> dict[str, object]:
        return dict(value) if isinstance(value, dict) else {}

    @staticmethod
    def _str_or_none(value: object) -> str | None:
        return str(value) if value else None
