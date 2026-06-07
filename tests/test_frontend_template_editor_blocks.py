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


def assert_template_design_block_contract(source: str) -> None:
    expected_tokens = [
        "table_headers?: string[];",
        "table_rows?: string[][];",
        "social_links?: Array<{ label: string; url: string }>",
        '`${name}\\\\s*=\\\\s*["\']([^"\']*)["\']`',
        'function paddingPair',
        "if (type === 'table') return",
        "if (type === 'footer') return",
        "if (type === 'social_links') return",
        "if (/^<table\\b/i.test(markup))",
        "const headerStyle = htmlAttribute(markup.match(/<th\\b[^>]*>/i)?.[0] || '', 'style')",
        "const cellPadding = paddingPair(styleValue(cellStyle, 'padding'), 10, 12)",
        "bg: styleValue(style, 'background') || styleValue(headerStyle, 'background') || '#f8fafc'",
        "padding_y: cellPadding.y",
        "padding_x: cellPadding.x",
        "if (/^<footer\\b/i.test(markup))",
        "if (/^<nav\\b/i.test(markup))",
        "footerTextWithoutLinks",
        "markup.replace(/<a\\b[\\s\\S]*?<\\/a>/gi, '')",
        "markup.matchAll(/<a\\b[\\s\\S]*?>([\\s\\S]*?)<\\/a>/gi)",
        "url: htmlAttribute(link[0], 'href')",
        "return `<table${classAttr || ' class=\"email-table\"'}",
        "return `<footer${classAttr || ' class=\"email-footer\"'}",
        "return `<nav${classAttr || ' class=\"email-social-links\"'}",
        "normalizedSocialLinks",
        "parseSocialLinksText",
        "parseTableRowsText",
        ".email-table { width: 100%; border-collapse: collapse;",
        ".email-social-links { color:",
        ".email-footer { color: #64748b;",
        "Edit table in inspector",
        "Edit footer text or URL",
        "Edit social links in inspector",
        "templateRenderResult",
        "recordTemplateRenderResult",
        "Latest render",
        "Preview is current with sample variables.",
        "template-render-result",
        "sample-variable-health",
        "nativeSampleVariableCount",
        "jsonSampleVariableCount",
        "Sample variable health",
        "Preview-aware variables",
        "design-inspector-group",
        "inspectorGroup",
        "Content', 'Header cells and row data",
        "Style', 'Class, alignment, and colors",
        "Layout', 'Cell padding",
        "Structure', 'Nested block count and insertion controls",
        "designImportConfidence",
        "designBlockSummary",
        "raw HTML/Jinja block(s) preserved",
        "Fully editable",
    ]

    for token in expected_tokens:
        assert token in source


def test_react_template_editor_source_supports_table_footer_and_social_blocks() -> None:
    assert_template_design_block_contract(frontend_source())


def test_built_esp_bundle_includes_table_footer_and_social_blocks() -> None:
    bundle = frontend_bundle()
    expected_tokens = [
        'table_headers',
        'table_rows',
        'social_links',
        'email-table',
        'email-footer',
        'email-social-links',
        'LinkedIn',
        'Instagram',
        'Website',
        'Unsubscribe',
        'Edit table in inspector',
        'Edit footer text or URL',
        'Edit social links in inspector',
        'Latest render',
        'Preview is current with sample variables.',
        'CSS gaps',
        'Sample variable health',
        'Preview-aware variables',
        'Nested block count and insertion controls',
        'Header cells and row data',
        'raw HTML/Jinja block(s) preserved',
        'Fully editable',
    ]

    for token in expected_tokens:
        assert token in bundle
