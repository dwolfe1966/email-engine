import hashlib
import hmac
import importlib.util
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
AGENT_SCRIPT = ROOT / 'scripts' / 'managed_smtp_mta_agent.py'


def load_agent_module():
    spec = importlib.util.spec_from_file_location(AGENT_SCRIPT.stem, AGENT_SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_mta_agent_signs_empty_runtime_config_body() -> None:
    module = load_agent_module()

    headers = module.sign_request('secret-value', b'', timestamp='1000')

    expected = hmac.new(b'secret-value', b'1000.', hashlib.sha256).hexdigest()
    assert headers == {
        'X-Email-Engine-Timestamp': '1000',
        'X-Email-Engine-Signature': expected,
    }


def test_mta_agent_parses_mailq_counts() -> None:
    module = load_agent_module()

    result = module.parse_mailq(
        """
-Queue ID-  --Size-- ----Arrival Time---- -Sender/Recipient-------
C268544253      582 Thu Jun 18 22:15:56  mta-smoke@email-engine.app
(Host or domain name not found. Name service error for name=gmail.com type=MX)
                                         davidtesterwex@gmail.com

ABC123DEF*      441 Thu Jun 18 22:17:01  mta-smoke@email-engine.app
                                         seed@example.com

-- 1 Kbytes in 2 Requests.
""".strip()
    )

    assert result['queue_depth'] == 2
    assert result['deferred_count'] == 1
    assert result['active_count'] == 1
    assert result['queue_samples'][0] == {
        'queue_id': 'C268544253',
        'active': False,
        'sender': 'mta-smoke@email-engine.app',
        'recipients': ['davidtesterwex@gmail.com'],
        'deferred_reason': (
            'Host or domain name not found. Name service error for name=gmail.com type=MX'
        ),
    }
    assert result['queue_samples'][1] == {
        'queue_id': 'ABC123DEF',
        'active': True,
        'sender': 'mta-smoke@email-engine.app',
        'recipients': ['seed@example.com'],
    }


def test_mta_agent_parses_systemctl_show_output() -> None:
    module = load_agent_module()

    values = module.parse_systemctl_show(
        """
LoadState=loaded
ActiveState=active
SubState=waiting
UnitFileState=enabled
NextElapseUSecRealtime=Fri 2026-06-19 00:34:09 UTC
""".strip()
    )

    assert values['LoadState'] == 'loaded'
    assert values['ActiveState'] == 'active'
    assert values['SubState'] == 'waiting'
    assert values['UnitFileState'] == 'enabled'
    assert values['NextElapseUSecRealtime'] == 'Fri 2026-06-19 00:34:09 UTC'


def test_mta_agent_collects_postfix_log_samples(tmp_path) -> None:
    module = load_agent_module()
    log_path = tmp_path / 'mail.log'
    log_path.write_text(
        '\n'.join(
            [
                'postfix/smtp[1]: ABC: status=sent (250 2.0.0 Ok)',
                'postfix/smtp[2]: DEF: status=deferred (connect timed out)',
                'postfix/smtp[3]: GHI: status=bounced (550 user unknown)',
            ]
        )
    )

    result = module.collect_postfix_logs(str(log_path), max_lines=2)

    assert result['ok'] is True
    assert result['line_count'] == 2
    assert result['entries'][0]['severity'] == 'deferred'
    assert result['entries'][1]['severity'] == 'bounce'


def test_mta_agent_builds_heartbeat_payload_from_runtime_config() -> None:
    module = load_agent_module()

    payload = module.build_heartbeat_payload(
        {
            'config_version': 'abc123',
            'node': {'hostname': 'mta-002.email-engine.app'},
            'provider_account': {'provider': 'scaleway'},
            'pools': [{'name': 'scaleway-internal-test'}],
            'domains': [{'domain': 'email-engine.app'}],
        },
        {
            'ok': True,
            'queue_depth': 3,
            'deferred_count': 2,
            'active_count': 1,
            'command': ['mailq'],
            'queue_samples': [{'queue_id': 'ABC123DEF', 'sender': 'sender@example.com'}],
        },
        previous_config_version='old-version',
        config_apply={
            'status': 'applied_changed',
            'applied': True,
            'summary': 'Runtime config applied with 1 changed file(s).',
            'rendered_config_hash': 'hash-value',
        },
        systemd={
            'service': {'active_state': 'inactive', 'sub_state': 'dead'},
            'timer': {'active_state': 'active', 'sub_state': 'waiting'},
        },
        revision={'revision': 'abc123def456', 'dirty': False},
        logs={
            'ok': True,
            'entries': [{'severity': 'deferred', 'line': 'postfix/smtp: status=deferred'}],
        },
    )

    assert payload['status'] == 'ok'
    assert 'Runtime config applied with 1 changed file(s).' in payload['summary']
    assert payload['queue_depth'] == 3
    assert payload['deferred_count'] == 2
    assert payload['active_count'] == 1
    assert payload['config_version'] == 'abc123'
    assert payload['applied_config_version'] == 'abc123'
    assert payload['payload_json']['provider'] == 'scaleway'
    assert payload['payload_json']['hostname'] == 'mta-002.email-engine.app'
    assert payload['payload_json']['pool_count'] == 1
    assert payload['payload_json']['domain_count'] == 1
    assert payload['payload_json']['systemd']['service']['active_state'] == 'inactive'
    assert payload['payload_json']['systemd']['timer']['sub_state'] == 'waiting'
    assert payload['payload_json']['revision']['revision'] == 'abc123def456'
    assert payload['payload_json']['revision']['dirty'] is False
    assert payload['payload_json']['queue_samples'] == [
        {'queue_id': 'ABC123DEF', 'sender': 'sender@example.com'}
    ]
    assert payload['payload_json']['logs']['entries'][0]['severity'] == 'deferred'
    assert payload['payload_json']['config_apply']['rendered_config_hash'] == 'hash-value'


def test_mta_agent_renders_runtime_config_files() -> None:
    module = load_agent_module()

    files = module.render_runtime_config_files(
        {
            'config_version': 'version-1',
            'node': {'id': 'node-id', 'hostname': 'mta-002.email-engine.app'},
            'provider_account': {'provider': 'scaleway'},
            'pools': [{'name': 'scaleway-internal-test'}],
            'domains': [
                {
                    'domain': 'email-engine.app',
                    'bounce_domain': 'returns-scaleway.email-engine.app',
                    'dkim_selector': 'ee2',
                    'dkim_key_ref': 'mta://mta-002.email-engine.app/email-engine.app/ee2',
                    'verified': True,
                }
            ],
        }
    )

    assert files['opendkim/KeyTable'] == (
        'ee2._domainkey.email-engine.app '
        'email-engine.app:ee2:/etc/opendkim/keys/email-engine.app/ee2.private\n'
    )
    assert files['opendkim/SigningTable'] == (
        '*@email-engine.app ee2._domainkey.email-engine.app\n'
    )
    assert 'mta-002.email-engine.app\n' in files['opendkim/TrustedHosts']
    assert files['postfix/managed_sender_domains'] == 'email-engine.app OK\n'
    assert files['postfix/managed_bounce_domains'] == 'returns-scaleway.email-engine.app OK\n'
    assert '"config_version": "version-1"' in files['runtime-config.json']


def test_mta_agent_dry_run_reports_config_diffs(tmp_path) -> None:
    module = load_agent_module()
    config_dir = tmp_path / 'generated'
    (config_dir / 'opendkim').mkdir(parents=True)
    (config_dir / 'opendkim' / 'SigningTable').write_text('old\n')

    result = module.apply_runtime_config(
        {
            'config_version': 'version-1',
            'node': {'hostname': 'mta-002.email-engine.app'},
            'provider_account': {'provider': 'scaleway'},
            'domains': [{'domain': 'email-engine.app', 'dkim_selector': 'ee2'}],
        },
        SimpleNamespace(
            config_dir=str(config_dir),
            apply_config=False,
            opendkim_key_root='/etc/opendkim/keys',
            reload_after_apply=False,
            reload_command=None,
            timeout=5,
        ),
    )

    assert result['status'] == 'dry_run_changed'
    assert result['applied'] is False
    assert 'opendkim/SigningTable' in result['changed_files']
    assert 'old' in result['diffs']['opendkim/SigningTable']
    assert (config_dir / 'opendkim' / 'SigningTable').read_text() == 'old\n'


def test_mta_agent_apply_writes_files_and_backs_up_existing(tmp_path) -> None:
    module = load_agent_module()
    config_dir = tmp_path / 'generated'
    (config_dir / 'postfix').mkdir(parents=True)
    sender_path = config_dir / 'postfix' / 'managed_sender_domains'
    sender_path.write_text('old.example OK\n')

    result = module.apply_runtime_config(
        {
            'config_version': 'version-1',
            'node': {'hostname': 'mta-002.email-engine.app'},
            'provider_account': {'provider': 'scaleway'},
            'domains': [{'domain': 'email-engine.app'}],
        },
        SimpleNamespace(
            config_dir=str(config_dir),
            apply_config=True,
            opendkim_key_root='/etc/opendkim/keys',
            reload_after_apply=False,
            reload_command=None,
            timeout=5,
        ),
    )

    assert result['status'] == 'applied_changed'
    assert result['applied'] is True
    assert sender_path.read_text() == 'email-engine.app OK\n'
    assert 'postfix/managed_sender_domains' in result['backups']
    assert Path(result['backups']['postfix/managed_sender_domains']).read_text() == (
        'old.example OK\n'
    )


def test_mta_agent_run_once_fetches_config_posts_heartbeat_and_event(monkeypatch, tmp_path) -> None:
    module = load_agent_module()
    calls = []

    runtime_config = {
        'config_version': 'new-version',
        'node': {'hostname': 'mta-002.email-engine.app'},
        'provider_account': {'provider': 'scaleway'},
        'pools': [{'name': 'scaleway-internal-test'}],
        'domains': [{'domain': 'email-engine.app'}],
    }

    def fake_fetch(base_url, secret, node_id, *, timeout):
        calls.append(('fetch', base_url, secret, node_id, timeout))
        return runtime_config

    def fake_collect(command, *, timeout):
        calls.append(('mailq', command, timeout))
        return {
            'ok': True,
            'queue_depth': 0,
            'deferred_count': 0,
            'active_count': 0,
            'command': command,
        }

    def fake_heartbeat(base_url, secret, node_id, payload, *, timeout):
        calls.append(('heartbeat', base_url, secret, node_id, payload, timeout))
        return {'id': 'check-id', 'status': 'ok'}

    def fake_event(base_url, secret, node_id, payload, *, timeout):
        calls.append(('event', base_url, secret, node_id, payload, timeout))
        return {'id': 'event-id'}

    monkeypatch.setattr(module, 'fetch_runtime_config', fake_fetch)
    monkeypatch.setattr(module, 'collect_mailq', fake_collect)
    monkeypatch.setattr(
        module,
        'collect_systemd_status',
        lambda args: {
            'service': {'active_state': 'inactive', 'sub_state': 'dead'},
            'timer': {'active_state': 'active', 'sub_state': 'waiting'},
        },
    )
    monkeypatch.setattr(
        module,
        'collect_git_revision',
        lambda path, *, timeout: {'revision': 'newrev123456', 'dirty': False},
    )
    monkeypatch.setattr(
        module,
        'collect_postfix_logs',
        lambda path, *, max_lines: {
            'ok': True,
            'path': path,
            'entries': [{'severity': 'sent', 'line': 'status=sent'}],
        },
    )
    monkeypatch.setattr(module, 'post_heartbeat', fake_heartbeat)
    monkeypatch.setattr(module, 'post_event', fake_event)

    args = SimpleNamespace(
        base_url='https://email-engine.app',
        feedback_secret='shared-secret',
        node_id='node-id',
        timeout=15,
        state_path=str(tmp_path / 'agent-state.json'),
        repo_path='/root/apps/email-engine',
        mailq_command=['mailq'],
        compose_file=None,
        env_file=None,
        compose_service='managed-smtp-postfix',
        systemd_service='email-engine-mta-agent.service',
        systemd_timer='email-engine-mta-agent.timer',
        postfix_log_path='/srv/email-engine/postfix/log/mail.log',
        log_sample_lines=20,
        config_dir=str(tmp_path / 'generated-config'),
        apply_config=True,
        opendkim_key_root='/etc/opendkim/keys',
        reload_after_apply=False,
        reload_command=None,
        post_config_event=True,
    )

    result = module.run_once(args)

    assert result['ok'] is True
    assert result['runtime_config']['config_version'] == 'new-version'
    assert result['event']['id'] == 'event-id'
    assert calls[0] == ('fetch', 'https://email-engine.app', 'shared-secret', 'node-id', 15)
    assert calls[1] == ('mailq', ['mailq'], 15)
    assert calls[2][0] == 'heartbeat'
    assert calls[2][4]['payload_json']['logs']['entries'][0]['severity'] == 'sent'
    assert calls[2][4]['applied_config_version'] == 'new-version'
    assert calls[2][4]['payload_json']['systemd']['timer']['active_state'] == 'active'
    assert calls[2][4]['payload_json']['revision']['revision'] == 'newrev123456'
    assert calls[3][0] == 'event'
    assert calls[3][4]['event_type'] == 'runtime_config_applied'
    assert calls[3][4]['payload_json']['changed_files']
    assert result['config_apply']['applied'] is True
