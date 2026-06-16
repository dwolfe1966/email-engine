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


def assert_overview_triage_contract(source: str) -> None:
    expected_tokens = [
        'overviewTriageAction',
        'overviewTriageItems',
        "title: 'Resolve schema readiness'",
        "title: 'Configure outbound provider'",
        "title: 'Plan owned SMTP'",
        "title: 'Review delivery pressure'",
        "title: 'Review import failures'",
        "title: 'Review journey failures'",
        "title: 'Configure AI handoff'",
        "title: 'Workspace ready'",
        'Workspace triage',
        'Provider',
        'Owned SMTP',
        'Delivery',
        'Imports',
        'AI handoff',
        'activeDataSources',
        'providerLinkedSuppressions',
        'platformFoundationItems',
        'Platform Foundations',
        'Data model, send engine, feedback loop, and agent layer readiness.',
        'Data model',
        'Activate data sources and model client-owned entities.',
        'Send engine',
        'SMTP server, queues, and throttle controls still need foundation work.',
        'Feedback loop',
        'Bounce and complaint events need durable webhook-backed feedback.',
        'Agent layer',
        'Production agents need OpenAI configuration and persistent workflow memory.',
        'Owned SMTP remains a platform foundation gap even while provider adapters are available.',
        'overview-foundation-panel',
        'overview-foundation-strip',
        'overview-foundation-item',
        'overview-triage-panel',
        'overview-triage-list',
        'overview-triage-row',
    ]

    for token in expected_tokens:
        assert token in source


def test_overview_source_has_workspace_triage_panel() -> None:
    assert_overview_triage_contract(frontend_source())


def test_built_esp_bundle_includes_workspace_triage_panel() -> None:
    bundle = frontend_bundle()
    expected_tokens = [
        'Workspace triage',
        'Resolve schema readiness',
        'Configure outbound provider',
        'Plan owned SMTP',
        'Review delivery pressure',
        'Review import failures',
        'Review journey failures',
        'Configure AI handoff',
        'Workspace ready',
        'Owned SMTP',
        'AI handoff',
        'Platform Foundations',
        'Data model',
        'Send engine',
        'Feedback loop',
        'Agent layer',
        'Open Integrations',
        'Open Delivery',
        'Open Reports',
    ]

    for token in expected_tokens:
        assert token in bundle
