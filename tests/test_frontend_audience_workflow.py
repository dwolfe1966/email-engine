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


def assert_audience_guided_next_step_contract(source: str) -> None:
    expected_tokens = [
        'const audienceNextAction = !formText(name)',
        "title: 'Name the audience'",
        "title: 'Fix rule JSON'",
        "title: 'Preview audience reach'",
        "title: 'Adjust rule or import contacts'",
        "title: 'Save campaign-ready audience'",
        "title: 'Snapshot before launch'",
        'Guided audience next step',
        'audienceNextAction.detail',
        'audienceNextAction.run',
        'audience-next-action',
        'audienceTriageAction',
        'audienceTriageItems',
        "title: 'Import contact data'",
        "title: 'Name the audience'",
        "title: 'Fix rule JSON'",
        "title: 'Preview audience reach'",
        "title: 'Adjust rule or import contacts'",
        "title: 'Save audience'",
        "title: 'Create campaign handoff'",
        "title: 'Snapshot before launch'",
        'Audience triage',
        'Contact data',
        'Rule',
        'Preview',
        'Samples',
        'Campaign handoff',
        'audience-triage-panel',
        'audience-triage-list',
        'audience-triage-row',
        'aiAudienceSummary',
        'aiAudienceRecommendations',
        'reviewAudienceWithAi',
        "fetchJson<AIWorkflowAnalysis>('/api/v1/ai/audiences/analyze'",
        'AI Audience Review',
        'audience-ai-review-panel',
        'audience-ai-summary',
        'Run AI Audience Review after previewing reach',
        'audienceImpactSummary',
        'Rule impact',
        'Preview needed',
        'No matched contacts',
        'Very broad audience',
        'Very narrow audience',
        'Audience impact ready',
        'audience-impact-summary',
        'selectedFieldProfile',
        'highlightedFieldProfiles',
        'fieldProfileForField',
        'Selected field',
        'Field sample coverage',
        'sample coverage',
        'audience-field-intel',
        'field-profile-strip',
        'stableAudienceRuleKey',
        'selectedAudienceCampaigns',
        'campaignAwareSummary',
        'Campaign awareness',
        'Campaign usage found',
        'No campaign usage yet',
        'audience-campaign-awareness',
        'audienceFoundationItems',
        'Audience Foundations',
        'Contact attributes, client entities, snapshots, and campaign usage readiness.',
        'Contact attributes',
        'Import richer contact attributes before relying on segmentation.',
        'Client entities',
        'Client-owned entities and relationships still need canonical storage before multi-entity audiences.',
        'Snapshot contract',
        'Create a stable snapshot before campaign launch.',
        'Campaign usage',
        'audience-foundation-panel',
        'audience-foundation-strip',
        'audience-foundation-item',
        'audienceSegmentationContractItems',
        'Audience Segmentation Contract',
        'Field metadata, entity joins, consent filters, impact checks, snapshots, and campaign handoff requirements.',
        'Field contract',
        'Audience rules need typed contact, attribute, and client-entity fields with examples and coverage metadata.',
        'Entity join contract',
        'Multi-entity targeting needs relationship joins across contacts, accounts, stores, orders, memberships, and custom objects.',
        'Consent filter contract',
        'Audience previews should expose suppression, unsubscribe, bounce, and complaint exclusions before activation.',
        'Impact contract',
        'Segment impact needs match count, sample contacts, match-rate banding, and warnings for broad or narrow reach.',
        'Activation should use immutable audience snapshots with rule version, contact count, and source metadata.',
        'Handoff contract',
        'Campaign and journey handoffs need stable audience IDs, snapshot references, and downstream usage visibility.',
        'audience-segmentation-contract-panel',
        'audience-segmentation-contract-list',
        'audience-segmentation-contract-row',
    ]

    for token in expected_tokens:
        assert token in source


def test_audience_builder_source_has_guided_next_step_action() -> None:
    assert_audience_guided_next_step_contract(frontend_source())


def test_built_esp_bundle_includes_audience_guided_next_step_action() -> None:
    bundle = frontend_bundle()
    expected_tokens = [
        'Guided audience next step',
        'Name the audience',
        'Fix rule JSON',
        'Preview audience reach',
        'Adjust rule or import contacts',
        'Save campaign-ready audience',
        'Snapshot before launch',
        'Preview Contacts',
        'Import Contacts',
        'Save Audience',
        'Create Snapshot',
        'Audience triage',
        'Import contact data',
        'Save audience',
        'Create campaign handoff',
        'Contact data',
        'Campaign handoff',
        'AI Audience Review',
        'Run AI Review',
        'No AI audience review loaded',
        'Run AI Audience Review after previewing reach',
        'Rule impact',
        'Preview needed',
        'No matched contacts',
        'Very broad audience',
        'Very narrow audience',
        'Audience impact ready',
        'Selected field',
        'Field sample coverage',
        'sample coverage',
        'No field selected',
        'Campaign awareness',
        'Campaign usage found',
        'No campaign usage yet',
        'Open Campaigns',
        'Audience Foundations',
        'Contact attributes',
        'Client entities',
        'Snapshot contract',
        'Campaign usage',
        'Audience Segmentation Contract',
        'Field contract',
        'Entity join contract',
        'Consent filter contract',
        'Impact contract',
        'Handoff contract',
        'Open Contacts',
        'Open Data',
    ]

    for token in expected_tokens:
        assert token in bundle
