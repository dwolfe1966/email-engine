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


def assert_compliance_triage_contract(source: str) -> None:
    expected_tokens = [
        'complianceTriageAction',
        'complianceTriageItems',
        "title: 'Review spam complaints'",
        "title: 'Watch hard bounces'",
        "title: 'Suppress failed recipients'",
        "title: 'Respect opt-outs'",
        "title: 'Compliance clear'",
        'Compliance triage',
        'Complaint risk',
        'Bounce protection',
        'Opt-out coverage',
        'Failed candidates',
        'complianceFeedbackItems',
        'Deliverability Feedback Loop',
        'Provider events, bounce queues, complaint handling, and retry safety.',
        'Provider feedback',
        'Provider webhooks need to feed durable bounce and complaint events.',
        'Bounce queue',
        'Hard bounces need a dedicated review queue before retry decisions.',
        'Complaint loop',
        'Spam complaints need a feedback loop tied to reputation and suppression policy.',
        'Retry safety',
        'failed recipient(s) should be classified before requeue.',
        'function draftSuppressionFromRecord',
        "setSource(`delivery_failure:${providerLabel(record.provider)}`)",
        'Failed Recipient Review',
        'Draft suppressions from failed delivery records before retrying.',
        'Draft Suppression',
        'compliance-candidate-panel',
        'compliance-feedback-panel',
        'compliance-feedback-strip',
        'compliance-feedback-item',
        'compliance-triage-panel',
        'compliance-triage-list',
        'compliance-triage-row',
        'complianceFoundationItems',
        'Compliance Foundations',
        'Consent ledger, preference center, suppression propagation, and audit readiness.',
        'Consent ledger',
        'Consent capture, source attribution, and historical proof need a canonical ledger.',
        'Preference center',
        'Contacts still need self-service preferences beyond global suppression records.',
        'Suppression propagation',
        'Suppressions must propagate to campaign, journey, and delivery execution before launch.',
        'Audit trail',
        'Operator changes, provider events, and policy decisions need immutable audit history.',
        'compliance-foundation-panel',
        'compliance-foundation-grid',
        'compliancePolicyContractItems',
        'Feedback Policy Contract',
        'Suppression scope, bounce and complaint disposition, retry blocking, traceability, and audit evidence.',
        'Suppression scope',
        'Suppression policy must define whether a block applies globally, by brand, by domain, or by campaign family.',
        'Bounce disposition',
        'Hard bounces should become permanent suppressions while soft bounces need retry windows and escalation rules.',
        'Complaint disposition',
        'Spam complaints must permanently suppress recipients and trigger reputation review before future sends.',
        'Retry block',
        'Failed delivery records should check suppression, complaint, and bounce policy before any requeue action.',
        'Provider traceability',
        'Provider event IDs, SMTP log IDs, and operator decisions need to stay attached to each suppression.',
        'Audit evidence',
        'Compliance actions need immutable evidence for source, actor, timestamp, policy version, and downstream propagation.',
        'compliance-policy-panel',
        'compliance-policy-grid',
    ]

    for token in expected_tokens:
        assert token in source


def test_compliance_source_has_triage_panel() -> None:
    assert_compliance_triage_contract(frontend_source())


def test_built_esp_bundle_includes_compliance_triage_panel() -> None:
    bundle = frontend_bundle()
    expected_tokens = [
        'Compliance triage',
        'Review spam complaints',
        'Watch hard bounces',
        'Suppress failed recipients',
        'Respect opt-outs',
        'Compliance clear',
        'Complaint risk',
        'Bounce protection',
        'Opt-out coverage',
        'Failed candidates',
        'Deliverability Feedback Loop',
        'Provider feedback',
        'Bounce queue',
        'Complaint loop',
        'Retry safety',
        'Failed Recipient Review',
        'Draft Suppression',
        'Compliance Foundations',
        'Consent ledger',
        'Preference center',
        'Suppression propagation',
        'Audit trail',
        'Feedback Policy Contract',
        'Suppression scope',
        'Bounce disposition',
        'Complaint disposition',
        'Retry block',
        'Provider traceability',
        'Audit evidence',
        'Open Contacts',
    ]

    for token in expected_tokens:
        assert token in bundle
