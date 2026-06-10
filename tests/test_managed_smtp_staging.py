from pathlib import Path
import importlib.util


ROOT = Path(__file__).resolve().parents[1]
INFRA = ROOT / 'infra' / 'managed-smtp'
SMOKE_SCRIPT = ROOT / 'scripts' / 'managed_smtp_feedback_smoke.py'
CONTROLLED_DELIVERY_SCRIPT = ROOT / 'scripts' / 'managed_smtp_controlled_delivery.py'
LOG_FEEDBACK_SCRIPT = ROOT / 'scripts' / 'managed_smtp_log_feedback.py'


def load_script_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_managed_smtp_staging_scaffold_documents_postfix_boundary() -> None:
    readme = (INFRA / 'README.md').read_text()

    expected_tokens = [
        'Postfix',
        'MANAGED_SMTP_FEEDBACK_SECRET',
        'SMTP_PORT=2587',
        'ManagedSmtpFeedbackEvent',
        'Email Engine remains responsible',
        'DSN parsing and MTA log',
    ]
    for token in expected_tokens:
        assert token in readme


def test_managed_smtp_staging_compose_exposes_constrained_ports() -> None:
    compose = (INFRA / 'docker-compose.staging.yml').read_text()

    assert 'managed-smtp-postfix' in compose
    assert '${POSTFIX_SMTP_PORT:-2525}:25' in compose
    assert '${POSTFIX_SUBMISSION_PORT:-2587}:587' in compose
    assert 'managed-smtp-spool' in compose


def test_postfix_staging_config_keeps_relay_restricted_to_mynetworks() -> None:
    entrypoint = (INFRA / 'postfix' / 'entrypoint.sh').read_text()
    master = (INFRA / 'postfix' / 'master.cf').read_text()

    assert 'smtpd_relay_restrictions = permit_mynetworks, reject_unauth_destination' in entrypoint
    assert 'smtpd_recipient_restrictions=permit_mynetworks,reject' in master
    assert 'postfix start-fg' in entrypoint


def test_managed_smtp_feedback_smoke_uses_signed_feedback_contract() -> None:
    source = SMOKE_SCRIPT.read_text()

    expected_tokens = [
        'MANAGED_SMTP_FEEDBACK_SECRET',
        'X-Email-Engine-Timestamp',
        'X-Email-Engine-Signature',
        "timestamp.encode('utf-8') + b'.' + body",
        '/api/v1/delivery/managed-smtp/feedback',
    ]
    for token in expected_tokens:
        assert token in source


def test_managed_smtp_controlled_delivery_runbook_sequences_readiness_and_smoke() -> None:
    source = CONTROLLED_DELIVERY_SCRIPT.read_text()

    expected_tokens = [
        'DOMAIN_POLICY_ID',
        'SEED_EMAIL',
        'CAMPAIGN_ID',
        'EMAIL_ENGINE_COOKIE',
        '/api/v1/system/diagnostics',
        '/api/v1/domain-delivery-policies/{policy_id}/verify-authentication',
        '/api/v1/domain-delivery-policies/{policy_id}/reputation-dashboard',
        '/api/v1/campaigns/{campaign_id}/test-send',
        '/api/v1/delivery/managed-smtp/feedback',
        'managed_smtp_controlled_delivery',
        'allow-compliance-hold',
        'allow-reputation-risk',
        'timestamp.encode',
        "b'.' + body",
    ]
    for token in expected_tokens:
        assert token in source


def test_managed_smtp_log_feedback_parser_maps_postfix_statuses_to_feedback_events() -> None:
    module = load_script_module(LOG_FEEDBACK_SCRIPT)
    lines = [
        'Jun 10 12:00:01 mx postfix/smtp[123]: ABC123DEF: to=<seed@example.com>, relay=mx.example.net[192.0.2.10]:25, delay=1.2, delays=0.1/0.1/0.5/0.5, dsn=2.0.0, status=sent (250 2.0.0 Ok: queued as 12345)',
        'Jun 10 12:00:02 mx postfix/smtp[124]: BAD987654: to=<bad@example.com>, relay=mx.example.net[192.0.2.11]:25, delay=2.0, delays=0.2/0.1/0.7/1.0, dsn=5.1.1, status=bounced (550 5.1.1 User unknown)',
        'Jun 10 12:00:03 mx postfix/smtp[125]: DEF456ABC: to=<later@example.com>, relay=mx.example.net[192.0.2.12]:25, delay=3.0, delays=0.3/0.1/1.2/1.4, dsn=4.2.0, status=deferred (421 4.2.0 Try again later)',
    ]

    events = module.parse_postfix_lines(lines)

    assert [event['event'] for event in events] == ['delivered', 'dsn_bounce', 'tempfail']
    assert events[0]['email'] == 'seed@example.com'
    assert events[0]['provider_message_id'] == 'ABC123DEF'
    assert events[0]['smtp_response_code'] == 250
    assert events[1]['smtp_response_code'] == 550
    assert events[1]['diagnostic_code'] == 'smtp; 5.1.1'
    assert events[2]['metadata_json']['postfix_status'] == 'deferred'


def test_managed_smtp_log_feedback_script_posts_signed_feedback_contract() -> None:
    source = LOG_FEEDBACK_SCRIPT.read_text()

    expected_tokens = [
        'ManagedSmtpFeedbackEvent',
        'postfix_queue_id',
        'managed_smtp_log_feedback',
        'status=sent',
        'status=bounced',
        'status=deferred',
        'X-Email-Engine-Timestamp',
        'X-Email-Engine-Signature',
        "timestamp.encode('utf-8') + b'.' + body",
        '/api/v1/delivery/managed-smtp/feedback',
        'MANAGED_SMTP_FEEDBACK_SECRET',
    ]
    for token in expected_tokens:
        assert token in source
