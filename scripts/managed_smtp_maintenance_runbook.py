#!/usr/bin/env python3
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

import managed_smtp_dsn_feedback


class ApiError(RuntimeError):
    pass


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


def run_maintenance(base_url: str, cookie: str | None, args) -> dict[str, Any]:
    payload = {
        'scan_blocklists': not args.skip_blocklist_scan,
        'progress_warmup': not args.skip_warmup_progression,
        'advance_warmup': not args.no_advance_warmup,
        'include_all_route_types': args.include_all_route_types,
        'zones': args.blocklist_zone,
        'max_bounce_rate': args.max_bounce_rate,
        'max_complaint_rate': args.max_complaint_rate,
        'min_sent_count': args.min_sent_count,
        'limit': args.limit,
        'operator': args.operator,
    }
    return request_json(
        base_url,
        '/api/v1/domain-delivery-policies/managed-smtp-maintenance',
        method='POST',
        payload=payload,
        cookie=cookie,
    )


def run_dsn_ingestion(base_url: str, dsn_path: str, secret: str) -> dict[str, Any]:
    events = managed_smtp_dsn_feedback.parse_dsn_messages(
        managed_smtp_dsn_feedback.read_messages(dsn_path)
    )
    if not events:
        return {'processed_count': 0, 'suppressed_count': 0, 'updated_send_records': 0}
    return managed_smtp_dsn_feedback.post_events(base_url, secret, events)


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Run scheduled managed-SMTP maintenance and optional DSN ingestion.',
    )
    parser.add_argument('--base-url', default=os.environ.get('BASE_URL', 'http://localhost:8000'))
    parser.add_argument('--cookie', default=os.environ.get('EMAIL_ENGINE_COOKIE'))
    parser.add_argument('--skip-maintenance', action='store_true')
    parser.add_argument('--dsn-path', default=os.environ.get('MANAGED_SMTP_DSN_PATH'))
    parser.add_argument('--skip-dsn', action='store_true')
    parser.add_argument('--skip-blocklist-scan', action='store_true')
    parser.add_argument('--skip-warmup-progression', action='store_true')
    parser.add_argument('--no-advance-warmup', action='store_true')
    parser.add_argument('--include-all-route-types', action='store_true')
    parser.add_argument('--blocklist-zone', action='append', default=['zen.spamhaus.org'])
    parser.add_argument('--max-bounce-rate', type=float, default=0.02)
    parser.add_argument('--max-complaint-rate', type=float, default=0.001)
    parser.add_argument('--min-sent-count', type=int, default=25)
    parser.add_argument('--limit', type=int, default=100)
    parser.add_argument('--operator', default='managed_smtp_maintenance_runbook')
    args = parser.parse_args()

    if not args.skip_dsn and args.dsn_path and not os.environ.get('MANAGED_SMTP_FEEDBACK_SECRET'):
        print('MANAGED_SMTP_FEEDBACK_SECRET is required for DSN ingestion', file=sys.stderr)
        return 2

    results: dict[str, Any] = {}
    try:
        if not args.skip_maintenance:
            results['maintenance'] = run_maintenance(args.base_url, args.cookie, args)
        if not args.skip_dsn and args.dsn_path:
            results['dsn_ingestion'] = run_dsn_ingestion(
                args.base_url,
                args.dsn_path,
                os.environ['MANAGED_SMTP_FEEDBACK_SECRET'],
            )
    except ApiError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps(results, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
