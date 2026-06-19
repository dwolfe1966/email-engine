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


def test_system_diagnostics_endpoint() -> None:
    client = TestClient(app)
    response = client.get('/api/v1/system/diagnostics')
    assert response.status_code == 200
    data = response.json()
    assert 'schema' in data
    assert data['email_provider']['provider']
    assert 'sendgrid_configured' in data['email_provider']
    assert 'managed_smtp_submission_configured' in data['email_provider']
    assert 'managed_smtp_submission_tls_enabled' in data['email_provider']
    assert 'managed_smtp_feedback_configured' in data['email_provider']
    assert 'managed_smtp_feedback_previous_secret_configured' in data['email_provider']
    assert 'openai_configured' in data['ai']
    assert 'entity_counts' in data
    assert 'database_tables' in data
    assert isinstance(data['database_tables'], list)
    assert 'database_table_columns' in data
    assert isinstance(data['database_table_columns'], dict)
