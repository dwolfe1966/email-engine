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
        'const audienceNextAction = !name.trim()',
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
        'audience-triage-grid',
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
    ]

    for token in expected_tokens:
        assert token in bundle
