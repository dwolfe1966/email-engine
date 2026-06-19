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
        'campaignTriageAction',
        'campaignTriageItems',
        "title: 'Create campaign draft'",
        "title: 'Choose template'",
        "title: 'Choose audience'",
        "title: 'Run readiness'",
        "title: 'Fix validation blockers'",
        "title: 'Send proof email'",
        "title: 'Dry-run launch'",
        "title: 'Monitor delivery'",
        "title: 'Campaign ready'",
        'Campaign triage',
        'Draft',
        'Content',
        'Audience',
        'Readiness',
        'Proof and launch',
        'launchFoundationItems',
        'Launch Foundations',
        'Template contract, audience snapshot, send engine handoff, and suppression impact.',
        'Template contract',
        'Select a saved template before proof or launch.',
        'Audience snapshot',
        'Choose an audience so launch volume and suppressions can be checked.',
        'Send engine handoff',
        'Run dry-run launch before production queueing.',
        'Suppression impact',
        'Dry-run to reveal opt-out, bounce, and complaint suppression impact.',
        'campaign-foundation-panel',
        'campaign-foundation-strip',
        'campaign-foundation-item',
        'campaign-triage-panel',
        'campaign-triage-list',
        'campaign-triage-row',
        'aiCampaignSummary',
        'aiCampaignRecommendations',
        'reviewCampaignWithAi',
        "fetchJson<AIWorkflowAnalysis>('/api/v1/ai/campaigns/analyze'",
        'AI Campaign Review',
        'campaign-ai-review-panel',
        'campaign-ai-summary',
        'Run AI Campaign Review after loading readiness',
        'type CampaignLaunchResult',
        'type CampaignTestSendResult',
        'lastLaunchResult',
        'lastTestSendResult',
        'setLastTestSendResult({ ...data, to_email: testEmail.trim() })',
        'setLastLaunchResult(data)',
        'Dry-run result',
        'Launch result',
        'Test send result',
        'test-send-result-card',
        'mta_hostname',
        'mta_ip_pool_name',
        'smtp_response_code',
        'mta_route_block_code',
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
        'Test send result',
        'Refresh Readiness',
        'Check Audience',
        'Preview Email',
        'Dry-Run Launch',
        'Open delivery',
        'Campaign triage',
        'Create campaign draft',
        'Choose template',
        'Choose audience',
        'Send proof email',
        'Monitor delivery',
        'Campaign ready',
        'Proof and launch',
        'Launch Foundations',
        'Template contract',
        'Audience snapshot',
        'Send engine handoff',
        'Suppression impact',
        'AI Campaign Review',
        'Run AI Review',
        'No AI campaign review loaded',
        'Run AI Campaign Review after loading readiness',
    ]

    for token in expected_tokens:
        assert token in bundle
