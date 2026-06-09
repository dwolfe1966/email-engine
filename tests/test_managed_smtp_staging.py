from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INFRA = ROOT / 'infra' / 'managed-smtp'
SMOKE_SCRIPT = ROOT / 'scripts' / 'managed_smtp_feedback_smoke.py'


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
