from types import SimpleNamespace
from uuid import uuid4

from email_platform.models.entities import DeliveryAttempt, EmailSendRecord, EmailSendStatus
from email_platform.providers.email import EmailDeliveryResult
from email_platform.services import sending as sending_module
from email_platform.services.sending import SendingService


class FakeProvider:
    def __init__(self) -> None:
        self.message = None

    def send(self, message):
        self.message = message
        return EmailDeliveryResult(
            provider='fake',
            provider_message_id='msg_123',
            status_code=202,
        )


class FakeTemplateService:
    def __init__(self, template_id):
        self.template_id = template_id
        self.render_context = None

    def get(self, template_id):
        if template_id != self.template_id:
            return None
        return SimpleNamespace(id=template_id)

    def variables_for_template(self, template_id):
        if template_id != self.template_id:
            return None
        return SimpleNamespace(
            sample_variables={
                'first_name': 'Sample',
                'order_number': 'SM-1001',
                'order_items': [
                    {'name': 'Starter plan', 'quantity': 1, 'total': '$49.00'}
                ],
            }
        )

    def render(self, template, variables):
        self.render_context = variables
        rows = ''.join(
            f'<tr><td>{item["name"]}</td><td>{item["total"]}</td></tr>'
            for item in variables['order_items']
        )
        return (
            f'Receipt for {variables["order_number"]}',
            f'<table>{rows}</table><p>Hello {variables["first_name"]}</p>',
            None,
        )


class FakeDb:
    def __init__(self, campaign):
        self.campaign = campaign
        self.added = []
        self.records = []
        self.jobs = []
        self.attempts = []
        self.commit_count = 0

    def get(self, model, item_id):
        return self.campaign if item_id == self.campaign.id else None

    def scalar(self, statement):
        return self.attempts[-1] if self.attempts else None

    def add(self, item):
        self.added.append(item)
        if isinstance(item, EmailSendRecord):
            self.records.append(item)
        elif hasattr(item, 'queued_count'):
            self.jobs.append(item)

    def flush(self):
        for item in self.added:
            if getattr(item, 'id', None) is None:
                item.id = uuid4()

    def refresh(self, item):
        return None

    def commit(self):
        self.commit_count += 1


def test_template_test_send_merges_sample_variables_before_rendering() -> None:
    template_id = uuid4()
    provider = FakeProvider()
    template_service = FakeTemplateService(template_id)
    service = SendingService.__new__(SendingService)
    service.provider = provider
    service.template_service = template_service
    service.settings = SimpleNamespace(default_from_email='sender@example.com')

    result = service.send_test(
        template_id,
        'recipient@example.com',
        {'first_name': 'Taylor'},
    )

    assert template_service.render_context == {
        'first_name': 'Taylor',
        'order_number': 'SM-1001',
        'order_items': [{'name': 'Starter plan', 'quantity': 1, 'total': '$49.00'}],
    }
    assert provider.message.subject == 'Receipt for SM-1001'
    assert 'Starter plan' in provider.message.html_body
    assert result['provider'] == 'fake'
    assert result['subject'] == 'Receipt for SM-1001'
    assert result['variables']['first_name'] == 'Taylor'


def test_campaign_test_send_uses_delivery_worker_path(monkeypatch) -> None:
    campaign_id = uuid4()
    template_id = uuid4()
    contact_id = uuid4()
    campaign = SimpleNamespace(id=campaign_id, template_id=template_id)
    db = FakeDb(campaign)
    template_service = FakeTemplateService(template_id)

    class FakeDeliveryService:
        calls = []

        def __init__(self, db_arg, settings_arg):
            self.db = db_arg
            self.settings = settings_arg

        def process_queued(self, *, limit, send_job_id=None, campaign_id=None):
            self.__class__.calls.append(
                {'limit': limit, 'send_job_id': send_job_id, 'campaign_id': campaign_id}
            )
            record = self.db.records[0]
            record.status = EmailSendStatus.submitted
            record.provider = 'managed_smtp'
            record.provider_message_id = 'managed-smtp-message'
            record.error_message = None
            self.db.attempts.append(
                DeliveryAttempt(
                    send_record_id=record.id,
                    send_job_id=self.db.jobs[0].id,
                    campaign_id=campaign_id,
                    attempt_number=1,
                    provider='managed_smtp',
                    route_type='managed_smtp',
                    route_key='managed-smtp-scaleway-primary',
                    status='submitted',
                    provider_message_id='managed-smtp-message',
                    smtp_response_code=250,
                    smtp_response='Provider accepted message with status 250',
                    metadata_json={
                        'mta_provider': 'scaleway',
                        'mta_route_domain': 'email-engine.app',
                        'mta_route_sender_domain': 'email-engine.app',
                        'mta_route_recipient_domain': 'gmail.com',
                        'mta_route_send_type': 'internal_test',
                        'mta_route_decision_basis': 'sender_domain_policy',
                        'mta_routing_rule_name': 'transactional-scaleway',
                        'mta_routing_rule_source': 'delivery_route_rule',
                        'mta_preferred_providers': ['scaleway'],
                        'mta_rule_hit_send_type': 'internal_test',
                        'mta_rule_hit_sender_domain': 'email-engine.app',
                        'mta_rule_hit_recipient_domain': 'gmail.com',
                        'mta_rule_hit_name': 'transactional-scaleway',
                        'mta_rule_hit_source': 'delivery_route_rule',
                        'mta_rule_hit_pool_source': 'delivery_route_rule',
                        'mta_rule_hit_provider_preference': ['scaleway'],
                        'mta_rule_hit_provider_preference_mode': 'fallback_allowed',
                        'mta_provider_preference_fallback_used': True,
                        'mta_node_name': 'mta-002',
                        'mta_node_selection_membership_id': 'pool-membership-002',
                        'mta_node_selection_priority': 100,
                        'mta_node_selection_weight': 100,
                        'mta_node_candidate_count': 1,
                        'mta_pool_available_node_count': 1,
                        'mta_pool_required_available_node_count': None,
                        'mta_pool_capacity_status': 'ok',
                        'mta_node_skipped_count': 0,
                        'mta_node_skipped_nodes': [],
                        'mta_hostname': 'mta-002.email-engine.app',
                        'mta_public_ipv4': '212.47.236.69',
                        'mta_submission_host': 'mta-002.email-engine.app',
                        'mta_submission_port': 587,
                        'mta_ip_pool_name': 'scaleway-internal-test',
                        'mta_ip_pool_selection_source': 'domain_policy',
                        'mta_route_resolved': True,
                        'envelope_from': f'bounces+{record.id}@returns-scaleway.email-engine.app',
                        'bounce_domain': 'returns-scaleway.email-engine.app',
                        'dkim_selector': 'ee2',
                        'dkim_signing_ready': True,
                    },
                )
            )
            return SimpleNamespace(sent_count=1, failed_count=0)

    monkeypatch.setattr(sending_module, 'DeliveryService', FakeDeliveryService)
    service = SendingService.__new__(SendingService)
    service.db = db
    service.settings = SimpleNamespace(default_from_email='mta-smoke@email-engine.app')
    service.template_service = template_service
    service.suppression_service = SimpleNamespace(is_suppressed=lambda _email: False)
    service._test_contact = lambda email, variables: SimpleNamespace(
        id=contact_id,
        email=email,
        is_unsubscribed=False,
    )
    service._campaign_test_context = lambda _campaign, variables: {
        'first_name': variables.get('first_name', 'Taylor'),
        'order_number': 'SM-1001',
        'order_items': [{'name': 'Starter plan', 'quantity': 1, 'total': '$49.00'}],
    }
    service._tracked_variables = lambda record: {
        **record.variables,
        'tracking_open': 'https://email-engine.app/open',
        'tracking_click_base': 'https://email-engine.app/click',
        'unsubscribe_url': 'https://email-engine.app/unsubscribe',
    }

    result = service.send_campaign_test(
        campaign_id,
        'davidtesterwex@gmail.com',
        {'first_name': 'David'},
    )

    assert FakeDeliveryService.calls == [
        {'limit': 1, 'send_job_id': db.jobs[0].id, 'campaign_id': None}
    ]
    assert db.records[0].status == EmailSendStatus.submitted
    assert db.records[0].attempt_count == 0
    assert db.records[0].provider == 'managed_smtp'
    assert db.jobs[0].status.value == 'completed'
    assert result['provider'] == 'managed_smtp'
    assert result['provider_message_id'] == 'managed-smtp-message'
    assert result['status_code'] == 250
    assert result['delivery_attempt_id'] == db.attempts[0].id
    assert result['send_job_status'] == 'completed'
    assert result['send_record_status'] == 'submitted'
    assert result['smtp_response_code'] == 250
    assert result['smtp_response'] == 'Provider accepted message with status 250'
    assert result['to_email'] == 'davidtesterwex@gmail.com'
    assert result['route_type'] == 'managed_smtp'
    assert result['route_key'] == 'managed-smtp-scaleway-primary'
    assert result['mta_provider'] == 'scaleway'
    assert result['mta_route_domain'] == 'email-engine.app'
    assert result['mta_route_sender_domain'] == 'email-engine.app'
    assert result['mta_route_recipient_domain'] == 'gmail.com'
    assert result['mta_route_send_type'] == 'internal_test'
    assert result['mta_route_decision_basis'] == 'sender_domain_policy'
    assert result['mta_routing_rule_name'] == 'transactional-scaleway'
    assert result['mta_routing_rule_source'] == 'delivery_route_rule'
    assert result['mta_preferred_providers'] == ['scaleway']
    assert result['mta_rule_hit_send_type'] == 'internal_test'
    assert result['mta_rule_hit_sender_domain'] == 'email-engine.app'
    assert result['mta_rule_hit_recipient_domain'] == 'gmail.com'
    assert result['mta_rule_hit_name'] == 'transactional-scaleway'
    assert result['mta_rule_hit_source'] == 'delivery_route_rule'
    assert result['mta_rule_hit_pool_source'] == 'delivery_route_rule'
    assert result['mta_rule_hit_provider_preference'] == ['scaleway']
    assert result['mta_rule_hit_provider_preference_mode'] == 'fallback_allowed'
    assert result['mta_provider_preference_fallback_used'] is True
    assert result['mta_node_name'] == 'mta-002'
    assert result['mta_node_selection_membership_id'] == 'pool-membership-002'
    assert result['mta_node_selection_priority'] == 100
    assert result['mta_node_selection_weight'] == 100
    assert result['mta_node_candidate_count'] == 1
    assert result['mta_pool_available_node_count'] == 1
    assert result['mta_pool_required_available_node_count'] is None
    assert result['mta_pool_capacity_status'] == 'ok'
    assert result['mta_node_skipped_count'] == 0
    assert result['mta_node_skipped_nodes'] == []
    assert result['mta_hostname'] == 'mta-002.email-engine.app'
    assert result['mta_submission_host'] == 'mta-002.email-engine.app'
    assert result['mta_submission_port'] == 587
    assert result['mta_ip_pool_name'] == 'scaleway-internal-test'
    assert result['mta_ip_pool_selection_source'] == 'domain_policy'
    assert result['mta_route_resolved'] is True
    assert result['mta_route_status'] == 'resolved'
    assert result['envelope_from'] == (
        f'bounces+{db.records[0].id}@returns-scaleway.email-engine.app'
    )
    assert result['bounce_domain'] == 'returns-scaleway.email-engine.app'
    assert result['dkim_selector'] == 'ee2'
    assert result['dkim_signing_ready'] is True


def test_campaign_test_send_returns_structured_delivery_failure(monkeypatch) -> None:
    campaign_id = uuid4()
    template_id = uuid4()
    contact_id = uuid4()
    campaign = SimpleNamespace(id=campaign_id, template_id=template_id)
    db = FakeDb(campaign)
    template_service = FakeTemplateService(template_id)

    class FakeDeliveryService:
        def __init__(self, db_arg, settings_arg):
            self.db = db_arg
            self.settings = settings_arg

        def process_queued(self, *, limit, send_job_id=None, campaign_id=None):
            record = self.db.records[0]
            record.status = EmailSendStatus.failed
            record.provider = None
            record.error_message = 'Managed SMTP route blocked (NO_HEALTHY_MTA_NODE)'
            self.db.attempts.append(
                DeliveryAttempt(
                    send_record_id=record.id,
                    send_job_id=self.db.jobs[0].id,
                    campaign_id=campaign_id,
                    attempt_number=1,
                    provider=None,
                    route_type='managed_smtp',
                    route_key='managed-smtp-scaleway-primary',
                    status='failed',
                    error_message=record.error_message,
                    metadata_json={
                        'mta_route_resolved': False,
                        'mta_route_sender_domain': 'email-engine.app',
                        'mta_route_recipient_domain': 'gmail.com',
                        'mta_route_send_type': 'internal_test',
                        'mta_route_block_code': 'NO_HEALTHY_MTA_NODE',
                        'mta_route_block_message': 'No active MTA node is available.',
                        'mta_node_candidate_count': 2,
                        'mta_pool_available_node_count': 1,
                        'mta_pool_required_available_node_count': 2,
                        'mta_pool_capacity_status': 'exhausted',
                        'mta_node_skipped_count': 1,
                        'mta_node_skipped_nodes': [{'reason': 'readiness_not_ok'}],
                        'mta_provider_preference_blocked': True,
                        'mta_provider_preference_fallback_available': True,
                        'mta_provider_preference_fallback_provider': 'aws',
                        'mta_provider_preference_fallback_node_name': 'mta-aws-001',
                        'mta_rate_limit_scope': 'ip_pool',
                        'mta_rate_limit_window_seconds': 60,
                        'mta_rate_limit_max_per_minute': 1,
                        'mta_rate_limit_recent_count': 1,
                    },
                )
            )
            return SimpleNamespace(sent_count=0, failed_count=1)

    monkeypatch.setattr(sending_module, 'DeliveryService', FakeDeliveryService)
    service = SendingService.__new__(SendingService)
    service.db = db
    service.settings = SimpleNamespace(default_from_email='mta-smoke@email-engine.app')
    service.template_service = template_service
    service.suppression_service = SimpleNamespace(is_suppressed=lambda _email: False)
    service._test_contact = lambda email, variables: SimpleNamespace(
        id=contact_id,
        email=email,
        is_unsubscribed=False,
    )
    service._campaign_test_context = lambda _campaign, variables: {
        'first_name': 'David',
        'order_number': 'SM-1001',
        'order_items': [{'name': 'Starter plan', 'quantity': 1, 'total': '$49.00'}],
    }
    service._tracked_variables = lambda record: {
        **record.variables,
        'tracking_open': 'https://email-engine.app/open',
        'tracking_click_base': 'https://email-engine.app/click',
        'unsubscribe_url': 'https://email-engine.app/unsubscribe',
    }

    result = service.send_campaign_test(
        campaign_id,
        'davidtesterwex@gmail.com',
        {'first_name': 'David'},
    )

    assert db.jobs[0].status.value == 'failed'
    assert result['provider'] == 'managed_smtp'
    assert result['status_code'] == 500
    assert result['delivery_attempt_id'] == db.attempts[0].id
    assert result['send_job_status'] == 'failed'
    assert result['send_record_status'] == 'failed'
    assert result['route_type'] == 'managed_smtp'
    assert result['mta_route_resolved'] is False
    assert result['mta_route_status'] == 'blocked'
    assert result['mta_route_sender_domain'] == 'email-engine.app'
    assert result['mta_route_recipient_domain'] == 'gmail.com'
    assert result['mta_route_send_type'] == 'internal_test'
    assert result['mta_route_block_code'] == 'NO_HEALTHY_MTA_NODE'
    assert result['mta_route_block_message'] == 'No active MTA node is available.'
    assert result['mta_node_candidate_count'] == 2
    assert result['mta_pool_available_node_count'] == 1
    assert result['mta_pool_required_available_node_count'] == 2
    assert result['mta_pool_capacity_status'] == 'exhausted'
    assert result['mta_node_skipped_count'] == 1
    assert result['mta_node_skipped_nodes'] == [{'reason': 'readiness_not_ok'}]
    assert result['mta_provider_preference_blocked'] is True
    assert result['mta_provider_preference_fallback_available'] is True
    assert result['mta_provider_preference_fallback_provider'] == 'aws'
    assert result['mta_provider_preference_fallback_node_name'] == 'mta-aws-001'
    assert result['mta_rate_limit_scope'] == 'ip_pool'
    assert result['mta_rate_limit_window_seconds'] == 60
    assert result['mta_rate_limit_max_per_minute'] == 1
    assert result['mta_rate_limit_recent_count'] == 1
    assert result['delivery_error_message'] == (
        'Managed SMTP route blocked (NO_HEALTHY_MTA_NODE)'
    )
