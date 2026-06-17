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


def assert_contacts_triage_contract(source: str) -> None:
    expected_tokens = [
        'contactsTriageAction',
        'contactsTriageItems',
        "title: 'Import contacts'",
        "title: 'Enrich contact attributes'",
        "title: 'Review opt-outs'",
        "title: 'Select contact'",
        "title: 'Inspect unsubscribe state'",
        "title: 'Use contact data'",
        'Contacts triage',
        'Contact base',
        'Attribute coverage',
        'Source diversity',
        'Compliance state',
        'currentAttributePreview',
        'activeAttributeKeys',
        'missingAttributeKeys',
        'contactEntityItems',
        'Canonical Entity Model',
        'Contacts, attributes, client-owned entities, and relationship readiness.',
        'Canonical contact',
        'Profile attributes',
        'Client entities',
        'Client-owned objects such as accounts, stores, orders, memberships, and contracts need canonical storage.',
        'Relationships',
        'Contact-to-entity links still need relationship APIs before multi-entity audiences and joins are first-class.',
        'contactFoundationItems',
        'Contact Foundations',
        'Identity resolution, consent state, enrichment freshness, and activation readiness.',
        'Identity resolution',
        'Contacts currently resolve around email; cross-source identity rules still need hardening.',
        'Consent state',
        'Visible opt-outs need durable consent history and suppression sync.',
        'Enrichment freshness',
        'Attribute enrichment is required before personalization and segmentation scale.',
        'Activation paths',
        'Contacts can feed audiences, templates, campaigns, and journey enrollment testing.',
        'contactRelationshipContractItems',
        'Contact Relationship Contract',
        'Entity registry, relationship API, join readiness, consent inheritance, activation, and audit requirements.',
        'Entity registry',
        'Client-owned entities need canonical definitions for accounts, stores, orders, memberships, contracts, and custom objects.',
        'Relationship API',
        'Contacts need typed links to client entities with cardinality, source system, confidence, and effective dates.',
        'Join readiness',
        'Contact attributes exist, but entity joins still need stable keys and relationship materialization.',
        'Consent inheritance',
        'Consent and suppression state must define whether opt-outs inherit across related entities and brands.',
        'Segment activation',
        'Audience rules need first-class filters for related entity attributes before multi-entity segmentation is production-ready.',
        'Entity audit',
        'Relationship changes need source lineage, replay, conflict resolution, and operator-visible audit history.',
        'function applyAttributeKey',
        'Attribute Helper',
        'Active attributes',
        'Missing known keys',
        'Template readiness',
        'contact-entity-model-panel',
        'contact-entity-model-grid',
        'contact-foundation-panel',
        'contact-foundation-strip',
        'contact-foundation-item',
        'contact-relationship-contract-panel',
        'contact-relationship-contract-grid',
        'contact-attribute-helper-panel',
        'contacts-triage-panel',
        'contacts-triage-list',
        'contacts-triage-row',
    ]

    for token in expected_tokens:
        assert token in source


def test_contacts_source_has_triage_panel() -> None:
    assert_contacts_triage_contract(frontend_source())


def test_built_esp_bundle_includes_contacts_triage_panel() -> None:
    bundle = frontend_bundle()
    expected_tokens = [
        'Contacts triage',
        'Import contacts',
        'Enrich contact attributes',
        'Review opt-outs',
        'Select contact',
        'Inspect unsubscribe state',
        'Use contact data',
        'Contact base',
        'Attribute coverage',
        'Compliance state',
        'Attribute Helper',
        'Active attributes',
        'Missing known keys',
        'Template readiness',
        'Canonical Entity Model',
        'Canonical contact',
        'Profile attributes',
        'Client entities',
        'Relationships',
        'Contact Foundations',
        'Identity resolution',
        'Consent state',
        'Enrichment freshness',
        'Activation paths',
        'Contact Relationship Contract',
        'Entity registry',
        'Relationship API',
        'Join readiness',
        'Consent inheritance',
        'Segment activation',
        'Entity audit',
        'Open Audiences',
        'Open Data Sources',
    ]

    for token in expected_tokens:
        assert token in bundle
