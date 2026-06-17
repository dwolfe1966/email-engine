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


def assert_data_triage_contract(source: str) -> None:
    expected_tokens = [
        'dataTriageAction',
        'dataTriageItems',
        "title: 'Create data source'",
        "title: 'Activate source'",
        "title: 'Validate source'",
        "title: 'Fix validation errors'",
        "title: 'Discover schema'",
        "title: 'Save contact mapping'",
        "title: 'Review import results'",
        "title: 'Open imported contacts'",
        "title: 'Run import dry run'",
        'Data triage',
        'Source readiness',
        'Mapping coverage',
        'Validation state',
        'Import health',
        'importReviewJobs',
        'function focusImportJob',
        'Import Job Review',
        'Review failed, skipped, or error-bearing import jobs before rerunning ingest.',
        'Dry Run Selected',
        'Review Job',
        'data-import-review-panel',
        'schemaFieldNames',
        'mappingPreview',
        'dataConfigPreview',
        'relationshipSourceType',
        'relationshipJoinFields',
        'relationshipPlanStatus',
        'relationshipPlannerItems',
        'Relationship Planner',
        'Relational schema ready',
        'Discover relational schema',
        'Plan API entity graph',
        'Single-entity import',
        'Connector class',
        'Join keys',
        'Entity targets',
        'Client entities',
        'Client-owned entities still need canonical storage and relationship APIs',
        'function applySchemaMappingSuggestion',
        'Schema Mapping Helper',
        'Suggest Mapping',
        'Direct contact fields',
        'Attribute fields',
        'Unmapped schema fields',
        'data-mapping-helper-panel',
        'data-relationship-planner',
        'data-relationship-grid',
        'dataFoundationItems',
        'Data Foundations',
        'Connector credentials, sync cadence, canonical entities, and lineage readiness.',
        'Connector credentials',
        'External connectors need managed secrets, rotation policy, and credential health checks.',
        'Sync cadence',
        'Scheduled sync, incremental cursors, and backfill controls remain foundation work.',
        'Canonical entities',
        'Client-specific entities need canonical storage before multi-entity segmentation.',
        'Lineage and replay',
        'Row lineage, replay, and rollback controls are needed before production data sync.',
        'dataSyncContractItems',
        'Connector Sync Contract',
        'Required contracts before RDBMS, warehouse, NoSQL, API, and client-entity sync can be production-grade.',
        'Credential contract',
        'Every production connector needs secret references, rotation metadata, and validation status exposed in the UI.',
        'Schema contract',
        'Connectors should publish discovered fields, object types, join candidates, and sample rows before mapping.',
        'Sync contract',
        'Production sync needs schedule policy, incremental cursor state, retry rules, and backfill windows.',
        'Relationship contract',
        'Multi-entity joins need canonical IDs, relationship cardinality, and client-owned entity storage.',
        'Audit contract',
        'Ingest records need row provenance, replay controls, rollback markers, and operator-visible failure reasons.',
        'data-foundation-panel',
        'data-foundation-grid',
        'data-sync-contract-panel',
        'data-sync-contract-grid',
        'data-triage-panel',
        'data-triage-list',
        'data-triage-row',
    ]

    for token in expected_tokens:
        assert token in source


def test_data_source_has_triage_panel() -> None:
    assert_data_triage_contract(frontend_source())


def test_built_esp_bundle_includes_data_triage_panel() -> None:
    bundle = frontend_bundle()
    expected_tokens = [
        'Data triage',
        'Create data source',
        'Validate source',
        'Discover schema',
        'Save contact mapping',
        'Review import results',
        'Open imported contacts',
        'Run import dry run',
        'Source readiness',
        'Validation state',
        'Import health',
        'Import Job Review',
        'Dry Run Selected',
        'Review Job',
        'Schema Mapping Helper',
        'Suggest Mapping',
        'Direct contact fields',
        'Attribute fields',
        'Relationship Planner',
        'Relational schema ready',
        'Discover relational schema',
        'Plan API entity graph',
        'Single-entity import',
        'Connector class',
        'Join keys',
        'Entity targets',
        'Client entities',
        'Data Foundations',
        'Connector credentials',
        'Sync cadence',
        'Canonical entities',
        'Lineage and replay',
        'Connector Sync Contract',
        'Credential contract',
        'Schema contract',
        'Sync contract',
        'Relationship contract',
        'Audit contract',
        'Discover Schema',
    ]

    for token in expected_tokens:
        assert token in bundle
