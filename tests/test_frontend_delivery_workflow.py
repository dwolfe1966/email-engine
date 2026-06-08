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
        'providerFootprint',
        'deliveryFoundationItems',
        'Send Engine Foundation',
        'Owned SMTP server',
        'Platform-owned SMTP service still needs MTA, auth, throttling, and domain controls.',
        'Send queues',
        'Bounce queues',
        'Dedicated bounce and complaint queues are still needed.',
        'Deliverability feedback',
        'Reputation, complaint, bounce, and inbox-placement feedback need a unified loop.',
        'deliveryOperationsContractItems',
        'Send Engine Operations Contract',
        'Operational contracts for owned SMTP, queue lifecycle, retries, bounces, feedback, and deliverability controls.',
        'SMTP service contract',
        'Owned SMTP needs MTA configuration, authenticated submission, domain policy, TLS, and tenant-level rate controls.',
        'Queue lifecycle',
        'Send queues need claim locks, visibility timeouts, dead-letter handling, and operator-safe replay controls.',
        'Retry policy',
        'Retries need provider-aware backoff, max-attempt policy, suppression checks, and permanent-failure promotion.',
        'Bounce classification',
        'Failures must classify hard bounce, soft bounce, complaint, deferral, and policy block outcomes.',
        'Feedback ingestion',
        'Provider events and owned SMTP logs need one durable feedback stream into suppression and analytics records.',
        'Deliverability controls',
        'Domain warmup, reputation monitoring, inbox-placement signals, and throttle overrides need admin controls.',
        'delivery-foundation-panel',
        'delivery-foundation-grid',
        'delivery-operations-panel',
        'delivery-operations-grid',
        'delivery-triage-panel',
        'delivery-triage-grid',
        'aiDeliverySummary',
        'aiDeliveryRecommendations',
        'function reviewDeliveryWithAi',
        'function deleteRecord',
        '/api/v1/ai/delivery/analyze',
        '/api/v1/email-send-records/${selectedRecordId}',
        "method: 'DELETE'",
        'delivery_context',
        'AI Delivery Review',
        'Delete Record',
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
        'Send Engine Foundation',
        'Owned SMTP server',
        'Send queues',
        'Bounce queues',
        'Deliverability feedback',
        'Send Engine Operations Contract',
        'SMTP service contract',
        'Queue lifecycle',
        'Retry policy',
        'Bounce classification',
        'Feedback ingestion',
        'Deliverability controls',
        'Provider settings',
        'Open Compliance',
        'AI Delivery Review',
        'Delete Record',
        'Run AI Review',
        '/api/v1/ai/delivery/analyze',
        'No AI delivery review loaded',
    ]

    for token in expected_tokens:
        assert token in bundle
