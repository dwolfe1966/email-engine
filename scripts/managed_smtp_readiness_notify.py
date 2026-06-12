#!/usr/bin/env python3
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


class NotificationError(RuntimeError):
    pass


def request_json(base_url: str, path: str, *, cookie: str | None = None) -> dict[str, Any]:
    headers = {'Accept': 'application/json'}
    if cookie:
        headers['Cookie'] = cookie
    request = urllib.request.Request(
        f'{base_url.rstrip("/")}{path}',
        headers=headers,
        method='GET',
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode('utf-8')
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode('utf-8')
        raise NotificationError(f'GET {path} failed with {exc.code}: {error_body}') from exc
    except urllib.error.URLError as exc:
        raise NotificationError(f'GET {path} failed: {exc}') from exc
    return json.loads(body) if body else {}


def post_webhook(
    webhook_url: str,
    payload: dict[str, Any],
    *,
    auth_header: str | None = None,
    auth_value: str | None = None,
) -> dict[str, Any]:
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
    }
    if auth_header and auth_value:
        headers[auth_header] = auth_value
    body = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    request = urllib.request.Request(webhook_url, data=body, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            response_body = response.read().decode('utf-8')
            return {
                'status_code': response.status,
                'response_body': response_body[:1000],
            }
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode('utf-8')
        raise NotificationError(f'POST webhook failed with {exc.code}: {error_body}') from exc
    except urllib.error.URLError as exc:
        raise NotificationError(f'POST webhook failed: {exc}') from exc


def notification_path(args) -> str:
    query = {
        'limit': args.limit,
        'source': args.source,
        'check_type': args.check_type,
        'domain': args.domain,
        'host': args.host,
    }
    params = urllib.parse.urlencode({key: value for key, value in query.items() if value})
    return f'/api/v1/managed-smtp/readiness-checks/notification?{params}'


def format_webhook_payload(notification: dict[str, Any], payload_format: str) -> dict[str, Any]:
    if payload_format == 'raw':
        return notification
    if payload_format != 'slack':
        raise NotificationError('MANAGED_SMTP_READINESS_WEBHOOK_FORMAT must be raw or slack')
    severity = str(notification.get('severity') or 'info').upper()
    title = str(notification.get('title') or 'Managed SMTP readiness notification')
    message = str(notification.get('message') or '')
    dedupe_key = str(notification.get('dedupe_key') or 'none')
    alert_count = notification.get('alert_count', 0)
    return {
        'text': f'[{severity}] {title}',
        'blocks': [
            {
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': f'*[{severity}] {title}*\n{message}',
                },
            },
            {
                'type': 'context',
                'elements': [
                    {
                        'type': 'mrkdwn',
                        'text': f'Dedupe: `{dedupe_key}` | Alert evidence: {alert_count}',
                    }
                ],
            },
        ],
    }


def dispatch_notification(args) -> dict[str, Any]:
    notification = request_json(args.base_url, notification_path(args), cookie=args.cookie)
    webhook_payload = format_webhook_payload(notification, args.webhook_format)
    result: dict[str, Any] = {
        'should_notify': bool(notification.get('should_notify')),
        'severity': notification.get('severity'),
        'dedupe_key': notification.get('dedupe_key'),
        'title': notification.get('title'),
        'alert_count': notification.get('alert_count', 0),
        'webhook_format': args.webhook_format,
        'posted': False,
    }
    if not notification.get('should_notify'):
        result['status'] = 'quiet'
        return result
    if args.dry_run:
        result['status'] = 'dry_run'
        result['payload'] = webhook_payload
        return result
    if not args.webhook_url:
        raise NotificationError('MANAGED_SMTP_READINESS_WEBHOOK_URL is required when should_notify is true')
    result['webhook'] = post_webhook(
        args.webhook_url,
        webhook_payload,
        auth_header=args.webhook_auth_header,
        auth_value=args.webhook_auth_value,
    )
    result['posted'] = True
    result['status'] = 'posted'
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Dispatch managed-SMTP readiness notifications to a webhook destination.',
    )
    parser.add_argument('--base-url', default=os.environ.get('BASE_URL', 'http://localhost:8000'))
    parser.add_argument('--cookie', default=os.environ.get('EMAIL_ENGINE_COOKIE'))
    parser.add_argument(
        '--webhook-url',
        default=os.environ.get('MANAGED_SMTP_READINESS_WEBHOOK_URL'),
    )
    parser.add_argument(
        '--webhook-auth-header',
        default=os.environ.get('MANAGED_SMTP_READINESS_WEBHOOK_AUTH_HEADER'),
    )
    parser.add_argument(
        '--webhook-auth-value',
        default=os.environ.get('MANAGED_SMTP_READINESS_WEBHOOK_AUTH_VALUE'),
    )
    parser.add_argument(
        '--webhook-format',
        choices=['raw', 'slack'],
        default=os.environ.get('MANAGED_SMTP_READINESS_WEBHOOK_FORMAT', 'raw'),
    )
    parser.add_argument('--source')
    parser.add_argument('--check-type', default='mta_smoke')
    parser.add_argument('--domain')
    parser.add_argument('--host')
    parser.add_argument('--limit', type=int, default=20)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    try:
        result = dispatch_notification(args)
    except NotificationError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
