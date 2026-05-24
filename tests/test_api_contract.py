from fastapi.testclient import TestClient

from email_platform.api.compat import _template_create_payload
from email_platform.main import app


def test_openapi_exposes_gui_integration_paths() -> None:
    client = TestClient(app)
    paths = client.get('/openapi.json').json()['paths']

    expected_paths = {
        '/api/v1/templates',
        '/api/v1/templates/lint',
        '/api/v1/templates/list',
        '/api/v1/templates/document/render',
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
        '/api/v1/delivery/process-queued',
        '/api/v1/email-send-records/list',
        '/api/v1/email-send-records/{send_record_id}',
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


def test_template_editor_page() -> None:
    client = TestClient(app)
    response = client.get('/template-editor')
    assert response.status_code == 200
    assert 'Email Engine Template Editor' in response.text
    assert 'Lint' in response.text
    assert 'Inspect Variables' in response.text
    assert 'Detected Variables' in response.text
    assert 'Use Sample JSON' in response.text
    assert 'Insert into' in response.text
    assert 'Seed Samples' in response.text
    assert 'CSS Builder' in response.text
    assert 'Insert Block' in response.text
    assert 'Design Blocks' in response.text
    assert 'Source -> Blocks' in response.text
    assert 'Blocks -> Source' in response.text
    assert 'designDocumentTemplateSource' in response.text
    assert 'previewDesignDocument' in response.text
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
    assert 'Email Engine Campaign Manager' in campaigns.text
    assert 'Clone' in campaigns.text
    assert 'Validate' in campaigns.text
    assert 'Workflow Status' in campaigns.text
    assert 'Workflow Readiness' in campaigns.text
    assert 'workflowSteps' in campaigns.text
    assert 'Test Preview' in campaigns.text
    assert 'Test Send' in campaigns.text
    assert 'Approve' in campaigns.text
    assert 'Process Due' in campaigns.text
    assert 'Email Engine Journey Manager' in journeys.text
    assert 'Save Journey' in journeys.text
    assert 'Enroll Contact' in journeys.text
    assert 'Process Due' in journeys.text
    assert 'Journey Graph' in journeys.text
    assert 'default_next_step_id' in journeys.text
    assert 'Email Engine Delivery Manager' in delivery.text
    assert 'Process Queued' in delivery.text
    assert 'All campaigns' in delivery.text
    assert 'All send jobs' in delivery.text
    assert 'Select send record' in delivery.text
    assert 'Requeue Record' in delivery.text
    assert 'Delete Record' in delivery.text
    assert 'Email Engine Suppressions' in suppressions.text
    assert 'Save Suppression' in suppressions.text
    assert 'Email Engine Analytics' in analytics.text
    assert 'Campaign Analytics' in analytics.text
    assert 'Analytics Overview' in analytics.text
    assert 'Audience Performance' in analytics.text
    assert 'Campaign Performance' in analytics.text
    assert 'Domain Deliverability' in analytics.text
    assert 'Journey Performance' in analytics.text
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
