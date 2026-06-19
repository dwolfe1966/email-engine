from types import SimpleNamespace
from uuid import uuid4

from email_platform.models.entities import (
    EmailSendRecord,
    EmailSendStatus,
    MtaIpPoolType,
    MtaProviderType,
)
from email_platform.schemas.contracts import (
    ManagedSmtpResolvedRoute,
    ManagedSmtpRouteBlockReason,
    ManagedSmtpRouteResolutionRead,
)
from email_platform.services import delivery as delivery_module
from email_platform.services.delivery import DeliveryService
from email_platform.services.delivery_routes import ManagedSmtpIdentity


class FakeDb:
    def __init__(self) -> None:
        self.added = []
        self.flush_count = 0
        self.records = []
        self.commit_count = 0

    def add(self, item) -> None:
        self.added.append(item)

    def flush(self) -> None:
        self.flush_count += 1

    def commit(self) -> None:
        self.commit_count += 1

    def scalars(self, statement):
        return SimpleNamespace(all=lambda: self.records)


class FakeRouteService:
    def select_for_record(self, record, settings, sender_domain=None):
        return SimpleNamespace(
            route_type=settings.email_provider,
            route_key=settings.email_provider,
            route_id=None,
            domain_policy_id=None,
            name=None,
            domain='example.com',
            warmup_stage=None,
            max_per_minute=None,
            max_concurrent=None,
            source='settings',
        )

    def managed_smtp_identity_for_record(self, record, sender_domain=None):
        return None


class SelectiveRouteService:
    def __init__(self, blocked_domain: str) -> None:
        self.blocked_domain = blocked_domain

    def claim_decision(self, record, reserved_count=0):
        domain = record.to_email.rsplit('@', 1)[-1].lower()
        return SimpleNamespace(
            can_claim=domain != self.blocked_domain,
            reason='domain_policy_max_per_minute' if domain == self.blocked_domain else None,
            domain=domain,
            domain_policy_id=uuid4() if domain == self.blocked_domain else None,
        )


class FakeManagedSmtpRoutingService:
    def __init__(self, result) -> None:
        self.result = result
        self.requests = []

    def resolve(self, payload):
        self.requests.append(payload)
        return self.result


class FailingProvider:
    def send(self, message):
        raise AssertionError('provider send should not be called')


class FailingTemplateService:
    def get(self, template_id):
        raise AssertionError('template lookup should not be called')


class NoopEventService:
    def record_no_commit(self, payload):
        raise AssertionError('event recording should not be called')


class CaptureManagedSmtpProvider:
    calls = []

    def __init__(self, settings, *, host=None, port=None, provider_name='smtp') -> None:
        self.settings = settings
        self.host = host
        self.port = port
        self.provider_name = provider_name
        self.__class__.calls.append(self)

    def send(self, message):
        return SimpleNamespace(
            provider=self.provider_name,
            provider_message_id='managed-smtp-message',
            status_code=250,
        )


def test_delivery_service_claim_records_skips_throttled_domains() -> None:
    db = FakeDb()
    blocked = EmailSendRecord(
        id=uuid4(),
        send_job_id=uuid4(),
        contact_id=uuid4(),
        template_id=uuid4(),
        status=EmailSendStatus.queued,
        to_email='blocked@gmail.com',
        variables={},
    )
    allowed = EmailSendRecord(
        id=uuid4(),
        send_job_id=uuid4(),
        contact_id=uuid4(),
        template_id=uuid4(),
        status=EmailSendStatus.queued,
        to_email='allowed@example.com',
        variables={},
    )
    db.records = [blocked, allowed]
    service = DeliveryService.__new__(DeliveryService)
    service.db = db
    service.route_service = SelectiveRouteService('gmail.com')

    claim_result = service._claim_records(limit=10)

    assert claim_result.records == [allowed]
    assert claim_result.skipped_record_ids == [str(blocked.id)]
    assert blocked.status == EmailSendStatus.queued
    assert allowed.status == EmailSendStatus.sending
    assert len(db.added) == 1
    assert db.added[0].send_record_id == blocked.id
    assert db.added[0].status == 'claim_blocked'
    assert db.added[0].route_type == 'queue_control'
    assert db.added[0].route_key == 'domain_policy_max_per_minute'
    assert db.added[0].metadata_json['reason'] == 'domain_policy_max_per_minute'
    assert db.flush_count == 1


def test_delivery_service_starts_attempt_with_route_context() -> None:
    db = FakeDb()
    service = DeliveryService.__new__(DeliveryService)
    service.db = db
    service.settings = SimpleNamespace(email_provider='console')
    service.route_service = FakeRouteService()
    record = EmailSendRecord(
        id=uuid4(),
        send_job_id=uuid4(),
        contact_id=uuid4(),
        template_id=uuid4(),
        status=EmailSendStatus.sending,
        to_email='recipient@example.com',
        variables={},
        attempt_count=2,
    )

    attempt = service._start_attempt(record)

    assert db.added == [attempt]
    assert db.flush_count == 1
    assert attempt.send_record_id == record.id
    assert attempt.send_job_id == record.send_job_id
    assert attempt.attempt_number == 2
    assert attempt.route_type == 'console'
    assert attempt.route_key == 'console'
    assert attempt.status == 'submitting'
    assert attempt.metadata_json['route_source'] == 'settings'
    assert attempt.metadata_json['to_domain'] == 'example.com'


def test_delivery_service_starts_managed_smtp_attempt_with_resolved_mta_context() -> None:
    db = FakeDb()
    route_id = uuid4()
    policy_id = uuid4()
    provider_account_id = uuid4()
    pool_id = uuid4()
    node_id = uuid4()
    service = DeliveryService.__new__(DeliveryService)
    service.db = db
    service.settings = SimpleNamespace(
        email_provider='console',
        default_from_email='mta-smoke@email-engine.app',
    )
    service.route_service = SimpleNamespace(
        select_for_record=lambda _record, _settings, sender_domain=None: SimpleNamespace(
            route_type='managed_smtp',
            route_key='managed-smtp-primary',
            route_id=route_id,
            domain_policy_id=policy_id,
            name='managed-smtp-primary',
            domain=sender_domain,
            warmup_stage='stage_1',
            max_per_minute=25,
            max_concurrent=2,
            source='domain_policy',
        )
    )
    service.managed_smtp_routing_service = FakeManagedSmtpRoutingService(
        ManagedSmtpRouteResolutionRead(
            ok=True,
            route=ManagedSmtpResolvedRoute(
                domain='example.com',
                delivery_route_id=route_id,
                delivery_route_name='managed-smtp-primary',
                domain_policy_id=policy_id,
                ip_pool_id=pool_id,
                ip_pool_name='warmup-a',
                ip_pool_type=MtaIpPoolType.warmup,
                mta_node_id=node_id,
                mta_node_name='mta-001',
                provider_account_id=provider_account_id,
                provider=MtaProviderType.aws,
                hostname='mta-001.email-engine.example',
                public_ipv4='192.0.2.10',
                submission_host='mta-001.email-engine.example',
                submission_port=587,
                auth_secret_ref='secret/mta-001/submission',
            ),
        )
    )
    record = EmailSendRecord(
        id=uuid4(),
        send_job_id=uuid4(),
        contact_id=uuid4(),
        template_id=uuid4(),
        status=EmailSendStatus.sending,
        to_email='recipient@gmail.com',
        variables={},
        attempt_count=1,
    )

    attempt = service._start_attempt(record)

    assert attempt.route_type == 'managed_smtp'
    assert attempt.metadata_json['mta_route_resolved'] is True
    assert attempt.metadata_json['mta_provider'] == 'aws'
    assert attempt.metadata_json['mta_provider_account_id'] == str(provider_account_id)
    assert attempt.metadata_json['mta_ip_pool_name'] == 'warmup-a'
    assert attempt.metadata_json['mta_node_name'] == 'mta-001'
    assert attempt.metadata_json['mta_submission_port'] == 587
    assert service.managed_smtp_routing_service.requests[0].from_domain == 'email-engine.app'
    assert service.managed_smtp_routing_service.requests[0].recipient_domain == 'gmail.com'
    assert service.managed_smtp_routing_service.requests[0].route_id == route_id


def test_delivery_service_starts_managed_smtp_attempt_with_route_block_reason() -> None:
    db = FakeDb()
    service = DeliveryService.__new__(DeliveryService)
    service.db = db
    service.settings = SimpleNamespace(email_provider='console')
    service.route_service = SimpleNamespace(
        select_for_record=lambda _record, _settings, sender_domain=None: SimpleNamespace(
            route_type='managed_smtp',
            route_key='managed-smtp-primary',
            route_id=uuid4(),
            domain_policy_id=uuid4(),
            name='managed-smtp-primary',
            domain='example.com',
            warmup_stage=None,
            max_per_minute=None,
            max_concurrent=None,
            source='domain_policy',
        )
    )
    service.managed_smtp_routing_service = FakeManagedSmtpRoutingService(
        ManagedSmtpRouteResolutionRead(
            ok=False,
            reason=ManagedSmtpRouteBlockReason(
                code='NO_HEALTHY_MTA_NODE',
                message='No active MTA node with passing readiness is available for this pool.',
                details={'ip_pool_id': str(uuid4())},
            ),
        )
    )
    record = EmailSendRecord(
        id=uuid4(),
        send_job_id=uuid4(),
        contact_id=uuid4(),
        template_id=uuid4(),
        status=EmailSendStatus.sending,
        to_email='recipient@example.com',
        variables={},
        attempt_count=1,
    )

    attempt = service._start_attempt(record)

    assert attempt.metadata_json['mta_route_resolved'] is False
    assert attempt.metadata_json['mta_route_block_code'] == 'NO_HEALTHY_MTA_NODE'
    assert 'passing readiness' in attempt.metadata_json['mta_route_block_message']


def test_delivery_service_fails_closed_for_blocked_managed_smtp_route() -> None:
    db = FakeDb()
    record = EmailSendRecord(
        id=uuid4(),
        send_job_id=uuid4(),
        contact_id=uuid4(),
        template_id=uuid4(),
        status=EmailSendStatus.queued,
        to_email='recipient@example.com',
        variables={},
        attempt_count=0,
        max_attempts=3,
    )
    service = DeliveryService.__new__(DeliveryService)
    service.db = db
    service.settings = SimpleNamespace(email_provider='console')
    service.provider = FailingProvider()
    service.template_service = FailingTemplateService()
    service.event_service = NoopEventService()
    service.route_service = SimpleNamespace(
        claim_decision=lambda _record, reserved_count=0: SimpleNamespace(
            can_claim=True,
            reason=None,
            domain='example.com',
            domain_policy_id=None,
        ),
        select_for_record=lambda _record, _settings, sender_domain=None: SimpleNamespace(
            route_type='managed_smtp',
            route_key='managed-smtp-primary',
            route_id=uuid4(),
            domain_policy_id=uuid4(),
            name='managed-smtp-primary',
            domain='example.com',
            warmup_stage=None,
            max_per_minute=None,
            max_concurrent=None,
            source='domain_policy',
        ),
    )
    service.managed_smtp_routing_service = FakeManagedSmtpRoutingService(
        ManagedSmtpRouteResolutionRead(
            ok=False,
            reason=ManagedSmtpRouteBlockReason(
                code='DOMAIN_NOT_READY',
                message='Domain authentication has not been verified.',
                details={'domain': 'example.com'},
            ),
        )
    )
    db.records = [record]

    result = service.process_queued(limit=1)

    assert result.claimed_count == 1
    assert result.sent_count == 0
    assert result.failed_count == 1
    assert record.status == EmailSendStatus.failed
    assert record.error_message is not None
    assert 'Managed SMTP route blocked (DOMAIN_NOT_READY)' in record.error_message
    attempt = db.added[0]
    assert attempt.status == 'failed'
    assert attempt.metadata_json['mta_route_resolved'] is False
    assert attempt.metadata_json['mta_route_block_code'] == 'DOMAIN_NOT_READY'
    assert db.commit_count == 1


def test_delivery_service_prepares_managed_smtp_envelope_and_signing_headers() -> None:
    service = DeliveryService.__new__(DeliveryService)
    record = EmailSendRecord(
        id=uuid4(),
        send_job_id=uuid4(),
        contact_id=uuid4(),
        template_id=uuid4(),
        status=EmailSendStatus.sending,
        to_email='recipient@example.com',
        variables={},
        attempt_count=1,
    )
    attempt = SimpleNamespace(
        route_type='managed_smtp',
        metadata_json={},
    )
    service.route_service = SimpleNamespace(
        managed_smtp_identity_for_record=lambda _record, sender_domain=None: ManagedSmtpIdentity(
            domain='example.com',
            bounce_domain='returns.example.com',
            envelope_from=f'bounces+{record.id}@returns.example.com',
            dkim_selector='ee3',
            dkim_key_ref='vault://dkim/example/ee3',
            dkim_signing_ready=True,
        )
    )

    options = service._managed_smtp_message_options(record, attempt)

    assert options['envelope_from'] == f'bounces+{record.id}@returns.example.com'
    assert options['headers']['X-Email-Engine-Route'] == 'managed_smtp'
    assert options['headers']['X-Email-Engine-DKIM-Selector'] == 'ee3'
    assert options['headers']['X-Email-Engine-DKIM-Key-Ref'] == 'vault://dkim/example/ee3'
    assert attempt.metadata_json['bounce_domain'] == 'returns.example.com'
    assert attempt.metadata_json['envelope_from'] == f'bounces+{record.id}@returns.example.com'
    assert attempt.metadata_json['dkim_signing_ready'] is True
    assert service._managed_smtp_event_metadata(attempt)['dkim_selector'] == 'ee3'


def test_delivery_service_uses_resolved_mta_submission_provider(monkeypatch) -> None:
    monkeypatch.setattr(delivery_module, 'SmtpEmailProvider', CaptureManagedSmtpProvider)
    CaptureManagedSmtpProvider.calls = []
    service = DeliveryService.__new__(DeliveryService)
    service.settings = SimpleNamespace(
        smtp_host=None,
        smtp_port=587,
        smtp_use_tls=True,
        smtp_username='mta-user',
        smtp_password='mta-password',
    )
    service.provider = FailingProvider()
    attempt = SimpleNamespace(
        route_type='managed_smtp',
        metadata_json={
            'mta_route_resolved': True,
            'mta_submission_host': 'mta-001.example.com',
            'mta_submission_port': 2525,
        },
    )

    provider = service._submission_provider_for_attempt(attempt)

    assert isinstance(provider, CaptureManagedSmtpProvider)
    assert provider.host == 'mta-001.example.com'
    assert provider.port == 2525
    assert provider.provider_name == 'managed_smtp'
    assert attempt.metadata_json['mta_submission_provider'] == 'managed_smtp'


def test_delivery_service_keeps_default_provider_for_unresolved_managed_smtp_attempt() -> None:
    service = DeliveryService.__new__(DeliveryService)
    service.provider = object()
    attempt = SimpleNamespace(
        route_type='managed_smtp',
        metadata_json={
            'mta_route_resolved': False,
            'mta_submission_host': 'mta-001.example.com',
            'mta_submission_port': 587,
        },
    )

    assert service._submission_provider_for_attempt(attempt) is service.provider
    assert 'mta_submission_provider' not in attempt.metadata_json


def test_delivery_service_marks_retryable_failure_attempt_deferred() -> None:
    service = DeliveryService.__new__(DeliveryService)
    record = EmailSendRecord(
        id=uuid4(),
        send_job_id=uuid4(),
        contact_id=uuid4(),
        template_id=uuid4(),
        status=EmailSendStatus.sending,
        to_email='recipient@example.com',
        variables={},
        attempt_count=1,
        max_attempts=3,
    )
    attempt = SimpleNamespace(
        status='submitting',
        provider=None,
        provider_message_id=None,
        smtp_response_code=None,
        smtp_response=None,
        error_message=None,
        metadata_json={},
        completed_at=None,
    )

    service._handle_failure(record, attempt, 'temporary provider failure')

    assert record.status == EmailSendStatus.deferred
    assert record.next_attempt_at is not None
    assert attempt.status == 'deferred'
    assert attempt.error_message == 'temporary provider failure'
    assert 'next_attempt_at' in attempt.metadata_json


def test_delivery_service_marks_terminal_failure_attempt_failed() -> None:
    service = DeliveryService.__new__(DeliveryService)
    record = EmailSendRecord(
        id=uuid4(),
        send_job_id=uuid4(),
        contact_id=uuid4(),
        template_id=uuid4(),
        status=EmailSendStatus.sending,
        to_email='recipient@example.com',
        variables={},
        attempt_count=3,
        max_attempts=3,
    )
    attempt = SimpleNamespace(
        status='submitting',
        provider=None,
        provider_message_id=None,
        smtp_response_code=None,
        smtp_response=None,
        error_message=None,
        metadata_json={},
        completed_at=None,
    )

    service._handle_failure(record, attempt, 'permanent provider failure')

    assert record.status == EmailSendStatus.failed
    assert record.next_attempt_at is None
    assert attempt.status == 'failed'
    assert attempt.error_message == 'permanent provider failure'
