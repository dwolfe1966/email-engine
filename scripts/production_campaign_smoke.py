#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


BASE_URL = os.environ.get('BASE_URL', 'https://email-engine.app').rstrip('/')
CONTACT_EMAIL = os.environ.get('CONTACT_EMAIL', 'smoke-test@example.com')
CLICK_TARGET_URL = os.environ.get('CLICK_TARGET_URL', 'https://email-engine.app/')


def request(path: str, method: str = 'GET', payload: dict[str, Any] | None = None) -> Any:
    data = None
    headers = {'Accept': 'application/json'}
    if payload is not None:
        data = json.dumps(payload).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(
        f'{BASE_URL}{path}',
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            body = response.read().decode('utf-8')
    except urllib.error.HTTPError as exc:
        body = exc.read().decode('utf-8')
        raise RuntimeError(f'{method} {path} failed: {exc.code} {body}') from exc
    return json.loads(body) if body else None


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    stamp = str(int(time.time()))
    source = f'production_campaign_smoke_{stamp}'
    print(f'Base URL: {BASE_URL}')
    print(f'Test recipient: {CONTACT_EMAIL}')

    print('1. Health/readiness')
    request('/health')
    request('/ready')

    print('2. Create template')
    template = request(
        '/api/v1/templates',
        method='POST',
        payload={
            'name': f'production-smoke-template-{stamp}',
            'subject': 'Smoke test for {{ first_name }}',
            'html_body': (
                '<div class="email-shell">'
                '<h1>Hello {{ first_name }}</h1>'
                '{% if plan == "trial" %}<p>Your trial plan is active.</p>'
                '{% else %}<p>Your plan is {{ plan }}.</p>{% endif %}'
                '<ul>{% for item in recommendations %}'
                '<li>{{ loop.index }}. {{ item }}</li>{% endfor %}</ul>'
                '<p><a href="{{ tracking_click }}">Open dashboard</a></p>'
                '{{ tracking_open }}'
                '<p><a href="{{ unsubscribe_url }}">Unsubscribe</a></p>'
                '</div>'
            ),
            'css_body': (
                '.email-shell { font-family: Arial, sans-serif; color: #17202a; } '
                'a { color: #2563eb; }'
            ),
            'text_body': (
                'Hello {{ first_name }}. '
                '{% for item in recommendations %}{{ loop.index }}. {{ item }} {% endfor %} '
                'Unsubscribe: {{ unsubscribe_url }}'
            ),
        },
    )

    print('3. Upsert contact and audience')
    contact = request(
        '/api/v1/audiences/contacts',
        method='POST',
        payload={
            'email': CONTACT_EMAIL,
            'first_name': 'Smoke',
            'last_name': 'Tester',
            'source': source,
            'attributes': {
                'plan': 'trial',
                'recommendations': ['Import audience', 'Create campaign', 'Review analytics'],
                'smoke_run': stamp,
            },
        },
    )
    audience_rule = {'field': 'source', 'comparator': 'eq', 'value': source}
    audience = request(
        '/api/v1/audiences',
        method='POST',
        payload={
            'name': f'production-smoke-audience-{stamp}',
            'description': 'Created by production campaign smoke test.',
            'rule_tree': audience_rule,
        },
    )
    audience_preview = request(
        '/api/v1/audiences/preview',
        method='POST',
        payload={'rule_tree': audience_rule, 'limit': 10},
    )
    assert_true(audience_preview['estimated_count'] >= 1, 'Audience preview matched no contacts')

    print('4. Create campaign and check workflow status')
    campaign = request(
        '/api/v1/campaigns',
        method='POST',
        payload={
            'name': f'production-smoke-campaign-{stamp}',
            'template_id': template['id'],
            'audience_query': audience_rule,
        },
    )
    workflow = request(f'/api/v1/campaigns/{campaign["id"]}/workflow-status')
    assert_true(workflow['validation']['ok'], f'Workflow not ready: {workflow["validation"]}')
    assert_true(
        workflow['audience_preview']['estimated_count'] >= 1,
        'Workflow audience preview matched no contacts',
    )

    print('5. Preview and send actual campaign test email')
    variables = {
        'first_name': 'Smoke',
        'plan': 'trial',
        'recommendations': ['Import audience', 'Create campaign', 'Review analytics'],
    }
    preview = request(
        f'/api/v1/campaigns/{campaign["id"]}/test-preview',
        method='POST',
        payload={'variables': variables},
    )
    assert_true('Smoke' in preview['html_body'], 'Preview did not render expected name')
    send = request(
        f'/api/v1/campaigns/{campaign["id"]}/test-send',
        method='POST',
        payload={'to_email': CONTACT_EMAIL, 'variables': variables},
    )
    assert_true(send['send_record_id'], 'Test send did not return send_record_id')

    print('6. Record test open and click')
    send_record_id = send['send_record_id']
    request(f'/api/v1/tests/email-send-records/{send_record_id}/open', method='POST')
    encoded_target = urllib.parse.quote(CLICK_TARGET_URL, safe='')
    request(
        f'/api/v1/tests/email-send-records/{send_record_id}/click?target_url={encoded_target}',
        method='POST',
    )

    print('7. Verify analytics/events')
    analytics = request(f'/api/v1/campaigns/{campaign["id"]}/analytics?send_job_id={send["send_job_id"]}')
    assert_true(analytics['sent_count'] >= 1, f'Expected sent_count >= 1: {analytics}')
    assert_true(analytics['opened_count'] >= 1, f'Expected opened_count >= 1: {analytics}')
    assert_true(analytics['clicked_count'] >= 1, f'Expected clicked_count >= 1: {analytics}')
    events = request(f'/api/v1/events/list?send_record_id={send_record_id}&limit=20&offset=0')
    event_types = {item['event_type'] for item in events['items']}
    assert_true({'sent', 'opened', 'clicked'}.issubset(event_types), f'Missing events: {events}')

    print(
        json.dumps(
            {
                'ok': True,
                'template_id': template['id'],
                'contact_id': contact['id'],
                'audience_id': audience['id'],
                'campaign_id': campaign['id'],
                'send_job_id': send['send_job_id'],
                'send_record_id': send_record_id,
                'analytics': {
                    'sent_count': analytics['sent_count'],
                    'opened_count': analytics['opened_count'],
                    'clicked_count': analytics['clicked_count'],
                },
            },
            indent=2,
        )
    )
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f'ERROR: {exc}', file=sys.stderr)
        raise SystemExit(1)
