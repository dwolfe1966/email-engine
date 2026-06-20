#!/usr/bin/env python3
import argparse
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StepResult:
    name: str
    ok: bool
    detail: str


class ApiError(RuntimeError):
    pass


def sign_feedback(secret: str, timestamp: str, body: bytes) -> str:
    return hmac.new(
        secret.encode('utf-8'),
        timestamp.encode('utf-8') + b'.' + body,
        hashlib.sha256,
    ).hexdigest()


def request_json(
    base_url: str,
    path: str,
    *,
    method: str = 'GET',
    payload: Any = None,
    cookie: str | None = None,
    headers: dict[str, str] | None = None,
) -> Any:
    body = (
        json.dumps(payload, separators=(',', ':')).encode('utf-8')
        if payload is not None
        else None
    )
    request_headers = {'Accept': 'application/json', **(headers or {})}
    if body is not None:
        request_headers['Content-Type'] = 'application/json'
    if cookie:
        request_headers['Cookie'] = cookie
    request = urllib.request.Request(
        f'{base_url.rstrip("/")}{path}',
        data=body,
        method=method,
        headers=request_headers,
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            response_body = response.read().decode('utf-8')
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode('utf-8')
        raise ApiError(f'{method} {path} failed with {exc.code}: {error_body}') from exc
    except urllib.error.URLError as exc:
        raise ApiError(f'{method} {path} failed: {exc}') from exc
    return json.loads(response_body) if response_body else None


def append_result(results: list[StepResult], name: str, ok: bool, detail: str) -> None:
    results.append(StepResult(name=name, ok=ok, detail=detail))


def preflight_diagnostics(base_url: str, cookie: str | None, results: list[StepResult]) -> None:
    diagnostics = request_json(base_url, '/api/v1/system/diagnostics', cookie=cookie)
    email = diagnostics.get('email_provider', {}) if isinstance(diagnostics, dict) else {}
    feedback_ready = bool(email.get('managed_smtp_feedback_configured'))
    smtp_ready = bool(email.get('smtp_configured'))
    submission_ready = bool(email.get('managed_smtp_submission_configured'))
    append_result(
        results,
        'diagnostics',
        feedback_ready and smtp_ready and submission_ready,
        (
            f'smtp_configured={smtp_ready}, '
            f'managed_smtp_submission_configured={submission_ready}, '
            f'managed_smtp_feedback_configured={feedback_ready}'
        ),
    )


def verify_domain_authentication(
    base_url: str,
    cookie: str | None,
    policy_id: str,
    results: list[StepResult],
) -> None:
    verification = request_json(
        base_url,
        f'/api/v1/domain-delivery-policies/{policy_id}/verify-authentication',
        method='POST',
        cookie=cookie,
    )
    records = verification.get('records', []) if isinstance(verification, dict) else []
    failed = [
        record
        for record in records
        if record.get('required') and record.get('status') != 'verified'
    ]
    detail = (
        f'{len(records) - len(failed)} verified or optional record(s), '
        f'{len(failed)} required issue(s)'
    )
    append_result(
        results,
        'dns_verification',
        bool(verification.get('verified')) and not failed,
        detail,
    )


def load_reputation_dashboard(
    base_url: str,
    cookie: str | None,
    policy_id: str,
    allow_compliance_hold: bool,
    allow_reputation_risk: bool,
    results: list[StepResult],
) -> dict[str, Any]:
    dashboard = request_json(
        base_url,
        f'/api/v1/domain-delivery-policies/{policy_id}/reputation-dashboard',
        cookie=cookie,
    )
    compliance_ok = allow_compliance_hold or dashboard.get('compliance_status') != 'hold'
    reputation_ok = allow_reputation_risk or dashboard.get('reputation_status') != 'risk'
    throttle_ok = dashboard.get('throttle_status') != 'paused'
    blocklist_ok = dashboard.get('blocklist_status') != 'listed'
    warmup_ok = dashboard.get('warmup_status') != 'hold'
    ok = compliance_ok and reputation_ok and throttle_ok and blocklist_ok and warmup_ok
    append_result(
        results,
        'reputation_dashboard',
        ok,
        (
            f'domain={dashboard.get("domain")}, reputation={dashboard.get("reputation_status")}, '
            f'compliance={dashboard.get("compliance_status")}, '
            f'throttle={dashboard.get("throttle_status")}, '
            f'blocklist={dashboard.get("blocklist_status")}, '
            f'warmup={dashboard.get("warmup_status")}'
        ),
    )
    return dashboard


def send_seed_message(
    base_url: str,
    cookie: str | None,
    campaign_id: str,
    seed_email: str,
    variables: dict[str, Any],
    results: list[StepResult],
) -> dict[str, Any]:
    response = request_json(
        base_url,
        f'/api/v1/campaigns/{campaign_id}/test-send',
        method='POST',
        payload={'to_email': seed_email, 'variables': variables},
        cookie=cookie,
    )
    append_result(
        results,
        'seed_send',
        200 <= int(response.get('status_code', 0)) < 300,
        (
            f'{seed_email} via {response.get("provider")} '
            f'status={response.get("status_code")} '
            f'route={response.get("mta_route_status") or "unknown"} '
            f'host={response.get("mta_submission_host") or response.get("mta_hostname") or "-"}'
        ),
    )
    return response


def post_feedback_smoke(
    base_url: str,
    secret: str,
    seed_email: str,
    provider_message_id: str,
    results: list[StepResult],
) -> None:
    payload = [
        {
            'email': seed_email,
            'event': 'delivered',
            'provider_message_id': provider_message_id,
            'smtp_response_code': 250,
            'smtp_response': '250 2.0.0 controlled delivery smoke',
            'metadata_json': {'source': 'managed_smtp_controlled_delivery'},
        }
    ]
    body = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    timestamp = str(int(time.time()))
    signature = sign_feedback(secret, timestamp, body)
    response = request_json(
        base_url,
        '/api/v1/delivery/managed-smtp/feedback',
        method='POST',
        payload=payload,
        headers={
            'X-Email-Engine-Timestamp': timestamp,
            'X-Email-Engine-Signature': signature,
        },
    )
    append_result(
        results,
        'feedback_smoke',
        int(response.get('processed_count', 0)) >= 1,
        (
            f'processed={response.get("processed_count")}, '
            f'updated={response.get("updated_send_records")}'
        ),
    )


def print_results(results: list[StepResult]) -> None:
    print(json.dumps([result.__dict__ for result in results], indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Run the managed-SMTP controlled delivery preflight and optional seed smoke.',
    )
    parser.add_argument('--base-url', default=os.environ.get('BASE_URL', 'http://localhost:8000'))
    parser.add_argument('--policy-id', default=os.environ.get('DOMAIN_POLICY_ID'))
    parser.add_argument('--campaign-id', default=os.environ.get('CAMPAIGN_ID'))
    parser.add_argument('--seed-email', default=os.environ.get('SEED_EMAIL'))
    parser.add_argument('--cookie', default=os.environ.get('EMAIL_ENGINE_COOKIE'))
    parser.add_argument('--variables-json', default=os.environ.get('SEED_VARIABLES_JSON', '{}'))
    parser.add_argument('--skip-dns', action='store_true')
    parser.add_argument('--send-seed', action='store_true')
    parser.add_argument('--post-feedback', action='store_true')
    parser.add_argument('--allow-compliance-hold', action='store_true')
    parser.add_argument('--allow-reputation-risk', action='store_true')
    args = parser.parse_args()

    if not args.policy_id:
        print('DOMAIN_POLICY_ID or --policy-id is required', file=sys.stderr)
        return 2
    if args.send_seed and (not args.campaign_id or not args.seed_email):
        print('--send-seed requires --campaign-id and --seed-email', file=sys.stderr)
        return 2
    if args.post_feedback and not args.seed_email:
        print('--post-feedback requires --seed-email', file=sys.stderr)
        return 2
    if args.post_feedback and not os.environ.get('MANAGED_SMTP_FEEDBACK_SECRET'):
        print('MANAGED_SMTP_FEEDBACK_SECRET is required for --post-feedback', file=sys.stderr)
        return 2

    try:
        variables = json.loads(args.variables_json)
    except json.JSONDecodeError as exc:
        print(f'Invalid --variables-json: {exc}', file=sys.stderr)
        return 2
    if not isinstance(variables, dict):
        print('--variables-json must decode to an object', file=sys.stderr)
        return 2

    results: list[StepResult] = []
    try:
        preflight_diagnostics(args.base_url, args.cookie, results)
        if not args.skip_dns:
            verify_domain_authentication(args.base_url, args.cookie, args.policy_id, results)
        dashboard = load_reputation_dashboard(
            args.base_url,
            args.cookie,
            args.policy_id,
            args.allow_compliance_hold,
            args.allow_reputation_risk,
            results,
        )
        seed_response: dict[str, Any] | None = None
        if args.send_seed:
            seed_response = send_seed_message(
                args.base_url,
                args.cookie,
                args.campaign_id,
                args.seed_email,
                variables,
                results,
            )
        if args.post_feedback:
            provider_message_id = str(
                (seed_response or {}).get('provider_message_id')
                or f'controlled-smoke-{dashboard.get("domain")}'
            )
            post_feedback_smoke(
                args.base_url,
                os.environ['MANAGED_SMTP_FEEDBACK_SECRET'],
                args.seed_email,
                provider_message_id,
                results,
            )
    except ApiError as exc:
        append_result(results, 'api_error', False, str(exc))

    print_results(results)
    return 0 if results and all(result.ok for result in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
