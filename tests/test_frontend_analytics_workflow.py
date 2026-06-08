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
        'const analyticsNextStep = !selectedCampaignId',
        "title: 'Select report campaign'",
        "title: 'Load campaign detail'",
        "title: 'Review delivery risk'",
        "title: 'Compare engagement'",
        "title: 'Review journey risk'",
        "title: 'Send brief to AI'",
        'Guided analytics next step',
        'analyticsNextStep.run',
        'analytics-next-step',
        'function csvCell',
        'function exportAnalyticsCsv',
        'Campaign Performance',
        'Audience Comparison',
        'Journey Risk',
        'Domain Deliverability',
        'email-engine-analytics-',
        'Export CSV',
        'analyticsAiBriefSummary',
        'Top campaigns:',
        'Audience comparison:',
        'Journey risk detail:',
        'Domain deliverability:',
        'Recent campaign timeline:',
        'AI analytics brief',
        'analytics-ai-brief',
        'analyticsAiActions',
        'analyticsAiPrimaryAction',
        'Primary AI action:',
        'Operator action checklist:',
        'AI action panel',
        'analytics-ai-action-panel',
        'analytics-ai-action-grid',
        'Delivery risk',
        'Audience fit',
        'Journey follow-up',
        'analyticsFoundationSignals',
        'Foundation Signals',
        'Data graph, send engine, feedback loop, and agent follow-up signals from reports.',
        'Data graph',
        'Load contacts, audiences, and client entities before attribution analysis.',
        'Send engine',
        'Launch and process sends before queue health can be measured.',
        'Feedback loop',
        'Load domain analytics and wire bounce/complaint feedback for durable deliverability signals.',
        'Agent follow-up',
        'Send analytics context to AI Studio for next-best-action planning and persistent operator handoff.',
        'analytics-foundation-panel',
        'analytics-foundation-grid',
        'analyticsDeliverabilityContractItems',
        'Deliverability Signal Contract',
        'Domain, bounce, failure, engagement, routing, and AI evidence requirements for durable feedback loops.',
        'Domain signal contract',
        'Domain reports need provider, DNS identity, bounce rate, complaint rate, and reputation state for each sending domain.',
        'Bounce signal contract',
        'Bounce metrics should connect analytics rows to compliance suppressions and delivery retry decisions.',
        'Failure signal contract',
        'Failed sends need error family, provider response, retry state, and operator disposition in reports.',
        'Engagement signal contract',
        'Open and click signals need bot filtering, identity resolution, attribution window, and audience segment context.',
        'Feedback routing',
        'Deliverability signals should route to Delivery, Compliance, Campaigns, and AI Studio without manual copying.',
        'AI evidence pack',
        'AI recommendations need the exact report rows, domain signals, suppression context, and operator action history.',
        'analytics-deliverability-panel',
        'analytics-deliverability-grid',
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
        'Guided analytics next step',
        'Select report campaign',
        'Load campaign detail',
        'Review delivery risk',
        'Compare engagement',
        'Review journey risk',
        'Send brief to AI',
        'AI Brief',
        'Export CSV',
        'email-engine-analytics-',
        'Downloaded analytics CSV export.',
        'AI analytics brief',
        'Primary AI action:',
        'Operator action checklist:',
        'AI action panel',
        'Delivery risk',
        'Audience fit',
        'Journey follow-up',
        'Foundation Signals',
        'Data graph',
        'Send engine',
        'Feedback loop',
        'Agent follow-up',
        'Deliverability Signal Contract',
        'Domain signal contract',
        'Bounce signal contract',
        'Failure signal contract',
        'Engagement signal contract',
        'Feedback routing',
        'AI evidence pack',
        'Top campaigns:',
        'Audience comparison:',
        'Journey risk detail:',
        'Domain deliverability:',
        'Recent campaign timeline:',
    ]

    for token in expected_tokens:
        assert token in bundle
