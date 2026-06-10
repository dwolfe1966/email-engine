#!/usr/bin/env python3
import argparse
import hashlib
import hmac
import json
import mailbox
import os
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser, Parser
from pathlib import Path
from typing import Any

ACTION_EVENT_MAP = {
    'failed': 'dsn_bounce',
    'delayed': 'tempfail',
    'delivered': 'delivered',
    'relayed': 'delivered',
    'expanded': 'delivered',
}
ORIGINAL_ENVELOPE_ID_HEADER = 'Original-Envelope-Id'
FINAL_RECIPIENT_HEADER = 'Final-Recipient'


@dataclass(frozen=True)
class DsnMessage:
    raw: bytes
    maildir_path: str | None = None
    maildir_key: str | None = None


def status_event(action: str | None, status: str | None) -> str | None:
    if action:
        event = ACTION_EVENT_MAP.get(action.lower())
        if event:
            return event
    if status and status.startswith('5.'):
        return 'dsn_bounce'
    if status and status.startswith('4.'):
        return 'tempfail'
    if status and status.startswith('2.'):
        return 'delivered'
    return None


def response_code(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r'\b([245]\d\d)\b', value)
    return int(match.group(1)) if match else None


def recipient_address(value: str | None) -> str | None:
    if not value:
        return None
    if ';' in value:
        value = value.split(';', 1)[1]
    return value.strip().strip('<>')


def delivery_status_blocks(message: EmailMessage) -> list[dict[str, str]]:
    blocks: list[dict[str, str]] = []
    for part in message.walk():
        if part.get_content_type() != 'message/delivery-status':
            continue
        payload = part.get_payload()
        if isinstance(payload, list):
            for block in payload:
                if isinstance(block, EmailMessage):
                    blocks.append({key.lower(): str(value) for key, value in block.items()})
        else:
            parsed_blocks = Parser(policy=policy.default).parsestr(str(payload))
            blocks.append({key.lower(): str(value) for key, value in parsed_blocks.items()})
    return blocks


def parse_dsn_message(message: EmailMessage) -> list[dict[str, Any]]:
    blocks = delivery_status_blocks(message)
    if not blocks:
        return []
    per_message = blocks[0]
    queue_id = (
        per_message.get(ORIGINAL_ENVELOPE_ID_HEADER.lower())
        or message.get('X-Postfix-Queue-ID')
        or message.get('X-Queue-ID')
    )
    events: list[dict[str, Any]] = []
    for block in blocks[1:] or blocks:
        email = recipient_address(
            block.get(FINAL_RECIPIENT_HEADER.lower()) or block.get('original-recipient')
        )
        action = block.get('action')
        status = block.get('status')
        diagnostic = block.get('diagnostic-code')
        event = status_event(action, status)
        if not email or not event:
            continue
        metadata = {
            'source': 'managed_smtp_dsn_feedback',
            'dsn_action': action,
            'dsn_status': status,
        }
        if queue_id:
            metadata['postfix_queue_id'] = str(queue_id)
        if block.get('remote-mta'):
            metadata['remote_mta'] = block['remote-mta']
        events.append(
            {
                'email': email,
                'event': event,
                'provider_message_id': str(queue_id) if queue_id else None,
                'smtp_response_code': response_code(diagnostic) or response_code(status),
                'smtp_response': diagnostic,
                'diagnostic_code': diagnostic,
                'metadata_json': metadata,
            }
        )
    return events


def parse_dsn_bytes(raw_message: bytes) -> list[dict[str, Any]]:
    return parse_dsn_message(BytesParser(policy=policy.default).parsebytes(raw_message))


def parse_dsn_text(raw_message: str) -> list[dict[str, Any]]:
    return parse_dsn_message(Parser(policy=policy.default).parsestr(raw_message))


def read_messages(path: str | None) -> list[DsnMessage]:
    if not path or path == '-':
        return [DsnMessage(raw=sys.stdin.buffer.read())]
    candidate = Path(path)
    if candidate.is_dir():
        maildir = mailbox.Maildir(candidate, create=False)
        return [
            DsnMessage(
                raw=maildir[key].as_bytes(policy=policy.default),
                maildir_path=str(candidate),
                maildir_key=key,
            )
            for key in maildir.keys()
        ]
    return [DsnMessage(raw=candidate.read_bytes())]


def parse_dsn_messages(messages: list[DsnMessage] | list[bytes]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for message in messages:
        raw_message = message.raw if isinstance(message, DsnMessage) else message
        maildir_key = message.maildir_key if isinstance(message, DsnMessage) else None
        for event in parse_dsn_bytes(raw_message):
            key = (
                str(event.get('provider_message_id')),
                str(event.get('email')),
                str(event.get('event')),
            )
            if key in seen:
                continue
            seen.add(key)
            if maildir_key:
                metadata = dict(event.get('metadata_json') or {})
                metadata['maildir_key'] = maildir_key
                event['metadata_json'] = metadata
            events.append(event)
    return events


def archive_maildir_messages(messages: list[DsnMessage], archive_path: str) -> int:
    archive = mailbox.Maildir(archive_path, create=True)
    moved_count = 0
    for message in messages:
        if not message.maildir_path or not message.maildir_key:
            continue
        source = mailbox.Maildir(message.maildir_path, create=False)
        if message.maildir_key not in source:
            continue
        archive.add(source[message.maildir_key])
        archive.flush()
        source.remove(message.maildir_key)
        source.flush()
        moved_count += 1
    return moved_count


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


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Parse RFC822 DSN bounce messages into ManagedSmtpFeedbackEvent payloads.',
    )
    parser.add_argument('path', nargs='?', default='-')
    parser.add_argument('--base-url', default=os.environ.get('BASE_URL', 'http://localhost:8000'))
    parser.add_argument('--post', action='store_true')
    parser.add_argument('--archive-maildir', default=os.environ.get('MANAGED_SMTP_DSN_ARCHIVE'))
    parser.add_argument('--allow-empty', action='store_true')
    args = parser.parse_args()

    messages = read_messages(args.path)
    events = parse_dsn_messages(messages)
    if not events and not args.allow_empty:
        print('No managed SMTP DSN feedback events parsed', file=sys.stderr)
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
    if args.archive_maildir:
        response['archived_count'] = archive_maildir_messages(messages, args.archive_maildir)
    print(json.dumps(response, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
