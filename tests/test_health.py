from fastapi.testclient import TestClient

from email_platform.main import app


def test_health() -> None:
    client = TestClient(app)
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'


def test_schema_status_endpoint() -> None:
    client = TestClient(app)
    response = client.get('/api/v1/system/schema-status')
    assert response.status_code == 200
    data = response.json()
    assert 'ok' in data
    assert 'current_revision' in data
    assert 'expected_revision' in data
    assert data['migration_command'] == 'alembic upgrade head'
