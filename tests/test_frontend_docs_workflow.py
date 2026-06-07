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


def assert_docs_triage_contract(source: str) -> None:
    expected_tokens = [
        'docsTriageAction',
        'docsTriageItems',
        "title: 'Resolve schema contract'",
        "title: 'Configure delivery contract'",
        "title: 'Document owned SMTP gap'",
        "title: 'Set public endpoints'",
        "title: 'Run live contract checks'",
        "title: 'Review failing workflow'",
        "title: 'Contract ready'",
        'Contract triage',
        'Schema',
        'Owned SMTP',
        'Public endpoints',
        'Live checks',
        'Object ownership',
        'Owned SMTP remains a first-class platform foundation even when provider adapters are available.',
        'Email Engine remains system of record for ESP objects',
        'docs-triage-panel',
        'docs-triage-grid',
    ]

    for token in expected_tokens:
        assert token in source


def test_docs_source_has_contract_triage_panel() -> None:
    assert_docs_triage_contract(frontend_source())


def test_built_esp_bundle_includes_contract_triage_panel() -> None:
    bundle = frontend_bundle()
    expected_tokens = [
        'Contract triage',
        'Resolve schema contract',
        'Configure delivery contract',
        'Document owned SMTP gap',
        'Set public endpoints',
        'Run live contract checks',
        'Review failing workflow',
        'Contract ready',
        'Owned SMTP',
        'Public endpoints',
        'Live checks',
        'Object ownership',
        'Open API Docs',
    ]

    for token in expected_tokens:
        assert token in bundle
