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
        "title: 'Plan owned SMTP'",
        "title: 'Set public base URL'",
        "title: 'Resolve schema state'",
        "title: 'Review diagnostics'",
        "title: 'Configure AI provider'",
        "title: 'Integrations ready'",
        'Integration triage',
        'Owned SMTP',
        'Provider adapters',
        'Public endpoints',
        'AI provider',
        'dataConnectorTableReady',
        'webhookContractReady',
        'integrationFoundationItems',
        'Integration Foundation Map',
        'Data connectors, owned SMTP, feedback webhooks, and AI operations.',
        'Data connectors',
        'Connector registry and mapping tables need schema visibility.',
        'Owned SMTP foundation',
        'Owned SMTP server, MTA policy, throttling, and domain controls remain platform work.',
        'Feedback webhooks',
        'Webhook routing must connect bounce and complaint events to durable compliance records.',
        'AI operations',
        'Production agent workflows need OpenAI configuration and observability.',
        'Owned SMTP should be first-class; use provider adapters only as delivery paths.',
        'integration-foundation-panel',
        'integration-foundation-grid',
        'integration-triage-panel',
        'integration-triage-grid',
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
        'Plan owned SMTP',
        'Set public base URL',
        'Configure AI provider',
        'Integrations ready',
        'Owned SMTP',
        'Provider adapters',
        'Public endpoints',
        'AI provider',
        'Integration Foundation Map',
        'Data connectors',
        'Owned SMTP foundation',
        'Feedback webhooks',
        'AI operations',
        'Open Settings',
    ]

    for token in expected_tokens:
        assert token in bundle
