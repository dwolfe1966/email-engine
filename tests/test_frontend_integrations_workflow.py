from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND_SOURCE = ROOT / 'frontend' / 'src' / 'main.tsx'
FRONTEND_DIST = ROOT / 'frontend' / 'dist'


def frontend_source() -> str:
    return FRONTEND_SOURCE.read_text()


def frontend_bundle() -> str:
    assets = sorted((FRONTEND_DIST / 'assets').glob('index-*.js'))
    assert assets, 'frontend/dist does not include the built ESP index bundle'
    return '\n'.join(asset.read_text() for asset in assets)


def assert_integrations_triage_contract(source: str) -> None:
    expected_tokens = [
        'integrationTriageAction',
        'integrationTriageItems',
        "title: 'Configure outbound provider'",
        "title: 'Review managed SMTP path'",
        "title: 'Set public base URL'",
        "title: 'Resolve schema state'",
        "title: 'Review diagnostics'",
        "title: 'Configure AI provider'",
        "title: 'Integrations ready'",
        'Integration triage',
        'Managed SMTP',
        'Provider adapters',
        'Public endpoints',
        'AI provider',
        'dataConnectorTableReady',
        'webhookContractReady',
        'integrationFoundationItems',
        'Integration Foundation Map',
        'Data connectors, managed SMTP, feedback webhooks, and AI operations.',
        'Data connectors',
        'Connector registry and mapping tables need schema visibility.',
        'Managed SMTP foundation',
        'Scaleway and future MTA providers are managed through provider profiles, inventory, and route policy.',
        'Feedback webhooks',
        'Webhook routing must connect bounce and complaint events to durable compliance records.',
        'AI operations',
        'Production agent workflows need OpenAI configuration and observability.',
        'integrationConnectorRoadmapItems',
        'Connector Roadmap',
        'Source families and platform services still needed for enterprise-grade data movement.',
        'RDBMS',
        'PostgreSQL, MySQL, and SQL Server connectors need credential vaulting, table discovery, and incremental sync cursors.',
        'Warehouse',
        'BigQuery, Snowflake, and Redshift imports need batch scheduling, field typing, and cost-aware preview limits.',
        'NoSQL',
        'MongoDB and document-store sources need collection sampling, nested field mapping, and stable entity extraction.',
        'API and webhook',
        'REST, GraphQL, and inbound webhook connectors need managed secrets, retries, and event-to-entity mapping.',
        'Managed SMTP is first-class; use provider adapters as additional delivery paths.',
        'AI agent tools',
        'Ever-present agents need scoped connector tools, approvals, memory, and cross-workflow audit trails.',
        'SendGrid remains available; manage Scaleway and future MTAs from the Delivery control plane.',
        'SMTP secret rotation',
        'managed_smtp_feedback_previous_secret_configured',
        'Previous managed SMTP feedback secret is still accepted temporarily.',
        'Only the current managed SMTP feedback secret is accepted.',
        'integration-foundation-panel',
        'integration-foundation-strip',
        'integration-foundation-item',
        'integration-connector-panel',
        'integration-connector-list',
        'integration-connector-row',
        'integration-triage-panel',
        'integration-triage-list',
        'integration-triage-row',
    ]

    for token in expected_tokens:
        assert token in source


def test_integrations_source_has_triage_panel() -> None:
    assert_integrations_triage_contract(frontend_source())


def test_built_esp_bundle_includes_integrations_triage_panel() -> None:
    bundle = frontend_bundle()
    expected_tokens = [
        'Integration triage',
        'Configure outbound provider',
        'Review managed SMTP path',
        'Set public base URL',
        'Configure AI provider',
        'Integrations ready',
        'Managed SMTP',
        'SMTP secret rotation',
        'Previous managed SMTP feedback secret is still accepted temporarily.',
        'Provider adapters',
        'Public endpoints',
        'AI provider',
        'Integration Foundation Map',
        'Data connectors',
        'Managed SMTP foundation',
        'Feedback webhooks',
        'AI operations',
        'Connector Roadmap',
        'RDBMS',
        'Warehouse',
        'NoSQL',
        'API and webhook',
        'AI agent tools',
        'Open Settings',
    ]

    for token in expected_tokens:
        assert token in bundle
