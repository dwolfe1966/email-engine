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
        'settingsFoundationItems',
        'Foundation Control Plane',
        'Schema, owned SMTP, public endpoint, and AI provider governance.',
        'Schema control',
        'Migration status must be resolved before production changes.',
        'Owned SMTP control',
        'Owned SMTP server settings, MTA policy, throttling, and domains need admin controls.',
        'Endpoint control',
        'PUBLIC_BASE_URL is required for tracking, unsubscribe, and webhook URLs.',
        'AI control',
        'OpenAI configuration and model governance are needed for production agents.',
        'Owned SMTP should be managed here as a platform foundation, not only through provider adapters.',
        'settings-foundation-panel',
        'settings-foundation-strip',
        'settings-foundation-item',
        'settingsGovernanceItems',
        'Platform Governance Contract',
        'Configuration ownership, secrets, policy controls, release evidence, and audit governance.',
        'Config ownership',
        'Production configuration changes need explicit owner, approval path, and operator role boundaries.',
        'Secret governance',
        'SMTP, provider, AI, and connector secrets need vault references, rotation cadence, and access audit.',
        'Policy governance',
        'Owned SMTP, AI tools, imports, and suppression policy need workspace-level controls before automation.',
        'Release governance',
        'Schema, public URL, docs, diagnostics, and smoke-test evidence should be captured before release handoff.',
        'Audit governance',
        'Operator changes, provider changes, AI actions, and data imports need immutable audit trails.',
        'settings-governance-panel',
        'settings-governance-grid',
        'settings-triage-panel',
        'settings-triage-list',
        'settings-triage-row',
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
        'Foundation Control Plane',
        'Schema control',
        'Owned SMTP control',
        'Endpoint control',
        'AI control',
        'Platform Governance Contract',
        'Config ownership',
        'Secret governance',
        'Policy governance',
        'Release governance',
        'Audit governance',
        'Refresh Diagnostics',
    ]

    for token in expected_tokens:
        assert token in bundle
