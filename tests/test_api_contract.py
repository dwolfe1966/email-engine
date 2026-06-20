from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from email_platform.api.compat import _template_create_payload
from email_platform.api.operation_feedback import with_operation_feedback
from email_platform.main import app
from email_platform.schemas.contracts import TemplatePreviewRequest, TemplateValidationRequest
from email_platform.services.documents import document_to_html, html_to_document
from email_platform.services.templates import SAMPLE_TEMPLATES, TemplateService


def test_openapi_exposes_gui_integration_paths() -> None:
    client = TestClient(app)
    paths = client.get('/openapi.json').json()['paths']

    expected_paths = {
        '/api/v1/ai/templates/draft',
        '/api/v1/ai/templates/edit',
        '/api/v1/ai/templates/recommend',
        '/api/v1/ai/analytics/analyze',
        '/api/v1/ai/audiences/analyze',
        '/api/v1/ai/campaigns/analyze',
        '/api/v1/ai/delivery/analyze',
        '/api/v1/ai/journeys/analyze',
        '/api/v1/system/diagnostics',
        '/api/v1/system/schema-status',
        '/api/v1/users',
        '/api/v1/users/list',
        '/api/v1/users/{user_id}',
        '/api/v1/users/{user_id}/password',
        '/api/v1/users/{user_id}/unlock',
        '/api/v1/templates',
        '/api/v1/templates/lint',
        '/api/v1/templates/list',
        '/api/v1/templates/document/import-html',
        '/api/v1/templates/document/render',
        '/api/v1/templates/document/validate',
        '/api/v1/templates/document/variables',
        '/api/v1/templates/preview',
        '/api/v1/templates/samples',
        '/api/v1/templates/validate',
        '/api/v1/templates/variables',
        '/api/v1/templates/{template_id}',
        '/api/v1/templates/{template_id}/document',
        '/api/v1/templates/{template_id}/preview-sample',
        '/api/v1/templates/{template_id}/variables',
        '/api/v1/templates/{template_id}/versions',
        '/api/v1/campaigns',
        '/api/v1/campaigns/list',
        '/api/v1/campaigns/process-due',
        '/api/v1/campaigns/{campaign_id}',
        '/api/v1/campaigns/{campaign_id}/analytics',
        '/api/v1/campaigns/{campaign_id}/analytics/timeline',
        '/api/v1/campaigns/{campaign_id}/approve',
        '/api/v1/campaigns/{campaign_id}/clone',
        '/api/v1/campaigns/{campaign_id}/launch',
        '/api/v1/campaigns/{campaign_id}/test-preview',
        '/api/v1/campaigns/{campaign_id}/test-send',
        '/api/v1/campaigns/{campaign_id}/validate',
        '/api/v1/campaigns/{campaign_id}/workflow-status',
        '/api/v1/analytics/audiences',
        '/api/v1/analytics/campaigns',
        '/api/v1/analytics/campaign-summaries',
        '/api/v1/analytics/domains',
        '/api/v1/analytics/journeys',
        '/api/v1/analytics/overview',
        '/api/v1/journeys',
        '/api/v1/journeys/list',
        '/api/v1/journeys/{journey_id}',
        '/api/v1/journeys/{journey_id}/enrollments',
        '/api/v1/journeys/{journey_id}/graph',
        '/api/v1/journeys/{journey_id}/steps',
        '/api/v1/journeys/process',
        '/api/v1/journey-enrollments/list',
        '/api/v1/journey-step-executions/list',
        '/api/v1/journey-steps/{step_id}',
        '/api/v1/campaign-send-jobs/list',
        '/api/v1/campaign-send-jobs/{send_job_id}/progress',
        '/api/v1/delivery/process-queued',
        '/api/v1/delivery/managed-smtp/feedback',
        '/api/v1/delivery/managed-smtp/readiness-checks',
        '/api/v1/delivery-attempts/list',
        '/api/v1/delivery-routes',
        '/api/v1/delivery-routes/list',
        '/api/v1/delivery-routes/{route_id}',
        '/api/v1/delivery-routes/{route_id}/pause',
        '/api/v1/delivery-routes/{route_id}/resume',
        '/api/v1/provider-feedback-events/list',
        '/api/v1/managed-smtp/node-events/list',
        '/api/v1/mta-agent/nodes/{node_id}/events',
        '/api/v1/mta-agent/nodes/{node_id}/heartbeat',
        '/api/v1/mta-agent/nodes/{node_id}/runtime-config',
        '/api/v1/managed-smtp/bootstrap-profiles/{profile_name}',
        '/api/v1/managed-smtp/bootstrap-profiles/list',
        '/api/v1/managed-smtp/deployment-summary',
        '/api/v1/managed-smtp/first-send-readiness',
        '/api/v1/managed-smtp/readiness-checks/list',
        '/api/v1/managed-smtp/readiness-checks/summary',
        '/api/v1/managed-smtp/readiness-checks/trend',
        '/api/v1/managed-smtp/readiness-checks/alerts',
        '/api/v1/managed-smtp/readiness-checks/notification',
        '/api/v1/domain-delivery-policies',
        '/api/v1/domain-delivery-policies/list',
        '/api/v1/domain-delivery-policies/managed-smtp-maintenance',
        '/api/v1/domain-delivery-policies/{policy_id}',
        '/api/v1/domain-delivery-policies/{policy_id}/authentication-plan',
        '/api/v1/domain-delivery-policies/{policy_id}/blocklist-scan',
        '/api/v1/domain-delivery-policies/{policy_id}/compliance-hold',
        '/api/v1/domain-delivery-policies/{policy_id}/dkim-key',
        '/api/v1/domain-delivery-policies/{policy_id}/pause',
        '/api/v1/domain-delivery-policies/{policy_id}/release-compliance-hold',
        '/api/v1/domain-delivery-policies/{policy_id}/reputation-dashboard',
        '/api/v1/domain-delivery-policies/{policy_id}/resume',
        '/api/v1/domain-delivery-policies/{policy_id}/verify-authentication',
        '/api/v1/domain-delivery-policies/{policy_id}/warmup-progress',
        '/api/v1/email-send-records/list',
        '/api/v1/email-send-records/{send_record_id}',
        '/api/v1/email-send-records/{send_record_id}/dead-letter',
        '/api/v1/email-send-records/{send_record_id}/requeue',
        '/api/v1/email-send-records/{send_record_id}/skip',
        '/api/v1/email-send-records/{send_record_id}/tracking-links',
        '/api/v1/tests/email-send-records/{send_record_id}/click',
        '/api/v1/tests/email-send-records/{send_record_id}/open',
        '/api/v1/tracking/click/{token}',
        '/api/v1/tracking/open/{token}',
        '/api/v1/provider-webhooks/sendgrid',
        '/api/v1/suppressions',
        '/api/v1/suppressions/list',
        '/api/v1/suppressions/{suppression_id}',
        '/api/v1/audiences/contacts',
        '/api/v1/audiences/contacts/list',
        '/api/v1/audiences/contacts/meta',
        '/api/v1/audiences/contacts/{contact_id}',
        '/api/v1/audiences/contacts/{contact_id}/unsubscribe-token',
        '/api/v1/audiences',
        '/api/v1/audiences/list',
        '/api/v1/audiences/import-csv',
        '/api/v1/audiences/import-csv/preview',
        '/api/v1/audience-snapshots/list',
        '/api/v1/audiences/{audience_id}',
        '/api/v1/audiences/{audience_id}/snapshots',
        '/api/v1/audiences/preview',
        '/api/v1/data-sources',
        '/api/v1/data-sources/list',
        '/api/v1/data-sources/{data_source_id}',
        '/api/v1/data-sources/{data_source_id}/ingest',
        '/api/v1/data-sources/{data_source_id}/schema',
        '/api/v1/data-sources/{data_source_id}/validate',
        '/api/v1/data-source-import-jobs/list',
        '/api/v1/data-source-mappings',
        '/api/v1/data-source-mappings/list',
        '/api/v1/data-source-mappings/{mapping_id}',
        '/api/v1/emails/send',
        '/api/v1/tests/send-email',
        '/api/v1/events',
        '/api/v1/events/list',
        '/api/v1/events/timeline',
        '/api/v1/events/{event_id}',
        '/api/v1/unsubscribe/{token}',
        '/api/templates',
        '/api/templates/{template_id}',
        '/api/templates/{template_id}/ai-draft',
        '/api/templates/{template_id}/versions',
        '/api/render',
        '/api/render-document',
        '/api/contacts',
        '/api/contacts/_meta',
        '/api/segments',
        '/api/segments/_meta/fields',
        '/api/segments/{segment_id}',
        '/api/segments/preview',
        '/api/segments/{segment_id}/refresh',
        '/api/journeys',
        '/api/journeys/{journey_id}/performance',
        '/api/providers',
        '/api/chat',
        '/api/experiments',
        '/api/experiments/{experiment_id}',
        '/api/experiments/{experiment_id}/results',
        '/api/experiments/{experiment_id}/launch',
        '/api/experiments/{experiment_id}/conclude',
        '/api/experiments/{experiment_id}/abort',
        '/api/approvals',
        '/api/approvals/{approval_id}/approve',
        '/api/approvals/{approval_id}/reject',
        '/api/sends',
        '/api/sends/{send_id}/launch',
        '/api/sends/{send_id}',
        '/api/sends/{send_id}/recipients/preview',
        '/api/sends/{send_id}/schedule',
        '/api/sends/{send_id}/cancel',
        '/api/sends/{send_id}/request_approval',
        '/api/reports/overview',
    }

    assert expected_paths.issubset(paths.keys())


def test_operator_user_schema_does_not_expose_password_hash() -> None:
    client = TestClient(app)
    schema = client.get('/openapi.json').json()['components']['schemas']['OperatorUserRead']
    properties = schema['properties']

    assert 'password_hash' not in properties
    assert {'email', 'display_name', 'role', 'is_active', 'failed_login_count'}.issubset(
        properties.keys()
    )


def test_campaign_test_send_response_exposes_managed_smtp_route_status() -> None:
    client = TestClient(app)
    schema = client.get('/openapi.json').json()['components']['schemas'][
        'CampaignTestSendResponse'
    ]
    properties = schema['properties']

    assert {
        'route_type',
        'route_key',
        'mta_route_resolved',
        'mta_route_status',
        'mta_route_send_type',
        'mta_rule_hit_send_type',
        'mta_rule_hit_sender_domain',
        'mta_rule_hit_recipient_domain',
        'mta_rule_hit_name',
        'mta_rule_hit_source',
        'mta_rule_hit_pool_source',
        'mta_rule_hit_provider_preference',
        'mta_rule_hit_provider_preference_mode',
        'mta_provider_preference_fallback_used',
        'mta_node_selection_membership_id',
        'mta_node_skipped_nodes',
        'mta_provider_preference_blocked',
        'mta_provider_preference_fallback_available',
        'mta_provider_preference_fallback_provider',
        'mta_provider_preference_fallback_node_name',
        'mta_pool_available_node_count',
        'mta_pool_required_available_node_count',
        'mta_pool_capacity_status',
        'mta_rate_limit_scope',
        'mta_rate_limit_window_seconds',
        'mta_rate_limit_max_per_minute',
        'mta_rate_limit_recent_count',
        'mta_route_block_code',
        'mta_route_block_message',
        'mta_submission_host',
        'smtp_response_code',
    }.issubset(properties.keys())
    assert set(properties['mta_route_status']['anyOf'][0]['enum']) == {
        'resolved',
        'blocked',
        'attempted',
        'not_attempted',
    }


def test_delivery_attempt_list_exposes_route_evidence_filters() -> None:
    client = TestClient(app)
    params = client.get('/openapi.json').json()['paths']['/api/v1/delivery-attempts/list']['get'][
        'parameters'
    ]
    names = {item['name'] for item in params}

    assert {
        'mta_ip_pool_id',
        'mta_node_id',
        'mta_provider',
        'mta_routing_rule_name',
        'mta_route_block_code',
    }.issubset(names)


def test_campaign_workflow_status_exposes_latest_proof_route() -> None:
    client = TestClient(app)
    schemas = client.get('/openapi.json').json()['components']['schemas']
    workflow_properties = schemas['CampaignWorkflowStatusRead']['properties']
    proof_route_properties = schemas['CampaignProofRouteRead']['properties']

    assert 'latest_proof_route' in workflow_properties
    assert {
        'delivery_attempt_id',
        'send_record_id',
        'mta_route_status',
        'mta_route_send_type',
        'mta_rule_hit_name',
        'mta_rule_hit_pool_source',
        'mta_rule_hit_provider_preference',
        'mta_submission_host',
        'smtp_response_code',
    }.issubset(proof_route_properties.keys())
    assert set(proof_route_properties['mta_route_status']['enum']) == {
        'resolved',
        'blocked',
        'attempted',
        'not_attempted',
    }


def test_api_tester_page() -> None:
    client = TestClient(app)
    response = client.get('/tester')
    assert response.status_code == 200
    assert 'Email Engine API Tester' in response.text
    assert '/admin' in response.text
    assert '/template-editor' in response.text
    assert '/admin/entities' in response.text
    assert '/admin/audience-import' in response.text
    assert '/admin/audiences' in response.text
    assert '/admin/campaigns' in response.text
    assert '/admin/journeys' in response.text
    assert '/admin/delivery' in response.text
    assert '/admin/suppressions' in response.text
    assert '/admin/analytics' in response.text
    assert '/admin/data-sources' in response.text
    assert '/docs' in response.text


def test_ai_template_draft_contract() -> None:
    client = TestClient(app)
    response = client.post(
        '/api/v1/ai/templates/draft',
        json={
            'brief': 'Trial activation email',
            'brand': {'name': 'SentientMail', 'primary_color': '#2563eb'},
            'required_variables': ['first_name', 'plan', 'recommendations'],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data['provider'] == 'email-engine'
    assert data['validation']['ok'] is True
    assert 'tracking_open' in data['template_variables']['sample_variables']
    assert 'recommendations' in data['template_variables']['sample_variables']
    assert '{% for item in recommendations %}' in data['html_body']


def test_ai_template_edit_contract() -> None:
    client = TestClient(app)
    response = client.post(
        '/api/v1/ai/templates/edit',
        json={
            'instruction': 'Make the CTA more urgent',
            'current_subject': 'Hello {{ first_name }}',
            'current_html': '<p>Hello {{ first_name }}</p><p><a href="{{ tracking_click }}">Review details</a></p>',
            'current_css': '.button { color: #ffffff; }',
            'current_text': 'Hello {{ first_name }}',
            'required_variables': ['first_name'],
            'sample_variables': {'first_name': 'Taylor'},
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data['provider'] == 'email-engine'
    assert data['validation']['ok'] is True
    assert data['sample_variables']['first_name'] == 'Taylor'
    assert 'tracking_open' in data['template_variables']['sample_variables']
    assert 'Requested update' in data['html_body']
    assert 'html_body' in data['changed_fields']
    assert 'HTML body changed.' in data['change_summary']


def test_ai_template_recommend_contract() -> None:
    client = TestClient(app)
    response = client.post(
        '/api/v1/ai/templates/recommend',
        json={
            'current_subject': 'Weekly update',
            'current_html': '<p>Hello {{ first_name }}</p>',
            'current_css': '',
            'current_text': 'Hello {{ first_name }}',
            'sample_variables': {
                'first_name': 'Taylor',
                'recommendations': ['One', 'Two'],
                'is_trial': True,
            },
            'goals': ['Improve conversion'],
            'audience_summary': 'Trial users',
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data['provider'] == 'email-engine'
    assert data['model'] == 'deterministic-template-recommend-v1'
    assert data['recommendations']
    codes = {item['code'] for item in data['recommendations']}
    assert 'add_tracked_cta' in codes
    assert 'add_unsubscribe' in codes
    assert 'use_loop_for_collection' in codes
    assert data['sample_variables']['first_name'] == 'Taylor'
    assert data['template_variables']['variables'][0]['name'] == 'first_name'


def test_ai_analytics_analysis_contract() -> None:
    client = TestClient(app)
    response = client.post(
        '/api/v1/ai/analytics/analyze',
        json={
            'report_type': 'campaign_performance',
            'report_context': {
                'items': [
                    {
                        'campaign_id': 'campaign-a',
                        'sent_count': 100,
                        'opened_count': 10,
                        'clicked_count': 1,
                        'failed_count': 4,
                        'bounced_count': 2,
                    }
                ]
            },
            'goals': ['Improve campaign performance'],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data['provider'] == 'email-engine'
    assert data['model'] == 'deterministic-analytics-analysis-v1'
    assert data['summary']
    assert data['recommendations']
    codes = {item['code'] for item in data['recommendations']}
    assert 'review_failed_delivery' in codes
    assert 'strengthen_cta' in codes


def test_ai_campaign_analysis_contract() -> None:
    client = TestClient(app)
    response = client.post(
        '/api/v1/ai/campaigns/analyze',
        json={
            'campaign_context': {
                'campaign': {'id': 'campaign-a', 'name': 'Launch test', 'status': 'draft'},
                'template': {'id': 'template-a', 'name': 'Trial template'},
                'validation': {
                    'ok': False,
                    'errors': ['Template is missing required field'],
                    'warnings': [],
                    'missing_variables': ['first_name'],
                },
                'audience_preview': {'estimated_count': 0, 'sample_contacts': []},
                'analytics': {
                    'sent_count': 100,
                    'opened_count': 10,
                    'clicked_count': 1,
                    'failed_count': 3,
                    'open_rate': 0.1,
                    'click_rate': 0.01,
                    'bounce_rate': 0.02,
                },
                'latest_send_record': None,
            },
            'goals': ['Assess launch readiness'],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data['provider'] == 'email-engine'
    assert data['model'] == 'deterministic-campaign-analysis-v1'
    assert data['summary']
    codes = {item['code'] for item in data['recommendations']}
    assert 'fix_launch_validation' in codes
    assert 'repair_audience_targeting' in codes
    assert 'triage_delivery_risk' in codes


def test_ai_audience_analysis_contract() -> None:
    client = TestClient(app)
    response = client.post(
        '/api/v1/ai/audiences/analyze',
        json={
            'audience_context': {
                'audience': {'name': 'Trial users'},
                'rule_tree': {
                    'operator': 'and',
                    'rules': [{'field': 'attributes.unknown_plan', 'comparator': 'eq', 'value': 'trial'}],
                },
                'preview': {'estimated_count': 0, 'sample_contacts': []},
                'contact_meta': {
                    'fields': ['email', 'first_name'],
                    'attribute_keys': ['plan', 'source'],
                },
            },
            'goals': ['Improve audience targeting'],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data['provider'] == 'email-engine'
    assert data['model'] == 'deterministic-audience-analysis-v1'
    assert data['summary']
    codes = {item['code'] for item in data['recommendations']}
    assert 'fix_unknown_fields' in codes
    assert 'broaden_zero_match_audience' in codes


def test_ai_delivery_analysis_contract() -> None:
    client = TestClient(app)
    response = client.post(
        '/api/v1/ai/delivery/analyze',
        json={
            'delivery_context': {
                'jobs': {
                    'items': [
                        {
                            'id': 'job-a',
                            'status': 'queued',
                            'queued_count': 5,
                        }
                    ]
                },
                'records': {
                    'items': [
                        {
                            'id': 'record-a',
                            'status': 'failed',
                            'provider': 'SG',
                            'error_message': 'Mailbox unavailable',
                            'attempt_count': 3,
                            'max_attempts': 3,
                        },
                        {
                            'id': 'record-b',
                            'status': 'queued',
                            'provider': 'SG',
                        },
                    ]
                },
            },
            'goals': ['Fix delivery failures'],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data['provider'] == 'email-engine'
    assert data['model'] == 'deterministic-delivery-analysis-v1'
    assert data['summary']
    codes = {item['code'] for item in data['recommendations']}
    assert 'process_queued_delivery' in codes
    assert 'triage_failed_records' in codes
    assert 'avoid_blind_retries' in codes


def test_ai_journey_analysis_contract() -> None:
    client = TestClient(app)
    response = client.post(
        '/api/v1/ai/journeys/analyze',
        json={
            'journey_context': {
                'journey': {
                    'id': 'journey-a',
                    'name': 'Trial activation',
                    'status': 'active',
                    'steps': [
                        {'id': 'step-a', 'step_type': 'branch'},
                        {'id': 'step-b', 'step_type': 'send_email'},
                    ],
                },
                'graph': {
                    'nodes': [
                        {
                            'id': 'node-a',
                            'step_id': 'step-a',
                            'step_type': 'branch',
                            'state': 'failed',
                            'counts': {'failed_count': 1, 'queued_send_count': 0},
                            'recent_error': 'Missing branch target',
                        },
                        {
                            'id': 'node-b',
                            'step_id': 'step-b',
                            'step_type': 'send_email',
                            'state': 'visited',
                            'config': {},
                            'counts': {'failed_count': 0, 'queued_send_count': 2},
                        },
                    ],
                    'edges': [],
                },
                'enrollments': {'items': [{'status': 'active'}]},
                'executions': {
                    'items': [
                        {'status': 'failed', 'error_message': 'Template missing'},
                    ]
                },
            },
            'goals': ['Improve journey reliability'],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data['provider'] == 'email-engine'
    assert data['model'] == 'deterministic-journey-analysis-v1'
    assert data['summary']
    codes = {item['code'] for item in data['recommendations']}
    assert 'connect_branch_outcomes' in codes
    assert 'triage_failed_journey_steps' in codes
    assert 'process_queued_journey_sends' in codes


def test_template_editor_page() -> None:
    client = TestClient(app)
    response = client.get('/template-editor')
    assert response.status_code == 200
    assert 'Email Engine Template Editor' in response.text
    assert 'Lint' in response.text
    assert 'Inspect Variables' in response.text
    assert 'Detected Variables' in response.text
    assert 'Use Sample JSON' in response.text
    assert 'Modify Current' in response.text
    assert 'Rendering complex Jinja/table template with sample variables' in response.text
    assert '.template-item.selected' in response.text
    assert 'applyInitialQuery' in response.text
    assert 'ai_prompt_loaded' in response.text
    assert 'Campaign recommendation loaded' in response.text
    assert 'aiPromptModify' in response.text
    assert 'Version History' in response.text
    assert 'Refresh Versions' in response.text
    assert 'Save Snapshot' in response.text
    assert 'restoreVersionToEditor' in response.text
    assert 'previewVersion' in response.text
    assert '/api/v1/templates/${templateId}/versions' in response.text
    assert 'Insert into' in response.text
    assert 'Seed Samples' in response.text
    assert 'Format Source' in response.text
    assert '/api/v1/templates/samples?reset=true' in response.text
    assert 'formatTemplateSource' in response.text
    assert 'CSS Builder' in response.text
    assert 'Insert Block' in response.text
    assert 'Body background' in response.text
    assert 'Container padding' in response.text
    assert 'Insert If/Else' in response.text
    assert 'Insert Loop' in response.text
    assert 'conditionalHtml' in response.text
    assert 'loopHtml' in response.text
    assert 'Design Blocks' in response.text
    assert 'Source -> Blocks' in response.text
    assert 'Blocks -> Source' in response.text
    assert 'designDocumentTemplateSource' in response.text
    assert 'previewDesignDocument' in response.text
    assert '/api/v1/templates/document/render' in response.text
    assert '/api/v1/templates/document/variables' in response.text
    assert '/api/v1/templates/document/validate' in response.text
    assert 'splitHtmlForDesignBlocks' in response.text
    assert 'protectedTemplateRanges' in response.text
    admin = client.get('/admin')
    assert admin.status_code == 200
    assert 'Schema status' in admin.text
    assert '/api/v1/system/diagnostics' in admin.text
    assert '/admin/system' in admin.text
    system = client.get('/admin/system')
    assert system.status_code == 200
    assert 'Email Engine System Diagnostics' in system.text
    assert '/api/v1/system/diagnostics' in system.text
    assert 'Entity Counts' in system.text
    assert 'Database Tables' in system.text
    assert 'renderTables' in system.text
    assert 'Table Columns' in system.text
    assert 'renderTableColumns' in system.text
    assert 'Raw Diagnostics' in system.text
    assert 'mergeRanges' in response.text
    assert 'html (raw Jinja)' in response.text
    assert 'htmlToDesignBlocks(template.html_body || "")' in response.text
    assert 'data-design-add="spacer"' in response.text
    assert 'data-design-add="trust_signal"' in response.text
    assert 'unwrapDesignContainers' in response.text
    assert 'rgbToHex' in response.text
    assert 'parsePadding' in response.text
    assert 'Inline HTML' in response.text
    assert 'Padding X' in response.text
    assert 'Duplicate' in response.text
    assert 'Block Document JSON' in response.text
    assert 'Export JSON' in response.text
    assert 'Import JSON' in response.text
    assert 'applyDesignDocJson' in response.text
    assert 'designDocForTemplate' in response.text
    assert '/api/v1/templates/${template.id}/document' in response.text
    assert 'document_json' in response.text
    assert 'Entity Workbench' in response.text
    assert '/admin' in response.text
    assert '/admin/audience-import' in response.text
    assert '/admin/audiences' in response.text
    assert '/admin/campaigns' in response.text
    assert '/admin/journeys' in response.text
    assert '/admin/delivery' in response.text
    assert '/admin/suppressions' in response.text
    assert '/admin/analytics' in response.text
    assert '/admin/data-sources' in response.text


def test_render_document_renders_design_blocks() -> None:
    client = TestClient(app)
    response = client.post(
        '/api/render-document',
        json={
            'document': {
                'blocks': [
                    {'type': 'heading', 'level': 2, 'align': 'center', 'text': 'Hello {{ first_name }}'},
                    {'type': 'paragraph', 'text': 'Your plan is {{ plan }}.'},
                    {
                        'type': 'button',
                        'text': 'Open dashboard',
                        'href': '{{ cta_url }}',
                        'bg': '#111827',
                        'color': '#ffffff',
                        'radius': 12,
                        'padding_y': 14,
                        'padding_x': 22,
                    },
                    {
                        'type': 'paragraph',
                        'html': '<strong>{{ plan }}</strong> with <a href="{{ cta_url }}">link</a>',
                    },
                    {'type': 'list', 'ordered': True, 'items': ['One {{ plan }}', 'Two']},
                    {
                        'type': 'image',
                        'src': 'https://example.com/hero.png',
                        'alt': 'Hero',
                        'width': 320,
                    },
                    {'type': 'divider', 'color': '#cccccc'},
                    {'type': 'spacer', 'height': 18},
                    {'type': 'html', 'code': '<ul><li>{{ item }}</li></ul>'},
                ]
            },
            'variables': {
                'first_name': 'Alex',
                'plan': 'trial',
                'cta_url': 'https://example.com/dashboard',
                'item': 'Saved raw HTML',
            },
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data['ok'] is True
    html = data['html_body']
    assert '<h2 style="text-align:center;">Hello Alex</h2>' in html
    assert 'Your plan is trial.' in html
    assert 'class="button"' in html
    assert 'href="https://example.com/dashboard"' in html
    assert 'border-radius:12px' in html
    assert 'padding:14px 22px' in html
    assert '<strong>trial</strong> with <a href="https://example.com/dashboard">link</a>' in html
    assert '<ol>' in html
    assert '<li>One trial</li>' in html
    assert '<li>Two</li>' in html
    assert 'src="https://example.com/hero.png"' in html
    assert 'alt="Hero"' in html
    assert 'border-top:1px solid #cccccc' in html
    assert 'height:18px' in html
    assert '<li>Saved raw HTML</li>' in html


def test_v1_render_document_renders_design_blocks() -> None:
    client = TestClient(app)
    response = client.post(
        '/api/v1/templates/document/render',
        json={
            'subject': 'Hello {{ first_name }}',
            'document_json': {
                'blocks': [
                    {'type': 'heading', 'level': 2, 'text': 'Hello {{ first_name }}'},
                    {
                        'type': 'button',
                        'text': 'Open',
                        'href': '{{ cta_url }}',
                        'radius': 10,
                    },
                ]
            },
            'variables': {
                'first_name': 'Alex',
                'cta_url': 'https://example.com/dashboard',
            },
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data['subject'] == 'Hello Alex'
    assert '<h2 style="text-align:left;">Hello Alex</h2>' in data['html_body']
    assert 'href="https://example.com/dashboard"' in data['html_body']
    assert 'border-radius:10px' in data['html_body']


def test_document_to_html_renders_nested_design_layout_blocks() -> None:
    html = document_to_html(
        {
            'blocks': [
                {
                    'type': 'section',
                    'className': 'email-section',
                    'bg': '#f8fafc',
                    'padding_y': 20,
                    'children': [
                        {
                            'type': 'heading',
                            'className': 'email-title',
                            'text': 'Hello {{ first_name }}',
                        },
                        {
                            'type': 'columns',
                            'gap': 20,
                            'mobile_stack': 'reverse',
                            'children': [
                                {
                                    'type': 'section',
                                    'className': 'email-column',
                                    'width': 40,
                                    'children': [
                                        {'type': 'paragraph', 'text': 'Plan {{ plan }}'}
                                    ],
                                },
                                {
                                    'type': 'section',
                                    'className': 'email-column',
                                    'width': 60,
                                    'children': [
                                        {
                                            'type': 'button',
                                            'text': 'Open',
                                            'href': '{{ tracking_click }}',
                                        }
                                    ],
                                },
                            ],
                        },
                        {
                            'type': 'conditional',
                            'variable': 'is_trial',
                            'children': [{'type': 'paragraph', 'text': 'Trial offer'}],
                            'else_children': [
                                {'type': 'paragraph', 'text': 'Account update'}
                            ],
                        },
                        {
                            'type': 'loop',
                            'item_name': 'item',
                            'collection': 'recommendations',
                            'children': [{'type': 'paragraph', 'text': '{{ item }}'}],
                        },
                    ],
                }
            ]
        }
    )

    assert '<div class="email-section" style="background:#f8fafc;padding:20px;">' in html
    assert '<table class="email-columns stack-mobile-reverse"' in html
    assert 'data-mobile-stack="reverse"' in html
    assert '<td width="40%"' in html
    assert '<td width="60%"' in html
    assert '<a class="button" href="{{ tracking_click }}"' in html
    assert '{% if is_trial %}' in html
    assert '{% else %}' in html
    assert '{% for item in recommendations %}' in html
    assert '{% endfor %}' in html


def test_html_to_document_imports_common_design_blocks_and_preserves_unknown_html() -> None:
    document = html_to_document(
        """
        <h1 class="email-title">Hello {{ first_name }}</h1>
        <p class="email-copy">Plain body copy</p>
        <p><strong>{{ plan }}</strong> with <a href="{{ tracking_click }}">link</a></p>
        <ul class="email-list"><li>One</li><li>{{ plan }}</li></ul>
        <img class="email-image" src="https://example.com/hero.png" alt="Hero" width="320" />
        <table class="summary"><tr><td>{{ item.name }}</td></tr></table>
        """
    )

    blocks = document['blocks']
    assert isinstance(blocks, list)
    assert blocks[0] == {
        'type': 'heading',
        'level': 1,
        'text': 'Hello {{ first_name }}',
        'className': 'email-title',
    }
    assert blocks[1] == {
        'type': 'paragraph',
        'className': 'email-copy',
        'text': 'Plain body copy',
    }
    assert blocks[2]['type'] == 'paragraph'
    assert '<strong>{{ plan }}</strong>' in str(blocks[2]['html'])
    assert blocks[3] == {
        'type': 'list',
        'ordered': False,
        'items': ['One', '{{ plan }}'],
        'className': 'email-list',
    }
    assert blocks[4]['type'] == 'image'
    assert blocks[4]['width'] == 320
    assert blocks[5]['type'] == 'table'
    assert blocks[5]['className'] == 'summary'
    assert blocks[5]['table_rows'] == [['{{ item.name }}']]


def test_html_document_round_trip_preserves_editable_table_footer_and_social_blocks() -> None:
    source = """
    <table class="email-table" role="presentation">
      <thead><tr><th>Metric</th><th>Value</th></tr></thead>
      <tbody><tr><td>Open rate</td><td>{{ open_rate }}</td></tr></tbody>
    </table>
    <footer class="email-footer">You subscribed.<br><a href="{{ unsubscribe_url }}">Unsubscribe</a></footer>
    <nav class="email-social-links">
      <a href="{{ linkedin_url }}">LinkedIn</a>
      <a href="{{ website_url }}">Website</a>
    </nav>
    """

    document = html_to_document(source)
    blocks = document['blocks']

    assert [block['type'] for block in blocks] == ['table', 'footer', 'social_links']
    assert blocks[0]['table_headers'] == ['Metric', 'Value']
    assert blocks[0]['table_rows'] == [['Open rate', '{{ open_rate }}']]
    assert blocks[1]['href'] == '{{ unsubscribe_url }}'
    assert blocks[2]['social_links'] == [
        {'label': 'LinkedIn', 'url': '{{ linkedin_url }}'},
        {'label': 'Website', 'url': '{{ website_url }}'},
    ]

    html = document_to_html(document)
    assert '<table class="email-table" role="presentation"' in html
    assert '<th style="border:1px solid #d8dee6;background:#f8fafc;' in html
    assert '<td style="border:1px solid #d8dee6;padding:10px 12px;vertical-align:top;">{{ open_rate }}</td>' in html
    assert '<footer class="email-footer"' in html
    assert '<a href="{{ unsubscribe_url }}">Unsubscribe</a>' in html
    assert '<nav class="email-social-links"' in html
    assert '<a href="{{ website_url }}" style="color:#2563eb;text-decoration:none;font-weight:700;">Website</a>' in html


def test_v1_document_import_html_endpoint_returns_safe_document_blocks() -> None:
    client = TestClient(app)
    response = client.post(
        '/api/v1/templates/document/import-html',
        json={
            'html_body': (
                '<div class="email-section">'
                '<h2>Welcome {{ first_name }}</h2>'
                '<p>Use {{ tracking_click }}</p>'
                '</div>'
                '<table class="summary"><tr><td>Keep raw</td></tr></table>'
            )
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data['block_count'] == 2
    assert data['raw_block_count'] == 0
    blocks = data['document_json']['blocks']
    assert blocks[0]['type'] == 'section'
    assert blocks[0]['children'][0]['type'] == 'heading'
    assert blocks[0]['children'][1]['text'] == 'Use {{ tracking_click }}'
    assert blocks[1]['type'] == 'table'
    assert blocks[1]['table_rows'] == [['Keep raw']]


def test_v1_document_render_handles_table_loop_sample_variables() -> None:
    client = TestClient(app)
    payload = {
        'subject': 'Receipt for {{ order_number }}',
        'document_json': {
            'blocks': [
                {'type': 'heading', 'text': 'Thanks, {{ first_name }}'},
                {
                    'type': 'html',
                    'code': (
                        '<table class="summary" role="presentation">'
                        '<tr><th>Item</th><th>Total</th></tr>'
                        '{% for item in order_items %}'
                        '<tr><td>{{ item.name }}</td><td>{{ item.total }}</td></tr>'
                        '{% endfor %}'
                        '</table>'
                    ),
                },
                {'type': 'html', 'code': '<a href="{{ unsubscribe_url }}">Unsubscribe</a>'},
            ]
        },
        'variables': {},
    }

    variables_response = client.post('/api/v1/templates/document/variables', json=payload)
    assert variables_response.status_code == 200
    payload['variables'] = variables_response.json()['sample_variables']
    response = client.post('/api/v1/templates/document/render', json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data['ok'] is True
    assert 'Starter plan' in data['html_body']
    assert '$49.00' in data['html_body']


def test_v1_template_preview_handles_table_loop_sample_variables() -> None:
    client = TestClient(app)
    payload = {
        'subject': 'Receipt for {{ order_number }}',
        'html_body': (
            '<table class="summary" role="presentation">'
            '<tr><th>Item</th><th>Total</th></tr>'
            '{% for item in order_items %}'
            '<tr><td>{{ item.name }}</td><td>{{ item.total }}</td></tr>'
            '{% endfor %}'
            '</table>'
            '<a href="{{ unsubscribe_url }}">Unsubscribe</a>'
        ),
        'css_body': '.summary { width: 100%; }',
        'text_body': '{% for item in order_items %}{{ item.name }} {{ item.total }}{% endfor %}',
        'variables': {},
    }
    variables_response = client.post('/api/v1/templates/variables', json=payload)
    assert variables_response.status_code == 200
    payload['variables'] = variables_response.json()['sample_variables']
    response = client.post('/api/v1/templates/preview', json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data['ok'] is True
    assert 'Starter plan' in data['html_body']
    assert '$49.00' in data['html_body']


def test_operation_feedback_injects_at_final_body_close() -> None:
    html = (
        '<html><body><script>'
        'function htmlDocument(){ return `<!doctype html><body>${content}</body></html>`; }'
        '</script><main>admin</main></body></html>'
    )

    rendered = with_operation_feedback(html)

    assert rendered.index('function htmlDocument') < rendered.index('<main>admin</main>')
    assert rendered.index('<main>admin</main>') < rendered.index('ee-operation-feedback')
    assert rendered.count('ee-operation-feedback') >= 1
    assert 'AI template edit' in rendered
    assert 'Campaign launch' in rendered
    assert 'Audience import preview' in rendered
    assert 'label: `${name} running`' in rendered
    assert 'operationFor(input, init)' in rendered
    assert 'return `<!doctype html><body>${content}</body></html>`;' in rendered


def test_analytics_overview_schema_allows_zero_recent_events() -> None:
    client = TestClient(app)

    response = client.get('/openapi.json')

    assert response.status_code == 200
    data = response.json()
    params = data['paths']['/api/v1/analytics/overview']['get']['parameters']
    recent_event_limit = next(
        item for item in params if item['name'] == 'recent_event_limit'
    )
    assert recent_event_limit['schema']['minimum'] == 0


def test_document_renderer_supports_sentientmail_logo_block() -> None:
    html = document_to_html(
        {
            'blocks': [
                {'type': 'spokeo_logo'},
                {'type': 'heading', 'text': 'Welcome {{ first_name }}'},
            ]
        }
    )

    assert 'Spokeo Logo' in html
    assert 'www.spokeo.com' in html
    assert 'Welcome {{ first_name }}' in html


def test_v1_document_variables_and_validate_use_design_blocks() -> None:
    client = TestClient(app)
    payload = {
        'subject': 'Hello {{ first_name }}',
        'document_json': {
            'blocks': [
                {'type': 'paragraph', 'text': 'Plan {{ plan }} for {{ first_name }}'},
                {'type': 'button', 'text': 'Open', 'href': '{{ cta_url }}'},
            ]
        },
        'variables': {'first_name': 'Alex'},
    }

    variables_response = client.post('/api/v1/templates/document/variables', json=payload)
    assert variables_response.status_code == 200
    variable_names = {item['name'] for item in variables_response.json()['variables']}
    assert {'first_name', 'plan', 'cta_url'}.issubset(variable_names)

    validate_response = client.post('/api/v1/templates/document/validate', json=payload)
    assert validate_response.status_code == 200
    validation = validate_response.json()
    assert validation['ok'] is False
    assert 'plan' in validation['missing_variables']
    assert 'cta_url' in validation['missing_variables']


def test_template_payload_accepts_document_json() -> None:
    document = {
        'blocks': [
            {
                'type': 'paragraph',
                'text': 'Hello {{ first_name }}',
                'align': 'left',
            }
        ]
    }
    payload = _template_create_payload(
        {
            'name': 'document-json',
            'subject': 'Hello {{ first_name }}',
            'html_body': '<p>Hello {{ first_name }}</p>',
            'document_json': document,
        }
    )

    assert payload.document_json == document


def test_template_document_json_round_trips_through_current_version() -> None:
    client = TestClient(app)
    name = f'document-roundtrip-{uuid4()}'
    initial_document = {
        'blocks': [
            {'type': 'section', 'children': [{'type': 'paragraph', 'text': 'Initial block'}]}
        ]
    }
    updated_document = {
        'blocks': [
            {
                'type': 'columns',
                'gap': 18,
                'children': [
                    {'type': 'section', 'width': 35, 'children': [{'type': 'heading', 'text': 'Left'}]},
                    {'type': 'section', 'width': 65, 'children': [{'type': 'button', 'text': 'Right'}]},
                ],
            }
        ]
    }

    try:
        create_response = client.post(
            '/api/v1/templates',
            json={
                'name': name,
                'subject': 'Structured document',
                'html_body': '<p>Fallback</p>',
                'document_json': initial_document,
            },
        )
    except OperationalError as exc:
        pytest.skip(f'database is unavailable for document_json round-trip test: {exc}')
    assert create_response.status_code == 200
    template_id = create_response.json()['id']

    update_response = client.patch(
        f'/api/v1/templates/{template_id}',
        json={'document_json': updated_document},
    )
    assert update_response.status_code == 200

    document_response = client.get(f'/api/v1/templates/{template_id}/document')
    assert document_response.status_code == 200
    data = document_response.json()
    assert data['version_number'] is not None
    assert data['document_json'] == updated_document


def test_template_document_update_refreshes_current_template_html() -> None:
    client = TestClient(app)
    name = f'document-current-html-{uuid4()}'

    try:
        create_response = client.post(
            '/api/v1/templates',
            json={
                'name': name,
                'subject': 'Current document',
                'html_body': '<p>Old body</p>',
                'document_json': {
                    'blocks': [{'type': 'paragraph', 'text': 'Old design body'}],
                },
            },
        )
    except OperationalError as exc:
        pytest.skip(f'database is unavailable for current document test: {exc}')
    assert create_response.status_code == 200
    template_id = create_response.json()['id']

    update_response = client.put(
        f'/api/v1/templates/{template_id}/document',
        json={
            'document_json': {
                'blocks': [
                    {
                        'type': 'section',
                        'children': [{'type': 'paragraph', 'text': 'New design body'}],
                    }
                ]
            },
            'set_current': True,
        },
    )
    assert update_response.status_code == 200

    template_response = client.get(f'/api/v1/templates/{template_id}')
    assert template_response.status_code == 200
    template = template_response.json()
    assert 'New design body' in template['html_body']
    assert 'Old body' not in template['html_body']


def test_template_variables_endpoint_extracts_samples_and_native_variables() -> None:
    client = TestClient(app)
    response = client.post(
        '/api/v1/templates/variables',
        json={
            'subject': 'Hello {{ first_name }}',
            'html_body': (
                '<p>{{ first_name }} is on {{ plan }}.</p>'
                '{% for item in recommendations %}<p>{{ loop.index }} {{ item }}</p>{% endfor %}'
                '{% for item in order_items %}<p>{{ item.name }} {{ item.total }}</p>{% endfor %}'
                '<a href="{{ tracking_click }}">Read more</a>'
                '{{ tracking_open }}'
                '<a href="{{ unsubscribe_url }}">Unsubscribe</a>'
            ),
            'css_body': '.plan-{{ plan }} { color: blue; }',
            'text_body': 'Hi {{ first_name }}',
            'variables': {},
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data['ok'] is True
    assert {item['name'] for item in data['variables']} == {
        'first_name',
        'plan',
        'order_items',
        'recommendations',
    }
    assert {item['name'] for item in data['native_variables']} == {
        'tracking_click',
        'tracking_open',
        'unsubscribe_url',
    }
    assert data['sample_variables']['first_name'] == 'Alex'
    assert data['sample_variables']['plan'] == 'trial'
    assert isinstance(data['sample_variables']['recommendations'], list)
    assert isinstance(data['sample_variables']['order_items'][0], dict)
    assert data['sample_variables']['unsubscribe_url'].startswith('https://')


def test_seeded_sample_template_collections_render_with_generated_data() -> None:
    service = TemplateService(db=None)  # type: ignore[arg-type]
    sample_names = {template.name for template in SAMPLE_TEMPLATES}

    assert {
        'Sample_Ecommerce_Order_Receipt',
        'Sample_Ecommerce_Abandoned_Cart',
        'Sample_Ecommerce_Back_In_Stock',
        'Sample_Subscription_Trial_Ending',
        'Sample_Subscription_Payment_Failed',
        'Sample_Subscription_Usage_Digest',
        'Sample_Social_Welcome',
        'Sample_Social_Connection_Request',
        'Sample_Social_Weekly_Digest',
    }.issubset(sample_names)

    for template in SAMPLE_TEMPLATES:
        variables = service.variables(
            TemplateValidationRequest(
                subject=template.subject,
                html_body=template.html_body,
                css_body=template.css_body,
                text_body=template.text_body,
                variables={},
            )
        ).sample_variables
        preview = service.preview(
            TemplatePreviewRequest(
                subject=template.subject,
                html_body=template.html_body,
                css_body=template.css_body,
                text_body=template.text_body,
                variables=variables,
            )
        )

        assert preview.ok, template.name
        assert preview.subject
        assert 'Unsubscribe' in preview.html_body


def test_admin_pages() -> None:
    client = TestClient(app)
    home = client.get('/admin')
    entities = client.get('/admin/entities')
    import_page = client.get('/admin/audience-import')
    audiences = client.get('/admin/audiences')
    campaigns = client.get('/admin/campaigns')
    journeys = client.get('/admin/journeys')
    delivery = client.get('/admin/delivery')
    suppressions = client.get('/admin/suppressions')
    analytics = client.get('/admin/analytics')
    data_sources = client.get('/admin/data-sources')
    assert home.status_code == 200
    assert entities.status_code == 200
    assert import_page.status_code == 200
    assert audiences.status_code == 200
    assert campaigns.status_code == 200
    assert journeys.status_code == 200
    assert delivery.status_code == 200
    assert suppressions.status_code == 200
    assert analytics.status_code == 200
    assert data_sources.status_code == 200
    assert 'Email Engine Admin' in home.text
    assert 'Email Engine Entity Workbench' in entities.text
    assert 'Email Engine Audience Import' in import_page.text
    assert 'Email Engine Audience Builder' in audiences.text
    assert 'Load Contact Fields' in audiences.text
    assert 'Snapshot' in audiences.text
    assert 'AI Audience Review' in audiences.text
    assert 'reviewAudienceWithAi' in audiences.text
    assert '/api/v1/ai/audiences/analyze' in audiences.text
    assert '.item.selected' in audiences.text
    assert 'Email Engine Campaign Manager' in campaigns.text
    assert 'Clone' in campaigns.text
    assert 'Validate' in campaigns.text
    assert 'Workflow Status' in campaigns.text
    assert 'Workflow Readiness' in campaigns.text
    assert 'workflowSteps' in campaigns.text
    assert 'campaignSummary' in campaigns.text
    assert 'launchProgress' in campaigns.text
    assert 'pollLaunchProgress' in campaigns.text
    assert 'launchActivity' in campaigns.text
    assert 'Continue Polling' in campaigns.text
    assert 'Process Queue Now' in campaigns.text
    assert 'Open Delivery' in campaigns.text
    assert 'processLaunchQueue' in campaigns.text
    assert 'Test Preview' in campaigns.text
    assert 'Test Send' in campaigns.text
    assert 'Approve' in campaigns.text
    assert 'AI Campaign Review' in campaigns.text
    assert 'AI Review' in campaigns.text
    assert '/api/v1/ai/campaigns/analyze' in campaigns.text
    assert 'Assess campaign workflow readiness' in campaigns.text
    assert 'Use in Template Editor' in campaigns.text
    assert 'templateEditorAiUrl' in campaigns.text
    assert 'Process Due' in campaigns.text
    assert 'Email Engine Journey Manager' in journeys.text
    assert 'Save Journey' in journeys.text
    assert 'Enroll Contact' in journeys.text
    assert 'Process Due' in journeys.text
    assert 'Journey Graph' in journeys.text
    assert 'AI Journey Review' in journeys.text
    assert 'reviewJourneyWithAi' in journeys.text
    assert '/api/v1/ai/journeys/analyze' in journeys.text
    assert 'graph-edge-label' in journeys.text
    assert 'default_next_step_id' in journeys.text
    assert 'Email Engine Delivery Manager' in delivery.text
    assert 'Process Queued' in delivery.text
    assert 'All campaigns' in delivery.text
    assert 'All send jobs' in delivery.text
    assert 'Select send record' in delivery.text
    assert 'Requeue Record' in delivery.text
    assert 'Delete Record' in delivery.text
    assert 'Load Domain Policies' in delivery.text
    assert 'Apply Compliance Hold' in delivery.text
    assert 'Release Compliance Hold' in delivery.text
    assert 'AI Delivery Review' in delivery.text
    assert 'reviewDeliveryWithAi' in delivery.text
    assert '/api/v1/ai/delivery/analyze' in delivery.text
    assert 'Email Engine Suppressions' in suppressions.text
    assert 'Save Suppression' in suppressions.text
    assert 'Email Engine Analytics' in analytics.text
    assert 'Campaign Analytics' in analytics.text
    assert 'Campaign Timeline' in analytics.text
    assert 'focusedCampaign' in analytics.text
    assert 'renderFocusedCampaign' in analytics.text
    assert 'Analytics Overview' in analytics.text
    assert 'Audience Performance' in analytics.text
    assert 'Campaign Performance' in analytics.text
    assert 'Campaign Rate Comparison' in analytics.text
    assert 'Performance Summary' in analytics.text
    assert 'performanceSummary' in analytics.text
    assert 'Recommended next action' in analytics.text
    assert 'AI Analysis' in analytics.text
    assert 'aiAnalyzeReport' in analytics.text
    assert '/api/v1/ai/analytics/analyze' in analytics.text
    assert 'Domain Deliverability' in analytics.text
    assert 'Journey Performance' in analytics.text
    assert 'journeyDashboard' in analytics.text
    assert 'Journey State Comparison' in analytics.text
    assert 'Journey Step Breakdown' in analytics.text
    assert 'journeyStatusCharts' in analytics.text
    assert 'Event Timeline' in analytics.text
    assert 'Email Engine Data Sources' in data_sources.text
    assert 'Save Source' in data_sources.text
    assert 'Validate Source' in data_sources.text
    assert 'Discover Schema' in data_sources.text
    assert 'Ingest Rows' in data_sources.text
    assert 'Preview Audience' in campaigns.text
    assert 'Preview Template' in campaigns.text
    assert 'Matched Contacts' in campaigns.text
    assert '/tester' in home.text
    assert '/template-editor' in home.text
    assert '/admin/entities' in home.text
    assert '/admin/audience-import' in home.text
    assert '/admin/audiences' in home.text
    assert '/admin/campaigns' in home.text
    assert '/admin/journeys' in home.text
    assert '/admin/delivery' in home.text
    assert '/admin/suppressions' in home.text
    assert '/admin/analytics' in home.text
    assert '/admin/data-sources' in home.text
    assert '/docs' in home.text


def test_root_redirects_to_admin() -> None:
    client = TestClient(app, follow_redirects=False)
    response = client.get('/')
    assert response.status_code == 307
    assert response.headers['location'] == '/admin'


def test_esp_shell_serves_react_app() -> None:
    client = TestClient(app)

    response = client.get('/esp')

    assert response.status_code == 200
    assert 'Email Engine ESP' in response.text
    assert '/esp/assets/' in response.text


def test_esp_shell_fallback_serves_react_app() -> None:
    client = TestClient(app)

    response = client.get('/esp/campaigns')

    assert response.status_code == 200
    assert 'Email Engine ESP' in response.text
