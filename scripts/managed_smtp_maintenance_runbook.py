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


def summarize_maintenance_result(result: dict[str, Any]) -> dict[str, Any]:
    rows = result.get('results') if isinstance(result, dict) else None
    policy_rows = rows if isinstance(rows, list) else []
    warmup_gate_evidence = [
        {
            'domain': row.get('domain'),
            'warmup_action': row.get('warmup_action'),
            'warmup_status': row.get('warmup_status'),
            'warmup_gate_evidence_key': row.get('warmup_gate_evidence_key') or '-',
        }
        for row in policy_rows
        if isinstance(row, dict) and row.get('warmup_action')
    ]
    return {
        'processed_count': result.get('processed_count', 0),
        'blocklist_scan_count': result.get('blocklist_scan_count', 0),
        'warmup_progression_count': result.get('warmup_progression_count', 0),
        'skipped_count': result.get('skipped_count', 0),
        'warmup_gate_evidence': warmup_gate_evidence,
    }


def run_dsn_ingestion(
    base_url: str,
    dsn_path: str,
    secret: str,
    archive_maildir: str | None = None,
    quarantine_maildir: str | None = None,
) -> dict[str, Any]:
    messages = managed_smtp_dsn_feedback.read_messages(dsn_path)
    outcomes = managed_smtp_dsn_feedback.parse_dsn_message_outcomes(messages)
    events = [event for outcome in outcomes for event in outcome.events]
    parsed_messages = [outcome.message for outcome in outcomes if outcome.events]
    unparsed_messages = [outcome.message for outcome in outcomes if not outcome.events]
    if not events:
        response = {'processed_count': 0, 'suppressed_count': 0, 'updated_send_records': 0}
        if quarantine_maildir:
            response['quarantined_count'] = managed_smtp_dsn_feedback.quarantine_maildir_messages(
                unparsed_messages,
                quarantine_maildir,
            )
        return response
    response = managed_smtp_dsn_feedback.post_events(base_url, secret, events)
    if archive_maildir:
        response['archived_count'] = managed_smtp_dsn_feedback.archive_maildir_messages(
            parsed_messages,
            archive_maildir,
        )
    if quarantine_maildir:
        response['quarantined_count'] = managed_smtp_dsn_feedback.quarantine_maildir_messages(
            unparsed_messages,
            quarantine_maildir,
        )
    return response


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Run scheduled managed-SMTP maintenance and optional DSN ingestion.',
    )
    parser.add_argument('--base-url', default=os.environ.get('BASE_URL', 'http://localhost:8000'))
    parser.add_argument('--cookie', default=os.environ.get('EMAIL_ENGINE_COOKIE'))
    parser.add_argument('--skip-maintenance', action='store_true')
    parser.add_argument('--dsn-path', default=os.environ.get('MANAGED_SMTP_DSN_PATH'))
    parser.add_argument('--archive-maildir', default=os.environ.get('MANAGED_SMTP_DSN_ARCHIVE'))
    parser.add_argument(
        '--quarantine-maildir',
        default=os.environ.get('MANAGED_SMTP_DSN_QUARANTINE'),
    )
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
            results['maintenance_summary'] = summarize_maintenance_result(results['maintenance'])
        if not args.skip_dsn and args.dsn_path:
            results['dsn_ingestion'] = run_dsn_ingestion(
                args.base_url,
                args.dsn_path,
                os.environ['MANAGED_SMTP_FEEDBACK_SECRET'],
                archive_maildir=args.archive_maildir,
                quarantine_maildir=args.quarantine_maildir,
            )
    except ApiError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps(results, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
