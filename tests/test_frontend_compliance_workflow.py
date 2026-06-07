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


def assert_compliance_triage_contract(source: str) -> None:
    expected_tokens = [
        'complianceTriageAction',
        'complianceTriageItems',
        "title: 'Review spam complaints'",
        "title: 'Watch hard bounces'",
        "title: 'Suppress failed recipients'",
        "title: 'Respect opt-outs'",
        "title: 'Compliance clear'",
        'Compliance triage',
        'Complaint risk',
        'Bounce protection',
        'Opt-out coverage',
        'Failed candidates',
        'function draftSuppressionFromRecord',
        "setSource(`delivery_failure:${providerLabel(record.provider)}`)",
        'Failed Recipient Review',
        'Draft suppressions from failed delivery records before retrying.',
        'Draft Suppression',
        'compliance-candidate-panel',
        'compliance-triage-panel',
        'compliance-triage-grid',
    ]

    for token in expected_tokens:
        assert token in source


def test_compliance_source_has_triage_panel() -> None:
    assert_compliance_triage_contract(frontend_source())


def test_built_esp_bundle_includes_compliance_triage_panel() -> None:
    bundle = frontend_bundle()
    expected_tokens = [
        'Compliance triage',
        'Review spam complaints',
        'Watch hard bounces',
        'Suppress failed recipients',
        'Respect opt-outs',
        'Compliance clear',
        'Complaint risk',
        'Bounce protection',
        'Opt-out coverage',
        'Failed candidates',
        'Failed Recipient Review',
        'Draft Suppression',
    ]

    for token in expected_tokens:
        assert token in bundle
