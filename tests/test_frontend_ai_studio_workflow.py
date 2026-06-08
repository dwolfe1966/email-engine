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


def assert_ai_studio_triage_contract(source: str) -> None:
    expected_tokens = [
        'aiStudioTriageAction',
        'aiStudioTriageItems',
        "title: 'Configure AI provider'",
        "title: 'Write agent brief'",
        "title: 'Run workflow review'",
        "title: 'Load template recommendations'",
        "title: 'Render AI preview'",
        "title: 'AI Studio ready'",
        'AI Studio triage',
        'Provider',
        'Agent brief',
        'Workflow review',
        'Template review',
        'Preview',
        'workflowCoverageAreas',
        'aiAgentLayerItems',
        'Ever-Present Agent Layer',
        'Cross-workflow orchestration, memory, handoff, and coverage.',
        'Orchestration',
        'Context memory',
        'Persistent agent memory, decisions, and follow-up state need canonical storage.',
        'Human handoff',
        'Workflow coverage',
        'Agents should remain present across templates, campaigns, audiences, delivery, analytics, and journeys.',
        'Use AI Studio as the cross-workflow agent layer across analytics, campaigns, audiences, delivery, and journeys.',
        'ai-agent-layer-panel',
        'ai-agent-layer-grid',
        'aiAgentFoundationItems',
        'AI Agent Foundations',
        'Model routing, tool permissions, run memory, and evaluation audit readiness.',
        'Model routing',
        'Production agents need explicit model routing beyond deterministic fallback.',
        'Tool permissions',
        'Agent tool calls need scoped permissions, approval rules, and workspace-level policy controls.',
        'Run memory',
        'Long-running agents need durable task memory, decision state, and resumable follow-up queues.',
        'Evaluation audit',
        'Agent outputs need evaluation scores, audit trails, and regression review before automation.',
        'ai-agent-foundation-panel',
        'ai-agent-foundation-grid',
        'ai-studio-triage-panel',
        'ai-studio-triage-grid',
    ]

    for token in expected_tokens:
        assert token in source


def test_ai_studio_source_has_triage_panel() -> None:
    assert_ai_studio_triage_contract(frontend_source())


def test_built_esp_bundle_includes_ai_studio_triage_panel() -> None:
    bundle = frontend_bundle()
    expected_tokens = [
        'AI Studio triage',
        'Configure AI provider',
        'Write agent brief',
        'Run workflow review',
        'Load template recommendations',
        'Render AI preview',
        'AI Studio ready',
        'Agent brief',
        'Workflow review',
        'Template review',
        'Ever-Present Agent Layer',
        'Orchestration',
        'Context memory',
        'Human handoff',
        'Workflow coverage',
        'AI Agent Foundations',
        'Model routing',
        'Tool permissions',
        'Run memory',
        'Evaluation audit',
        'Open Settings',
        'Review Workflow',
        'Save as Template',
    ]

    for token in expected_tokens:
        assert token in bundle
