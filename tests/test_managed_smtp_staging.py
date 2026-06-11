import importlib.util
import mailbox
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INFRA = ROOT / 'infra' / 'managed-smtp'
SMOKE_SCRIPT = ROOT / 'scripts' / 'managed_smtp_feedback_smoke.py'
CONTROLLED_DELIVERY_SCRIPT = ROOT / 'scripts' / 'managed_smtp_controlled_delivery.py'
LOG_FEEDBACK_SCRIPT = ROOT / 'scripts' / 'managed_smtp_log_feedback.py'
DSN_FEEDBACK_SCRIPT = ROOT / 'scripts' / 'managed_smtp_dsn_feedback.py'
DSN_QUARANTINE_SCRIPT = ROOT / 'scripts' / 'managed_smtp_dsn_quarantine.py'
MAINTENANCE_RUNBOOK_SCRIPT = ROOT / 'scripts' / 'managed_smtp_maintenance_runbook.py'
MTA_PREFLIGHT_SCRIPT = ROOT / 'scripts' / 'managed_smtp_mta_preflight.py'
MTA_SMOKE_SCRIPT = ROOT / 'scripts' / 'managed_smtp_mta_smoke.py'
RENDER_BLUEPRINT = ROOT / 'render.yaml'
DOCKERFILE = ROOT / 'Dockerfile'
PRODUCTION_HARDENING = INFRA / 'PRODUCTION_HARDENING.md'


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


def test_managed_smtp_production_compose_wires_postfix_to_opendkim() -> None:
    compose = (INFRA / 'docker-compose.production.yml').read_text()
    env_example = (INFRA / 'production.env.example').read_text()
    opendkim_conf = (INFRA / 'opendkim' / 'opendkim.conf').read_text()
    opendkim_entrypoint = (INFRA / 'opendkim' / 'entrypoint.sh').read_text()

    expected_compose_tokens = [
        'managed-smtp-postfix',
        'managed-smtp-opendkim',
        'POSTFIX_DKIM_MILTER: inet:managed-smtp-opendkim:8891',
        'POSTFIX_TLS_CERT_FILE',
        'POSTFIX_TLS_KEY_FILE',
        'POSTFIX_TLS_DIR',
        '/etc/postfix/tls:ro',
        'POSTFIX_SPOOL_DIR',
        'POSTFIX_LOG_DIR',
        'MANAGED_SMTP_DSN_MAILDIR',
        'MANAGED_SMTP_DSN_ARCHIVE_DIR',
        'MANAGED_SMTP_DSN_QUARANTINE_DIR',
        '/var/mail/dsn',
        '/var/mail/dsn-archive',
        '/var/mail/dsn-quarantine',
        'OPENDKIM_DOMAINS',
        'OPENDKIM_SELECTOR',
        'OPENDKIM_KEYS_DIR',
        '/etc/opendkim/keys:ro',
        'depends_on',
    ]
    for token in expected_compose_tokens:
        assert token in compose

    expected_opendkim_tokens = [
        'Socket                  inet:8891@0.0.0.0',
        'KeyTable                /etc/opendkim/KeyTable',
        'SigningTable            refile:/etc/opendkim/SigningTable',
        'InternalHosts           /etc/opendkim/TrustedHosts',
        'RequireSafeKeys         yes',
    ]
    for token in expected_opendkim_tokens:
        assert token in opendkim_conf

    assert 'Missing DKIM private key' in opendkim_entrypoint
    assert '/etc/opendkim/keys/${domain}/${SELECTOR}.private' in opendkim_entrypoint
    assert 'OPENDKIM_KEYS_DIR=/srv/email-engine/opendkim/keys' in env_example
    assert 'POSTFIX_TLS_DIR=/srv/email-engine/postfix/tls' in env_example
    assert 'POSTFIX_SPOOL_DIR=/srv/email-engine/postfix/spool' in env_example
    assert 'POSTFIX_LOG_DIR=/srv/email-engine/postfix/log' in env_example
    assert 'MANAGED_SMTP_DSN_MAILDIR=/srv/email-engine/mail/returns' in env_example


def test_postfix_entrypoint_configures_tls_certificate_mounts() -> None:
    entrypoint = (INFRA / 'postfix' / 'entrypoint.sh').read_text()

    expected_tokens = [
        'POSTFIX_TLS_CERT_FILE',
        'POSTFIX_TLS_KEY_FILE',
        'Missing Postfix TLS certificate',
        'Missing Postfix TLS private key',
        'smtpd_tls_cert_file',
        'smtpd_tls_key_file',
        'smtpd_tls_auth_only = yes',
        'POSTFIX_OUTBOUND_TLS_SECURITY_LEVEL',
    ]
    for token in expected_tokens:
        assert token in entrypoint


def test_managed_smtp_production_hardening_runbook_covers_mta_controls() -> None:
    source = PRODUCTION_HARDENING.read_text()
    readme = (INFRA / 'README.md').read_text()

    expected_tokens = [
        'Network Boundary',
        'Allow inbound TCP `25`',
        'Allow inbound TCP `587` only from trusted Email Engine workers',
        'Do not expose OpenDKIM port `8891` publicly',
        'TLS And Identity',
        'POSTFIX_TLS_DIR',
        'POSTFIX_TLS_CERT_FILE',
        'POSTFIX_TLS_KEY_FILE',
        'PTR',
        'SPF',
        'DKIM',
        'DMARC',
        'Key And Secret Custody',
        'OPENDKIM_KEYS_DIR',
        '0400',
        'Queue And Mailbox Retention',
        'POSTFIX_SPOOL_DIR',
        'MANAGED_SMTP_DSN_MAILDIR',
        'MANAGED_SMTP_DSN_ARCHIVE_DIR',
        'MANAGED_SMTP_DSN_QUARANTINE_DIR',
        'MANAGED_SMTP_DSN_ARCHIVE',
        'MANAGED_SMTP_DSN_QUARANTINE',
        'Logs And Feedback',
        'POSTFIX_LOG_DIR',
        'managed_smtp_log_feedback.py --post',
        '/api/v1/provider-feedback-events/list',
        'Abuse Controls',
        'compliance hold',
        'Backup And Recovery',
        'emergency domain pause',
    ]
    for token in expected_tokens:
        assert token in source

    assert 'PRODUCTION_HARDENING.md' in readme


def test_managed_smtp_mta_preflight_validates_mounts_tls_and_dkim(tmp_path) -> None:
    module = load_script_module(MTA_PREFLIGHT_SCRIPT)
    root = tmp_path / 'mta'
    env = {
        'POSTFIX_MYHOSTNAME': 'smtp.example.com',
        'POSTFIX_MYDOMAIN': 'example.com',
        'POSTFIX_MYNETWORKS': '127.0.0.0/8',
        'POSTFIX_SPOOL_DIR': str(root / 'postfix' / 'spool'),
        'POSTFIX_LOG_DIR': str(root / 'postfix' / 'log'),
        'POSTFIX_TLS_DIR': str(root / 'postfix' / 'tls'),
        'POSTFIX_TLS_CERT_FILE': '/etc/postfix/tls/tls.crt',
        'POSTFIX_TLS_KEY_FILE': '/etc/postfix/tls/tls.key',
        'OPENDKIM_DOMAINS': 'example.com,example.net',
        'OPENDKIM_SELECTOR': 'ee1',
        'OPENDKIM_KEYS_DIR': str(root / 'opendkim' / 'keys'),
        'MANAGED_SMTP_DSN_MAILDIR': str(root / 'mail' / 'returns'),
        'MANAGED_SMTP_DSN_ARCHIVE_DIR': str(root / 'mail' / 'returns-archive'),
        'MANAGED_SMTP_DSN_QUARANTINE_DIR': str(root / 'mail' / 'returns-quarantine'),
    }
    for key in module.REQUIRED_DIRS:
        Path(env[key]).mkdir(parents=True)
    (Path(env['POSTFIX_TLS_DIR']) / 'tls.crt').write_text('cert')
    (Path(env['POSTFIX_TLS_DIR']) / 'tls.key').write_text('key')
    for domain in ['example.com', 'example.net']:
        key_dir = Path(env['OPENDKIM_KEYS_DIR']) / domain
        key_dir.mkdir(parents=True, exist_ok=True)
        (key_dir / 'ee1.private').write_text('private')

    result = module.check_preflight(env)

    assert result['ok'] is True
    assert not result['errors']
    assert any(item['key'] == 'POSTFIX_TLS_CERT_FILE' for item in result['checked'])
    assert sum(1 for item in result['checked'] if item['key'] == 'OPENDKIM_PRIVATE_KEY') == 2


def test_managed_smtp_mta_preflight_reports_missing_requirements(tmp_path) -> None:
    module = load_script_module(MTA_PREFLIGHT_SCRIPT)
    env = {
        'POSTFIX_MYHOSTNAME': 'smtp.example.com',
        'POSTFIX_MYDOMAIN': 'example.com',
        'POSTFIX_MYNETWORKS': '127.0.0.0/8',
        'POSTFIX_SPOOL_DIR': str(tmp_path / 'spool'),
        'POSTFIX_LOG_DIR': str(tmp_path / 'log'),
        'POSTFIX_TLS_DIR': str(tmp_path / 'tls'),
        'POSTFIX_TLS_CERT_FILE': '/etc/postfix/tls/tls.crt',
        'POSTFIX_TLS_KEY_FILE': '/etc/postfix/tls/tls.key',
        'OPENDKIM_DOMAINS': 'example.com',
        'OPENDKIM_SELECTOR': 'ee1',
        'OPENDKIM_KEYS_DIR': str(tmp_path / 'keys'),
        'MANAGED_SMTP_DSN_MAILDIR': str(tmp_path / 'returns'),
        'MANAGED_SMTP_DSN_ARCHIVE_DIR': str(tmp_path / 'archive'),
        'MANAGED_SMTP_DSN_QUARANTINE_DIR': str(tmp_path / 'quarantine'),
    }

    result = module.check_preflight(env)

    assert result['ok'] is False
    assert any('Missing directory for POSTFIX_SPOOL_DIR' in error for error in result['errors'])
    assert any('Missing TLS file for POSTFIX_TLS_CERT_FILE' in error for error in result['errors'])
    assert any('Missing DKIM private key for example.com' in error for error in result['errors'])


def test_managed_smtp_mta_smoke_probes_starttls_with_injected_smtp() -> None:
    module = load_script_module(MTA_SMOKE_SCRIPT)

    class FakeSMTP:
        instances = []

        def __init__(self, timeout):
            self.timeout = timeout
            self.esmtp_features = {'starttls': '', '8bitmime': ''}
            self.started_tls = False
            self.quit_called = False
            FakeSMTP.instances.append(self)

        def connect(self, host, port):
            self.host = host
            self.port = port
            return 220, b'mx.example.com ESMTP Postfix'

        def ehlo(self, name):
            self.ehlo_name = name
            return 250, b'mx.example.com'

        def starttls(self, context=None):
            self.started_tls = True
            return 220, b'2.0.0 Ready to start TLS'

        def quit(self):
            self.quit_called = True

    result = module.smtp_probe(
        'mx.example.com',
        587,
        ehlo_name='email-engine-test',
        require_starttls=True,
        starttls_handshake=True,
        timeout=5,
        smtp_factory=FakeSMTP,
    )

    assert result['ok'] is True
    assert result['banner_code'] == 220
    assert result['has_starttls'] is True
    assert result['starttls_code'] == 220
    assert FakeSMTP.instances[0].started_tls is True
    assert FakeSMTP.instances[0].quit_called is True


def test_managed_smtp_mta_smoke_reports_missing_starttls() -> None:
    module = load_script_module(MTA_SMOKE_SCRIPT)

    class FakeSMTP:
        def __init__(self, timeout):
            self.esmtp_features = {}

        def connect(self, host, port):
            return 220, b'mx.example.com ESMTP Postfix'

        def ehlo(self, name):
            return 250, b'mx.example.com'

        def quit(self):
            pass

    result = module.smtp_probe(
        'mx.example.com',
        587,
        require_starttls=True,
        smtp_factory=FakeSMTP,
    )

    assert result['ok'] is False
    assert result['has_starttls'] is False
    assert result['error'] == 'SMTP server did not advertise STARTTLS'


def test_managed_smtp_mta_smoke_builds_message_and_signed_feedback_contract() -> None:
    module = load_script_module(MTA_SMOKE_SCRIPT)
    message = module.build_test_message(
        'sender@example.com',
        'seed@example.net',
        'Smoke',
        'Hello',
    )
    payload = module.build_feedback_payload('seed@example.net', 'queue-id-123')
    body = b'[{"ok":true}]'
    headers = module.sign_feedback('secret', body, timestamp='1718040000')

    assert message['X-Email-Engine-Smoke'] == 'managed_smtp_mta_smoke'
    assert payload[0]['metadata_json']['source'] == 'managed_smtp_mta_smoke'
    assert payload[0]['event'] == 'delivered'
    assert headers['X-Email-Engine-Timestamp'] == '1718040000'
    assert headers['X-Email-Engine-Signature']


def test_managed_smtp_mta_smoke_verifies_captured_dkim_message() -> None:
    module = load_script_module(MTA_SMOKE_SCRIPT)
    raw_message = b"""DKIM-Signature: v=1; a=rsa-sha256; d=example.com; s=ee1;
 bh=abc; b=def
From: Sender <sender@example.com>
To: seed@example.net
Subject: Smoke

Hello
"""

    result = module.verify_captured_dkim_message(
        raw_message,
        expected_domain='example.com',
        expected_selector='ee1',
        require_from_domain=True,
    )

    assert result['ok'] is True
    assert result['signature_count'] == 1
    assert result['matched_signature']['domain'] == 'example.com'
    assert result['matched_signature']['selector'] == 'ee1'
    assert result['from_domain'] == 'example.com'


def test_managed_smtp_mta_smoke_supports_cryptographic_dkim_verifier() -> None:
    module = load_script_module(MTA_SMOKE_SCRIPT)
    raw_message = b"""DKIM-Signature: v=1; a=rsa-sha256; d=example.com; s=ee1; b=abc
From: sender@example.com

Hello
"""
    seen_messages = []

    def fake_verifier(message):
        seen_messages.append(message)
        return True

    result = module.verify_captured_dkim_message(
        raw_message,
        expected_domain='example.com',
        expected_selector='ee1',
        verify_crypto=True,
        dkim_verifier=fake_verifier,
    )

    assert result['ok'] is True
    assert result['crypto_verification']['ok'] is True
    assert result['crypto_verification']['library'] == 'dkimpy'
    assert seen_messages == [raw_message]


def test_managed_smtp_mta_smoke_fails_closed_on_crypto_dkim_failure() -> None:
    module = load_script_module(MTA_SMOKE_SCRIPT)
    raw_message = b"""DKIM-Signature: v=1; a=rsa-sha256; d=example.com; s=ee1; b=abc
From: sender@example.com

Hello
"""

    result = module.verify_captured_dkim_message(
        raw_message,
        expected_domain='example.com',
        expected_selector='ee1',
        verify_crypto=True,
        dkim_verifier=lambda message: False,
    )

    assert result['ok'] is False
    assert result['crypto_verification']['ok'] is False
    assert result['error'] == 'Cryptographic DKIM verification failed'


def test_managed_smtp_mta_smoke_reports_missing_or_mismatched_dkim() -> None:
    module = load_script_module(MTA_SMOKE_SCRIPT)
    missing = module.verify_captured_dkim_message(b'From: sender@example.com\n\nHello')
    mismatched = module.verify_captured_dkim_message(
        b"""DKIM-Signature: v=1; a=rsa-sha256; d=other.example; s=ee2; b=abc
From: sender@example.com

Hello
""",
        expected_domain='example.com',
        expected_selector='ee1',
        require_from_domain=True,
    )

    assert missing['ok'] is False
    assert missing['error'] == 'Captured message does not contain a DKIM-Signature header'
    assert mismatched['ok'] is False
    assert 'No DKIM signature matched required tags' in mismatched['error']


def test_managed_smtp_mta_smoke_script_contract_is_documented() -> None:
    source = MTA_SMOKE_SCRIPT.read_text()
    readme = (INFRA / 'README.md').read_text()
    deployment = (ROOT / 'docs' / 'DEPLOYMENT.md').read_text()
    hardening = PRODUCTION_HARDENING.read_text()

    expected_tokens = [
        'managed_smtp_mta_smoke',
        'smtplib.SMTP',
        'starttls',
        'X-Email-Engine-Smoke',
        '/api/v1/delivery/managed-smtp/feedback',
        'X-Email-Engine-Signature',
        'MANAGED_SMTP_FEEDBACK_SECRET',
        'require-starttls',
        'send-test',
        'post-feedback',
        'DKIM-Signature',
        'verify-dkim-message',
        'dkim-domain',
        'dkim-selector',
        'require-dkim-from-domain',
        'skip-smtp-probe',
        'verify-dkim-crypto',
        'dkimpy',
    ]
    for token in expected_tokens:
        assert token in source

    assert 'managed_smtp_mta_smoke.py' in readme
    assert 'managed_smtp_mta_smoke.py' in deployment
    assert 'managed_smtp_mta_smoke.py' in hardening


def test_postfix_staging_config_keeps_relay_restricted_to_mynetworks() -> None:
    entrypoint = (INFRA / 'postfix' / 'entrypoint.sh').read_text()
    master = (INFRA / 'postfix' / 'master.cf').read_text()

    assert 'smtpd_relay_restrictions = permit_mynetworks, reject_unauth_destination' in entrypoint
    assert 'smtpd_recipient_restrictions=permit_mynetworks,reject' in master
    assert 'POSTFIX_DKIM_MILTER' in entrypoint
    assert 'smtpd_milters' in entrypoint
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
        'blocklist_status',
        'warmup_status',
        'timestamp.encode',
        "b'.' + body",
    ]
    for token in expected_tokens:
        assert token in source


def test_managed_smtp_log_feedback_parser_maps_postfix_statuses_to_feedback_events() -> None:
    module = load_script_module(LOG_FEEDBACK_SCRIPT)
    lines = [
        (
            'Jun 10 12:00:01 mx postfix/smtp[123]: ABC123DEF: to=<seed@example.com>, '
            'relay=mx.example.net[192.0.2.10]:25, delay=1.2, '
            'delays=0.1/0.1/0.5/0.5, dsn=2.0.0, '
            'status=sent (250 2.0.0 Ok: queued as 12345)'
        ),
        (
            'Jun 10 12:00:02 mx postfix/smtp[124]: BAD987654: to=<bad@example.com>, '
            'relay=mx.example.net[192.0.2.11]:25, delay=2.0, '
            'delays=0.2/0.1/0.7/1.0, dsn=5.1.1, '
            'status=bounced (550 5.1.1 User unknown)'
        ),
        (
            'Jun 10 12:00:03 mx postfix/smtp[125]: DEF456ABC: to=<later@example.com>, '
            'relay=mx.example.net[192.0.2.12]:25, delay=3.0, '
            'delays=0.3/0.1/1.2/1.4, dsn=4.2.0, '
            'status=deferred (421 4.2.0 Try again later)'
        ),
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


def test_managed_smtp_dsn_feedback_parser_maps_delivery_status_to_feedback_events() -> None:
    module = load_script_module(DSN_FEEDBACK_SCRIPT)
    raw_message = """From: MAILER-DAEMON@example.com
To: bounces+record@example.com
Subject: Delivery Status Notification (Failure)
Content-Type: multipart/report; report-type=delivery-status; boundary=\"dsn-boundary\"

--dsn-boundary
Content-Type: text/plain

Delivery failed.

--dsn-boundary
Content-Type: message/delivery-status

Reporting-MTA: dns; mx.example.com
Original-Envelope-Id: ABC123DEF

Final-Recipient: rfc822; bad@example.net
Action: failed
Status: 5.1.1
Remote-MTA: dns; mx.example.net
Diagnostic-Code: smtp; 550 5.1.1 User unknown

--dsn-boundary--
"""

    events = module.parse_dsn_text(raw_message)

    assert len(events) == 1
    event = events[0]
    assert event['email'] == 'bad@example.net'
    assert event['event'] == 'dsn_bounce'
    assert event['provider_message_id'] == 'ABC123DEF'
    assert event['smtp_response_code'] == 550
    assert event['diagnostic_code'] == 'smtp; 550 5.1.1 User unknown'
    assert event['metadata_json']['source'] == 'managed_smtp_dsn_feedback'
    assert event['metadata_json']['postfix_queue_id'] == 'ABC123DEF'


def test_managed_smtp_dsn_feedback_archives_processed_maildir_messages(tmp_path) -> None:
    module = load_script_module(DSN_FEEDBACK_SCRIPT)
    source = tmp_path / 'dsn'
    archive = tmp_path / 'archive'
    maildir = mailbox.Maildir(source, create=True)
    key = maildir.add('From: MAILER-DAEMON@example.com\n\nDelivery failed.')
    maildir.flush()

    messages = module.read_messages(str(source))
    moved_count = module.archive_maildir_messages(messages, str(archive))

    assert messages[0].maildir_key == key
    assert moved_count == 1
    assert len(mailbox.Maildir(source, create=False)) == 0
    assert len(mailbox.Maildir(archive, create=False)) == 1


def test_managed_smtp_dsn_feedback_quarantines_unparsed_maildir_messages(tmp_path) -> None:
    module = load_script_module(DSN_FEEDBACK_SCRIPT)
    source = tmp_path / 'dsn'
    archive = tmp_path / 'archive'
    quarantine = tmp_path / 'quarantine'
    maildir = mailbox.Maildir(source, create=True)
    valid_key = maildir.add("""From: MAILER-DAEMON@example.com
Content-Type: multipart/report; report-type=delivery-status; boundary=\"dsn-boundary\"

--dsn-boundary
Content-Type: message/delivery-status

Reporting-MTA: dns; mx.example.com
Original-Envelope-Id: ABC123DEF

Final-Recipient: rfc822; bad@example.net
Action: failed
Status: 5.1.1

--dsn-boundary--
""")
    malformed_key = maildir.add('From: autoresponder@example.com\n\nOut of office.')
    maildir.flush()

    messages = module.read_messages(str(source))
    outcomes = module.parse_dsn_message_outcomes(messages)
    parsed_messages = [outcome.message for outcome in outcomes if outcome.events]
    unparsed_messages = [outcome.message for outcome in outcomes if not outcome.events]

    assert [message.maildir_key for message in parsed_messages] == [valid_key]
    assert [message.maildir_key for message in unparsed_messages] == [malformed_key]

    archived_count = module.archive_maildir_messages(parsed_messages, str(archive))
    quarantined_count = module.quarantine_maildir_messages(unparsed_messages, str(quarantine))

    assert archived_count == 1
    assert quarantined_count == 1
    assert len(mailbox.Maildir(source, create=False)) == 0
    assert len(mailbox.Maildir(archive, create=False)) == 1
    quarantined = mailbox.Maildir(quarantine, create=False)
    assert len(quarantined) == 1
    quarantined_message = quarantined[next(iter(quarantined.keys()))]
    assert quarantined_message['X-Email-Engine-Quarantine-Reason']


def test_managed_smtp_dsn_feedback_script_posts_signed_feedback_contract() -> None:
    source = DSN_FEEDBACK_SCRIPT.read_text()

    expected_tokens = [
        'ManagedSmtpFeedbackEvent',
        'message/delivery-status',
        'managed_smtp_dsn_feedback',
        'Original-Envelope-Id',
        'Final-Recipient',
        'X-Email-Engine-Timestamp',
        'X-Email-Engine-Signature',
        "timestamp.encode('utf-8') + b'.' + body",
        '/api/v1/delivery/managed-smtp/feedback',
        'MANAGED_SMTP_FEEDBACK_SECRET',
        'mailbox.Maildir',
        'archive_maildir_messages',
        'quarantine_maildir_messages',
        'MANAGED_SMTP_DSN_ARCHIVE',
        'MANAGED_SMTP_DSN_QUARANTINE',
    ]
    for token in expected_tokens:
        assert token in source


def test_managed_smtp_dsn_quarantine_tool_lists_and_purges_maildir_messages(tmp_path) -> None:
    module = load_script_module(DSN_QUARANTINE_SCRIPT)
    quarantine = tmp_path / 'quarantine'
    maildir = mailbox.Maildir(quarantine, create=True)
    first_key = maildir.add(
        'From: autoresponder@example.com\n'
        'Subject: Out of office\n'
        'X-Email-Engine-Quarantine-Reason: no managed SMTP DSN feedback events parsed\n'
        '\n'
        'I am away from the office.'
    )
    second_key = maildir.add('From: junk@example.com\nSubject: not a DSN\n\nHello.')
    maildir.flush()

    rows = module.list_quarantine(str(quarantine), limit=10, preview_chars=12)

    assert [row['key'] for row in rows] == sorted([first_key, second_key])
    first_row = next(row for row in rows if row['key'] == first_key)
    assert first_row['subject'] == 'Out of office'
    assert first_row['quarantine_reason'] == 'no managed SMTP DSN feedback events parsed'
    assert first_row['preview'] == 'I am away fr'

    dry_run = module.purge_quarantine(
        str(quarantine),
        keys=[first_key],
        older_than_days=None,
        all_messages=False,
        dry_run=True,
    )

    assert dry_run['removed_count'] == 1
    assert len(mailbox.Maildir(quarantine, create=False)) == 2

    result = module.purge_quarantine(
        str(quarantine),
        keys=[first_key],
        older_than_days=None,
        all_messages=False,
        dry_run=False,
    )

    assert result['removed_keys'] == [first_key]
    remaining = mailbox.Maildir(quarantine, create=False)
    assert len(remaining) == 1
    assert second_key in remaining


def test_managed_smtp_dsn_quarantine_tool_reports_backlog_health(tmp_path) -> None:
    module = load_script_module(DSN_QUARANTINE_SCRIPT)
    quarantine = tmp_path / 'quarantine'
    maildir = mailbox.Maildir(quarantine, create=True)
    key = maildir.add('From: junk@example.com\nSubject: old message\n\nHello.')
    maildir.flush()
    message_path = Path(maildir._path) / maildir._lookup(key)
    old_timestamp = time.time() - 3 * 3600
    os.utime(message_path, (old_timestamp, old_timestamp))

    stats = module.quarantine_stats(
        str(quarantine),
        warning_count=1,
        critical_count=10,
        max_age_hours=1,
    )

    assert stats['status'] == 'warning'
    assert stats['message_count'] == 1
    assert stats['stale_count'] == 1
    assert stats['oldest_age_hours'] >= 3
    assert stats['reasons']


def test_managed_smtp_dsn_quarantine_tool_contract() -> None:
    source = DSN_QUARANTINE_SCRIPT.read_text()

    expected_tokens = [
        'managed-SMTP DSN quarantine Maildir',
        'X-Email-Engine-Quarantine-Reason',
        'list_quarantine',
        'purge_quarantine',
        'purge-key',
        'purge-older-than-days',
        'purge-all',
        'dry-run',
        '--check',
        'warning-count',
        'critical-count',
        'max-age-hours',
        'MANAGED_SMTP_DSN_QUARANTINE',
        'preview-chars',
    ]
    for token in expected_tokens:
        assert token in source


def test_managed_smtp_maintenance_runbook_sequences_maintenance_and_dsn_ingestion() -> None:
    source = MAINTENANCE_RUNBOOK_SCRIPT.read_text()

    expected_tokens = [
        '/api/v1/domain-delivery-policies/managed-smtp-maintenance',
        'managed_smtp_dsn_feedback',
        'MANAGED_SMTP_DSN_PATH',
        'MANAGED_SMTP_DSN_ARCHIVE',
        'MANAGED_SMTP_DSN_QUARANTINE',
        'MANAGED_SMTP_FEEDBACK_SECRET',
        'skip-maintenance',
        'skip-dsn',
        'skip-blocklist-scan',
        'skip-warmup-progression',
        'no-advance-warmup',
        'archive-maildir',
        'quarantine-maildir',
        'managed_smtp_maintenance_runbook',
    ]
    for token in expected_tokens:
        assert token in source


def test_render_blueprint_configures_managed_smtp_recurring_jobs() -> None:
    render_yaml = RENDER_BLUEPRINT.read_text()
    dockerfile = DOCKERFILE.read_text()

    expected_render_tokens = [
        'email-engine-managed-smtp-dsn-ingestion',
        'email-engine-managed-smtp-maintenance',
        'email-engine-managed-smtp-quarantine-check',
        'type: cron',
        'runtime: docker',
        'dockerCommand: python scripts/managed_smtp_maintenance_runbook.py --skip-maintenance',
        'dockerCommand: python scripts/managed_smtp_maintenance_runbook.py --skip-dsn',
        'schedule: "*/10 * * * *"',
        'schedule: "17 6 * * *"',
        'BASE_URL',
        'EMAIL_ENGINE_COOKIE',
        'MANAGED_SMTP_FEEDBACK_SECRET',
        'MANAGED_SMTP_DSN_PATH',
        'MANAGED_SMTP_DSN_ARCHIVE',
        'MANAGED_SMTP_DSN_QUARANTINE',
        'managed_smtp_dsn_quarantine.py --check',
    ]
    for token in expected_render_tokens:
        assert token in render_yaml

    assert 'COPY scripts ./scripts' in dockerfile
