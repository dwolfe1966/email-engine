from datetime import datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

from email_platform.models.entities import (
    DeliveryRouteStatus,
    DeliveryRouteType,
    MtaOperationalStatus,
)
from email_platform.schemas.contracts import (
    ControlledExpansionApprovalRequest,
    DomainAuthenticationPlanRequest,
    DomainBlocklistScanRequest,
    DomainComplianceHoldRequest,
    DomainComplianceReleaseRequest,
    DomainDeliverabilityRead,
    DomainDkimKeyCreateRequest,
    DomainWarmupProgressionRequest,
    ManagedSmtpMaintenanceRequest,
    ManagedSmtpRoutingRulePromotionRequest,
    ManagedSmtpRoutingRuleUpsert,
)
from email_platform.services.delivery_routes import DeliveryRouteService, DnsLookupUnavailable


class FakeDb:
    def __init__(self, scalar_results=None, get_result=None) -> None:
        self.scalar_results = list(scalar_results or [])
        self.get_result = get_result
        self.committed = False
        self.refreshed = []

    def scalar(self, statement):
        if self.scalar_results:
            return self.scalar_results.pop(0)
        return None

    def get(self, model, item_id):
        return self.get_result

    def commit(self):
        self.committed = True

    def refresh(self, item):
        self.refreshed.append(item)


class FakeDkimKeyGenerator:
    def generate(self, key_size: int) -> tuple[str, str]:
        return (
            '-----BEGIN PRIVATE KEY-----\nfake-private-key\n-----END PRIVATE KEY-----\n',
            'fake-public-key',
        )


class FakeDnsResolver:
    def __init__(self, records=None, fail: bool = False) -> None:
        self.records = records or {}
        self.fail = fail

    def lookup(self, record_type: str, name: str) -> list[str]:
        if self.fail:
            raise DnsLookupUnavailable('dig unavailable')
        return self.records.get((record_type, name), [])


def test_delivery_route_selector_falls_back_to_settings_provider() -> None:
    service = DeliveryRouteService(FakeDb())

    selected = service.select_for_record(
        SimpleNamespace(to_email='recipient@example.com'),
        SimpleNamespace(email_provider='console'),
    )

    assert selected.route_type == 'console'
    assert selected.route_key == 'console'
    assert selected.route_id is None
    assert selected.source == 'settings'


def test_delivery_route_selector_maps_smtp_provider_to_smtp_relay() -> None:
    service = DeliveryRouteService(FakeDb())

    selected = service.select_for_record(
        SimpleNamespace(to_email='recipient@example.com'),
        SimpleNamespace(email_provider='smtp'),
    )

    assert selected.route_type == 'smtp_relay'
    assert selected.route_key == 'smtp'
    assert selected.source == 'settings'


def test_upsert_managed_smtp_routing_rule_preserves_route_config() -> None:
    route_id = uuid4()
    route = SimpleNamespace(
        id=route_id,
        name='managed-smtp-primary',
        config={
            'mta_ip_pool_id': str(uuid4()),
            'routing_rules': [
                {
                    'name': 'existing-rule',
                    'priority': 50,
                    'send_types': ['internal_test'],
                    'ip_pool_name': 'old-pool',
                }
            ],
        },
    )
    db = FakeDb(get_result=route)
    service = DeliveryRouteService(db)

    result = service.upsert_managed_smtp_routing_rule(
        route_id,
        ManagedSmtpRoutingRuleUpsert(
            name='gmail-scaleway',
            priority=10,
            send_types=['Transactional', 'internal_test'],
            sender_domains=['Sender@Email-Engine.App'],
            recipient_domains=['GMAIL.COM'],
            ip_pool_name='scaleway-transactional',
            preferred_providers=['Scaleway'],
            provider_preference_mode='fallback_allowed',
        ),
    )

    assert result is not None
    assert db.committed
    assert route.config['mta_ip_pool_id']
    assert [rule['name'] for rule in route.config['routing_rules']] == [
        'gmail-scaleway',
        'existing-rule',
    ]
    rule = route.config['routing_rules'][0]
    assert rule['send_types'] == ['transactional', 'internal_test']
    assert rule['sender_domains'] == ['email-engine.app']
    assert rule['recipient_domains'] == ['gmail.com']
    assert rule['preferred_providers'] == ['scaleway']
    assert rule['provider_preference_mode'] == 'fallback_allowed'


def test_upsert_managed_smtp_routing_rule_replaces_rule_by_name() -> None:
    route_id = uuid4()
    route = SimpleNamespace(
        id=route_id,
        name='managed-smtp-primary',
        config={
            'routing_rules': [
                {
                    'name': 'gmail-scaleway',
                    'priority': 100,
                    'ip_pool_name': 'old-pool',
                }
            ],
        },
    )
    service = DeliveryRouteService(FakeDb(get_result=route))

    result = service.upsert_managed_smtp_routing_rule(
        route_id,
        ManagedSmtpRoutingRuleUpsert(
            name='gmail-scaleway',
            priority=5,
            ip_pool_name='new-pool',
        ),
    )

    assert result is not None
    assert len(route.config['routing_rules']) == 1
    assert route.config['routing_rules'][0]['priority'] == 5
    assert route.config['routing_rules'][0]['ip_pool_name'] == 'new-pool'


def test_set_managed_smtp_routing_rule_enabled_updates_named_rule() -> None:
    route_id = uuid4()
    route = SimpleNamespace(
        id=route_id,
        name='managed-smtp-primary',
        config={
            'routing_rules': [
                {'name': 'gmail-scaleway', 'priority': 10, 'enabled': True},
                {'name': 'backup', 'priority': 20, 'enabled': True},
            ],
        },
    )
    db = FakeDb(get_result=route)
    service = DeliveryRouteService(db)

    result = service.set_managed_smtp_routing_rule_enabled(
        route_id,
        'gmail-scaleway',
        enabled=False,
    )

    assert result is not None
    assert db.committed
    assert route.config['routing_rules'][0]['enabled'] is False
    assert route.config['routing_rules'][1]['enabled'] is True


def test_delete_managed_smtp_routing_rule_removes_named_rule() -> None:
    route_id = uuid4()
    route = SimpleNamespace(
        id=route_id,
        name='managed-smtp-primary',
        config={
            'mta_ip_pool_id': str(uuid4()),
            'routing_rules': [
                {'name': 'gmail-scaleway', 'priority': 10},
                {'name': 'backup', 'priority': 20},
            ],
        },
    )
    db = FakeDb(get_result=route)
    service = DeliveryRouteService(db)

    result = service.delete_managed_smtp_routing_rule(route_id, 'gmail-scaleway')

    assert result is not None
    assert db.committed
    assert route.config['mta_ip_pool_id']
    assert [rule['name'] for rule in route.config['routing_rules']] == ['backup']


def test_managed_smtp_routing_rules_reports_same_priority_overlap() -> None:
    route_id = uuid4()
    route = SimpleNamespace(
        id=route_id,
        name='managed-smtp-primary',
        config={
            'routing_rules': [
                {
                    'name': 'gmail-scaleway',
                    'priority': 10,
                    'enabled': True,
                    'send_types': ['internal_test'],
                    'sender_domains': ['email-engine.app'],
                    'recipient_domains': ['gmail.com'],
                },
                {
                    'name': 'gmail-backup',
                    'priority': 10,
                    'enabled': True,
                    'send_types': ['internal_test'],
                    'sender_domains': ['Email-Engine.App'],
                    'recipient_domains': ['gmail.com'],
                },
            ],
        },
    )
    service = DeliveryRouteService(FakeDb(get_result=route))

    result = service.managed_smtp_routing_rules(route_id)

    assert result is not None
    assert len(result.conflicts) == 1
    assert result.conflicts[0]['code'] == 'ROUTING_RULE_OVERLAP'
    assert result.conflicts[0]['rule_names'] == ['gmail-scaleway', 'gmail-backup']


def test_managed_smtp_routing_rules_ignores_disabled_or_lower_priority_overlap() -> None:
    route_id = uuid4()
    route = SimpleNamespace(
        id=route_id,
        name='managed-smtp-primary',
        config={
            'routing_rules': [
                {'name': 'primary', 'priority': 10, 'send_types': ['internal_test']},
                {'name': 'backup', 'priority': 20, 'send_types': ['internal_test']},
                {
                    'name': 'disabled',
                    'priority': 10,
                    'enabled': False,
                    'send_types': ['internal_test'],
                },
            ],
        },
    )
    service = DeliveryRouteService(FakeDb(get_result=route))

    result = service.managed_smtp_routing_rules(route_id)

    assert result is not None
    assert result.conflicts == []


def test_routing_rule_promotion_preview_blocks_missing_pool() -> None:
    route_id = uuid4()
    route = SimpleNamespace(id=route_id, name='managed-smtp-primary', config={})
    service = DeliveryRouteService(FakeDb(get_result=route))

    result = service.preview_managed_smtp_routing_rule_promotion(
        route_id,
        ManagedSmtpRoutingRulePromotionRequest(
            rules=[
                ManagedSmtpRoutingRuleUpsert(
                    name='gmail-scaleway',
                    send_types=['campaign'],
                    recipient_domains=['gmail.com'],
                    ip_pool_name='missing-pool',
                )
            ],
            operator='ops@example.com',
            reason='preview missing pool',
        ),
    )

    assert result is not None
    assert result.status == 'blocked'
    assert result.blocking_issue_count == 1
    assert result.issues[0]['code'] == 'POOL_NOT_FOUND'


def test_routing_rule_promotion_draft_and_activate_writes_audit_metadata() -> None:
    route_id = uuid4()
    pool_id = uuid4()
    pool = SimpleNamespace(
        id=pool_id,
        name='scaleway-internal-test',
        status=MtaOperationalStatus.active,
    )
    route = SimpleNamespace(
        id=route_id,
        name='managed-smtp-primary',
        config={
            'routing_rules': [
                {'name': 'old-rule', 'priority': 50, 'enabled': True, 'ip_pool_name': 'old'}
            ]
        },
    )

    class PromotionDb(FakeDb):
        def get(self, model, item_id):
            if item_id == route_id:
                return route
            if item_id == pool_id:
                return pool
            return None

    db = PromotionDb()
    service = DeliveryRouteService(db)
    payload = ManagedSmtpRoutingRulePromotionRequest(
        rules=[
            ManagedSmtpRoutingRuleUpsert(
                name='gmail-scaleway',
                priority=10,
                send_types=['campaign'],
                recipient_domains=['gmail.com'],
                mta_ip_pool_id=pool_id,
                preferred_providers=['scaleway'],
            )
        ],
        operator='ops@example.com',
        reason='promote scaleway gmail traffic',
    )

    draft = service.draft_managed_smtp_routing_rule_promotion(route_id, payload)
    assert draft is not None
    assert draft.status == 'ready'
    assert route.config['routing_rules_draft']['rules'][0]['name'] == 'gmail-scaleway'

    activated = service.activate_managed_smtp_routing_rule_draft(route_id)

    assert activated is not None
    assert activated.status == 'activated'
    assert route.config['routing_rules'][0]['name'] == 'gmail-scaleway'
    assert route.config['routing_rules_previous']['rules'][0]['name'] == 'old-rule'
    assert route.config['routing_rules_audit_log'][-1]['action'] == 'activate'
    assert db.committed


def test_routing_rule_promotion_rollback_restores_previous_rules() -> None:
    route_id = uuid4()
    route = SimpleNamespace(
        id=route_id,
        name='managed-smtp-primary',
        config={
            'routing_rules': [{'name': 'new-rule', 'priority': 10, 'enabled': True}],
            'routing_rules_previous': {
                'rules': [{'name': 'old-rule', 'priority': 50, 'enabled': True}]
            },
        },
    )
    service = DeliveryRouteService(FakeDb(get_result=route))

    result = service.rollback_managed_smtp_routing_rules(
        route_id,
        operator='ops@example.com',
        reason='bad routing signal',
    )

    assert result is not None
    assert result.status == 'rolled_back'
    assert route.config['routing_rules'][0]['name'] == 'old-rule'
    assert route.config['routing_rules_previous']['rules'][0]['name'] == 'new-rule'
    assert route.config['routing_rules_audit_log'][-1]['action'] == 'rollback'


def test_delivery_route_selector_prefers_active_matching_route() -> None:
    route_id = uuid4()
    service = DeliveryRouteService(
        FakeDb(
            scalar_results=[
                None,
                SimpleNamespace(
                    id=route_id,
                    name='primary-console',
                    route_type=DeliveryRouteType.console,
                ),
            ],
        )
    )

    selected = service.select_for_record(
        SimpleNamespace(to_email='recipient@example.com'),
        SimpleNamespace(email_provider='console'),
    )

    assert selected.route_type == 'console'
    assert selected.route_key == 'primary-console'
    assert selected.route_id == route_id
    assert selected.name == 'primary-console'
    assert selected.source == 'delivery_routes'


def test_delivery_route_selector_prefers_matching_domain_policy_route() -> None:
    route_id = uuid4()
    policy_id = uuid4()
    route = SimpleNamespace(
        id=route_id,
        name='gmail-warmup',
        route_type=DeliveryRouteType.managed_smtp,
        status=DeliveryRouteStatus.active,
    )
    policy = SimpleNamespace(
        id=policy_id,
        domain='gmail.com',
        route_id=route_id,
        warmup_stage='stage_1',
        max_per_minute=25,
        max_concurrent=2,
        paused_until=None,
    )
    service = DeliveryRouteService(FakeDb(scalar_results=[policy], get_result=route))

    selected = service.select_for_record(
        SimpleNamespace(to_email='recipient@gmail.com'),
        SimpleNamespace(email_provider='console'),
    )

    assert selected.route_type == 'managed_smtp'
    assert selected.route_key == 'gmail-warmup'
    assert selected.route_id == route_id
    assert selected.domain_policy_id == policy_id
    assert selected.domain == 'gmail.com'
    assert selected.warmup_stage == 'stage_1'
    assert selected.max_per_minute == 25
    assert selected.max_concurrent == 2
    assert selected.source == 'domain_policy'


def test_delivery_route_selector_can_match_sender_domain_for_managed_smtp_route() -> None:
    route_id = uuid4()
    policy_id = uuid4()
    route = SimpleNamespace(
        id=route_id,
        name='scaleway-primary',
        route_type=DeliveryRouteType.managed_smtp,
        status=DeliveryRouteStatus.active,
    )
    policy = SimpleNamespace(
        id=policy_id,
        domain='email-engine.app',
        route_id=route_id,
        warmup_stage='stage_1',
        max_per_minute=10,
        max_concurrent=2,
        paused_until=None,
    )
    service = DeliveryRouteService(FakeDb(scalar_results=[policy], get_result=route))

    selected = service.select_for_record(
        SimpleNamespace(to_email='recipient@gmail.com'),
        SimpleNamespace(email_provider='sendgrid'),
        sender_domain='email-engine.app',
    )

    assert selected.route_type == 'managed_smtp'
    assert selected.route_key == 'scaleway-primary'
    assert selected.route_id == route_id
    assert selected.domain_policy_id == policy_id
    assert selected.domain == 'email-engine.app'
    assert selected.source == 'domain_policy'


def test_delivery_route_selector_ignores_paused_domain_policy() -> None:
    policy = SimpleNamespace(
        id=uuid4(),
        domain='gmail.com',
        route_id=uuid4(),
        warmup_stage='stage_1',
        max_per_minute=25,
        max_concurrent=2,
        paused_until=datetime.utcnow() + timedelta(hours=1),
    )
    service = DeliveryRouteService(FakeDb(scalar_results=[policy, None]))

    selected = service.select_for_record(
        SimpleNamespace(to_email='recipient@gmail.com'),
        SimpleNamespace(email_provider='console'),
    )

    assert selected.route_type == 'console'
    assert selected.route_key == 'console'
    assert selected.source == 'settings'


def test_delivery_claim_decision_blocks_paused_domain_policy() -> None:
    policy = SimpleNamespace(
        id=uuid4(),
        domain='gmail.com',
        paused_until=datetime.utcnow() + timedelta(minutes=10),
        max_per_minute=None,
        max_concurrent=None,
    )
    service = DeliveryRouteService(FakeDb(scalar_results=[policy]))

    decision = service.claim_decision(SimpleNamespace(to_email='recipient@gmail.com'))

    assert not decision.can_claim
    assert decision.reason == 'domain_policy_paused'
    assert decision.domain == 'gmail.com'
    assert decision.domain_policy_id == policy.id


def test_delivery_claim_decision_blocks_campaign_without_controlled_expansion() -> None:
    route = SimpleNamespace(id=uuid4(), route_type=DeliveryRouteType.managed_smtp)
    policy = SimpleNamespace(
        id=uuid4(),
        domain='email-engine.app',
        route_id=route.id,
        paused_until=None,
        max_per_minute=None,
        max_concurrent=None,
        metadata_json={},
    )
    service = DeliveryRouteService(FakeDb(scalar_results=[policy], get_result=route))

    decision = service.claim_decision(
        SimpleNamespace(to_email='recipient@gmail.com', campaign_id=uuid4()),
        sender_domain='email-engine.app',
    )

    assert not decision.can_claim
    assert decision.reason == 'controlled_expansion_not_approved'
    assert decision.domain == 'email-engine.app'
    assert decision.domain_policy_id == policy.id


def test_delivery_claim_decision_allows_campaign_with_controlled_expansion() -> None:
    route = SimpleNamespace(id=uuid4(), route_type=DeliveryRouteType.managed_smtp)
    policy = SimpleNamespace(
        id=uuid4(),
        domain='email-engine.app',
        route_id=route.id,
        paused_until=None,
        max_per_minute=None,
        max_concurrent=None,
        metadata_json={
            'controlled_expansion': {
                'status': 'active',
                'approved_daily_limit': 5,
                'send_types': ['campaign'],
                'expires_at': (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            }
        },
    )
    service = DeliveryRouteService(FakeDb(scalar_results=[policy, 2], get_result=route))

    decision = service.claim_decision(
        SimpleNamespace(to_email='recipient@gmail.com', campaign_id=uuid4()),
        sender_domain='email-engine.app',
    )

    assert decision.can_claim
    assert decision.domain == 'email-engine.app'
    assert decision.domain_policy_id == policy.id


def test_delivery_claim_decision_blocks_controlled_expansion_daily_limit() -> None:
    route = SimpleNamespace(id=uuid4(), route_type=DeliveryRouteType.managed_smtp)
    policy = SimpleNamespace(
        id=uuid4(),
        domain='email-engine.app',
        route_id=route.id,
        paused_until=None,
        max_per_minute=None,
        max_concurrent=None,
        metadata_json={
            'controlled_expansion': {
                'status': 'active',
                'approved_daily_limit': 2,
                'send_types': ['campaign'],
                'expires_at': (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            }
        },
    )
    service = DeliveryRouteService(FakeDb(scalar_results=[policy, 2], get_result=route))

    decision = service.claim_decision(
        SimpleNamespace(to_email='recipient@gmail.com', campaign_id=uuid4()),
        sender_domain='email-engine.app',
    )

    assert not decision.can_claim
    assert decision.reason == 'controlled_expansion_daily_limit'


def test_approve_controlled_expansion_writes_policy_metadata_and_audit_log() -> None:
    policy = SimpleNamespace(
        id=uuid4(),
        domain='email-engine.app',
        metadata_json={'existing': 'value'},
    )
    db = FakeDb(get_result=policy)
    service = DeliveryRouteService(db)

    result = service.approve_controlled_expansion(
        policy.id,
        ControlledExpansionApprovalRequest(
            approved_daily_limit=25,
            send_types=['Campaign'],
            expires_hours=12,
            operator='ops@example.com',
            reason='seed metrics clean',
            evidence={'pool': 'scaleway-internal-test'},
        ),
    )

    assert result is not None
    assert result.domain == 'email-engine.app'
    assert result.status == 'active'
    assert result.approved_daily_limit == 25
    assert result.send_types == ['campaign']
    assert result.operator == 'ops@example.com'
    assert policy.metadata_json['existing'] == 'value'
    approval = policy.metadata_json['controlled_expansion']
    assert approval['status'] == 'active'
    assert approval['evidence']['pool'] == 'scaleway-internal-test'
    assert policy.metadata_json['controlled_expansion_audit_log'][-1]['action'] == 'approve'
    assert db.committed
    assert db.refreshed == [policy]


def test_domain_compliance_hold_pauses_policy_and_writes_audit_metadata() -> None:
    previous_pause = datetime.utcnow() + timedelta(minutes=30)
    policy = SimpleNamespace(
        id=uuid4(),
        domain='gmail.com',
        paused_until=previous_pause,
        metadata_json={'existing': 'value'},
    )
    db = FakeDb(get_result=policy)
    service = DeliveryRouteService(db)

    updated = service.apply_domain_compliance_hold(
        policy.id,
        DomainComplianceHoldRequest(
            reason='Complaint spike from seed list',
            abuse_type='complaint_spike',
            operator='ops@example.com',
            paused_hours=4,
        ),
    )

    assert updated is policy
    assert policy.paused_until is not None
    assert policy.paused_until > datetime.utcnow() + timedelta(hours=3)
    assert policy.metadata_json['existing'] == 'value'
    hold = policy.metadata_json['compliance_hold']
    assert hold['status'] == 'active'
    assert hold['reason'] == 'Complaint spike from seed list'
    assert hold['abuse_type'] == 'complaint_spike'
    assert hold['operator'] == 'ops@example.com'
    audit_log = policy.metadata_json['compliance_audit_log']
    assert len(audit_log) == 1
    assert audit_log[0]['action'] == 'hold'
    assert audit_log[0]['previous_paused_until'] == previous_pause.isoformat()
    assert db.committed
    assert db.refreshed == [policy]


def test_domain_compliance_release_clears_pause_and_appends_audit_metadata() -> None:
    active_hold = {
        'status': 'active',
        'reason': 'Manual review',
        'abuse_type': 'manual_review',
    }
    policy = SimpleNamespace(
        id=uuid4(),
        domain='gmail.com',
        paused_until=datetime.utcnow() + timedelta(hours=2),
        metadata_json={
            'compliance_hold': active_hold,
            'compliance_audit_log': [{'action': 'hold'}],
        },
    )
    db = FakeDb(get_result=policy)
    service = DeliveryRouteService(db)

    updated = service.release_domain_compliance_hold(
        policy.id,
        DomainComplianceReleaseRequest(reason='Review cleared', operator='ops@example.com'),
    )

    assert updated is policy
    assert policy.paused_until is None
    hold = policy.metadata_json['compliance_hold']
    assert hold['status'] == 'released'
    assert hold['reason'] == 'Review cleared'
    assert hold['operator'] == 'ops@example.com'
    assert hold['previous_hold'] == active_hold
    audit_log = policy.metadata_json['compliance_audit_log']
    assert [entry['action'] for entry in audit_log] == ['hold', 'release']
    assert db.committed
    assert db.refreshed == [policy]


def test_delivery_claim_decision_blocks_per_minute_limit() -> None:
    policy = SimpleNamespace(
        id=uuid4(),
        domain='gmail.com',
        paused_until=None,
        max_per_minute=2,
        max_concurrent=None,
    )
    service = DeliveryRouteService(FakeDb(scalar_results=[policy, 2]))

    decision = service.claim_decision(SimpleNamespace(to_email='recipient@gmail.com'))

    assert not decision.can_claim
    assert decision.reason == 'domain_policy_max_per_minute'


def test_delivery_claim_decision_accounts_for_reserved_batch_count() -> None:
    policy = SimpleNamespace(
        id=uuid4(),
        domain='gmail.com',
        paused_until=None,
        max_per_minute=2,
        max_concurrent=None,
    )
    service = DeliveryRouteService(FakeDb(scalar_results=[policy, 1]))

    decision = service.claim_decision(
        SimpleNamespace(to_email='recipient@gmail.com'),
        reserved_count=1,
    )

    assert not decision.can_claim
    assert decision.reason == 'domain_policy_max_per_minute'


def test_delivery_claim_decision_allows_under_limits() -> None:
    policy = SimpleNamespace(
        id=uuid4(),
        domain='gmail.com',
        paused_until=None,
        max_per_minute=3,
        max_concurrent=2,
    )
    service = DeliveryRouteService(FakeDb(scalar_results=[policy, 1, 0]))

    decision = service.claim_decision(SimpleNamespace(to_email='recipient@gmail.com'))

    assert decision.can_claim
    assert decision.domain == 'gmail.com'
    assert decision.domain_policy_id == policy.id


def test_domain_authentication_plan_generates_dns_records_and_persists_metadata() -> None:
    policy = SimpleNamespace(
        id=uuid4(),
        domain='Example.COM',
        metadata_json={'existing': 'value'},
    )
    db = FakeDb(get_result=policy)
    service = DeliveryRouteService(db)

    plan = service.build_domain_authentication_plan(
        policy.id,
        DomainAuthenticationPlanRequest(
            dkim_selector='EE2',
            bounce_subdomain='returns',
            mta_hostname='smtp-staging.example.com',
            dkim_public_key='abc123',
        ),
    )

    assert plan is not None
    assert plan.domain == 'example.com'
    assert plan.dkim_selector == 'ee2'
    assert plan.bounce_domain == 'returns.example.com'
    assert db.committed
    assert db.refreshed == [policy]
    records = {(record.record_type, record.name): record.value for record in plan.dns_records}
    assert records[('TXT', 'ee2._domainkey.example.com')] == 'v=DKIM1; k=rsa; p=abc123'
    assert records[('TXT', 'example.com')] == 'v=spf1 mx -all'
    assert records[('TXT', '_dmarc.example.com')].startswith('v=DMARC1; p=none')
    assert records[('MX', 'returns.example.com')] == '10 smtp-staging.example.com'
    assert policy.metadata_json['existing'] == 'value'
    assert policy.metadata_json['domain_authentication']['bounce_domain'] == 'returns.example.com'


def test_domain_authentication_plan_returns_none_for_missing_policy() -> None:
    service = DeliveryRouteService(FakeDb(get_result=None))

    plan = service.build_domain_authentication_plan(
        uuid4(),
        DomainAuthenticationPlanRequest(),
    )

    assert plan is None


def test_create_domain_dkim_key_returns_private_key_once_and_persists_public_metadata() -> None:
    policy = SimpleNamespace(
        id=uuid4(),
        domain='example.com',
        metadata_json={},
    )
    db = FakeDb(get_result=policy)
    service = DeliveryRouteService(db, dkim_key_generator=FakeDkimKeyGenerator())

    result = service.create_domain_dkim_key(
        policy.id,
        DomainDkimKeyCreateRequest(dkim_selector='EE3', key_ref='vault://dkim/example/ee3'),
    )

    assert result is not None
    assert result.domain == 'example.com'
    assert result.dkim_selector == 'ee3'
    assert result.key_ref == 'vault://dkim/example/ee3'
    assert 'fake-private-key' in result.private_key_pem
    assert result.public_key == 'fake-public-key'
    assert result.dns_record.name == 'ee3._domainkey.example.com'
    assert policy.metadata_json['dkim_key']['key_ref'] == 'vault://dkim/example/ee3'
    assert policy.metadata_json['dkim_key']['public_key'] == 'fake-public-key'
    assert 'private' not in policy.metadata_json['dkim_key']
    assert db.committed
    assert db.refreshed == [policy]


def test_managed_smtp_identity_uses_bounce_domain_and_dkim_metadata() -> None:
    route = SimpleNamespace(id=uuid4(), route_type=DeliveryRouteType.managed_smtp)
    policy = SimpleNamespace(
        id=uuid4(),
        domain='example.com',
        route_id=route.id,
        metadata_json={
            'domain_authentication': {'bounce_domain': 'returns.example.com'},
            'dkim_key': {'selector': 'ee3', 'key_ref': 'vault://dkim/example/ee3'},
        },
    )
    record = SimpleNamespace(id=uuid4(), to_email='recipient@example.com')
    service = DeliveryRouteService(FakeDb(scalar_results=[policy], get_result=route))

    identity = service.managed_smtp_identity_for_record(record)

    assert identity is not None
    assert identity.domain == 'example.com'
    assert identity.bounce_domain == 'returns.example.com'
    assert identity.envelope_from == f'bounces+{record.id}@returns.example.com'
    assert identity.dkim_selector == 'ee3'
    assert identity.dkim_key_ref == 'vault://dkim/example/ee3'
    assert identity.dkim_signing_ready


def test_managed_smtp_identity_can_use_sender_domain_for_any_recipient() -> None:
    route = SimpleNamespace(id=uuid4(), route_type=DeliveryRouteType.managed_smtp)
    policy = SimpleNamespace(
        id=uuid4(),
        domain='email-engine.app',
        route_id=route.id,
        metadata_json={
            'domain_authentication': {'bounce_domain': 'returns-scaleway.email-engine.app'},
            'dkim_key': {'selector': 'ee2', 'key_ref': 'mta://mta-002/email-engine.app/ee2'},
        },
    )
    record = SimpleNamespace(id=uuid4(), to_email='recipient@gmail.com')
    service = DeliveryRouteService(FakeDb(scalar_results=[policy], get_result=route))

    identity = service.managed_smtp_identity_for_record(
        record,
        sender_domain='email-engine.app',
    )

    assert identity is not None
    assert identity.domain == 'email-engine.app'
    assert identity.bounce_domain == 'returns-scaleway.email-engine.app'
    assert identity.envelope_from == f'bounces+{record.id}@returns-scaleway.email-engine.app'
    assert identity.dkim_selector == 'ee2'


def test_verify_domain_authentication_checks_required_dns_records() -> None:
    policy = SimpleNamespace(
        id=uuid4(),
        domain='example.com',
        metadata_json={
            'domain_authentication': {
                'dns_records': [
                    {
                        'record_type': 'TXT',
                        'name': 'ee1._domainkey.example.com',
                        'value': 'v=DKIM1; k=rsa; p=abc123',
                        'purpose': 'DKIM',
                        'required': True,
                    },
                    {
                        'record_type': 'TXT',
                        'name': 'example.com',
                        'value': 'v=spf1 mx -all',
                        'purpose': 'SPF',
                        'required': True,
                    },
                ],
            },
        },
    )
    resolver = FakeDnsResolver(
        {
            ('TXT', 'ee1._domainkey.example.com'): ['"v=DKIM1; k=rsa; p=abc123"'],
            ('TXT', 'example.com'): ['v=spf1 mx -all'],
        }
    )
    service = DeliveryRouteService(FakeDb(get_result=policy), dns_resolver=resolver)

    result = service.verify_domain_authentication(policy.id)

    assert result is not None
    assert result.verified
    assert [record.status for record in result.records] == ['verified', 'verified']
    assert policy.metadata_json['domain_authentication_verification']['verified']


def test_verify_domain_authentication_reports_mismatch_and_unavailable_lookup() -> None:
    policy = SimpleNamespace(
        id=uuid4(),
        domain='example.com',
        metadata_json={
            'domain_authentication': {
                'dns_records': [
                    {
                        'record_type': 'TXT',
                        'name': 'example.com',
                        'value': 'v=spf1 mx -all',
                        'purpose': 'SPF',
                        'required': True,
                    },
                ],
            },
        },
    )
    mismatch = DeliveryRouteService(
        FakeDb(get_result=policy),
        dns_resolver=FakeDnsResolver(
            {('TXT', 'example.com'): ['v=spf1 include:_spf.example.com -all']}
        ),
    ).verify_domain_authentication(policy.id)
    unavailable = DeliveryRouteService(
        FakeDb(get_result=policy),
        dns_resolver=FakeDnsResolver(fail=True),
    ).verify_domain_authentication(policy.id)

    assert mismatch is not None
    assert not mismatch.verified
    assert mismatch.records[0].status == 'mismatch'
    assert unavailable is not None
    assert not unavailable.verified
    assert unavailable.records[0].status == 'unchecked'


def test_scan_domain_blocklists_updates_policy_metadata_from_dns_results() -> None:
    route = SimpleNamespace(
        id=uuid4(),
        config={'ip_addresses': ['192.0.2.10']},
    )
    policy = SimpleNamespace(
        id=uuid4(),
        domain='example.com',
        route_id=route.id,
        metadata_json={},
    )
    service = DeliveryRouteService(
        FakeDb(get_result=route),
        dns_resolver=FakeDnsResolver(
            {('A', '10.2.0.192.zen.spamhaus.org'): ['127.0.0.2']}
        ),
    )
    service.get_domain_policy = lambda policy_id: policy

    result = service.scan_domain_blocklists(
        policy.id,
        DomainBlocklistScanRequest(zones=['zen.spamhaus.org']),
    )

    assert result is not None
    assert result.status == 'listed'
    assert result.hits == ['192.0.2.10@zen.spamhaus.org']
    assert result.records[0].query == '10.2.0.192.zen.spamhaus.org'
    assert policy.metadata_json['blocklist_status'] == 'listed'
    assert policy.metadata_json['blocklist_hits'] == ['192.0.2.10@zen.spamhaus.org']
    assert policy.metadata_json['ip_addresses'] == ['192.0.2.10']
    assert policy.metadata_json['blocklist_checked_at']


def test_scan_domain_blocklists_marks_unavailable_dns_as_unknown() -> None:
    policy = SimpleNamespace(
        id=uuid4(),
        domain='example.com',
        route_id=None,
        metadata_json={'ip_addresses': ['192.0.2.10']},
    )
    service = DeliveryRouteService(
        FakeDb(get_result=None),
        dns_resolver=FakeDnsResolver(fail=True),
    )
    service.get_domain_policy = lambda policy_id: policy

    result = service.scan_domain_blocklists(
        policy.id,
        DomainBlocklistScanRequest(zones=['zen.spamhaus.org']),
    )

    assert result is not None
    assert result.status == 'unknown'
    assert result.records[0].status == 'unchecked'
    assert policy.metadata_json['blocklist_status'] == 'unknown'
    assert 'blocklist_checked_at' not in policy.metadata_json


def test_domain_reputation_dashboard_combines_policy_route_and_deliverability() -> None:
    route = SimpleNamespace(
        id=uuid4(),
        name='managed-smtp-primary',
        route_type=DeliveryRouteType.managed_smtp,
        config={'ip_pool': 'pool-a', 'ip_addresses': ['192.0.2.10']},
    )
    policy = SimpleNamespace(
        id=uuid4(),
        domain='example.com',
        route_id=route.id,
        warmup_stage='stage_1',
        max_per_minute=25,
        max_concurrent=2,
        paused_until=None,
        metadata_json={
            'domain_authentication_verification': {'verified': True},
            'blocklist_checked_at': '2026-06-10T12:00:00',
            'warmup_daily_limit': 100,
            'warmup_stage_order': 1,
        },
    )
    deliverability = DomainDeliverabilityRead(
        domain='example.com',
        provider='managed_smtp',
        send_record_count=100,
        queued_count=0,
        sent_count=100,
        failed_count=0,
        suppressed_count=0,
        delivered_count=95,
        opened_count=20,
        clicked_count=5,
        bounced_count=1,
        complained_count=0,
        unsubscribed_count=0,
        open_rate=0.2,
        click_rate=0.05,
        bounce_rate=0.01,
    )
    service = DeliveryRouteService(FakeDb(get_result=route))
    service.get_domain_policy = lambda policy_id: policy

    dashboard = service.domain_reputation_dashboard(policy.id, deliverability=deliverability)

    assert dashboard is not None
    assert dashboard.domain == 'example.com'
    assert dashboard.route_name == 'managed-smtp-primary'
    assert dashboard.ip_pool == 'pool-a'
    assert dashboard.ip_addresses == ['192.0.2.10']
    assert dashboard.blocklist_status == 'clear'
    assert dashboard.warmup_status == 'active'
    assert dashboard.warmup_daily_limit == 100
    assert dashboard.warmup_stage_order == 1
    assert dashboard.authentication_status == 'verified'
    assert dashboard.reputation_status == 'healthy'
    assert dashboard.throttle_status == 'limited'
    assert dashboard.bounce_rate == 0.01
    assert dashboard.complaint_rate == 0.0
    assert dashboard.recommendations == []


def test_domain_reputation_dashboard_flags_risk_and_missing_controls() -> None:
    policy = SimpleNamespace(
        id=uuid4(),
        domain='example.com',
        route_id=None,
        warmup_stage=None,
        max_per_minute=None,
        max_concurrent=None,
        paused_until=None,
        metadata_json={
            'compliance_hold': {
                'status': 'active',
                'reason': 'Complaint spike review',
            }
        },
    )
    deliverability = DomainDeliverabilityRead(
        domain='example.com',
        provider='managed_smtp',
        send_record_count=100,
        queued_count=0,
        sent_count=100,
        failed_count=10,
        suppressed_count=1,
        delivered_count=80,
        opened_count=10,
        clicked_count=1,
        bounced_count=7,
        complained_count=1,
        unsubscribed_count=0,
        open_rate=0.1,
        click_rate=0.01,
        bounce_rate=0.07,
    )
    service = DeliveryRouteService(FakeDb(get_result=None))
    service.get_domain_policy = lambda policy_id: policy

    dashboard = service.domain_reputation_dashboard(policy.id, deliverability=deliverability)

    assert dashboard is not None
    assert dashboard.authentication_status == 'pending'
    assert dashboard.reputation_status == 'risk'
    assert dashboard.throttle_status == 'unlimited'
    assert dashboard.compliance_status == 'hold'
    assert dashboard.compliance_reason == 'Complaint spike review'
    assert dashboard.complaint_rate == 0.01
    assert (
        'Resolve or release the compliance hold before managed-SMTP sending resumes.'
        in dashboard.recommendations
    )
    assert 'Assign an IP pool before production managed-SMTP sends.' in dashboard.recommendations
    assert 'Attach sending IP addresses before blocklist preflight.' in dashboard.recommendations
    assert (
        'Run blocklist checks for assigned IPs before production sends.'
        in dashboard.recommendations
    )
    assert 'Set throttle limits before staging or production sends.' in dashboard.recommendations


def test_domain_reputation_dashboard_blocks_listed_ips_and_holds_warmup() -> None:
    route = SimpleNamespace(
        id=uuid4(),
        name='managed-smtp-primary',
        route_type=DeliveryRouteType.managed_smtp,
        config={'ip_pool': 'pool-a', 'ip_addresses': ['192.0.2.10']},
    )
    policy = SimpleNamespace(
        id=uuid4(),
        domain='example.com',
        route_id=route.id,
        warmup_stage='stage_1',
        max_per_minute=25,
        max_concurrent=2,
        paused_until=None,
        metadata_json={
            'domain_authentication_verification': {'verified': True},
            'blocklist_hits': ['zen.spamhaus.org'],
            'blocklist_checked_at': '2026-06-10T12:00:00',
        },
    )
    deliverability = DomainDeliverabilityRead(
        domain='example.com',
        provider='managed_smtp',
        send_record_count=100,
        queued_count=0,
        sent_count=100,
        failed_count=0,
        suppressed_count=0,
        delivered_count=90,
        opened_count=10,
        clicked_count=2,
        bounced_count=6,
        complained_count=0,
        unsubscribed_count=0,
        open_rate=0.1,
        click_rate=0.02,
        bounce_rate=0.06,
    )
    service = DeliveryRouteService(FakeDb(get_result=route))
    service.get_domain_policy = lambda policy_id: policy

    dashboard = service.domain_reputation_dashboard(policy.id, deliverability=deliverability)

    assert dashboard is not None
    assert dashboard.blocklist_status == 'listed'
    assert dashboard.blocklist_hits == ['zen.spamhaus.org']
    assert dashboard.reputation_status == 'risk'
    assert dashboard.warmup_status == 'hold'
    assert (
        'Pause managed-SMTP scaling until listed IPs or domains are remediated.'
        in dashboard.recommendations
    )
    assert (
        'Hold warmup progression until bounce and complaint rates recover.'
        in dashboard.recommendations
    )


def test_progress_domain_warmup_advances_healthy_stage() -> None:
    policy = SimpleNamespace(
        id=uuid4(),
        domain='example.com',
        warmup_stage='stage_1',
        metadata_json={'warmup_daily_limit': 100, 'warmup_stage_order': 1},
    )
    deliverability = DomainDeliverabilityRead(
        domain='example.com',
        provider='managed_smtp',
        send_record_count=100,
        queued_count=0,
        sent_count=100,
        failed_count=0,
        suppressed_count=0,
        delivered_count=98,
        opened_count=10,
        clicked_count=2,
        bounced_count=1,
        complained_count=0,
        unsubscribed_count=0,
        open_rate=0.1,
        click_rate=0.02,
        bounce_rate=0.01,
    )
    db = FakeDb(get_result=policy)
    service = DeliveryRouteService(db)

    result = service.progress_domain_warmup(
        policy.id,
        DomainWarmupProgressionRequest(
            gate_evidence={
                'controlled_seed_proof': {'value': 'Expand cautiously'},
                'expansion_pool_gate': {'value': 'Ready'},
                'feedback_gate': {'value': 'Quiet', 'warning_count': 0},
            }
        ),
        deliverability=deliverability,
    )

    assert result is not None
    assert result.action == 'advance'
    assert result.current_stage == 'stage_2'
    assert result.current_daily_limit == 200
    assert policy.warmup_stage == 'stage_2'
    assert policy.metadata_json['warmup_stage_order'] == 2
    assert policy.metadata_json['warmup_daily_limit'] == 200
    assert policy.metadata_json['warmup_audit_log'][-1]['action'] == 'advance'
    assert policy.metadata_json['warmup_audit_log'][-1]['gate_evidence']['feedback_gate']['value'] == 'Quiet'
    assert db.committed


def test_progress_domain_warmup_holds_on_complaint_rate() -> None:
    policy = SimpleNamespace(
        id=uuid4(),
        domain='example.com',
        warmup_stage='stage_1',
        metadata_json={'warmup_daily_limit': 100, 'warmup_stage_order': 1},
    )
    deliverability = DomainDeliverabilityRead(
        domain='example.com',
        provider='managed_smtp',
        send_record_count=100,
        queued_count=0,
        sent_count=100,
        failed_count=0,
        suppressed_count=0,
        delivered_count=95,
        opened_count=10,
        clicked_count=2,
        bounced_count=1,
        complained_count=1,
        unsubscribed_count=0,
        open_rate=0.1,
        click_rate=0.02,
        bounce_rate=0.01,
    )
    service = DeliveryRouteService(FakeDb(get_result=policy))

    result = service.progress_domain_warmup(
        policy.id,
        DomainWarmupProgressionRequest(),
        deliverability=deliverability,
    )

    assert result is not None
    assert result.action == 'hold'
    assert result.status == 'hold'
    assert result.current_stage == 'stage_1'
    assert policy.warmup_stage == 'stage_1'
    assert policy.metadata_json['warmup_status'] == 'hold'
    assert policy.metadata_json['warmup_hold_reason'] == result.reason


def test_managed_smtp_maintenance_scans_and_advances_warmup() -> None:
    route = SimpleNamespace(
        id=uuid4(),
        route_type=DeliveryRouteType.managed_smtp,
        config={'ip_addresses': ['192.0.2.10']},
    )
    policy = SimpleNamespace(
        id=uuid4(),
        domain='example.com',
        route_id=route.id,
        warmup_stage='stage_1',
        metadata_json={'warmup_daily_limit': 100, 'warmup_stage_order': 1},
    )
    deliverability = DomainDeliverabilityRead(
        domain='example.com',
        provider='managed_smtp',
        send_record_count=100,
        queued_count=0,
        sent_count=100,
        failed_count=0,
        suppressed_count=0,
        delivered_count=98,
        opened_count=10,
        clicked_count=2,
        bounced_count=1,
        complained_count=0,
        unsubscribed_count=0,
        open_rate=0.1,
        click_rate=0.02,
        bounce_rate=0.01,
    )
    service = DeliveryRouteService(FakeDb(get_result=route), dns_resolver=FakeDnsResolver())
    service.list_domain_policies = lambda limit=100, **kwargs: [policy]
    service.get_domain_policy = lambda policy_id: policy

    result = service.run_managed_smtp_maintenance(
        ManagedSmtpMaintenanceRequest(zones=['zen.spamhaus.org']),
        deliverability_by_domain={'example.com': deliverability},
    )

    assert result.processed_count == 1
    assert result.blocklist_scan_count == 1
    assert result.warmup_progression_count == 1
    assert result.skipped_count == 0
    assert result.results[0].blocklist_status == 'clear'
    assert result.results[0].warmup_action == 'advance'
    assert result.results[0].warmup_stage == 'stage_2'
    assert result.results[0].warmup_gate_evidence_key == 'blocklist_gate,domain_metrics,maintenance'
    assert policy.metadata_json['blocklist_status'] == 'clear'
    assert policy.metadata_json['warmup_stage_order'] == 2
    audit_entry = policy.metadata_json['warmup_audit_log'][-1]
    assert audit_entry['gate_evidence']['maintenance']['operator'] == 'managed_smtp_maintenance'
    assert audit_entry['gate_evidence']['domain_metrics']['ready'] is True
    assert audit_entry['gate_evidence']['blocklist_gate']['status'] == 'clear'


def test_managed_smtp_maintenance_skips_non_managed_smtp_routes() -> None:
    route = SimpleNamespace(
        id=uuid4(),
        route_type=DeliveryRouteType.smtp_relay,
        config={},
    )
    policy = SimpleNamespace(
        id=uuid4(),
        domain='example.com',
        route_id=route.id,
        warmup_stage='stage_1',
        metadata_json={},
    )
    service = DeliveryRouteService(FakeDb(get_result=route))
    service.list_domain_policies = lambda limit=100, **kwargs: [policy]

    result = service.run_managed_smtp_maintenance(ManagedSmtpMaintenanceRequest())

    assert result.processed_count == 0
    assert result.skipped_count == 1
    assert result.results[0].skipped_reason == 'not_managed_smtp'
