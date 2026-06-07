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


def assert_data_triage_contract(source: str) -> None:
    expected_tokens = [
        'dataTriageAction',
        'dataTriageItems',
        "title: 'Create data source'",
        "title: 'Activate source'",
        "title: 'Validate source'",
        "title: 'Fix validation errors'",
        "title: 'Discover schema'",
        "title: 'Save contact mapping'",
        "title: 'Review import results'",
        "title: 'Open imported contacts'",
        "title: 'Run import dry run'",
        'Data triage',
        'Source readiness',
        'Mapping coverage',
        'Validation state',
        'Import health',
        'importReviewJobs',
        'function focusImportJob',
        'Import Job Review',
        'Review failed, skipped, or error-bearing import jobs before rerunning ingest.',
        'Dry Run Selected',
        'Review Job',
        'data-import-review-panel',
        'data-triage-panel',
        'data-triage-grid',
    ]

    for token in expected_tokens:
        assert token in source


def test_data_source_has_triage_panel() -> None:
    assert_data_triage_contract(frontend_source())


def test_built_esp_bundle_includes_data_triage_panel() -> None:
    bundle = frontend_bundle()
    expected_tokens = [
        'Data triage',
        'Create data source',
        'Validate source',
        'Discover schema',
        'Save contact mapping',
        'Review import results',
        'Open imported contacts',
        'Run import dry run',
        'Source readiness',
        'Validation state',
        'Import health',
        'Import Job Review',
        'Dry Run Selected',
        'Review Job',
    ]

    for token in expected_tokens:
        assert token in bundle
