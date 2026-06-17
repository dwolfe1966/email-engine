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


def assert_journey_triage_contract(source: str) -> None:
    expected_tokens = [
        'journeyTriageAction',
        'journeyTriageItems',
        "title: 'Review journey failures'",
        "title: 'Process queued sends'",
        "title: 'Process due enrollments'",
        "title: 'Select or create journey'",
        "title: 'Add first send step'",
        "title: 'Journey ready'",
        'Journey triage',
        'Failure pressure',
        'Queued sends',
        'Active enrollments',
        'Builder readiness',
        'journey-triage-panel',
        'journey-triage-list',
        'journey-triage-row',
        'aiJourneySummary',
        'aiJourneyRecommendations',
        'function reviewJourneyWithAi',
        '/api/v1/ai/journeys/analyze',
        '/api/v1/journeys/${selectedJourneyId}/graph',
        'journey_context',
        'AI Journey Review',
        'Run AI Review',
        'journey-ai-review-panel',
        'journey-ai-summary',
        'No AI journey review loaded',
        'entryRuleValid',
        'journeyFoundationItems',
        'Journey Foundations',
        'Orchestration queues, event triggers, send handoff, and feedback readiness.',
        'Orchestration queue',
        'Due enrollments and generated sends need durable worker monitoring.',
        'Event triggers',
        'Real-time event and data-source triggers still need connector-backed activation.',
        'Send handoff',
        'Add a send step with a template before journey delivery can run.',
        'Feedback loop',
        'Bounce, engagement, and delivery feedback should feed journey decisions.',
        'journey-foundation-panel',
        'journey-foundation-grid',
    ]

    for token in expected_tokens:
        assert token in source


def test_journey_source_has_triage_panel() -> None:
    assert_journey_triage_contract(frontend_source())


def test_built_esp_bundle_includes_journey_triage_panel() -> None:
    bundle = frontend_bundle()
    expected_tokens = [
        'Journey triage',
        'Review journey failures',
        'Process queued sends',
        'Process due enrollments',
        'Select or create journey',
        'Add first send step',
        'Journey ready',
        'Failure pressure',
        'Active enrollments',
        'Builder readiness',
        'AI Journey Review',
        'Run AI Review',
        '/api/v1/ai/journeys/analyze',
        'No AI journey review loaded',
        'Journey Foundations',
        'Orchestration queue',
        'Event triggers',
        'Send handoff',
        'Feedback loop',
        'Open Delivery',
    ]

    for token in expected_tokens:
        assert token in bundle
