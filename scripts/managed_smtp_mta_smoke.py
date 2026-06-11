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
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import parseaddr
from pathlib import Path
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


def parse_dkim_signature(value: str) -> dict[str, str]:
    tags: dict[str, str] = {}
    for raw_part in value.replace('\r\n', '\n').replace('\n', '').split(';'):
        if '=' not in raw_part:
            continue
        key, tag_value = raw_part.split('=', 1)
        key = key.strip().lower()
        if key:
            tags[key] = tag_value.strip()
    return tags


def verify_captured_dkim_message(
    raw_message: bytes,
    *,
    expected_domain: str | None = None,
    expected_selector: str | None = None,
    require_from_domain: bool = False,
    verify_crypto: bool = False,
    dkim_verifier: Callable[[bytes], bool] | None = None,
) -> dict[str, Any]:
    message = BytesParser(policy=policy.default).parsebytes(raw_message)
    from_header = message.get('From', '')
    from_email = parseaddr(from_header)[1]
    from_domain = from_email.rsplit('@', 1)[1].lower() if '@' in from_email else None
    signatures = [
        {
            'domain': tags.get('d'),
            'selector': tags.get('s'),
            'identity': tags.get('i'),
            'algorithm': tags.get('a'),
        }
        for tags in (parse_dkim_signature(value) for value in message.get_all('DKIM-Signature', []))
    ]

    result: dict[str, Any] = {
        'name': 'dkim_message',
        'ok': False,
        'from_domain': from_domain,
        'expected_domain': expected_domain,
        'expected_selector': expected_selector,
        'require_from_domain': require_from_domain,
        'verify_crypto': verify_crypto,
        'signature_count': len(signatures),
        'signatures': signatures,
    }
    if not signatures:
        result['error'] = 'Captured message does not contain a DKIM-Signature header'
        return result

    expected_domain = expected_domain.lower() if expected_domain else None
    expected_selector = expected_selector.lower() if expected_selector else None
    for signature in signatures:
        signature_domain = signature.get('domain').lower() if signature.get('domain') else None
        signature_selector = signature.get('selector').lower() if signature.get('selector') else None
        if expected_domain and signature_domain != expected_domain:
            continue
        if expected_selector and signature_selector != expected_selector:
            continue
        if require_from_domain and signature_domain != from_domain:
            continue
        if verify_crypto:
            crypto_result = verify_dkim_crypto(raw_message, dkim_verifier=dkim_verifier)
            result['crypto_verification'] = crypto_result
            if not crypto_result['ok']:
                result['error'] = crypto_result['error']
                return result
        result['ok'] = True
        result['matched_signature'] = signature
        return result

    requirements: list[str] = []
    if expected_domain:
        requirements.append(f'd={expected_domain}')
    if expected_selector:
        requirements.append(f's={expected_selector}')
    if require_from_domain:
        requirements.append('d=From domain')
    result['error'] = 'No DKIM signature matched required tags: ' + ', '.join(requirements)
    return result


def verify_dkim_crypto(
    raw_message: bytes,
    *,
    dkim_verifier: Callable[[bytes], bool] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {'ok': False, 'library': 'dkimpy'}
    try:
        if dkim_verifier is None:
            try:
                import dkim  # type: ignore[import-not-found]
            except ModuleNotFoundError:
                result['error'] = 'dkimpy is required for cryptographic DKIM verification'
                return result
            dkim_verifier = dkim.verify
        result['ok'] = bool(dkim_verifier(raw_message))
        if not result['ok']:
            result['error'] = 'Cryptographic DKIM verification failed'
        return result
    except Exception as exc:
        result['error'] = f'Cryptographic DKIM verification errored: {exc}'
        return result


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


def build_readiness_payload(
    steps: list[dict[str, Any]],
    *,
    host: str | None = None,
    domain: str | None = None,
    source: str = 'managed_smtp_mta_smoke',
    check_type: str = 'mta_smoke',
) -> dict[str, Any]:
    ok = all(step.get('ok') for step in steps)
    failed_steps = [str(step.get('name', 'unknown')) for step in steps if not step.get('ok')]
    summary = 'Managed SMTP smoke passed' if ok else f'Managed SMTP smoke failed: {", ".join(failed_steps)}'
    return {
        'source': source,
        'check_type': check_type,
        'status': 'ok' if ok else 'failed',
        'domain': domain,
        'host': host,
        'summary': summary,
        'result_json': {'ok': ok, 'steps': steps},
    }


def post_readiness_check(
    base_url: str,
    secret: str,
    payload: dict[str, Any],
    *,
    timeout: float = 15,
) -> dict[str, Any]:
    body = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    request = urllib.request.Request(
        f'{base_url.rstrip("/")}/api/v1/delivery/managed-smtp/readiness-checks',
        data=body,
        method='POST',
        headers={
            'Content-Type': 'application/json',
            **sign_feedback(secret, body),
        },
    )
    result: dict[str, Any] = {'name': 'readiness_publish', 'ok': False, 'base_url': base_url}
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
    parser.add_argument('--post-readiness', action='store_true')
    parser.add_argument('--base-url', default=os.environ.get('BASE_URL', 'http://localhost:8000'))
    parser.add_argument('--feedback-secret', default=os.environ.get('MANAGED_SMTP_FEEDBACK_SECRET'))
    parser.add_argument('--provider-message-id', default=f'managed-smtp-mta-smoke-{int(time.time())}')
    parser.add_argument('--skip-smtp-probe', action='store_true')
    parser.add_argument('--verify-dkim-message')
    parser.add_argument('--dkim-domain', default=os.environ.get('DKIM_DOMAIN'))
    parser.add_argument('--dkim-selector', default=os.environ.get('DKIM_SELECTOR') or os.environ.get('OPENDKIM_SELECTOR'))
    parser.add_argument('--require-dkim-from-domain', action='store_true')
    parser.add_argument('--verify-dkim-crypto', action='store_true')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()

    if (
        args.skip_smtp_probe
        and not args.send_test
        and not args.post_feedback
        and not args.post_readiness
        and not args.verify_dkim_message
    ):
        print('--skip-smtp-probe requires at least one other smoke step', file=sys.stderr)
        return 2
    if args.send_test and (not args.from_email or not args.to_email):
        print('--send-test requires --from-email and --to-email, or DEFAULT_FROM_EMAIL and SEED_EMAIL', file=sys.stderr)
        return 2
    if (args.post_feedback or args.post_readiness) and not args.feedback_secret:
        print('--post-feedback/--post-readiness require MANAGED_SMTP_FEEDBACK_SECRET', file=sys.stderr)
        return 2
    if args.post_feedback and not args.to_email:
        print('--post-feedback requires --to-email or SEED_EMAIL', file=sys.stderr)
        return 2

    steps = []
    if not args.skip_smtp_probe:
        steps.append(
            smtp_probe(
                args.host,
                args.port,
                ehlo_name=args.ehlo_name,
                require_starttls=args.require_starttls,
                starttls_handshake=args.starttls_handshake,
                timeout=args.timeout,
            )
        )
    if args.verify_dkim_message:
        steps.append(
            verify_captured_dkim_message(
                Path(args.verify_dkim_message).read_bytes(),
                expected_domain=args.dkim_domain,
                expected_selector=args.dkim_selector,
                require_from_domain=args.require_dkim_from_domain,
                verify_crypto=args.verify_dkim_crypto,
            )
        )
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
    if args.post_readiness:
        readiness_payload = build_readiness_payload(
            steps,
            host=args.host,
            domain=args.dkim_domain,
        )
        steps.append(
            post_readiness_check(
                args.base_url,
                args.feedback_secret,
                readiness_payload,
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
