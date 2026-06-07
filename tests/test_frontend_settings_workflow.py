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


def assert_settings_triage_contract(source: str) -> None:
    expected_tokens = [
        'settingsTriageAction',
        'settingsTriageItems',
        "title: 'Sign in to manage settings'",
        "title: 'Require admin access'",
        "title: 'Review locked accounts'",
        "title: 'Review failed logins'",
        "title: 'Resolve schema state'",
        "title: 'Configure owned SMTP'",
        "title: 'Set public base URL'",
        "title: 'Configure AI provider'",
        "title: 'Settings ready'",
        'Settings triage',
        'Access',
        'Owned SMTP',
        'Public URL',
        'Schema',
        'AI provider',
        'Owned SMTP should be managed here as a platform foundation, not only through provider adapters.',
        'settings-triage-panel',
        'settings-triage-grid',
    ]

    for token in expected_tokens:
        assert token in source


def test_settings_source_has_triage_panel() -> None:
    assert_settings_triage_contract(frontend_source())


def test_built_esp_bundle_includes_settings_triage_panel() -> None:
    bundle = frontend_bundle()
    expected_tokens = [
        'Settings triage',
        'Sign in to manage settings',
        'Require admin access',
        'Review locked accounts',
        'Configure owned SMTP',
        'Set public base URL',
        'Configure AI provider',
        'Settings ready',
        'Owned SMTP',
        'Public URL',
        'AI provider',
    ]

    for token in expected_tokens:
        assert token in bundle
