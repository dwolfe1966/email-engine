#!/usr/bin/env python3
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any


class ApiError(RuntimeError):
    pass


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def env_int(name: str, default: int | None = None) -> int | None:
    value = os.getenv(name)
    if value is None or value.strip() == '':
        return default
    return int(value)


def request_json(
    base_url: str,
    path: str,
    *,
    method: str = 'GET',
    payload: dict[str, Any] | None = None,
    cookie: str | None = None,
) -> Any:
    body = (
        json.dumps(payload, separators=(',', ':')).encode('utf-8')
        if payload is not None
        else None
    )
    headers = {'Accept': 'application/json'}
    if body is not None:
        headers['Content-Type'] = 'application/json'
    if cookie:
        headers['Cookie'] = cookie
    request = urllib.request.Request(
        f'{base_url.rstrip("/")}{path}',
        data=body,
        method=method,
        headers=headers,
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            response_body = response.read().decode('utf-8')
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode('utf-8')
        raise ApiError(f'{method} {path} failed with {exc.code}: {error_body}') from exc
    except urllib.error.URLError as exc:
        raise ApiError(f'{method} {path} failed: {exc}') from exc
    return json.loads(response_body) if response_body else None


def bootstrap_payload(args: argparse.Namespace) -> dict[str, Any]:
    return {
        'provider_account_name': args.provider_account_name,
        'provider': args.provider,
        'provider_account_ref': args.provider_account_ref,
        'region': args.region,
        'abuse_contact_email': args.abuse_contact_email,
        'support_case_ref': args.support_case_ref,
        'port25_status': args.port25_status,
        'rdns_status': args.rdns_status,
        'provider_secret_ref': args.provider_secret_ref,
        'node_name': args.node_name,
        'hostname': args.hostname,
        'public_ipv4': args.public_ipv4,
        'submission_host': args.submission_host,
        'submission_port': args.submission_port,
        'auth_secret_ref': args.auth_secret_ref,
        'ip_pool_name': args.ip_pool_name,
        'ip_pool_type': args.ip_pool_type,
        'route_name': args.route_name,
        'domain': args.domain,
        'bounce_domain': args.bounce_domain,
        'dkim_selector': args.dkim_selector,
        'dkim_key_ref': args.dkim_key_ref,
        'warmup_stage': args.warmup_stage,
        'max_per_minute': args.max_per_minute,
        'max_concurrent': args.max_concurrent,
        'activate_inventory': args.activate_inventory,
        'mark_domain_verified': args.mark_domain_verified,
        'metadata_json': {},
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Register or update the first managed SMTP MTA control-plane mapping.',
    )
    parser.add_argument('--base-url', default=os.getenv('BASE_URL'))
    parser.add_argument('--cookie', default=os.getenv('EMAIL_ENGINE_COOKIE'))
    parser.add_argument('--provider-account-name', default=os.getenv('MTA_PROVIDER_ACCOUNT_NAME'))
    parser.add_argument('--provider', default=os.getenv('MTA_PROVIDER', 'custom'))
    parser.add_argument('--provider-account-ref', default=os.getenv('MTA_PROVIDER_ACCOUNT_REF'))
    parser.add_argument('--region', default=os.getenv('MTA_PROVIDER_REGION'))
    parser.add_argument('--abuse-contact-email', default=os.getenv('MTA_ABUSE_CONTACT_EMAIL'))
    parser.add_argument('--support-case-ref', default=os.getenv('MTA_SUPPORT_CASE_REF'))
    parser.add_argument('--port25-status', default=os.getenv('MTA_PORT25_STATUS', 'unknown'))
    parser.add_argument('--rdns-status', default=os.getenv('MTA_RDNS_STATUS', 'unknown'))
    parser.add_argument('--provider-secret-ref', default=os.getenv('MTA_PROVIDER_SECRET_REF'))
    parser.add_argument('--node-name', default=os.getenv('MTA_NODE_NAME'))
    parser.add_argument('--hostname', default=os.getenv('MTA_HOSTNAME'))
    parser.add_argument('--public-ipv4', default=os.getenv('MTA_PUBLIC_IPV4'))
    parser.add_argument('--submission-host', default=os.getenv('MTA_SUBMISSION_HOST'))
    parser.add_argument(
        '--submission-port',
        type=int,
        default=env_int('MTA_SUBMISSION_PORT', 587),
    )
    parser.add_argument('--auth-secret-ref', default=os.getenv('MTA_AUTH_SECRET_REF'))
    parser.add_argument('--ip-pool-name', default=os.getenv('MTA_IP_POOL_NAME', 'internal-test'))
    parser.add_argument('--ip-pool-type', default=os.getenv('MTA_IP_POOL_TYPE', 'internal_test'))
    parser.add_argument('--route-name', default=os.getenv('MTA_ROUTE_NAME', 'managed-smtp-primary'))
    parser.add_argument('--domain', default=os.getenv('MTA_SENDING_DOMAIN'))
    parser.add_argument('--bounce-domain', default=os.getenv('MTA_BOUNCE_DOMAIN'))
    parser.add_argument('--dkim-selector', default=os.getenv('MTA_DKIM_SELECTOR'))
    parser.add_argument('--dkim-key-ref', default=os.getenv('MTA_DKIM_KEY_REF'))
    parser.add_argument('--warmup-stage', default=os.getenv('MTA_WARMUP_STAGE', 'stage_1'))
    parser.add_argument('--max-per-minute', type=int, default=env_int('MTA_MAX_PER_MINUTE', 25))
    parser.add_argument('--max-concurrent', type=int, default=env_int('MTA_MAX_CONCURRENT', 2))
    parser.add_argument(
        '--activate-inventory',
        action='store_true',
        default=env_bool('MTA_ACTIVATE_INVENTORY'),
    )
    parser.add_argument(
        '--mark-domain-verified',
        action='store_true',
        default=env_bool('MTA_MARK_DOMAIN_VERIFIED'),
    )
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    missing = [
        name
        for name, value in {
            'BASE_URL': args.base_url,
            'MTA_PROVIDER_ACCOUNT_NAME': args.provider_account_name,
            'MTA_NODE_NAME': args.node_name,
            'MTA_HOSTNAME': args.hostname,
            'MTA_SENDING_DOMAIN': args.domain,
        }.items()
        if not value
    ]
    if missing:
        print(f'Missing required values: {", ".join(missing)}', file=sys.stderr)
        return 2

    payload = bootstrap_payload(args)
    if args.dry_run:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    try:
        response = request_json(
            args.base_url,
            '/api/v1/managed-smtp/bootstrap',
            method='POST',
            payload=payload,
            cookie=args.cookie,
        )
    except ApiError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps(response, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
