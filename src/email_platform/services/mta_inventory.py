import os
from collections import Counter
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from email_platform.core.settings import Settings
from email_platform.models.entities import (
    DeliveryRoute,
    DeliveryRouteType,
    DomainDeliveryPolicy,
    MtaIpPool,
    MtaIpPoolNode,
    MtaNode,
    MtaNodeEvent,
    MtaOperationalStatus,
    MtaProviderAccount,
)
from email_platform.schemas.contracts import (
    ManagedSmtpDeploymentNodeSummary,
    ManagedSmtpDeploymentSummaryRead,
    ManagedSmtpFirstSendChecklistItem,
    ManagedSmtpFirstSendRead,
    ManagedSmtpFleetHealthRead,
    ManagedSmtpLogSampleRead,
    ManagedSmtpQueueSampleRead,
    MtaInventoryCounts,
    MtaIpPoolCreate,
    MtaIpPoolNodeCreate,
    MtaIpPoolNodeUpdate,
    MtaIpPoolUpdate,
    MtaNodeCreate,
    MtaNodeUpdate,
    MtaProviderAccountCreate,
    MtaProviderAccountUpdate,
)
from email_platform.services.managed_smtp_agent import (
    ManagedSmtpAgentError,
    ManagedSmtpAgentService,
)
from email_platform.services.managed_smtp_readiness import ManagedSmtpReadinessService


class MtaInventoryError(ValueError):
    pass


class MtaInventoryService:
    agent_heartbeat_stale_after_seconds = 180

    def __init__(self, db: Session) -> None:
        self.db = db

    def create_provider_account(self, payload: MtaProviderAccountCreate) -> MtaProviderAccount:
        account = MtaProviderAccount(**payload.model_dump())
        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)
        return account

    def get_provider_account(self, account_id: UUID) -> MtaProviderAccount | None:
        return self.db.get(MtaProviderAccount, account_id)

    def list_provider_accounts(
        self,
        status: MtaOperationalStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[MtaProviderAccount]:
        statement = select(MtaProviderAccount).order_by(
            MtaProviderAccount.created_at.desc(),
        )
        if status:
            statement = statement.where(MtaProviderAccount.status == status)
        return list(self.db.scalars(statement.limit(limit).offset(offset)).all())

    def count_provider_accounts(self, status: MtaOperationalStatus | None = None) -> int:
        statement = select(func.count()).select_from(MtaProviderAccount)
        if status:
            statement = statement.where(MtaProviderAccount.status == status)
        return int(self.db.scalar(statement) or 0)

    def update_provider_account(
        self,
        account_id: UUID,
        payload: MtaProviderAccountUpdate,
    ) -> MtaProviderAccount | None:
        account = self.get_provider_account(account_id)
        if not account:
            return None
        self._apply(account, payload.model_dump(exclude_unset=True))
        return self._commit_refresh(account)

    def set_provider_account_status(
        self,
        account_id: UUID,
        status: MtaOperationalStatus,
    ) -> MtaProviderAccount | None:
        account = self.get_provider_account(account_id)
        if not account:
            return None
        account.status = status
        return self._commit_refresh(account)

    def create_node(self, payload: MtaNodeCreate) -> MtaNode:
        self._require_provider_account(payload.provider_account_id)
        node = MtaNode(**payload.model_dump())
        self.db.add(node)
        self.db.commit()
        self.db.refresh(node)
        return node

    def get_node(self, node_id: UUID) -> MtaNode | None:
        return self.db.get(MtaNode, node_id)

    def list_nodes(
        self,
        status: MtaOperationalStatus | None = None,
        provider_account_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[MtaNode]:
        statement = select(MtaNode).order_by(MtaNode.created_at.desc())
        if status:
            statement = statement.where(MtaNode.status == status)
        if provider_account_id:
            statement = statement.where(MtaNode.provider_account_id == provider_account_id)
        return list(self.db.scalars(statement.limit(limit).offset(offset)).all())

    def count_nodes(
        self,
        status: MtaOperationalStatus | None = None,
        provider_account_id: UUID | None = None,
    ) -> int:
        statement = select(func.count()).select_from(MtaNode)
        if status:
            statement = statement.where(MtaNode.status == status)
        if provider_account_id:
            statement = statement.where(MtaNode.provider_account_id == provider_account_id)
        return int(self.db.scalar(statement) or 0)

    def list_node_events(
        self,
        mta_node_id: UUID | None = None,
        event_type: str | None = None,
        severity: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[MtaNodeEvent]:
        statement = select(MtaNodeEvent).order_by(MtaNodeEvent.received_at.desc())
        if mta_node_id:
            statement = statement.where(MtaNodeEvent.mta_node_id == mta_node_id)
        if event_type:
            statement = statement.where(MtaNodeEvent.event_type == event_type)
        if severity:
            statement = statement.where(MtaNodeEvent.severity == severity)
        return list(self.db.scalars(statement.limit(limit).offset(offset)).all())

    def count_node_events(
        self,
        mta_node_id: UUID | None = None,
        event_type: str | None = None,
        severity: str | None = None,
    ) -> int:
        statement = select(func.count()).select_from(MtaNodeEvent)
        if mta_node_id:
            statement = statement.where(MtaNodeEvent.mta_node_id == mta_node_id)
        if event_type:
            statement = statement.where(MtaNodeEvent.event_type == event_type)
        if severity:
            statement = statement.where(MtaNodeEvent.severity == severity)
        return int(self.db.scalar(statement) or 0)

    def update_node(self, node_id: UUID, payload: MtaNodeUpdate) -> MtaNode | None:
        node = self.get_node(node_id)
        if not node:
            return None
        updates = payload.model_dump(exclude_unset=True)
        provider_account_id = updates.get('provider_account_id')
        if provider_account_id:
            self._require_provider_account(provider_account_id)
        self._apply(node, updates)
        return self._commit_refresh(node)

    def set_node_status(
        self,
        node_id: UUID,
        status: MtaOperationalStatus,
        *,
        reason: str | None = None,
        operator: str | None = None,
    ) -> MtaNode | None:
        node = self.get_node(node_id)
        if not node:
            return None
        previous_status = self._status_value(node.status)
        node.status = status
        if reason:
            event_type = 'operator_node_pause' if status == MtaOperationalStatus.paused else 'operator_node_resume'
            event = MtaNodeEvent(
                mta_node_id=node.id,
                event_type=event_type,
                severity='warning' if status == MtaOperationalStatus.paused else 'info',
                summary=f'MTA node {node.name} set to {status.value}',
                payload_json={
                    'source': 'email_engine_operator',
                    'operator': operator,
                    'reason': reason.strip(),
                    'hostname': node.hostname,
                    'previous_status': previous_status,
                    'new_status': status.value,
                    'route_impact': {
                        'managed_smtp_route_count': self._managed_smtp_route_count(),
                        'managed_smtp_domain_policy_count': self._managed_smtp_domain_policy_count(),
                        'pool_membership_count': self.count_pool_nodes(mta_node_id=node.id),
                        'active_pool_membership_count': self.count_pool_nodes(
                            mta_node_id=node.id,
                            status=MtaOperationalStatus.active,
                        ),
                    },
                },
            )
            self.db.add(event)
        return self._commit_refresh(node)

    def create_ip_pool(self, payload: MtaIpPoolCreate) -> MtaIpPool:
        pool = MtaIpPool(**payload.model_dump())
        self.db.add(pool)
        self.db.commit()
        self.db.refresh(pool)
        return pool

    def get_ip_pool(self, pool_id: UUID) -> MtaIpPool | None:
        return self.db.get(MtaIpPool, pool_id)

    def list_ip_pools(
        self,
        status: MtaOperationalStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[MtaIpPool]:
        statement = select(MtaIpPool).order_by(MtaIpPool.created_at.desc())
        if status:
            statement = statement.where(MtaIpPool.status == status)
        return list(self.db.scalars(statement.limit(limit).offset(offset)).all())

    def count_ip_pools(self, status: MtaOperationalStatus | None = None) -> int:
        statement = select(func.count()).select_from(MtaIpPool)
        if status:
            statement = statement.where(MtaIpPool.status == status)
        return int(self.db.scalar(statement) or 0)

    def update_ip_pool(self, pool_id: UUID, payload: MtaIpPoolUpdate) -> MtaIpPool | None:
        pool = self.get_ip_pool(pool_id)
        if not pool:
            return None
        self._apply(pool, payload.model_dump(exclude_unset=True))
        return self._commit_refresh(pool)

    def set_ip_pool_status(self, pool_id: UUID, status: MtaOperationalStatus) -> MtaIpPool | None:
        pool = self.get_ip_pool(pool_id)
        if not pool:
            return None
        pool.status = status
        return self._commit_refresh(pool)

    def create_pool_node(self, payload: MtaIpPoolNodeCreate) -> MtaIpPoolNode:
        self._require_ip_pool(payload.ip_pool_id)
        self._require_node(payload.mta_node_id)
        pool_node = MtaIpPoolNode(**payload.model_dump())
        self.db.add(pool_node)
        self.db.commit()
        self.db.refresh(pool_node)
        return pool_node

    def get_pool_node(self, pool_node_id: UUID) -> MtaIpPoolNode | None:
        return self.db.get(MtaIpPoolNode, pool_node_id)

    def list_pool_nodes(
        self,
        ip_pool_id: UUID | None = None,
        mta_node_id: UUID | None = None,
        status: MtaOperationalStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[MtaIpPoolNode]:
        statement = select(MtaIpPoolNode).order_by(
            MtaIpPoolNode.priority.asc(),
            MtaIpPoolNode.created_at.desc(),
        )
        if ip_pool_id:
            statement = statement.where(MtaIpPoolNode.ip_pool_id == ip_pool_id)
        if mta_node_id:
            statement = statement.where(MtaIpPoolNode.mta_node_id == mta_node_id)
        if status:
            statement = statement.where(MtaIpPoolNode.status == status)
        return list(self.db.scalars(statement.limit(limit).offset(offset)).all())

    def count_pool_nodes(
        self,
        ip_pool_id: UUID | None = None,
        mta_node_id: UUID | None = None,
        status: MtaOperationalStatus | None = None,
    ) -> int:
        statement = select(func.count()).select_from(MtaIpPoolNode)
        if ip_pool_id:
            statement = statement.where(MtaIpPoolNode.ip_pool_id == ip_pool_id)
        if mta_node_id:
            statement = statement.where(MtaIpPoolNode.mta_node_id == mta_node_id)
        if status:
            statement = statement.where(MtaIpPoolNode.status == status)
        return int(self.db.scalar(statement) or 0)

    def update_pool_node(
        self,
        pool_node_id: UUID,
        payload: MtaIpPoolNodeUpdate,
    ) -> MtaIpPoolNode | None:
        pool_node = self.get_pool_node(pool_node_id)
        if not pool_node:
            return None
        self._apply(pool_node, payload.model_dump(exclude_unset=True))
        return self._commit_refresh(pool_node)

    def set_pool_node_status(
        self,
        pool_node_id: UUID,
        status: MtaOperationalStatus,
    ) -> MtaIpPoolNode | None:
        pool_node = self.get_pool_node(pool_node_id)
        if not pool_node:
            return None
        pool_node.status = status
        return self._commit_refresh(pool_node)

    def deployment_summary(
        self,
        limit: int = 10,
        settings: Settings | None = None,
    ) -> ManagedSmtpDeploymentSummaryRead:
        readiness_service = ManagedSmtpReadinessService(self.db)
        agent_service = ManagedSmtpAgentService(self.db)
        recent_nodes = self.list_nodes(limit=limit, offset=0)
        node_summaries = [
            ManagedSmtpDeploymentNodeSummary(
                node=node,
                provider_account=self.get_provider_account(node.provider_account_id),
                pool_memberships=self.list_pool_nodes(mta_node_id=node.id, limit=100, offset=0),
                readiness_summary=readiness_service.summary(host=node.hostname),
                **self._agent_heartbeat_state(node),
                **self._agent_config_state(
                    node,
                    self._runtime_config_or_none(agent_service, node.id),
                ),
            )
            for node in recent_nodes
        ]
        for item in node_summaries:
            item.provider_blockers = self._provider_blockers(item.provider_account)
            item.provider_blocker_labels = [
                self._provider_blocker_label(blocker) for blocker in item.provider_blockers
            ]
            item.agent_heartbeat_status_label = self._agent_heartbeat_status_label(
                item.agent_heartbeat_status
            )
            item.agent_operational_status = self._agent_operational_status(item)
            item.agent_operational_status_label = self._agent_operational_status_label(
                item.agent_operational_status
            )
            item.agent_queue_status_label = self._agent_queue_status_label(
                item.agent_queue_status
            )
            item.agent_log_issue_status_label = self._agent_log_issue_status_label(
                item.agent_log_issue_status
            )
            item.operator_next_action_code = self._operator_next_action_code(item)
            item.operator_next_action = self._operator_next_action(item)
            item.operator_next_action_tone = self._operator_next_action_tone(item)
        return ManagedSmtpDeploymentSummaryRead(
            provider_accounts=self._inventory_counts(
                total=self.count_provider_accounts(),
                count_by_status=self.count_provider_accounts,
            ),
            nodes=self._inventory_counts(
                total=self.count_nodes(),
                count_by_status=self.count_nodes,
            ),
            ip_pools=self._inventory_counts(
                total=self.count_ip_pools(),
                count_by_status=self.count_ip_pools,
            ),
            pool_nodes=self._inventory_counts(
                total=self.count_pool_nodes(),
                count_by_status=lambda status: self.count_pool_nodes(status=status),
            ),
            submission_credentials_configured=bool(
                settings and settings.smtp_username and settings.smtp_password
            ),
            submission_tls_enabled=bool(settings.smtp_use_tls) if settings else True,
            managed_smtp_route_count=self._managed_smtp_route_count(),
            managed_smtp_domain_policy_count=self._managed_smtp_domain_policy_count(),
            fleet_health=self._fleet_health(node_summaries),
            recent_nodes=node_summaries,
        )

    def first_send_readiness(
        self,
        limit: int = 10,
        settings: Settings | None = None,
    ) -> ManagedSmtpFirstSendRead:
        deployment = self.deployment_summary(limit=limit, settings=settings)
        node_summary = deployment.recent_nodes[0] if deployment.recent_nodes else None
        provider_account = node_summary.provider_account if node_summary else None
        node = node_summary.node if node_summary else None
        latest_check = node_summary.readiness_summary.latest_check if node_summary else None
        domain_policy = self._first_managed_smtp_domain_policy()
        policy_metadata = domain_policy.metadata_json if domain_policy else {}
        verification = (
            policy_metadata.get('domain_authentication_verification')
            if isinstance(policy_metadata, dict)
            else None
        )
        compliance_hold = (
            policy_metadata.get('compliance_hold') if isinstance(policy_metadata, dict) else None
        )
        compliance_hold_active = (
            isinstance(compliance_hold, dict) and compliance_hold.get('status') == 'active'
        )
        domain_auth_verified = isinstance(verification, dict) and bool(verification.get('verified'))
        submission_ready = bool(
            deployment.submission_credentials_configured and deployment.submission_tls_enabled
        )

        items = [
            self._first_send_item(
                key='provider_account',
                label='Provider account',
                ready=bool(provider_account and self._status_value(provider_account.status) == 'active'),
                value=self._status_value(provider_account.status) if provider_account else 'missing',
                ready_detail='Provider account is active.',
                blocked_detail='Activate a provider account before first send.',
            ),
            self._first_send_item(
                key='mta_node',
                label='MTA node',
                ready=bool(node and self._status_value(node.status) == 'active'),
                value=self._status_value(node.status) if node else 'missing',
                ready_detail='MTA node is active in inventory.',
                blocked_detail='Register and activate an MTA node before first send.',
            ),
            self._first_send_item(
                key='ip_pool',
                label='IP pool',
                ready=deployment.ip_pools.active > 0 and deployment.pool_nodes.active > 0,
                value=f'{deployment.ip_pools.active} pool(s), {deployment.pool_nodes.active} node(s)',
                ready_detail='An active IP pool has an active MTA node membership.',
                blocked_detail='Assign the MTA node to an active IP pool.',
            ),
            self._first_send_item(
                key='route_policy',
                label='Route policy',
                ready=(
                    deployment.managed_smtp_route_count > 0
                    and deployment.managed_smtp_domain_policy_count > 0
                ),
                value=(
                    f'{deployment.managed_smtp_route_count} route(s), '
                    f'{deployment.managed_smtp_domain_policy_count} policy row(s)'
                ),
                ready_detail='Managed SMTP route and domain policy are mapped.',
                blocked_detail='Create a managed SMTP route and assign a domain policy.',
            ),
            self._first_send_item(
                key='port25',
                label='Outbound port 25',
                ready=bool(provider_account and provider_account.port25_status == 'approved'),
                value=provider_account.port25_status if provider_account else 'unknown',
                ready_detail='Provider has approved outbound direct-MX SMTP.',
                blocked_detail='First seed send is blocked until outbound TCP port 25 is approved.',
            ),
            self._first_send_item(
                key='rdns',
                label='PTR/rDNS',
                ready=bool(provider_account and provider_account.rdns_status == 'configured'),
                value=provider_account.rdns_status if provider_account else 'unknown',
                ready_detail='Reverse DNS is configured for the sending IP.',
                blocked_detail='Configure PTR/rDNS before direct-MX sending.',
            ),
            self._first_send_item(
                key='submission_auth',
                label='Submission auth',
                ready=submission_ready,
                value='configured' if submission_ready else 'missing',
                ready_detail='Worker-to-MTA SMTP credentials and TLS are configured.',
                blocked_detail='Configure SMTP username, password, and TLS for MTA submission.',
            ),
            self._first_send_item(
                key='domain_auth',
                label='Domain auth',
                ready=domain_auth_verified,
                value='verified' if domain_auth_verified else 'pending',
                ready_detail=f'{domain_policy.domain} DNS authentication is verified.'
                if domain_policy
                else 'Domain authentication is verified.',
                blocked_detail='Verify SPF, DKIM, DMARC, and bounce-domain DNS before first send.',
            ),
            self._first_send_item(
                key='mta_smoke',
                label='MTA smoke',
                ready=bool(latest_check and latest_check.status == 'ok'),
                value=latest_check.status if latest_check else 'missing',
                ready_detail='Latest MTA readiness smoke check is passing.',
                blocked_detail='Publish a passing MTA smoke/readiness check before first send.',
            ),
            self._first_send_item(
                key='compliance',
                label='Compliance',
                ready=not compliance_hold_active and not getattr(domain_policy, 'paused_until', None),
                value='hold' if compliance_hold_active else 'clear',
                ready_detail='No active compliance hold is loaded for the managed SMTP domain.',
                blocked_detail='Release compliance hold or pause window before first send.',
            ),
        ]
        blockers = [item.label for item in items if item.blocking and item.status != 'ready']
        return ManagedSmtpFirstSendRead(
            ok=not blockers,
            status='ready' if not blockers else 'blocked',
            blockers=blockers,
            items=items,
            deployment_summary=deployment,
        )

    def _require_provider_account(self, account_id: UUID) -> MtaProviderAccount:
        account = self.get_provider_account(account_id)
        if not account:
            raise MtaInventoryError('MTA provider account not found')
        return account

    def _require_node(self, node_id: UUID) -> MtaNode:
        node = self.get_node(node_id)
        if not node:
            raise MtaInventoryError('MTA node not found')
        return node

    def _require_ip_pool(self, pool_id: UUID) -> MtaIpPool:
        pool = self.get_ip_pool(pool_id)
        if not pool:
            raise MtaInventoryError('MTA IP pool not found')
        return pool

    def _commit_refresh(self, item):
        self.db.commit()
        self.db.refresh(item)
        return item

    def _first_managed_smtp_domain_policy(self) -> DomainDeliveryPolicy | None:
        statement = (
            select(DomainDeliveryPolicy)
            .join(DeliveryRoute, DomainDeliveryPolicy.route_id == DeliveryRoute.id)
            .where(DeliveryRoute.route_type == DeliveryRouteType.managed_smtp)
            .order_by(DomainDeliveryPolicy.created_at.desc())
        )
        return self.db.scalars(statement.limit(1)).first()

    def _first_send_item(
        self,
        *,
        key: str,
        label: str,
        ready: bool,
        value: str,
        ready_detail: str,
        blocked_detail: str,
    ) -> ManagedSmtpFirstSendChecklistItem:
        return ManagedSmtpFirstSendChecklistItem(
            key=key,
            label=label,
            status='ready' if ready else 'blocked',
            value=value,
            detail=ready_detail if ready else blocked_detail,
            blocking=True,
        )

    def _status_value(self, status) -> str:
        return getattr(status, 'value', str(status))

    def _agent_heartbeat_state(self, node: MtaNode) -> dict[str, object]:
        metadata = node.metadata_json or {}
        raw_heartbeat = metadata.get('agent_last_heartbeat_at')
        stale_after = self.agent_heartbeat_stale_after_seconds
        if not raw_heartbeat:
            queue_depth = self._metadata_int(metadata, 'agent_queue_depth')
            deferred_count = self._metadata_int(metadata, 'agent_deferred_count')
            active_count = self._metadata_int(metadata, 'agent_active_count')
            agent_log_samples = self._agent_log_samples(metadata)
            return {
                'agent_heartbeat_status': 'missing',
                'agent_last_heartbeat_at': None,
                'agent_heartbeat_age_seconds': None,
                'agent_heartbeat_stale_after_seconds': stale_after,
                'agent_queue_depth': queue_depth,
                'agent_deferred_count': deferred_count,
                'agent_active_count': active_count,
                'agent_queue_status': self._agent_queue_status(
                    queue_depth, deferred_count, active_count
                ),
                'agent_queue_samples': self._agent_queue_samples(metadata),
                'agent_log_samples': agent_log_samples,
                'agent_log_issue_status': self._agent_log_issue_status(agent_log_samples),
                **self._agent_systemd_state(metadata),
                **self._agent_code_state(metadata),
            }
        try:
            heartbeat_at = datetime.fromisoformat(str(raw_heartbeat))
        except ValueError:
            queue_depth = self._metadata_int(metadata, 'agent_queue_depth')
            deferred_count = self._metadata_int(metadata, 'agent_deferred_count')
            active_count = self._metadata_int(metadata, 'agent_active_count')
            agent_log_samples = self._agent_log_samples(metadata)
            return {
                'agent_heartbeat_status': 'invalid',
                'agent_last_heartbeat_at': None,
                'agent_heartbeat_age_seconds': None,
                'agent_heartbeat_stale_after_seconds': stale_after,
                'agent_queue_depth': queue_depth,
                'agent_deferred_count': deferred_count,
                'agent_active_count': active_count,
                'agent_queue_status': self._agent_queue_status(
                    queue_depth, deferred_count, active_count
                ),
                'agent_queue_samples': self._agent_queue_samples(metadata),
                'agent_log_samples': agent_log_samples,
                'agent_log_issue_status': self._agent_log_issue_status(agent_log_samples),
                **self._agent_systemd_state(metadata),
                **self._agent_code_state(metadata),
            }
        age_seconds = max(
            0,
            int((datetime.utcnow() - heartbeat_at.replace(tzinfo=None)).total_seconds()),
        )
        queue_depth = self._metadata_int(metadata, 'agent_queue_depth')
        deferred_count = self._metadata_int(metadata, 'agent_deferred_count')
        active_count = self._metadata_int(metadata, 'agent_active_count')
        agent_log_samples = self._agent_log_samples(metadata)
        return {
            'agent_heartbeat_status': 'stale' if age_seconds > stale_after else 'ok',
            'agent_last_heartbeat_at': heartbeat_at,
            'agent_heartbeat_age_seconds': age_seconds,
            'agent_heartbeat_stale_after_seconds': stale_after,
            'agent_queue_depth': queue_depth,
            'agent_deferred_count': deferred_count,
            'agent_active_count': active_count,
            'agent_queue_status': self._agent_queue_status(
                queue_depth, deferred_count, active_count
            ),
            'agent_queue_samples': self._agent_queue_samples(metadata),
            'agent_log_samples': agent_log_samples,
            'agent_log_issue_status': self._agent_log_issue_status(agent_log_samples),
            **self._agent_systemd_state(metadata),
            **self._agent_code_state(metadata),
        }

    def _agent_config_state(self, node: MtaNode, runtime_config) -> dict[str, object]:
        metadata = node.metadata_json or {}
        platform_config_version = getattr(runtime_config, 'config_version', None)
        agent_config_version = self._metadata_str(metadata, 'agent_config_version')
        agent_applied_config_version = self._metadata_str(metadata, 'agent_applied_config_version')
        in_sync = bool(
            platform_config_version
            and agent_applied_config_version
            and platform_config_version == agent_applied_config_version
        )
        return {
            'platform_config_version': platform_config_version,
            'agent_config_version': agent_config_version,
            'agent_applied_config_version': agent_applied_config_version,
            'agent_config_in_sync': in_sync,
        }

    @staticmethod
    def _runtime_config_or_none(agent_service: ManagedSmtpAgentService, node_id: UUID):
        try:
            return agent_service.runtime_config(node_id)
        except ManagedSmtpAgentError:
            return None

    def _fleet_health(
        self,
        node_summaries: list[ManagedSmtpDeploymentNodeSummary],
    ) -> ManagedSmtpFleetHealthRead:
        active_nodes = [
            item for item in node_summaries if self._status_value(item.node.status) == 'active'
        ]
        readiness_ok_nodes = sum(
            1
            for item in active_nodes
            if item.readiness_summary.latest_check
            and item.readiness_summary.latest_check.status == 'ok'
        )
        route_ready_nodes = sum(
            1
            for item in active_nodes
            if item.agent_heartbeat_status == 'ok'
            and item.readiness_summary.latest_check
            and item.readiness_summary.latest_check.status == 'ok'
            and item.pool_memberships
        )
        operational_ok_nodes = sum(
            1 for item in node_summaries if item.agent_operational_status == 'ok'
        )
        operational_warning_nodes = sum(
            1 for item in node_summaries if item.agent_operational_status == 'warning'
        )
        operational_blocked_nodes = sum(
            1 for item in node_summaries if item.agent_operational_status == 'blocked'
        )
        operator_next_action_counts = dict(
            Counter(item.operator_next_action_code for item in node_summaries)
        )
        operator_next_action_label_counts = {
            self._operator_next_action_code_label(code): count
            for code, count in operator_next_action_counts.items()
        }
        primary_next_action_code = self._primary_next_action_code(operator_next_action_counts)
        primary_next_action_label = self._operator_next_action_code_label(primary_next_action_code)
        primary_next_action_count = operator_next_action_counts.get(primary_next_action_code, 0)
        primary_next_action_summary = self._primary_next_action_summary(
            operator_next_action_label_counts,
            primary_next_action_count,
        )
        action_required = primary_next_action_code != 'none'
        primary_next_action_tone = 'warn' if action_required else 'good'
        stale_agent_nodes = sum(
            1 for item in node_summaries if item.agent_heartbeat_status in {'stale', 'invalid'}
        )
        missing_agent_nodes = sum(
            1 for item in node_summaries if item.agent_heartbeat_status == 'missing'
        )
        config_drift_nodes = sum(
            1
            for item in node_summaries
            if item.platform_config_version and not item.agent_config_in_sync
        )
        code_missing_nodes = sum(
            1
            for item in node_summaries
            if item.agent_heartbeat_status == 'ok' and not item.agent_code_revision
        )
        code_dirty_nodes = sum(1 for item in node_summaries if item.agent_code_dirty is True)
        platform_code_revision = self._platform_code_revision()
        code_outdated_nodes = sum(
            1
            for item in node_summaries
            if platform_code_revision
            and item.agent_code_revision
            and not platform_code_revision.startswith(item.agent_code_revision)
        )
        host_update_required_nodes = sum(
            1 for item in node_summaries if getattr(item, 'agent_host_update_required', False)
        )
        agent_service_failed_nodes = sum(
            1
            for item in node_summaries
            if getattr(item, 'agent_service_active_state', None) == 'failed'
            or getattr(item, 'agent_service_sub_state', None) == 'failed'
        )
        agent_timer_unhealthy_nodes = sum(
            1
            for item in node_summaries
            if getattr(item, 'agent_timer_active_state', None)
            and (
                getattr(item, 'agent_timer_active_state', None) != 'active'
                or getattr(item, 'agent_timer_sub_state', None)
                not in {None, 'waiting', 'running', 'elapsed'}
            )
        )
        agent_log_bounce_nodes = sum(
            1 for item in node_summaries if self._node_has_log_severity(item, 'bounce')
        )
        agent_log_deferred_nodes = sum(
            1 for item in node_summaries if self._node_has_log_severity(item, 'deferred')
        )
        agent_log_warning_nodes = sum(
            1 for item in node_summaries if self._node_has_log_severity(item, 'warning')
        )
        blocked_provider_count = sum(
            1
            for item in node_summaries
            if item.provider_account
            and (
                item.provider_account.port25_status != 'approved'
                or item.provider_account.rdns_status != 'configured'
                or self._status_value(item.provider_account.status) != 'active'
            )
        )
        provider_port25_blocked_count = len(
            {
                str(item.provider_account.id)
                for item in node_summaries
                if item.provider_account and item.provider_account.port25_status != 'approved'
            }
        )
        provider_rdns_blocked_count = len(
            {
                str(item.provider_account.id)
                for item in node_summaries
                if item.provider_account and item.provider_account.rdns_status != 'configured'
            }
        )
        provider_inactive_count = len(
            {
                str(item.provider_account.id)
                for item in node_summaries
                if item.provider_account
                and self._status_value(item.provider_account.status) != 'active'
            }
        )
        queue_depth = sum(item.agent_queue_depth or 0 for item in node_summaries)
        deferred_count = sum(item.agent_deferred_count or 0 for item in node_summaries)
        active_queue_count = sum(item.agent_active_count or 0 for item in node_summaries)
        if route_ready_nodes == 0:
            status = 'blocked'
            summary = 'No route-ready MTA nodes are available.'
        elif (
            stale_agent_nodes
            or missing_agent_nodes
            or config_drift_nodes
            or code_missing_nodes
            or code_dirty_nodes
            or code_outdated_nodes
            or host_update_required_nodes
            or agent_service_failed_nodes
            or agent_timer_unhealthy_nodes
            or agent_log_bounce_nodes
            or agent_log_deferred_nodes
            or agent_log_warning_nodes
            or blocked_provider_count
            or deferred_count
        ):
            status = 'warning'
            summary = 'MTA fleet has route capacity with operational warnings.'
        else:
            status = 'ok'
            summary = 'MTA fleet is route-ready.'
        return ManagedSmtpFleetHealthRead(
            status=status,
            summary=summary,
            platform_code_revision=platform_code_revision,
            provider_count=len(
                {
                    str(item.provider_account.id)
                    for item in node_summaries
                    if item.provider_account
                }
            ),
            active_provider_count=len(
                {
                    str(item.provider_account.id)
                    for item in node_summaries
                    if item.provider_account
                    and self._status_value(item.provider_account.status) == 'active'
                }
            ),
            blocked_provider_count=blocked_provider_count,
            provider_port25_blocked_count=provider_port25_blocked_count,
            provider_rdns_blocked_count=provider_rdns_blocked_count,
            provider_inactive_count=provider_inactive_count,
            total_nodes=len(node_summaries),
            active_nodes=len(active_nodes),
            route_ready_nodes=route_ready_nodes,
            operational_ok_nodes=operational_ok_nodes,
            operational_warning_nodes=operational_warning_nodes,
            operational_blocked_nodes=operational_blocked_nodes,
            operator_next_action_counts=operator_next_action_counts,
            operator_next_action_label_counts=operator_next_action_label_counts,
            primary_next_action_code=primary_next_action_code,
            primary_next_action_label=primary_next_action_label,
            primary_next_action_count=primary_next_action_count,
            primary_next_action_summary=primary_next_action_summary,
            primary_next_action_tone=primary_next_action_tone,
            action_required=action_required,
            readiness_ok_nodes=readiness_ok_nodes,
            stale_agent_nodes=stale_agent_nodes,
            missing_agent_nodes=missing_agent_nodes,
            config_drift_nodes=config_drift_nodes,
            code_missing_nodes=code_missing_nodes,
            code_dirty_nodes=code_dirty_nodes,
            code_outdated_nodes=code_outdated_nodes,
            host_update_required_nodes=host_update_required_nodes,
            agent_service_failed_nodes=agent_service_failed_nodes,
            agent_timer_unhealthy_nodes=agent_timer_unhealthy_nodes,
            agent_log_bounce_nodes=agent_log_bounce_nodes,
            agent_log_deferred_nodes=agent_log_deferred_nodes,
            agent_log_warning_nodes=agent_log_warning_nodes,
            queue_depth=queue_depth,
            deferred_count=deferred_count,
            active_queue_count=active_queue_count,
        )

    @staticmethod
    def _node_has_log_severity(item: object, severity: str) -> bool:
        return any(
            getattr(sample, 'severity', None) == severity
            for sample in getattr(item, 'agent_log_samples', [])
        )

    @staticmethod
    def _agent_log_issue_status(samples: list[ManagedSmtpLogSampleRead]) -> str:
        severities = {sample.severity for sample in samples}
        for severity in ('bounce', 'deferred', 'warning'):
            if severity in severities:
                return severity
        return 'ok'

    @staticmethod
    def _agent_log_issue_status_label(status: str) -> str:
        return {
            'ok': 'Clear',
            'warning': 'Warning',
            'deferred': 'Deferred',
            'bounce': 'Bounce',
        }.get(status, status)

    @staticmethod
    def _agent_queue_status(
        queue_depth: int | None,
        deferred_count: int | None,
        active_count: int | None,
    ) -> str:
        if queue_depth is None and deferred_count is None and active_count is None:
            return 'unknown'
        if deferred_count and deferred_count > 0:
            return 'deferred'
        if active_count and active_count > 0:
            return 'active'
        if queue_depth and queue_depth > 0:
            return 'queued'
        return 'empty'

    @staticmethod
    def _agent_queue_status_label(status: str) -> str:
        return {
            'unknown': 'Unknown',
            'empty': 'Empty',
            'queued': 'Queued',
            'active': 'Active',
            'deferred': 'Deferred',
        }.get(status, status)

    def _agent_operational_status(self, item: ManagedSmtpDeploymentNodeSummary) -> str:
        if self._status_value(item.node.status) != 'active':
            return 'blocked'
        if item.provider_blockers:
            return 'blocked'
        if item.agent_heartbeat_status != 'ok':
            return 'blocked'
        if not item.readiness_summary.latest_check:
            return 'blocked'
        if item.readiness_summary.latest_check.status != 'ok':
            return 'blocked'
        if not item.pool_memberships:
            return 'blocked'
        if (
            not item.agent_config_in_sync
            or item.agent_host_update_required
            or item.agent_queue_status == 'deferred'
            or item.agent_log_issue_status in {'bounce', 'deferred', 'warning'}
            or item.agent_service_active_state == 'failed'
            or item.agent_service_sub_state == 'failed'
            or (
                item.agent_timer_active_state
                and (
                    item.agent_timer_active_state != 'active'
                    or item.agent_timer_sub_state not in {None, 'waiting', 'running', 'elapsed'}
                )
            )
        ):
            return 'warning'
        return 'ok'

    @staticmethod
    def _agent_operational_status_label(status: str) -> str:
        return {
            'ok': 'Operational',
            'warning': 'Needs review',
            'blocked': 'Blocked',
        }.get(status, status)

    @staticmethod
    def _agent_heartbeat_status_label(status: str) -> str:
        return {
            'ok': 'Current',
            'missing': 'Missing',
            'stale': 'Stale',
            'invalid': 'Invalid',
        }.get(status, status)

    def _provider_blockers(self, provider_account) -> list[str]:
        if not provider_account:
            return ['provider_missing']
        blockers: list[str] = []
        if self._status_value(provider_account.status) != 'active':
            blockers.append('provider_inactive')
        if provider_account.port25_status != 'approved':
            blockers.append('port25_blocked')
        if provider_account.rdns_status != 'configured':
            blockers.append('rdns_blocked')
        return blockers

    def _operator_next_action(self, item: ManagedSmtpDeploymentNodeSummary) -> str:
        action_code = getattr(
            item, 'operator_next_action_code', None
        ) or self._operator_next_action_code(item)
        if item.provider_blockers:
            blockers = ', '.join(
                self._provider_blocker_label(blocker) for blocker in item.provider_blockers
            )
            return f'Resolve provider blocker(s): {blockers}.'
        if action_code == 'restart_mta_agent':
            return 'Restart or manually run the MTA agent on the host, then reload deployment summary.'
        if action_code == 'restart_mta_agent_service':
            return 'Restart the MTA agent service and inspect the service journal before routing traffic.'
        if action_code == 'restart_mta_agent_timer':
            return 'Restart the MTA agent timer so recurring heartbeat and config checks continue.'
        if action_code == 'inspect_deferred_queue':
            return 'Inspect the MTA mail queue and resolve deferred delivery before increasing volume.'
        if action_code == 'review_postfix_logs':
            return 'Review recent Postfix log samples and resolve delivery issues before increasing volume.'
        if action_code == 'resolve_host_worktree':
            return 'Resolve the host working-tree changes before using this MTA for production traffic.'
        if action_code == 'update_host_revision':
            return 'Run the host update workflow so this MTA pulls the deployed platform revision.'
        if action_code == 'report_host_revision':
            return 'Run the host update workflow so this MTA reports its code revision.'
        if action_code == 'apply_runtime_config':
            return 'Run the MTA agent once so it fetches and applies the latest runtime config.'
        if action_code == 'publish_readiness':
            return 'Run managed SMTP readiness smoke and publish the result before routing traffic.'
        return 'No operator action required for this MTA node.'

    def _operator_next_action_code(self, item: ManagedSmtpDeploymentNodeSummary) -> str:
        if item.provider_blockers:
            return 'resolve_provider_blockers'
        if item.agent_heartbeat_status in {'missing', 'stale', 'invalid'}:
            return 'restart_mta_agent'
        if item.agent_service_active_state == 'failed' or item.agent_service_sub_state == 'failed':
            return 'restart_mta_agent_service'
        if item.agent_timer_active_state and (
            item.agent_timer_active_state != 'active'
            or item.agent_timer_sub_state not in {None, 'waiting', 'running', 'elapsed'}
        ):
            return 'restart_mta_agent_timer'
        if item.agent_queue_status == 'deferred':
            return 'inspect_deferred_queue'
        if item.agent_log_issue_status in {'bounce', 'deferred', 'warning'}:
            return 'review_postfix_logs'
        if item.agent_host_update_status == 'dirty':
            return 'resolve_host_worktree'
        if item.agent_host_update_status == 'outdated':
            return 'update_host_revision'
        if item.agent_host_update_status == 'revision_missing':
            return 'report_host_revision'
        if not item.agent_config_in_sync:
            return 'apply_runtime_config'
        if not item.readiness_summary.latest_check or item.readiness_summary.latest_check.status != 'ok':
            return 'publish_readiness'
        return 'none'

    @staticmethod
    def _operator_next_action_tone(item: ManagedSmtpDeploymentNodeSummary) -> str:
        if item.operator_next_action_code == 'none':
            return 'good'
        if getattr(item, 'agent_operational_status', None) == 'warning':
            return 'warn'
        return 'warn'

    @staticmethod
    def _provider_blocker_label(blocker: str) -> str:
        return {
            'provider_missing': 'Provider missing',
            'provider_inactive': 'Provider inactive',
            'port25_blocked': 'Port 25 blocked',
            'rdns_blocked': 'rDNS blocked',
        }.get(blocker, blocker)

    @staticmethod
    def _operator_next_action_code_label(code: str) -> str:
        return {
            'resolve_provider_blockers': 'Resolve provider blockers',
            'restart_mta_agent': 'Restart MTA agent',
            'restart_mta_agent_service': 'Restart MTA agent service',
            'restart_mta_agent_timer': 'Restart MTA agent timer',
            'inspect_deferred_queue': 'Inspect deferred queue',
            'review_postfix_logs': 'Review Postfix logs',
            'resolve_host_worktree': 'Resolve host worktree',
            'update_host_revision': 'Update host revision',
            'report_host_revision': 'Report host revision',
            'apply_runtime_config': 'Apply runtime config',
            'publish_readiness': 'Publish readiness',
            'none': 'No action',
        }.get(code, code)

    @staticmethod
    def _primary_next_action_code(action_counts: dict[str, int]) -> str:
        candidates = [
            (code, count)
            for code, count in action_counts.items()
            if code != 'none' and count > 0
        ]
        if not candidates:
            return 'none'
        return sorted(candidates, key=lambda item: (-item[1], item[0]))[0][0]

    @staticmethod
    def _primary_next_action_summary(label_counts: dict[str, int], no_action_count: int) -> str:
        action_items = [
            (label, count)
            for label, count in label_counts.items()
            if label != 'No action' and count > 0
        ]
        if not action_items:
            return f'{no_action_count} no action'
        return ', '.join(
            f'{count} {label}'
            for label, count in sorted(action_items, key=lambda item: (-item[1], item[0]))[:2]
        )

    @staticmethod
    def _metadata_int(metadata: dict[str, object], key: str) -> int | None:
        value = metadata.get(key)
        if value is None:
            return None
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return None

    def _agent_systemd_state(self, metadata: dict[str, object]) -> dict[str, object]:
        return {
            'agent_service_active_state': self._metadata_str(
                metadata, 'agent_service_active_state'
            ),
            'agent_service_sub_state': self._metadata_str(metadata, 'agent_service_sub_state'),
            'agent_timer_active_state': self._metadata_str(metadata, 'agent_timer_active_state'),
            'agent_timer_sub_state': self._metadata_str(metadata, 'agent_timer_sub_state'),
            'agent_timer_next_elapse': self._metadata_str(metadata, 'agent_timer_next_elapse'),
        }

    def _agent_code_state(self, metadata: dict[str, object]) -> dict[str, object]:
        agent_code_revision = self._metadata_str(metadata, 'agent_code_revision')
        agent_code_dirty = self._metadata_bool(metadata, 'agent_code_dirty')
        platform_code_revision = self._platform_code_revision()
        if agent_code_dirty is True:
            update_required = True
            update_status = 'dirty'
            update_detail = 'Host working tree has local changes.'
        elif not agent_code_revision:
            update_required = True
            update_status = 'revision_missing'
            update_detail = 'Host agent has not reported its code revision.'
        elif platform_code_revision and not platform_code_revision.startswith(agent_code_revision):
            update_required = True
            update_status = 'outdated'
            update_detail = 'Host code revision differs from the deployed platform revision.'
        elif platform_code_revision:
            update_required = False
            update_status = 'current'
            update_detail = 'Host code revision matches the deployed platform revision.'
        else:
            update_required = False
            update_status = 'unverified'
            update_detail = 'Platform revision is not available for comparison.'
        return {
            'agent_code_revision': agent_code_revision,
            'agent_code_dirty': agent_code_dirty,
            'agent_host_update_required': update_required,
            'agent_host_update_status': update_status,
            'agent_host_update_detail': update_detail,
        }

    def _agent_queue_samples(self, metadata: dict[str, object]) -> list[ManagedSmtpQueueSampleRead]:
        samples = metadata.get('agent_queue_samples')
        if not isinstance(samples, list):
            return []
        parsed: list[ManagedSmtpQueueSampleRead] = []
        for sample in samples[:10]:
            if not isinstance(sample, dict):
                continue
            recipients = sample.get('recipients')
            parsed.append(
                ManagedSmtpQueueSampleRead(
                    queue_id=self._metadata_value_str(sample.get('queue_id')),
                    active=sample.get('active') if isinstance(sample.get('active'), bool) else None,
                    sender=self._metadata_value_str(sample.get('sender')),
                    recipients=[
                        str(recipient)
                        for recipient in recipients
                        if isinstance(recipient, str) and recipient.strip()
                    ]
                    if isinstance(recipients, list)
                    else [],
                    deferred_reason=self._metadata_value_str(sample.get('deferred_reason')),
                )
            )
        return parsed

    def _agent_log_samples(self, metadata: dict[str, object]) -> list[ManagedSmtpLogSampleRead]:
        samples = metadata.get('agent_log_samples')
        if not isinstance(samples, list):
            return []
        parsed: list[ManagedSmtpLogSampleRead] = []
        for sample in samples[:20]:
            if not isinstance(sample, dict):
                continue
            line = self._metadata_value_str(sample.get('line'))
            if not line:
                continue
            parsed.append(
                ManagedSmtpLogSampleRead(
                    severity=self._metadata_value_str(sample.get('severity')),
                    line=line,
                )
            )
        return parsed

    @staticmethod
    def _metadata_str(metadata: dict[str, object], key: str) -> str | None:
        value = metadata.get(key)
        return MtaInventoryService._metadata_value_str(value)

    @staticmethod
    def _metadata_value_str(value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _metadata_bool(metadata: dict[str, object], key: str) -> bool | None:
        value = metadata.get(key)
        return value if isinstance(value, bool) else None

    @staticmethod
    def _platform_code_revision() -> str | None:
        for key in ('VERCEL_GIT_COMMIT_SHA', 'GIT_COMMIT_SHA', 'SOURCE_VERSION'):
            value = os.environ.get(key)
            if value:
                return value.strip() or None
        return None

    @staticmethod
    def _apply(item, updates: dict[str, object]) -> None:
        for key, value in updates.items():
            setattr(item, key, value)

    @staticmethod
    def _inventory_counts(total: int, count_by_status) -> MtaInventoryCounts:
        status_counts = {
            status.value: count_by_status(status)
            for status in MtaOperationalStatus
        }
        return MtaInventoryCounts(total=total, **status_counts)

    def _managed_smtp_route_count(self) -> int:
        statement = (
            select(func.count())
            .select_from(DeliveryRoute)
            .where(DeliveryRoute.route_type == DeliveryRouteType.managed_smtp)
        )
        return int(self.db.scalar(statement) or 0)

    def _managed_smtp_domain_policy_count(self) -> int:
        route_ids = select(DeliveryRoute.id).where(
            DeliveryRoute.route_type == DeliveryRouteType.managed_smtp,
        )
        statement = (
            select(func.count())
            .select_from(DomainDeliveryPolicy)
            .where(DomainDeliveryPolicy.route_id.in_(route_ids))
        )
        return int(self.db.scalar(statement) or 0)
