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


def assert_delivery_triage_contract(source: str) -> None:
    expected_tokens = [
        'deliveryTriageAction',
        'deliveryTriageItems',
        "title: 'Review failed records'",
        "title: 'Process queued delivery'",
        "title: 'Load job progress'",
        "title: 'Delivery clear'",
        'Delivery triage',
        'Queue pressure',
        'Failure review',
        'Selected job',
        'Selected record',
        'delivery-triage-panel',
        'delivery-triage-grid',
        'aiDeliverySummary',
        'aiDeliveryRecommendations',
        'function reviewDeliveryWithAi',
        '/api/v1/ai/delivery/analyze',
        'delivery_context',
        'AI Delivery Review',
        'Run AI Review',
        'delivery-ai-review-panel',
        'delivery-ai-summary',
        'No AI delivery review loaded',
    ]

    for token in expected_tokens:
        assert token in source


def test_delivery_source_has_triage_panel() -> None:
    assert_delivery_triage_contract(frontend_source())


def test_built_esp_bundle_includes_delivery_triage_panel() -> None:
    bundle = frontend_bundle()
    expected_tokens = [
        'Delivery triage',
        'Review failed records',
        'Process queued delivery',
        'Load job progress',
        'Delivery clear',
        'Queue pressure',
        'Failure review',
        'Selected job',
        'Selected record',
        'AI Delivery Review',
        'Run AI Review',
        '/api/v1/ai/delivery/analyze',
        'No AI delivery review loaded',
    ]

    for token in expected_tokens:
        assert token in bundle
