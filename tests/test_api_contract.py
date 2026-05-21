from fastapi.testclient import TestClient

from email_platform.main import app


def test_openapi_exposes_gui_integration_paths() -> None:
    client = TestClient(app)
    paths = client.get('/openapi.json').json()['paths']

    expected_paths = {
        '/api/v1/templates',
        '/api/v1/templates/list',
        '/api/v1/templates/preview',
        '/api/v1/templates/validate',
        '/api/v1/templates/{template_id}',
        '/api/v1/campaigns',
        '/api/v1/campaigns/list',
        '/api/v1/campaigns/{campaign_id}',
        '/api/v1/campaigns/{campaign_id}/analytics',
        '/api/v1/campaigns/{campaign_id}/launch',
        '/api/v1/campaign-send-jobs/list',
        '/api/v1/delivery/process-queued',
        '/api/v1/email-send-records/list',
        '/api/v1/email-send-records/{send_record_id}/tracking-links',
        '/api/v1/tracking/click/{token}',
        '/api/v1/tracking/open/{token}',
        '/api/v1/provider-webhooks/sendgrid',
        '/api/v1/suppressions',
        '/api/v1/audiences/contacts',
        '/api/v1/audiences/contacts/list',
        '/api/v1/audiences/contacts/{contact_id}',
        '/api/v1/audiences/contacts/{contact_id}/unsubscribe-token',
        '/api/v1/audiences',
        '/api/v1/audiences/list',
        '/api/v1/audiences/{audience_id}',
        '/api/v1/audiences/preview',
        '/api/v1/data-sources',
        '/api/v1/data-sources/list',
        '/api/v1/data-sources/{data_source_id}',
        '/api/v1/data-source-mappings',
        '/api/v1/data-source-mappings/list',
        '/api/v1/data-source-mappings/{mapping_id}',
        '/api/v1/emails/send',
        '/api/v1/tests/send-email',
        '/api/v1/events',
        '/api/v1/events/{event_id}',
        '/api/v1/unsubscribe/{token}',
    }

    assert expected_paths.issubset(paths.keys())


def test_api_tester_page() -> None:
    client = TestClient(app)
    response = client.get('/tester')
    assert response.status_code == 200
    assert 'Email Engine API Tester' in response.text


def test_template_editor_page() -> None:
    client = TestClient(app)
    response = client.get('/template-editor')
    assert response.status_code == 200
    assert 'Email Engine Template Editor' in response.text


def test_admin_pages() -> None:
    client = TestClient(app)
    home = client.get('/admin')
    entities = client.get('/admin/entities')
    assert home.status_code == 200
    assert entities.status_code == 200
    assert 'Email Engine Admin' in home.text
    assert 'Email Engine Entity Workbench' in entities.text
