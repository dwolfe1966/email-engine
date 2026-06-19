from datetime import datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from email_platform.models.entities import MtaNodeEvent, MtaOperationalStatus, MtaProviderAccount
from email_platform.schemas.contracts import (
    ManagedSmtpLogSampleRead,
    ManagedSmtpReadinessCheckRead,
    ManagedSmtpReadinessSummaryRead,
    MtaIpPoolNodeCreate,
    MtaNodeCreate,
    MtaNodeUpdate,
    MtaProviderAccountCreate,
)
from email_platform.services import mta_inventory as mta_inventory_module
from email_platform.services.mta_inventory import MtaInventoryError, MtaInventoryService


class FakeDb:
    def __init__(self, get_results=None) -> None:
        self.get_results = get_results or {}
        self.added = []
        self.committed = False
        self.refreshed = []

    def add(self, item):
        self.added.append(item)

    def commit(self):
        self.committed = True

    def refresh(self, item):
        self.refreshed.append(item)

    def get(self, model, item_id):
        return self.get_results.get((model, item_id))

    def scalar(self, statement):
        return 0


def test_create_provider_account_defaults_to_secret_ref_not_raw_credentials() -> None:
    db = FakeDb()
    service = MtaInventoryService(db)

    account = service.create_provider_account(
        MtaProviderAccountCreate(
            name='aws-staging',
            provider='aws',
            account_ref='123456789012',
            region='us-west-2',
            secret_ref='secret/email-engine/mta/aws-staging',
        )
    )

    assert account.name == 'aws-staging'
    assert account.provider == 'aws'
    assert account.secret_ref == 'secret/email-engine/mta/aws-staging'
    assert db.added == [account]
    assert db.committed
    assert db.refreshed == [account]


def test_create_node_requires_existing_provider_account() -> None:
    service = MtaInventoryService(FakeDb())

    with pytest.raises(MtaInventoryError, match='MTA provider account not found'):
        service.create_node(
            MtaNodeCreate(
                provider_account_id=uuid4(),
                name='mta-001',
                hostname='mta-001.email-engine.example',
            )
        )


def test_update_node_validates_reassigned_provider_account() -> None:
    node_id = uuid4()
    node = SimpleNamespace(id=node_id)
    service = MtaInventoryService(FakeDb(get_results={(object, node_id): node}))

    def fake_get_node(item_id):
        return node if item_id == node_id else None

    service.get_node = fake_get_node

    with pytest.raises(MtaInventoryError, match='MTA provider account not found'):
        service.update_node(node_id, MtaNodeUpdate(provider_account_id=uuid4()))


def test_provider_account_pause_and_resume_change_operational_status() -> None:
    account_id = uuid4()
    account = SimpleNamespace(id=account_id, status=MtaOperationalStatus.active)
    db = FakeDb(get_results={(MtaProviderAccount, account_id): account})
    service = MtaInventoryService(db)

    paused = service.set_provider_account_status(account_id, MtaOperationalStatus.paused)
    resumed = service.set_provider_account_status(account_id, MtaOperationalStatus.active)

    assert paused is account
    assert resumed is account
    assert account.status == MtaOperationalStatus.active
    assert db.committed
    assert db.refreshed == [account, account]


def test_node_pause_records_operator_audit_event() -> None:
    node_id = uuid4()
    node = SimpleNamespace(
        id=node_id,
        name='mta-002',
        hostname='mta-002.email-engine.app',
        status=MtaOperationalStatus.active,
    )
    db = FakeDb()
    service = MtaInventoryService(db)
    service.get_node = lambda item_id: node if item_id == node_id else None

    updated = service.set_node_status(
        node_id,
        MtaOperationalStatus.paused,
        reason='Provider maintenance window',
        operator='esp_admin',
    )

    events = [item for item in db.added if isinstance(item, MtaNodeEvent)]
    assert updated is node
    assert node.status == MtaOperationalStatus.paused
    assert len(events) == 1
    event = events[0]
    assert event.mta_node_id == node_id
    assert event.event_type == 'operator_node_pause'
    assert event.severity == 'warning'
    assert event.payload_json['operator'] == 'esp_admin'
    assert event.payload_json['reason'] == 'Provider maintenance window'
    assert event.payload_json['previous_status'] == 'active'
    assert event.payload_json['new_status'] == 'paused'
    assert event.payload_json['route_impact']['managed_smtp_route_count'] == 0
    assert db.committed
    assert db.refreshed == [node]


def test_create_pool_node_requires_existing_pool_before_node() -> None:
    service = MtaInventoryService(FakeDb())

    with pytest.raises(MtaInventoryError, match='MTA IP pool not found'):
        service.create_pool_node(MtaIpPoolNodeCreate(ip_pool_id=uuid4(), mta_node_id=uuid4()))


def test_deployment_summary_combines_inventory_counts_and_node_readiness(monkeypatch) -> None:
    monkeypatch.delenv('VERCEL_GIT_COMMIT_SHA', raising=False)
    monkeypatch.delenv('GIT_COMMIT_SHA', raising=False)
    monkeypatch.delenv('SOURCE_VERSION', raising=False)
    account_id = uuid4()
    node_id = uuid4()
    pool_node_id = uuid4()
    pool_id = uuid4()
    now = datetime.utcnow()
    account = SimpleNamespace(
        id=account_id,
        name='aws-staging',
        provider='aws',
        status=MtaOperationalStatus.active,
        account_ref='123456789012',
        region='us-west-2',
        abuse_contact_email='abuse@example.com',
        support_case_ref='case-123',
        port25_status='approved',
        rdns_status='configured',
        secret_ref='secret/provider/aws-staging',
        metadata_json={},
        created_at=now,
        updated_at=now,
    )
    node = SimpleNamespace(
        id=node_id,
        provider_account_id=account_id,
        name='mta-001',
        hostname='smtp.example.com',
        public_ipv4='192.0.2.10',
        status=MtaOperationalStatus.active,
        submission_host='smtp.example.com',
        submission_port=587,
        auth_secret_ref='secret/mta-001/submission',
        last_readiness_at=now,
        metadata_json={
            'agent_last_heartbeat_at': now.isoformat(),
            'agent_queue_depth': 1,
            'agent_deferred_count': 0,
            'agent_active_count': 1,
            'agent_queue_samples': [
                {
                    'queue_id': 'ABC123DEF',
                    'active': False,
                    'sender': 'mta-smoke@email-engine.app',
                    'recipients': ['seed@example.com'],
                    'deferred_reason': 'temporary DNS failure',
                }
            ],
            'agent_log_samples': [
                {'severity': 'sent', 'line': 'postfix/smtp: status=sent'}
            ],
            'agent_config_version': 'config-v1',
            'agent_applied_config_version': 'config-v1',
            'agent_service_active_state': 'inactive',
            'agent_service_sub_state': 'dead',
            'agent_timer_active_state': 'active',
            'agent_timer_sub_state': 'waiting',
            'agent_timer_next_elapse': 'Fri 2026-06-19 00:34:09 UTC',
            'agent_code_revision': 'abc123def456',
            'agent_code_dirty': False,
        },
        created_at=now,
        updated_at=now,
    )
    pool_node = SimpleNamespace(
        id=pool_node_id,
        ip_pool_id=pool_id,
        mta_node_id=node_id,
        priority=100,
        weight=100,
        status=MtaOperationalStatus.active,
        metadata_json={},
        created_at=now,
        updated_at=now,
    )

    class FakeReadinessService:
        def __init__(self, db) -> None:
            self.db = db

        def summary(self, **kwargs):
            assert kwargs == {'host': 'smtp.example.com'}
            return ManagedSmtpReadinessSummaryRead(
                total_count=2,
                ok_count=2,
                warning_count=0,
                failed_count=0,
                latest_check=ManagedSmtpReadinessCheckRead(
                    id=uuid4(),
                    source='mta_agent',
                    check_type='heartbeat',
                    status='ok',
                    host='smtp.example.com',
                    created_at=now,
                ),
            )

    class FakeAgentService:
        def __init__(self, db) -> None:
            self.db = db

        def runtime_config(self, item_id):
            assert item_id == node_id
            return SimpleNamespace(config_version='config-v1')

    class FakeSummaryService(MtaInventoryService):
        def list_nodes(self, **kwargs):
            assert kwargs['limit'] == 5
            return [node]

        def get_provider_account(self, item_id):
            return account if item_id == account_id else None

        def list_pool_nodes(self, **kwargs):
            assert kwargs['mta_node_id'] == node_id
            return [pool_node]

        def count_provider_accounts(self, status=None):
            return 1 if status in {None, MtaOperationalStatus.active} else 0

        def count_nodes(self, status=None, provider_account_id=None):
            return 1 if status in {None, MtaOperationalStatus.active} else 0

        def count_ip_pools(self, status=None):
            return 1 if status in {None, MtaOperationalStatus.paused} else 0

        def count_pool_nodes(self, ip_pool_id=None, mta_node_id=None, status=None):
            assert ip_pool_id is None
            assert mta_node_id is None
            return 1 if status in {None, MtaOperationalStatus.active} else 0

        def _managed_smtp_route_count(self):
            return 1

        def _managed_smtp_domain_policy_count(self):
            return 1

    monkeypatch.setattr(
        mta_inventory_module,
        'ManagedSmtpReadinessService',
        FakeReadinessService,
    )
    monkeypatch.setattr(
        mta_inventory_module,
        'ManagedSmtpAgentService',
        FakeAgentService,
    )

    summary = FakeSummaryService(FakeDb()).deployment_summary(
        limit=5,
        settings=SimpleNamespace(
            smtp_username='submission-user',
            smtp_password='submission-password',
            smtp_use_tls=True,
        ),
    )

    assert summary.provider_accounts.total == 1
    assert summary.provider_accounts.active == 1
    assert summary.ip_pools.paused == 1
    assert summary.managed_smtp_route_count == 1
    assert summary.managed_smtp_domain_policy_count == 1
    assert summary.submission_credentials_configured is True
    assert summary.submission_tls_enabled is True
    assert summary.recent_nodes[0].node.hostname == 'smtp.example.com'
    assert summary.recent_nodes[0].provider_account is not None
    assert summary.recent_nodes[0].provider_account.name == 'aws-staging'
    assert summary.recent_nodes[0].provider_blockers == []
    assert summary.recent_nodes[0].operator_next_action == (
        'No operator action required for this MTA node.'
    )
    assert summary.recent_nodes[0].pool_memberships[0].id == pool_node_id
    assert summary.recent_nodes[0].readiness_summary.ok_count == 2
    assert summary.recent_nodes[0].agent_heartbeat_status == 'ok'
    assert summary.recent_nodes[0].agent_operational_status == 'ok'
    assert summary.recent_nodes[0].agent_last_heartbeat_at is not None
    assert summary.recent_nodes[0].agent_heartbeat_age_seconds is not None
    assert summary.recent_nodes[0].agent_heartbeat_stale_after_seconds == 180
    assert summary.recent_nodes[0].agent_queue_depth == 1
    assert summary.recent_nodes[0].agent_queue_status == 'active'
    assert summary.recent_nodes[0].agent_queue_samples[0].queue_id == 'ABC123DEF'
    assert summary.recent_nodes[0].agent_queue_samples[0].deferred_reason == (
        'temporary DNS failure'
    )
    assert summary.recent_nodes[0].agent_log_samples[0].severity == 'sent'
    assert summary.recent_nodes[0].agent_log_samples[0].line == 'postfix/smtp: status=sent'
    assert summary.recent_nodes[0].agent_log_issue_status == 'ok'
    assert summary.recent_nodes[0].platform_config_version == 'config-v1'
    assert summary.recent_nodes[0].agent_applied_config_version == 'config-v1'
    assert summary.recent_nodes[0].agent_config_in_sync is True
    assert summary.recent_nodes[0].agent_service_active_state == 'inactive'
    assert summary.recent_nodes[0].agent_timer_active_state == 'active'
    assert summary.recent_nodes[0].agent_timer_next_elapse == 'Fri 2026-06-19 00:34:09 UTC'
    assert summary.recent_nodes[0].agent_code_revision == 'abc123def456'
    assert summary.recent_nodes[0].agent_code_dirty is False
    assert summary.recent_nodes[0].agent_host_update_required is False
    assert summary.recent_nodes[0].agent_host_update_status == 'unverified'
    assert summary.fleet_health.status == 'ok'
    assert summary.fleet_health.route_ready_nodes == 1
    assert summary.fleet_health.operational_ok_nodes == 1
    assert summary.fleet_health.operational_warning_nodes == 0
    assert summary.fleet_health.operational_blocked_nodes == 0
    assert summary.fleet_health.blocked_provider_count == 0
    assert summary.fleet_health.provider_port25_blocked_count == 0
    assert summary.fleet_health.provider_rdns_blocked_count == 0
    assert summary.fleet_health.provider_inactive_count == 0
    assert summary.fleet_health.config_drift_nodes == 0
    assert summary.fleet_health.code_missing_nodes == 0
    assert summary.fleet_health.code_dirty_nodes == 0
    assert summary.fleet_health.code_outdated_nodes == 0
    assert summary.fleet_health.host_update_required_nodes == 0
    assert summary.fleet_health.agent_service_failed_nodes == 0
    assert summary.fleet_health.agent_timer_unhealthy_nodes == 0
    assert summary.fleet_health.agent_log_bounce_nodes == 0
    assert summary.fleet_health.agent_log_deferred_nodes == 0
    assert summary.fleet_health.agent_log_warning_nodes == 0
    assert summary.fleet_health.queue_depth == 1
    assert summary.fleet_health.active_queue_count == 1


def test_agent_heartbeat_state_marks_old_heartbeat_stale() -> None:
    service = MtaInventoryService(FakeDb())
    old_heartbeat = datetime.utcnow() - timedelta(seconds=240)
    node = SimpleNamespace(metadata_json={'agent_last_heartbeat_at': old_heartbeat.isoformat()})

    state = service._agent_heartbeat_state(node)

    assert state['agent_heartbeat_status'] == 'stale'
    assert state['agent_heartbeat_age_seconds'] >= 180
    assert state['agent_heartbeat_stale_after_seconds'] == 180


def test_agent_config_state_marks_runtime_config_drift() -> None:
    service = MtaInventoryService(FakeDb())
    node = SimpleNamespace(
        metadata_json={
            'agent_config_version': 'config-v1',
            'agent_applied_config_version': 'config-v1',
        }
    )

    state = service._agent_config_state(node, SimpleNamespace(config_version='config-v2'))

    assert state['platform_config_version'] == 'config-v2'
    assert state['agent_applied_config_version'] == 'config-v1'
    assert state['agent_config_in_sync'] is False


def test_agent_heartbeat_state_marks_worst_log_issue_status() -> None:
    service = MtaInventoryService(FakeDb())
    node = SimpleNamespace(
        metadata_json={
            'agent_last_heartbeat_at': datetime.utcnow().isoformat(),
            'agent_log_samples': [
                {'severity': 'sent', 'line': 'postfix/smtp: status=sent'},
                {'severity': 'warning', 'line': 'postfix/smtpd: warning'},
                {'severity': 'deferred', 'line': 'postfix/smtp: status=deferred'},
            ],
        }
    )

    state = service._agent_heartbeat_state(node)

    assert state['agent_log_issue_status'] == 'deferred'


def test_agent_queue_status_summarizes_queue_counts() -> None:
    service = MtaInventoryService(FakeDb())

    assert service._agent_queue_status(None, None, None) == 'unknown'
    assert service._agent_queue_status(0, 0, 0) == 'empty'
    assert service._agent_queue_status(3, 0, 0) == 'queued'
    assert service._agent_queue_status(3, 0, 2) == 'active'
    assert service._agent_queue_status(3, 1, 2) == 'deferred'


def test_agent_operational_status_summarizes_node_health() -> None:
    service = MtaInventoryService(FakeDb())
    latest_check = ManagedSmtpReadinessCheckRead(
        id=uuid4(),
        source='mta_agent',
        check_type='heartbeat',
        status='ok',
        host='smtp.example.com',
        created_at=datetime.utcnow(),
    )

    def node_summary(**overrides):
        values = {
            'node': SimpleNamespace(status=MtaOperationalStatus.active),
            'provider_blockers': [],
            'pool_memberships': [SimpleNamespace()],
            'readiness_summary': ManagedSmtpReadinessSummaryRead(
                total_count=1,
                ok_count=1,
                warning_count=0,
                failed_count=0,
                latest_check=latest_check,
            ),
            'agent_heartbeat_status': 'ok',
            'agent_config_in_sync': True,
            'agent_host_update_required': False,
            'agent_queue_status': 'empty',
            'agent_log_issue_status': 'ok',
            'agent_service_active_state': 'inactive',
            'agent_service_sub_state': 'dead',
            'agent_timer_active_state': 'active',
            'agent_timer_sub_state': 'waiting',
        }
        values.update(overrides)
        return SimpleNamespace(**values)

    assert service._agent_operational_status(node_summary()) == 'ok'
    assert service._agent_operational_status(node_summary(agent_heartbeat_status='stale')) == (
        'blocked'
    )
    assert service._agent_operational_status(node_summary(agent_queue_status='deferred')) == (
        'warning'
    )
    assert service._agent_operational_status(node_summary(agent_log_issue_status='warning')) == (
        'warning'
    )
    assert service._agent_operational_status(node_summary(provider_blockers=['port25_blocked'])) == (
        'blocked'
    )


def test_provider_blockers_identify_port25_rdns_and_inactive_provider() -> None:
    service = MtaInventoryService(FakeDb())
    provider = SimpleNamespace(
        status=MtaOperationalStatus.paused,
        port25_status='pending',
        rdns_status='pending',
    )

    assert service._provider_blockers(provider) == [
        'provider_inactive',
        'port25_blocked',
        'rdns_blocked',
    ]
    assert service._provider_blockers(None) == ['provider_missing']


def test_operator_next_action_prioritizes_provider_blockers() -> None:
    service = MtaInventoryService(FakeDb())
    latest_check = ManagedSmtpReadinessCheckRead(
        id=uuid4(),
        source='mta_agent',
        check_type='heartbeat',
        status='ok',
        host='smtp.example.com',
        created_at=datetime.utcnow(),
    )
    item = SimpleNamespace(
        provider_blockers=['port25_blocked'],
        agent_heartbeat_status='ok',
        agent_service_active_state='inactive',
        agent_service_sub_state='dead',
        agent_timer_active_state='active',
        agent_timer_sub_state='waiting',
        agent_queue_status='empty',
        agent_log_issue_status='ok',
        agent_host_update_status='current',
        agent_config_in_sync=True,
        readiness_summary=ManagedSmtpReadinessSummaryRead(
            total_count=1,
            ok_count=1,
            warning_count=0,
            failed_count=0,
            latest_check=latest_check,
        ),
    )

    assert service._operator_next_action(item) == (
        'Resolve provider blocker(s): Port 25 blocked.'
    )


def test_agent_code_state_marks_host_update_required_for_outdated_revision(monkeypatch) -> None:
    monkeypatch.setenv('VERCEL_GIT_COMMIT_SHA', 'abc123def456')
    service = MtaInventoryService(FakeDb())

    state = service._agent_code_state(
        {
            'agent_code_revision': 'old123',
            'agent_code_dirty': False,
        }
    )

    assert state['agent_host_update_required'] is True
    assert state['agent_host_update_status'] == 'outdated'
    assert state['agent_host_update_detail'] == (
        'Host code revision differs from the deployed platform revision.'
    )


def test_fleet_health_warns_when_agent_code_revision_is_missing_dirty_or_outdated(
    monkeypatch,
) -> None:
    monkeypatch.setenv('VERCEL_GIT_COMMIT_SHA', 'currentrev999999')
    service = MtaInventoryService(FakeDb())
    latest_check = ManagedSmtpReadinessCheckRead(
        id=uuid4(),
        source='mta_agent',
        check_type='heartbeat',
        status='ok',
        host='smtp.example.com',
        created_at=datetime.utcnow(),
    )
    node = SimpleNamespace(status=MtaOperationalStatus.active)
    summary = service._fleet_health(
        [
            SimpleNamespace(
                node=node,
                agent_operational_status='warning',
                provider_account=None,
                pool_memberships=[SimpleNamespace()],
                readiness_summary=ManagedSmtpReadinessSummaryRead(
                    total_count=1,
                    ok_count=1,
                    warning_count=0,
                    failed_count=0,
                    latest_check=latest_check,
                ),
                agent_heartbeat_status='ok',
                agent_config_in_sync=True,
                platform_config_version='config-v1',
                agent_code_revision=None,
                agent_code_dirty=None,
                agent_host_update_required=True,
                agent_queue_depth=0,
                agent_deferred_count=0,
                agent_active_count=0,
            ),
            SimpleNamespace(
                node=node,
                agent_operational_status='warning',
                provider_account=None,
                pool_memberships=[SimpleNamespace()],
                readiness_summary=ManagedSmtpReadinessSummaryRead(
                    total_count=1,
                    ok_count=1,
                    warning_count=0,
                    failed_count=0,
                    latest_check=latest_check,
                ),
                agent_heartbeat_status='ok',
                agent_config_in_sync=True,
                platform_config_version='config-v1',
                agent_code_revision='dirtyrev123',
                agent_code_dirty=True,
                agent_host_update_required=True,
                agent_queue_depth=0,
                agent_deferred_count=0,
                agent_active_count=0,
            ),
            SimpleNamespace(
                node=node,
                agent_operational_status='warning',
                provider_account=None,
                pool_memberships=[SimpleNamespace()],
                readiness_summary=ManagedSmtpReadinessSummaryRead(
                    total_count=1,
                    ok_count=1,
                    warning_count=0,
                    failed_count=0,
                    latest_check=latest_check,
                ),
                agent_heartbeat_status='ok',
                agent_config_in_sync=True,
                platform_config_version='config-v1',
                agent_code_revision='oldrev123456',
                agent_code_dirty=False,
                agent_host_update_required=True,
                agent_queue_depth=0,
                agent_deferred_count=0,
                agent_active_count=0,
            ),
        ]
    )

    assert summary.status == 'warning'
    assert summary.platform_code_revision == 'currentrev999999'
    assert summary.code_missing_nodes == 1
    assert summary.code_dirty_nodes == 1
    assert summary.code_outdated_nodes == 2
    assert summary.host_update_required_nodes == 3
    assert summary.operational_warning_nodes == 3


def test_fleet_health_warns_when_agent_systemd_state_is_unhealthy(monkeypatch) -> None:
    monkeypatch.delenv('VERCEL_GIT_COMMIT_SHA', raising=False)
    monkeypatch.delenv('GIT_COMMIT_SHA', raising=False)
    monkeypatch.delenv('SOURCE_VERSION', raising=False)
    service = MtaInventoryService(FakeDb())
    latest_check = ManagedSmtpReadinessCheckRead(
        id=uuid4(),
        source='mta_agent',
        check_type='heartbeat',
        status='ok',
        host='smtp.example.com',
        created_at=datetime.utcnow(),
    )
    node = SimpleNamespace(status=MtaOperationalStatus.active)

    def node_summary(**systemd_state):
        return SimpleNamespace(
            node=node,
            agent_operational_status='warning',
            provider_account=None,
            pool_memberships=[SimpleNamespace()],
            readiness_summary=ManagedSmtpReadinessSummaryRead(
                total_count=1,
                ok_count=1,
                warning_count=0,
                failed_count=0,
                latest_check=latest_check,
            ),
            agent_heartbeat_status='ok',
            agent_config_in_sync=True,
            platform_config_version='config-v1',
            agent_code_revision='abc123',
            agent_code_dirty=False,
            agent_queue_depth=0,
            agent_deferred_count=0,
            agent_active_count=0,
            **systemd_state,
        )

    summary = service._fleet_health(
        [
            node_summary(
                agent_service_active_state='failed',
                agent_service_sub_state='failed',
                agent_timer_active_state='active',
                agent_timer_sub_state='waiting',
            ),
            node_summary(
                agent_service_active_state='inactive',
                agent_service_sub_state='dead',
                agent_timer_active_state='inactive',
                agent_timer_sub_state='dead',
            ),
        ]
    )

    assert summary.status == 'warning'
    assert summary.agent_service_failed_nodes == 1
    assert summary.agent_timer_unhealthy_nodes == 1
    assert summary.operational_warning_nodes == 2


def test_fleet_health_warns_when_agent_log_samples_show_delivery_issues() -> None:
    service = MtaInventoryService(FakeDb())
    latest_check = ManagedSmtpReadinessCheckRead(
        id=uuid4(),
        source='mta_agent',
        check_type='heartbeat',
        status='ok',
        host='smtp.example.com',
        created_at=datetime.utcnow(),
    )
    node = SimpleNamespace(status=MtaOperationalStatus.active)

    def node_summary(*severities: str):
        operational_status = (
            'warning' if {'bounce', 'deferred', 'warning'}.intersection(severities) else 'ok'
        )
        return SimpleNamespace(
            node=node,
            agent_operational_status=operational_status,
            provider_account=None,
            pool_memberships=[SimpleNamespace()],
            readiness_summary=ManagedSmtpReadinessSummaryRead(
                total_count=1,
                ok_count=1,
                warning_count=0,
                failed_count=0,
                latest_check=latest_check,
            ),
            agent_heartbeat_status='ok',
            agent_config_in_sync=True,
            platform_config_version='config-v1',
            agent_code_revision='abc123',
            agent_code_dirty=False,
            agent_host_update_required=False,
            agent_queue_depth=0,
            agent_deferred_count=0,
            agent_active_count=0,
            agent_log_samples=[
                ManagedSmtpLogSampleRead(
                    severity=severity,
                    line=f'postfix/smtp: status={severity}',
                )
                for severity in severities
            ],
        )

    summary = service._fleet_health(
        [
            node_summary('bounce', 'warning'),
            node_summary('deferred'),
            node_summary('sent'),
        ]
    )

    assert summary.status == 'warning'
    assert summary.agent_log_bounce_nodes == 1
    assert summary.agent_log_deferred_nodes == 1
    assert summary.agent_log_warning_nodes == 1
    assert summary.operational_ok_nodes == 1
    assert summary.operational_warning_nodes == 2


def test_fleet_health_splits_provider_blocker_counts() -> None:
    service = MtaInventoryService(FakeDb())
    latest_check = ManagedSmtpReadinessCheckRead(
        id=uuid4(),
        source='mta_agent',
        check_type='heartbeat',
        status='ok',
        host='smtp.example.com',
        created_at=datetime.utcnow(),
    )
    node = SimpleNamespace(status=MtaOperationalStatus.active)

    def node_summary(provider_account):
        return SimpleNamespace(
            node=node,
            agent_operational_status='ok',
            provider_account=provider_account,
            pool_memberships=[SimpleNamespace()],
            readiness_summary=ManagedSmtpReadinessSummaryRead(
                total_count=1,
                ok_count=1,
                warning_count=0,
                failed_count=0,
                latest_check=latest_check,
            ),
            agent_heartbeat_status='ok',
            agent_config_in_sync=True,
            platform_config_version='config-v1',
            agent_code_revision='abc123',
            agent_code_dirty=False,
            agent_host_update_required=False,
            agent_queue_depth=0,
            agent_deferred_count=0,
            agent_active_count=0,
            agent_log_samples=[],
        )

    summary = service._fleet_health(
        [
            node_summary(
                SimpleNamespace(
                    id=uuid4(),
                    status=MtaOperationalStatus.active,
                    port25_status='pending',
                    rdns_status='configured',
                )
            ),
            node_summary(
                SimpleNamespace(
                    id=uuid4(),
                    status=MtaOperationalStatus.active,
                    port25_status='approved',
                    rdns_status='pending',
                )
            ),
            node_summary(
                SimpleNamespace(
                    id=uuid4(),
                    status=MtaOperationalStatus.paused,
                    port25_status='approved',
                    rdns_status='configured',
                )
            ),
        ]
    )

    assert summary.status == 'warning'
    assert summary.blocked_provider_count == 3
    assert summary.provider_port25_blocked_count == 1
    assert summary.provider_rdns_blocked_count == 1
    assert summary.provider_inactive_count == 1


def test_first_send_readiness_marks_ready_when_all_controls_pass(monkeypatch) -> None:
    account_id = uuid4()
    node_id = uuid4()
    pool_node_id = uuid4()
    pool_id = uuid4()
    now = datetime.utcnow()
    account = _provider_account(account_id, now)
    node = _mta_node(node_id, account_id, now)
    pool_node = _pool_node(pool_node_id, pool_id, node_id, now)
    policy = SimpleNamespace(
        domain='email-engine.example',
        paused_until=None,
        metadata_json={
            'domain_authentication_verification': {'verified': True},
            'compliance_hold': {'status': 'released'},
        },
    )

    _install_fake_readiness(monkeypatch, node.hostname, status='ok', now=now)

    first_send = _FakeFirstSendService(
        FakeDb(),
        account=account,
        node=node,
        pool_node=pool_node,
        policy=policy,
    ).first_send_readiness(
        limit=5,
        settings=SimpleNamespace(
            smtp_username='submission-user',
            smtp_password='submission-password',
            smtp_use_tls=True,
        ),
    )

    assert first_send.ok is True
    assert first_send.status == 'ready'
    assert first_send.blockers == []
    assert first_send.deployment_summary.recent_nodes[0].node.hostname == 'smtp.example.com'
    statuses = {item.key: item.status for item in first_send.items}
    assert statuses['port25'] == 'ready'
    assert statuses['domain_auth'] == 'ready'
    assert statuses['mta_smoke'] == 'ready'


def test_first_send_readiness_blocks_when_port25_is_pending(monkeypatch) -> None:
    account_id = uuid4()
    node_id = uuid4()
    pool_node_id = uuid4()
    pool_id = uuid4()
    now = datetime.utcnow()
    account = _provider_account(account_id, now, port25_status='pending')
    node = _mta_node(node_id, account_id, now)
    pool_node = _pool_node(pool_node_id, pool_id, node_id, now)
    policy = SimpleNamespace(
        domain='email-engine.example',
        paused_until=None,
        metadata_json={'domain_authentication_verification': {'verified': True}},
    )

    _install_fake_readiness(monkeypatch, node.hostname, status='ok', now=now)

    first_send = _FakeFirstSendService(
        FakeDb(),
        account=account,
        node=node,
        pool_node=pool_node,
        policy=policy,
    ).first_send_readiness(
        settings=SimpleNamespace(
            smtp_username='submission-user',
            smtp_password='submission-password',
            smtp_use_tls=True,
        ),
    )

    assert first_send.ok is False
    assert first_send.status == 'blocked'
    assert 'Outbound port 25' in first_send.blockers
    port25 = next(item for item in first_send.items if item.key == 'port25')
    assert port25.status == 'blocked'
    assert port25.value == 'pending'


def _provider_account(account_id, now, port25_status='approved'):
    return SimpleNamespace(
        id=account_id,
        name='aws-staging',
        provider='aws',
        status=MtaOperationalStatus.active,
        account_ref='123456789012',
        region='us-west-2',
        abuse_contact_email='abuse@example.com',
        support_case_ref='case-123',
        port25_status=port25_status,
        rdns_status='configured',
        secret_ref='secret/provider/aws-staging',
        metadata_json={},
        created_at=now,
        updated_at=now,
    )


def _mta_node(node_id, account_id, now):
    return SimpleNamespace(
        id=node_id,
        provider_account_id=account_id,
        name='mta-001',
        hostname='smtp.example.com',
        public_ipv4='192.0.2.10',
        status=MtaOperationalStatus.active,
        submission_host='smtp.example.com',
        submission_port=587,
        auth_secret_ref='secret/mta-001/submission',
        last_readiness_at=now,
        metadata_json={},
        created_at=now,
        updated_at=now,
    )


def _pool_node(pool_node_id, pool_id, node_id, now):
    return SimpleNamespace(
        id=pool_node_id,
        ip_pool_id=pool_id,
        mta_node_id=node_id,
        priority=100,
        weight=100,
        status=MtaOperationalStatus.active,
        metadata_json={},
        created_at=now,
        updated_at=now,
    )


def _install_fake_readiness(monkeypatch, expected_host, status, now) -> None:
    class FakeReadinessService:
        def __init__(self, db) -> None:
            self.db = db

        def summary(self, **kwargs):
            assert kwargs == {'host': expected_host}
            check = ManagedSmtpReadinessCheckRead(
                id=uuid4(),
                source='managed_smtp_mta_smoke',
                check_type='mta_smoke',
                status=status,
                domain='email-engine.example',
                host=expected_host,
                summary='MTA smoke check passed',
                result_json={},
                created_at=now,
            )
            return ManagedSmtpReadinessSummaryRead(
                total_count=1,
                ok_count=1 if status == 'ok' else 0,
                warning_count=0,
                failed_count=0 if status == 'ok' else 1,
                latest_check=check,
                latest_success=check if status == 'ok' else None,
            )

    monkeypatch.setattr(
        mta_inventory_module,
        'ManagedSmtpReadinessService',
        FakeReadinessService,
    )


class _FakeFirstSendService(MtaInventoryService):
    def __init__(self, db, *, account, node, pool_node, policy) -> None:
        super().__init__(db)
        self.account = account
        self.node = node
        self.pool_node = pool_node
        self.policy = policy

    def list_nodes(self, **kwargs):
        return [self.node]

    def get_provider_account(self, item_id):
        return self.account if item_id == self.account.id else None

    def list_pool_nodes(self, **kwargs):
        return [self.pool_node]

    def count_provider_accounts(self, status=None):
        return 1 if status in {None, MtaOperationalStatus.active} else 0

    def count_nodes(self, status=None, provider_account_id=None):
        return 1 if status in {None, MtaOperationalStatus.active} else 0

    def count_ip_pools(self, status=None):
        return 1 if status in {None, MtaOperationalStatus.active} else 0

    def count_pool_nodes(self, ip_pool_id=None, mta_node_id=None, status=None):
        return 1 if status in {None, MtaOperationalStatus.active} else 0

    def _managed_smtp_route_count(self):
        return 1

    def _managed_smtp_domain_policy_count(self):
        return 1

    def _first_managed_smtp_domain_policy(self):
        return self.policy
