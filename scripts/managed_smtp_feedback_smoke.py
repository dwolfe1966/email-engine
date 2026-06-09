#!/usr/bin/env python3
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.request


def main() -> int:
    base_url = os.environ.get('BASE_URL', 'http://localhost:8000').rstrip('/')
    secret = os.environ.get('MANAGED_SMTP_FEEDBACK_SECRET')
    if not secret:
        print('MANAGED_SMTP_FEEDBACK_SECRET is required', file=sys.stderr)
        return 2

    payload = [
        {
            'email': os.environ.get('FEEDBACK_EMAIL', 'seed@example.com'),
            'event': os.environ.get('FEEDBACK_EVENT', 'dsn_bounce'),
            'provider_message_id': os.environ.get('PROVIDER_MESSAGE_ID', 'staging-smoke-message'),
            'smtp_response_code': int(os.environ.get('SMTP_RESPONSE_CODE', '550')),
            'smtp_response': os.environ.get(
                'SMTP_RESPONSE',
                '550 5.1.1 staging smoke feedback',
            ),
            'metadata_json': {'source': 'managed_smtp_feedback_smoke'},
        }
    ]
    body = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    timestamp = str(int(time.time()))
    signature = hmac.new(
        secret.encode('utf-8'),
        timestamp.encode('utf-8') + b'.' + body,
        hashlib.sha256,
    ).hexdigest()
    request = urllib.request.Request(
        f'{base_url}/api/v1/delivery/managed-smtp/feedback',
        data=body,
        method='POST',
        headers={
            'Content-Type': 'application/json',
            'X-Email-Engine-Timestamp': timestamp,
            'X-Email-Engine-Signature': signature,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            print(response.read().decode('utf-8'))
            return 0
    except urllib.error.HTTPError as exc:
        print(exc.read().decode('utf-8'), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
