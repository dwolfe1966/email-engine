#!/usr/bin/env python3
import argparse
import hashlib
import hmac
import json
import os
import smtplib
import ssl
import sys
import time
import urllib.error
import urllib.request
from email.message import EmailMessage
from typing import Any, Callable


SMTPFactory = Callable[..., smtplib.SMTP]


def smtp_probe(
    host: str,
    port: int,
    *,
    ehlo_name: str = 'email-engine-smoke',
    require_starttls: bool = True,
    starttls_handshake: bool = False,
    timeout: float = 10,
    smtp_factory: SMTPFactory = smtplib.SMTP,
) -> dict[str, Any]:
    smtp = smtp_factory(timeout=timeout)
    result: dict[str, Any] = {
        'name': 'smtp_probe',
        'ok': False,
        'host': host,
        'port': port,
        'require_starttls': require_starttls,
        'starttls_handshake': starttls_handshake,
    }
    try:
        banner_code, banner = smtp.connect(host, port)
        ehlo_code, ehlo_response = smtp.ehlo(ehlo_name)
        features = sorted(str(key).lower() for key in getattr(smtp, 'esmtp_features', {}).keys())
        has_starttls = 'starttls' in features
        result.update(
            {
                'banner_code': banner_code,
                'banner': _decode_smtp_value(banner),
                'ehlo_code': ehlo_code,
                'ehlo_response': _decode_smtp_value(ehlo_response),
                'features': features,
                'has_starttls': has_starttls,
            }
        )
        if require_starttls and not has_starttls:
            result['error'] = 'SMTP server did not advertise STARTTLS'
            return result
        if starttls_handshake:
            if not has_starttls:
                result['error'] = 'Cannot perform STARTTLS handshake; capability is not advertised'
                return result
            starttls_code, starttls_response = smtp.starttls(context=ssl.create_default_context())
            re_ehlo_code, re_ehlo_response = smtp.ehlo(ehlo_name)
            result.update(
                {
                    'starttls_code': starttls_code,
                    'starttls_response': _decode_smtp_value(starttls_response),
                    'post_starttls_ehlo_code': re_ehlo_code,
                    'post_starttls_ehlo_response': _decode_smtp_value(re_ehlo_response),
                }
            )
        result['ok'] = True
        return result
    except OSError as exc:
        result['error'] = str(exc)
        return result
    finally:
        try:
            smtp.quit()
        except (OSError, smtplib.SMTPException):
            pass


def build_test_message(from_email: str, to_email: str, subject: str, body: str) -> EmailMessage:
    message = EmailMessage()
    message['From'] = from_email
    message['To'] = to_email
    message['Subject'] = subject
    message['X-Email-Engine-Smoke'] = 'managed_smtp_mta_smoke'
    message.set_content(body)
    return message


def smtp_submit(
    host: str,
    port: int,
    *,
    from_email: str,
    to_email: str,
    subject: str,
    body: str,
    ehlo_name: str = 'email-engine-smoke',
    starttls: bool = True,
    timeout: float = 10,
    smtp_factory: SMTPFactory = smtplib.SMTP,
) -> dict[str, Any]:
    smtp = smtp_factory(timeout=timeout)
    result: dict[str, Any] = {
        'name': 'smtp_submit',
        'ok': False,
        'host': host,
        'port': port,
        'from_email': from_email,
        'to_email': to_email,
        'starttls': starttls,
    }
    try:
        smtp.connect(host, port)
        smtp.ehlo(ehlo_name)
        features = sorted(str(key).lower() for key in getattr(smtp, 'esmtp_features', {}).keys())
        if starttls:
            if 'starttls' not in features:
                result['error'] = 'SMTP server did not advertise STARTTLS for test submission'
                return result
            smtp.starttls(context=ssl.create_default_context())
            smtp.ehlo(ehlo_name)
        message = build_test_message(from_email, to_email, subject, body)
        send_errors = smtp.send_message(message, from_addr=from_email, to_addrs=[to_email])
        result.update({'ok': not send_errors, 'send_errors': send_errors})
        if send_errors:
            result['error'] = 'SMTP server rejected at least one recipient'
        return result
    except (OSError, smtplib.SMTPException) as exc:
        result['error'] = str(exc)
        return result
    finally:
        try:
            smtp.quit()
        except (OSError, smtplib.SMTPException):
            pass


def build_feedback_payload(email: str, provider_message_id: str) -> list[dict[str, Any]]:
    return [
        {
            'email': email,
            'event': 'delivered',
            'provider_message_id': provider_message_id,
            'smtp_response_code': 250,
            'smtp_response': '250 2.0.0 managed SMTP MTA smoke accepted',
            'metadata_json': {'source': 'managed_smtp_mta_smoke'},
        }
    ]


def sign_feedback(secret: str, body: bytes, timestamp: str | None = None) -> dict[str, str]:
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


def post_feedback_smoke(
    base_url: str,
    secret: str,
    *,
    email: str,
    provider_message_id: str,
    timeout: float = 15,
) -> dict[str, Any]:
    payload = build_feedback_payload(email, provider_message_id)
    body = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    request = urllib.request.Request(
        f'{base_url.rstrip("/")}/api/v1/delivery/managed-smtp/feedback',
        data=body,
        method='POST',
        headers={
            'Content-Type': 'application/json',
            **sign_feedback(secret, body),
        },
    )
    result: dict[str, Any] = {'name': 'feedback_smoke', 'ok': False, 'base_url': base_url}
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response_body = response.read().decode('utf-8')
            result.update({'ok': 200 <= response.status < 300, 'status': response.status, 'body': response_body})
            return result
    except urllib.error.HTTPError as exc:
        result.update({'status': exc.code, 'body': exc.read().decode('utf-8'), 'error': 'HTTP error'})
        return result
    except OSError as exc:
        result['error'] = str(exc)
        return result


def _decode_smtp_value(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode('utf-8', errors='replace')
    return str(value)


def env_default(*keys: str, default: str) -> str:
    for key in keys:
        value = os.environ.get(key)
        if value:
            return value
    return default


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Smoke-test a running managed-SMTP MTA banner, EHLO, STARTTLS, optional submit, and optional feedback.',
    )
    parser.add_argument('--host', default=env_default('SMTP_HOST', 'POSTFIX_MYHOSTNAME', default='localhost'))
    parser.add_argument('--port', type=int, default=int(env_default('SMTP_PORT', 'POSTFIX_SUBMISSION_PORT', default='587')))
    parser.add_argument('--ehlo-name', default=os.environ.get('SMTP_EHLO_NAME', 'email-engine-smoke'))
    parser.add_argument('--timeout', type=float, default=float(os.environ.get('SMTP_TIMEOUT', '10')))
    parser.add_argument('--require-starttls', dest='require_starttls', action='store_true', default=True)
    parser.add_argument('--allow-no-starttls', dest='require_starttls', action='store_false')
    parser.add_argument('--starttls-handshake', action='store_true')
    parser.add_argument('--send-test', action='store_true')
    parser.add_argument('--from-email', default=os.environ.get('DEFAULT_FROM_EMAIL'))
    parser.add_argument('--to-email', default=os.environ.get('SEED_EMAIL'))
    parser.add_argument('--subject', default='Managed SMTP MTA smoke')
    parser.add_argument('--body', default='Managed SMTP MTA smoke test from Email Engine.')
    parser.add_argument('--post-feedback', action='store_true')
    parser.add_argument('--base-url', default=os.environ.get('BASE_URL', 'http://localhost:8000'))
    parser.add_argument('--feedback-secret', default=os.environ.get('MANAGED_SMTP_FEEDBACK_SECRET'))
    parser.add_argument('--provider-message-id', default=f'managed-smtp-mta-smoke-{int(time.time())}')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()

    if args.send_test and (not args.from_email or not args.to_email):
        print('--send-test requires --from-email and --to-email, or DEFAULT_FROM_EMAIL and SEED_EMAIL', file=sys.stderr)
        return 2
    if args.post_feedback and (not args.feedback_secret or not args.to_email):
        print('--post-feedback requires MANAGED_SMTP_FEEDBACK_SECRET and --to-email or SEED_EMAIL', file=sys.stderr)
        return 2

    steps = [
        smtp_probe(
            args.host,
            args.port,
            ehlo_name=args.ehlo_name,
            require_starttls=args.require_starttls,
            starttls_handshake=args.starttls_handshake,
            timeout=args.timeout,
        )
    ]
    if args.send_test:
        steps.append(
            smtp_submit(
                args.host,
                args.port,
                from_email=args.from_email,
                to_email=args.to_email,
                subject=args.subject,
                body=args.body,
                ehlo_name=args.ehlo_name,
                starttls=args.require_starttls,
                timeout=args.timeout,
            )
        )
    if args.post_feedback:
        steps.append(
            post_feedback_smoke(
                args.base_url,
                args.feedback_secret,
                email=args.to_email,
                provider_message_id=args.provider_message_id,
                timeout=args.timeout,
            )
        )

    if args.json:
        print(json.dumps({'ok': all(step['ok'] for step in steps), 'steps': steps}, indent=2))
    else:
        for step in steps:
            status = 'ok' if step['ok'] else 'failed'
            print(f'{step["name"]}: {status}')
            if step.get('error'):
                print(f'  {step["error"]}')
    return 0 if all(step['ok'] for step in steps) else 1


if __name__ == '__main__':
    raise SystemExit(main())
