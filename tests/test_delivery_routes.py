from datetime import datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

from email_platform.models.entities import DeliveryRouteStatus, DeliveryRouteType
from email_platform.schemas.contracts import (
    DomainComplianceHoldRequest,
    DomainComplianceReleaseRequest,
    DomainDeliverabilityRead,
    DomainAuthenticationPlanRequest,
    DomainDkimKeyCreateRequest,
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


def test_domain_reputation_dashboard_combines_policy_route_and_deliverability() -> None:
    route = SimpleNamespace(
        id=uuid4(),
        name='managed-smtp-primary',
        route_type=DeliveryRouteType.managed_smtp,
        config={'ip_pool': 'pool-a'},
    )
    policy = SimpleNamespace(
        id=uuid4(),
        domain='example.com',
        route_id=route.id,
        warmup_stage='stage_1',
        max_per_minute=25,
        max_concurrent=2,
        paused_until=None,
        metadata_json={'domain_authentication_verification': {'verified': True}},
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
    assert 'Set throttle limits before staging or production sends.' in dashboard.recommendations
