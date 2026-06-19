from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

from email_platform.models.entities import MtaNode
from email_platform.schemas.contracts import MtaNodeHeartbeatRequest
from email_platform.services import managed_smtp_agent as agent_module
from email_platform.services.managed_smtp_agent import ManagedSmtpAgentService


class FakeDb:
    def __init__(self, node) -> None:
        self.node = node
        self.committed = False
        self.refreshed = []

    def get(self, model, item_id):
        return self.node if model is MtaNode and item_id == self.node.id else None

    def commit(self):
        self.committed = True

    def refresh(self, item):
        self.refreshed.append(item)


def test_mta_agent_heartbeat_persists_systemd_state(monkeypatch) -> None:
    node = SimpleNamespace(id=uuid4(), hostname='mta-002.email-engine.app', metadata_json={})
    check = SimpleNamespace(id=uuid4(), created_at=datetime.utcnow())

    class FakeReadinessService:
        def __init__(self, db) -> None:
            self.db = db

        def create(self, payload):
            assert payload.source == 'mta_agent'
            assert payload.result_json['systemd']['timer']['active_state'] == 'active'
            assert payload.result_json['revision']['revision'] == 'abc123def456'
            return check

    monkeypatch.setattr(agent_module, 'ManagedSmtpReadinessService', FakeReadinessService)

    result = ManagedSmtpAgentService(FakeDb(node)).heartbeat(
        node.id,
        MtaNodeHeartbeatRequest(
            status='ok',
            queue_depth=0,
            deferred_count=0,
            active_count=0,
            config_version='config-v1',
            applied_config_version='config-v1',
            payload_json={
                'queue_samples': [
                    {
                        'queue_id': 'ABC123DEF',
                        'sender': 'mta-smoke@email-engine.app',
                        'recipients': ['seed@example.com'],
                    }
                ],
                'logs': {
                    'entries': [
                        {'severity': 'deferred', 'line': 'postfix/smtp: status=deferred'}
                    ]
                },
                'systemd': {
                    'service': {'active_state': 'inactive', 'sub_state': 'dead'},
                    'timer': {
                        'active_state': 'active',
                        'sub_state': 'waiting',
                        'next_elapse': 'Fri 2026-06-19 00:34:09 UTC',
                    },
                },
                'revision': {'revision': 'abc123def456', 'dirty': False},
            },
        ),
    )

    assert result is check
    assert node.metadata_json['agent_service_active_state'] == 'inactive'
    assert node.metadata_json['agent_service_sub_state'] == 'dead'
    assert node.metadata_json['agent_timer_active_state'] == 'active'
    assert node.metadata_json['agent_timer_sub_state'] == 'waiting'
    assert node.metadata_json['agent_timer_next_elapse'] == 'Fri 2026-06-19 00:34:09 UTC'
    assert node.metadata_json['agent_code_revision'] == 'abc123def456'
    assert node.metadata_json['agent_code_dirty'] is False
    assert node.metadata_json['agent_queue_samples'] == [
        {
            'queue_id': 'ABC123DEF',
            'sender': 'mta-smoke@email-engine.app',
            'recipients': ['seed@example.com'],
        }
    ]
    assert node.metadata_json['agent_log_samples'] == [
        {'severity': 'deferred', 'line': 'postfix/smtp: status=deferred'}
    ]
