#!/usr/bin/env python3
import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

REQUIRED_ENV = [
    'POSTFIX_MYHOSTNAME',
    'POSTFIX_MYDOMAIN',
    'POSTFIX_MYNETWORKS',
    'POSTFIX_SPOOL_DIR',
    'POSTFIX_LOG_DIR',
    'POSTFIX_TLS_DIR',
    'POSTFIX_TLS_CERT_FILE',
    'POSTFIX_TLS_KEY_FILE',
    'OPENDKIM_DOMAINS',
    'OPENDKIM_SELECTOR',
    'OPENDKIM_KEYS_DIR',
    'MANAGED_SMTP_DSN_MAILDIR',
    'MANAGED_SMTP_DSN_ARCHIVE_DIR',
    'MANAGED_SMTP_DSN_QUARANTINE_DIR',
]

REQUIRED_DIRS = [
    'POSTFIX_SPOOL_DIR',
    'POSTFIX_LOG_DIR',
    'POSTFIX_TLS_DIR',
    'OPENDKIM_KEYS_DIR',
    'MANAGED_SMTP_DSN_MAILDIR',
    'MANAGED_SMTP_DSN_ARCHIVE_DIR',
    'MANAGED_SMTP_DSN_QUARANTINE_DIR',
]


def parse_env_file(path: str | None) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path:
        return values
    candidate = Path(path)
    if not candidate.exists():
        raise FileNotFoundError(f'Env file not found: {path}')
    for raw_line in candidate.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def merged_env(env_file: str | None) -> dict[str, str]:
    values = parse_env_file(env_file)
    values.update({key: value for key, value in os.environ.items() if key in REQUIRED_ENV})
    return values


def host_tls_path(env: dict[str, str], container_path: str) -> Path:
    tls_dir = Path(env['POSTFIX_TLS_DIR'])
    name = Path(container_path).name
    return tls_dir / name


def dkim_domains(value: str) -> list[str]:
    return [domain for domain in value.replace(',', ' ').split() if domain]


def check_preflight(env: dict[str, str], *, create_dirs: bool = False) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    for key in REQUIRED_ENV:
        if not env.get(key):
            errors.append(f'Missing required env var: {key}')

    if errors:
        return {'ok': False, 'errors': errors, 'warnings': warnings, 'checked': []}

    checked: list[dict[str, str]] = []
    for key in REQUIRED_DIRS:
        path = Path(env[key])
        if create_dirs:
            path.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            errors.append(f'Missing directory for {key}: {path}')
            continue
        if not path.is_dir():
            errors.append(f'Path for {key} is not a directory: {path}')
            continue
        checked.append({'type': 'directory', 'key': key, 'path': str(path)})

    cert_path = host_tls_path(env, env['POSTFIX_TLS_CERT_FILE'])
    key_path = host_tls_path(env, env['POSTFIX_TLS_KEY_FILE'])
    for label, path in [('POSTFIX_TLS_CERT_FILE', cert_path), ('POSTFIX_TLS_KEY_FILE', key_path)]:
        if not path.exists():
            errors.append(f'Missing TLS file for {label}: {path}')
        elif not path.is_file():
            errors.append(f'TLS path for {label} is not a file: {path}')
        else:
            checked.append({'type': 'file', 'key': label, 'path': str(path)})

    selector = env['OPENDKIM_SELECTOR']
    for domain in dkim_domains(env['OPENDKIM_DOMAINS']):
        path = Path(env['OPENDKIM_KEYS_DIR']) / domain / f'{selector}.private'
        if not path.exists():
            errors.append(f'Missing DKIM private key for {domain}: {path}')
        elif not path.is_file():
            errors.append(f'DKIM key path for {domain} is not a file: {path}')
        else:
            checked.append({'type': 'file', 'key': 'OPENDKIM_PRIVATE_KEY', 'path': str(path)})

    if env.get('POSTFIX_TLS_SECURITY_LEVEL') == 'none':
        warnings.append('POSTFIX_TLS_SECURITY_LEVEL is none; production STARTTLS will be disabled.')
    if env.get('POSTFIX_OUTBOUND_TLS_SECURITY_LEVEL') == 'none':
        warnings.append(
            'POSTFIX_OUTBOUND_TLS_SECURITY_LEVEL is none; outbound TLS will be disabled.'
        )
    submission_username = env.get('POSTFIX_SUBMISSION_USERNAME')
    submission_password = env.get('POSTFIX_SUBMISSION_PASSWORD')
    if bool(submission_username) != bool(submission_password):
        errors.append(
            'POSTFIX_SUBMISSION_USERNAME and POSTFIX_SUBMISSION_PASSWORD must be set together.'
        )
    elif not submission_username:
        warnings.append(
            'POSTFIX_SUBMISSION_USERNAME/PASSWORD are not set; '
            'submission will rely on trusted networks.'
        )

    return {
        'ok': not errors,
        'errors': errors,
        'warnings': warnings,
        'checked': checked,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Validate managed-SMTP production MTA env, mounts, TLS files, and DKIM keys.',
    )
    parser.add_argument('--env-file', default='infra/managed-smtp/production.env.example')
    parser.add_argument('--create-dirs', action='store_true')
    args = parser.parse_args()

    try:
        env = merged_env(args.env_file)
        result = check_preflight(env, create_dirs=args.create_dirs)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(json.dumps(result, indent=2))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
