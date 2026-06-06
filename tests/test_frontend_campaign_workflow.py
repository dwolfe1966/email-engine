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


def assert_campaign_next_step_contract(source: str) -> None:
    expected_tokens = [
        'const campaignNextStep = !workflowStatus',
        "label: 'Run readiness'",
        "actionLabel: 'Refresh Readiness'",
        "label: 'Fix validation blockers'",
        "actionLabel: 'Check Audience'",
        "label: 'Preview test content'",
        "actionLabel: 'Preview Email'",
        "label: 'Dry-run launch'",
        "actionLabel: 'Dry-Run Launch'",
        'Guided next step',
        'campaignNextStep.detail',
        'campaignNextStep.run',
        'type CampaignLaunchResult',
        'lastLaunchResult',
        'setLastLaunchResult(data)',
        'Dry-run result',
        'Launch result',
        'lastLaunchResult.requested_count',
        'lastLaunchResult.queued_count',
        'lastLaunchResult.suppressed_count',
        'launch-result-card',
    ]

    for token in expected_tokens:
        assert token in source


def test_campaign_workspace_source_has_guided_next_step_action() -> None:
    assert_campaign_next_step_contract(frontend_source())


def test_built_esp_bundle_includes_campaign_guided_next_step_action() -> None:
    bundle = frontend_bundle()
    expected_tokens = [
        'Guided next step',
        'Run readiness',
        'Fix validation blockers',
        'Preview test content',
        'Dry-run launch',
        'Dry-run result',
        'Launch result',
        'Refresh Readiness',
        'Check Audience',
        'Preview Email',
        'Dry-Run Launch',
        'Open delivery',
    ]

    for token in expected_tokens:
        assert token in bundle
