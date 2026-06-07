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


def assert_contacts_triage_contract(source: str) -> None:
    expected_tokens = [
        'contactsTriageAction',
        'contactsTriageItems',
        "title: 'Import contacts'",
        "title: 'Enrich contact attributes'",
        "title: 'Review opt-outs'",
        "title: 'Select contact'",
        "title: 'Inspect unsubscribe state'",
        "title: 'Use contact data'",
        'Contacts triage',
        'Contact base',
        'Attribute coverage',
        'Source diversity',
        'Compliance state',
        'contacts-triage-panel',
        'contacts-triage-grid',
    ]

    for token in expected_tokens:
        assert token in source


def test_contacts_source_has_triage_panel() -> None:
    assert_contacts_triage_contract(frontend_source())


def test_built_esp_bundle_includes_contacts_triage_panel() -> None:
    bundle = frontend_bundle()
    expected_tokens = [
        'Contacts triage',
        'Import contacts',
        'Enrich contact attributes',
        'Review opt-outs',
        'Select contact',
        'Inspect unsubscribe state',
        'Use contact data',
        'Contact base',
        'Attribute coverage',
        'Compliance state',
    ]

    for token in expected_tokens:
        assert token in bundle
