#!/usr/bin/env python3
import argparse
import hashlib
import hmac
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


QUEUE_ID_PATTERN = re.compile(r'\bpostfix/(?:smtp|lmtp)\[\d+\]:\s+([A-F0-9]+):\s+(.*)$')
FIELD_PATTERN = re.compile(r'(\w+)=<([^>]*)>|(\w+)=([^,]+)')
STATUS_EVENT_MAP = {
    'sent': 'delivered',
    'bounced': 'dsn_bounce',
    'deferred': 'tempfail',
    'expired': 'tempfail',
}
# Postfix statuses expected by this ManagedSmtpFeedbackEvent bridge:
# status=sent, status=bounced, status=deferred.


def parse_fields(message: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for match in FIELD_PATTERN.finditer(message):
        if match.group(1):
            fields[match.group(1)] = match.group(2).strip()
        elif match.group(3):
            fields[match.group(3)] = match.group(4).strip()
    return fields


def smtp_response_from_message(message: str) -> str | None:
    if 'status=' not in message:
        return None
    start = message.find('status=')
    paren = message.find('(', start)
    if paren < 0:
        return None
    value = message[paren + 1 :].strip()
    if value.endswith(')'):
        value = value[:-1]
    return value or None


def response_code(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r'\b([245]\d\d)\b', value)
    return int(match.group(1)) if match else None


def parse_postfix_line(line: str) -> dict[str, Any] | None:
    match = QUEUE_ID_PATTERN.search(line)
    if not match:
        return None
    queue_id, message = match.groups()
    fields = parse_fields(message)
    email = fields.get('to')
    status = fields.get('status')
    if not email or not status:
        return None
    status_token = status.split()[0].lower()
    event = STATUS_EVENT_MAP.get(status_token)
    if not event:
        return None
    smtp_response = smtp_response_from_message(message)
    metadata = {
        'source': 'managed_smtp_log_feedback',
        'postfix_queue_id': queue_id,
        'postfix_status': status_token,
    }
    for key in ['relay', 'delay', 'delays', 'dsn']:
        if fields.get(key):
            metadata[key] = fields[key]
    return {
        'email': email,
        'event': event,
        'provider_message_id': queue_id,
        'smtp_response_code': response_code(smtp_response) or response_code(fields.get('dsn')),
        'smtp_response': smtp_response,
        'diagnostic_code': f"smtp; {fields['dsn']}" if fields.get('dsn') else None,
        'metadata_json': metadata,
    }


def parse_postfix_lines(lines: list[str]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for line in lines:
        event = parse_postfix_line(line)
        if not event:
            continue
        key = (
            str(event.get('provider_message_id')),
            str(event.get('email')),
            str(event.get('event')),
        )
        if key in seen:
            continue
        seen.add(key)
        events.append(event)
    return events


def sign_feedback(secret: str, timestamp: str, body: bytes) -> str:
    return hmac.new(
        secret.encode('utf-8'),
        timestamp.encode('utf-8') + b'.' + body,
        hashlib.sha256,
    ).hexdigest()


def post_events(base_url: str, secret: str, events: list[dict[str, Any]]) -> dict[str, Any]:
    body = json.dumps(events, separators=(',', ':')).encode('utf-8')
    timestamp = str(int(time.time()))
    request = urllib.request.Request(
        f'{base_url.rstrip("/")}/api/v1/delivery/managed-smtp/feedback',
        data=body,
        method='POST',
        headers={
            'Content-Type': 'application/json',
            'X-Email-Engine-Timestamp': timestamp,
            'X-Email-Engine-Signature': sign_feedback(secret, timestamp, body),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            text = response.read().decode('utf-8')
    except urllib.error.HTTPError as exc:
        raise RuntimeError(exc.read().decode('utf-8')) from exc
    return json.loads(text) if text else {}


def read_lines(path: str | None) -> list[str]:
    if not path or path == '-':
        return sys.stdin.read().splitlines()
    return Path(path).read_text().splitlines()


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Parse Postfix delivery log lines into ManagedSmtpFeedbackEvent payloads.',
    )
    parser.add_argument('log_file', nargs='?', default='-')
    parser.add_argument('--base-url', default=os.environ.get('BASE_URL', 'http://localhost:8000'))
    parser.add_argument('--post', action='store_true')
    parser.add_argument('--allow-empty', action='store_true')
    args = parser.parse_args()

    events = parse_postfix_lines(read_lines(args.log_file))
    if not events and not args.allow_empty:
        print('No managed SMTP feedback events parsed', file=sys.stderr)
        return 1
    if not args.post:
        print(json.dumps(events, indent=2))
        return 0
    secret = os.environ.get('MANAGED_SMTP_FEEDBACK_SECRET')
    if not secret:
        print('MANAGED_SMTP_FEEDBACK_SECRET is required for --post', file=sys.stderr)
        return 2
    try:
        response = post_events(args.base_url, secret, events)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(response, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
