#!/usr/bin/env python3
import argparse
import hashlib
import hmac
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

QUEUE_SUMMARY_PATTERN = re.compile(r'--\s+\d+\s+Kbytes\s+in\s+(\d+)\s+Requests?\.')
QUEUE_ID_PATTERN = re.compile(r'^[A-F0-9]{5,}\*?\s+')


class MtaAgentError(RuntimeError):
    pass


def sign_request(secret: str, body: bytes, timestamp: str | None = None) -> dict[str, str]:
    timestamp = timestamp or str(int(time.time()))
    signature = hmac.new(
        secret.encode('utf-8'),
        timestamp.encode('utf-8') + b'.' + body,
        hashlib.sha256,
    ).hexdigest()
    return {
        'X-Email-Engine-Timestamp': timestamp,
        'X-Email-Engine-Signature': signature,
    }


def signed_json_request(
    base_url: str,
    path: str,
    secret: str,
    *,
    method: str = 'GET',
    payload: dict[str, Any] | None = None,
    timeout: float = 20,
) -> dict[str, Any]:
    body = b'' if payload is None else json.dumps(payload, separators=(',', ':')).encode('utf-8')
    headers = {
        'Accept': 'application/json',
        **sign_request(secret, body),
    }
    if payload is not None:
        headers['Content-Type'] = 'application/json'
    request = urllib.request.Request(
        f'{base_url.rstrip("/")}{path}',
        data=body if payload is not None else None,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response_body = response.read().decode('utf-8')
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode('utf-8')
        raise MtaAgentError(f'{method} {path} failed with {exc.code}: {error_body}') from exc
    except urllib.error.URLError as exc:
        raise MtaAgentError(f'{method} {path} failed: {exc}') from exc
    return json.loads(response_body) if response_body else {}


def fetch_runtime_config(
    base_url: str,
    secret: str,
    node_id: str,
    *,
    timeout: float = 20,
) -> dict[str, Any]:
    return signed_json_request(
        base_url,
        f'/api/v1/mta-agent/nodes/{node_id}/runtime-config',
        secret,
        timeout=timeout,
    )


def post_heartbeat(
    base_url: str,
    secret: str,
    node_id: str,
    payload: dict[str, Any],
    *,
    timeout: float = 20,
) -> dict[str, Any]:
    return signed_json_request(
        base_url,
        f'/api/v1/mta-agent/nodes/{node_id}/heartbeat',
        secret,
        method='POST',
        payload=payload,
        timeout=timeout,
    )


def post_event(
    base_url: str,
    secret: str,
    node_id: str,
    payload: dict[str, Any],
    *,
    timeout: float = 20,
) -> dict[str, Any]:
    return signed_json_request(
        base_url,
        f'/api/v1/mta-agent/nodes/{node_id}/events',
        secret,
        method='POST',
        payload=payload,
        timeout=timeout,
    )


def parse_mailq(output: str) -> dict[str, int]:
    queue_depth = 0
    deferred_count = 0
    for line in output.splitlines():
        if QUEUE_ID_PATTERN.match(line):
            queue_depth += 1
        if line.strip().startswith('('):
            deferred_count += 1
        summary = QUEUE_SUMMARY_PATTERN.search(line)
        if summary:
            queue_depth = int(summary.group(1))
    return {
        'queue_depth': queue_depth,
        'deferred_count': min(deferred_count, queue_depth),
        'active_count': max(queue_depth - deferred_count, 0),
    }


def default_mailq_command(args) -> list[str]:
    if args.mailq_command:
        return args.mailq_command
    if args.compose_file:
        command = ['docker', 'compose']
        if args.env_file:
            command.extend(['--env-file', args.env_file])
        command.extend(['-f', args.compose_file, 'exec', '-T', args.compose_service, 'mailq'])
        return command
    return ['mailq']


def collect_mailq(command: list[str], *, timeout: float = 20) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            'ok': False,
            'queue_depth': None,
            'deferred_count': None,
            'active_count': None,
            'error': str(exc),
            'command': command,
        }
    output = completed.stdout + completed.stderr
    counts = parse_mailq(output)
    return {
        'ok': completed.returncode == 0,
        **counts,
        'returncode': completed.returncode,
        'command': command,
        'output_tail': output[-2000:],
    }


def parse_systemctl_show(output: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in output.splitlines():
        if '=' not in line:
            continue
        key, value = line.split('=', 1)
        values[key] = value
    return values


def collect_systemd_unit(unit: str, *, timeout: float = 20) -> dict[str, Any]:
    command = [
        'systemctl',
        'show',
        unit,
        '--property=LoadState',
        '--property=ActiveState',
        '--property=SubState',
        '--property=UnitFileState',
        '--property=NextElapseUSecRealtime',
        '--no-pager',
    ]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {'ok': False, 'unit': unit, 'error': str(exc), 'command': command}
    values = parse_systemctl_show(completed.stdout + completed.stderr)
    return {
        'ok': completed.returncode == 0,
        'unit': unit,
        'load_state': values.get('LoadState'),
        'active_state': values.get('ActiveState'),
        'sub_state': values.get('SubState'),
        'unit_file_state': values.get('UnitFileState'),
        'next_elapse': values.get('NextElapseUSecRealtime'),
        'returncode': completed.returncode,
        'command': command,
    }


def collect_systemd_status(args) -> dict[str, Any]:
    return {
        'service': collect_systemd_unit(args.systemd_service, timeout=args.timeout),
        'timer': collect_systemd_unit(args.systemd_timer, timeout=args.timeout),
    }


def collect_git_revision(path: str | None, *, timeout: float = 20) -> dict[str, Any]:
    if not path:
        return {'ok': False, 'error': 'repository path not configured'}
    command = ['git', '-C', path, 'rev-parse', '--short=12', 'HEAD']
    dirty_command = ['git', '-C', path, 'status', '--porcelain']
    try:
        revision = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        dirty = subprocess.run(
            dirty_command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {'ok': False, 'path': path, 'error': str(exc), 'command': command}
    return {
        'ok': revision.returncode == 0 and dirty.returncode == 0,
        'path': path,
        'revision': revision.stdout.strip() or None,
        'dirty': bool(dirty.stdout.strip()),
        'returncode': revision.returncode,
        'dirty_returncode': dirty.returncode,
        'command': command,
    }


def read_state(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    state_path = Path(path)
    if not state_path.exists():
        return {}
    try:
        return json.loads(state_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise MtaAgentError(f'Could not read MTA agent state: {exc}') from exc


def write_state(path: str | None, state: dict[str, Any]) -> None:
    if not path:
        return
    state_path = Path(path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True))


def build_heartbeat_payload(
    runtime_config: dict[str, Any],
    queue: dict[str, Any],
    *,
    previous_config_version: str | None = None,
    systemd: dict[str, Any] | None = None,
    revision: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config_version = str(runtime_config.get('config_version') or '')
    queue_ok = bool(queue.get('ok'))
    status = 'ok' if queue_ok else 'warning'
    summary = 'MTA agent heartbeat ok' if queue_ok else 'MTA agent heartbeat warning'
    if previous_config_version and previous_config_version != config_version:
        summary = 'MTA agent heartbeat ok; runtime config changed'
    return {
        'status': status,
        'summary': summary,
        'queue_depth': queue.get('queue_depth'),
        'deferred_count': queue.get('deferred_count'),
        'active_count': queue.get('active_count'),
        'config_version': config_version,
        'applied_config_version': config_version,
        'payload_json': {
            'source': 'managed_smtp_mta_agent',
            'queue_ok': queue_ok,
            'queue_command': queue.get('command'),
            'queue_error': queue.get('error'),
            'provider': (runtime_config.get('provider_account') or {}).get('provider'),
            'hostname': (runtime_config.get('node') or {}).get('hostname'),
            'pool_count': len(runtime_config.get('pools') or []),
            'domain_count': len(runtime_config.get('domains') or []),
            'systemd': systemd or {},
            'revision': revision or {},
        },
    }


def build_config_event(
    runtime_config: dict[str, Any],
    previous_config_version: str | None,
) -> dict[str, Any] | None:
    config_version = str(runtime_config.get('config_version') or '')
    if not config_version or previous_config_version == config_version:
        return None
    hostname = (runtime_config.get('node') or {}).get('hostname')
    return {
        'event_type': 'runtime_config_applied',
        'severity': 'info',
        'summary': f'MTA runtime config applied for {hostname or "node"}',
        'payload_json': {
            'source': 'managed_smtp_mta_agent',
            'previous_config_version': previous_config_version,
            'config_version': config_version,
            'pool_count': len(runtime_config.get('pools') or []),
            'domain_count': len(runtime_config.get('domains') or []),
        },
    }


def run_once(args) -> dict[str, Any]:
    state = read_state(args.state_path)
    runtime_config = fetch_runtime_config(
        args.base_url,
        args.feedback_secret,
        args.node_id,
        timeout=args.timeout,
    )
    previous_config_version = state.get('applied_config_version')
    queue = collect_mailq(default_mailq_command(args), timeout=args.timeout)
    systemd = collect_systemd_status(args)
    revision = collect_git_revision(args.repo_path, timeout=args.timeout)
    heartbeat_payload = build_heartbeat_payload(
        runtime_config,
        queue,
        previous_config_version=previous_config_version,
        systemd=systemd,
        revision=revision,
    )
    heartbeat = post_heartbeat(
        args.base_url,
        args.feedback_secret,
        args.node_id,
        heartbeat_payload,
        timeout=args.timeout,
    )
    event_response = None
    config_event = build_config_event(runtime_config, previous_config_version)
    if config_event and args.post_config_event:
        event_response = post_event(
            args.base_url,
            args.feedback_secret,
            args.node_id,
            config_event,
            timeout=args.timeout,
        )
    state.update(
        {
            'last_run_at': int(time.time()),
            'applied_config_version': heartbeat_payload.get('applied_config_version'),
            'last_heartbeat_id': heartbeat.get('id'),
        }
    )
    write_state(args.state_path, state)
    return {
        'ok': bool(heartbeat.get('id')),
        'runtime_config': {
            'config_version': runtime_config.get('config_version'),
            'node': (runtime_config.get('node') or {}).get('hostname'),
            'pool_count': len(runtime_config.get('pools') or []),
            'domain_count': len(runtime_config.get('domains') or []),
        },
        'queue': queue,
        'systemd': systemd,
        'revision': revision,
        'heartbeat': heartbeat,
        'event': event_response,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Fetch managed-SMTP MTA runtime config and publish node heartbeat telemetry.',
    )
    parser.add_argument('--base-url', default=os.environ.get('BASE_URL', 'https://email-engine.app'))
    parser.add_argument('--node-id', default=os.environ.get('MANAGED_SMTP_MTA_NODE_ID'))
    parser.add_argument(
        '--feedback-secret',
        default=os.environ.get('MANAGED_SMTP_FEEDBACK_SECRET'),
        help='Shared secret used to sign MTA agent API requests.',
    )
    parser.add_argument('--state-path', default=os.environ.get('MANAGED_SMTP_MTA_AGENT_STATE'))
    parser.add_argument(
        '--repo-path',
        default=os.environ.get('MANAGED_SMTP_REPO_PATH', str(Path(__file__).resolve().parents[1])),
    )
    parser.add_argument(
        '--timeout',
        type=float,
        default=float(os.environ.get('SMTP_TIMEOUT', '20')),
    )
    parser.add_argument('--compose-file', default=os.environ.get('MANAGED_SMTP_COMPOSE_FILE'))
    parser.add_argument('--env-file', default=os.environ.get('MANAGED_SMTP_ENV_FILE'))
    parser.add_argument(
        '--compose-service',
        default=os.environ.get('MANAGED_SMTP_COMPOSE_SERVICE', 'managed-smtp-postfix'),
    )
    parser.add_argument('--mailq-command', nargs='+')
    parser.add_argument(
        '--systemd-service',
        default=os.environ.get('MANAGED_SMTP_MTA_AGENT_SERVICE', 'email-engine-mta-agent.service'),
    )
    parser.add_argument(
        '--systemd-timer',
        default=os.environ.get('MANAGED_SMTP_MTA_AGENT_TIMER', 'email-engine-mta-agent.timer'),
    )
    parser.add_argument('--post-config-event', action='store_true')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()

    if not args.node_id:
        print('--node-id or MANAGED_SMTP_MTA_NODE_ID is required', file=sys.stderr)
        return 2
    if not args.feedback_secret:
        print('--feedback-secret or MANAGED_SMTP_FEEDBACK_SECRET is required', file=sys.stderr)
        return 2

    try:
        result = run_once(args)
    except MtaAgentError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        status = 'ok' if result.get('ok') else 'failed'
        config = result.get('runtime_config') or {}
        queue = result.get('queue') or {}
        print(f'mta_agent: {status}')
        print(f'  node: {config.get("node")}')
        print(f'  config_version: {config.get("config_version")}')
        print(f'  queue_depth: {queue.get("queue_depth")}')
    return 0 if result.get('ok') else 1


if __name__ == '__main__':
    raise SystemExit(main())
