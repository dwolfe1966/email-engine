from fastapi.testclient import TestClient

from email_platform.main import app


def test_openapi_exposes_gui_integration_paths() -> None:
    client = TestClient(app)
    paths = client.get('/openapi.json').json()['paths']

    expected_paths = {
        '/api/v1/templates',
        '/api/v1/templates/{template_id}',
        '/api/v1/campaigns',
        '/api/v1/campaigns/{campaign_id}',
        '/api/v1/audiences/contacts',
        '/api/v1/audiences/contacts/{contact_id}',
        '/api/v1/audiences/contacts/{contact_id}/unsubscribe-token',
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
