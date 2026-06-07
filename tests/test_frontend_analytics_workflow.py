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


def assert_analytics_report_focus_contract(source: str) -> None:
    expected_tokens = [
        'const reportFocusSummary = !selectedCampaignId',
        "title: 'Select a campaign'",
        "title: 'Detail report not loaded'",
        "title: campaignDetail.failed_count || campaignDetail.bounced_count ? 'Review delivery issues' : 'Detail report loaded'",
        'Report focus',
        'Timeline window',
        'Deliverability',
        'reportFocusSummary.domainStatus',
        'analytics-focus-summary',
    ]

    for token in expected_tokens:
        assert token in source


def test_analytics_source_has_report_focus_summary() -> None:
    assert_analytics_report_focus_contract(frontend_source())


def test_built_esp_bundle_includes_report_focus_summary() -> None:
    bundle = frontend_bundle()
    expected_tokens = [
        'Report focus',
        'Select a campaign',
        'Detail report not loaded',
        'Review delivery issues',
        'Detail report loaded',
        'Timeline window',
        'Deliverability',
        'Load Report',
    ]

    for token in expected_tokens:
        assert token in bundle
