from __future__ import annotations

from collections.abc import Mapping


def document_to_html(document: Mapping[str, object]) -> str:
    blocks = document.get('blocks')
    if not isinstance(blocks, list):
        return str(document.get('html', ''))
    html_parts: list[str] = ['<div class="email-document">']
    for block in blocks:
        if not isinstance(block, dict):
            continue
        html_parts.append(document_block_to_html(block))
    html_parts.append('</div>')
    return '\n'.join(html_parts)


def document_block_to_html(block: Mapping[str, object]) -> str:
    block_type = str(block.get('type', 'paragraph'))
    if block_type in {'html', 'raw'}:
        return str(block.get('code', block.get('html', block.get('content', ''))))
    if block_type == 'heading' or block_type in {'h1', 'h2', 'h3'}:
        level = _bounded_int(block.get('level'), default=1, minimum=1, maximum=3)
        if block_type in {'h1', 'h2', 'h3'}:
            level = int(block_type[1])
        align = _one_of(block.get('align'), {'left', 'center', 'right'}, 'left')
        text = _escape_html(str(block.get('text', block.get('content', ''))))
        return f'<h{level} style="text-align:{align};">{text}</h{level}>'
    if block_type == 'paragraph':
        html = _optional_str(block.get('html'))
        if html:
            return f'<p>{html}</p>'
        text = _escape_html(str(block.get('text', block.get('content', ''))))
        align = _one_of(block.get('align'), {'left', 'center', 'right'}, 'left')
        color = _escape_html(str(block.get('color', '')))
        styles = [f'text-align:{align};']
        if color:
            styles.append(f'color:{color};')
        return f'<p style="{"".join(styles)}">{text.replace(chr(10), "<br>")}</p>'
    if block_type == 'image':
        src = _escape_html(str(block.get('src', '')))
        alt = _escape_html(str(block.get('alt', '')))
        width = _bounded_int(block.get('width'), default=600, minimum=50, maximum=600)
        img = (
            f'<img src="{src}" alt="{alt}" width="{width}" '
            f'style="display:block;border:0;width:100%;max-width:{width}px;height:auto;" />'
        )
        href = _optional_str(block.get('href'))
        if href:
            return f'<a href="{_escape_html(href)}">{img}</a>'
        return img
    if block_type == 'button':
        text = _escape_html(str(block.get('text', 'Call to Action')))
        href = _escape_html(str(block.get('href', '{{ cta_url }}')))
        bg = _escape_html(str(block.get('bg', '#2563eb')))
        color = _escape_html(str(block.get('color', '#ffffff')))
        radius = _bounded_int(block.get('radius'), default=6, minimum=0, maximum=48)
        padding_y = _bounded_int(block.get('padding_y'), default=11, minimum=4, maximum=32)
        padding_x = _bounded_int(block.get('padding_x'), default=16, minimum=8, maximum=48)
        return (
            f'<p><a class="button" href="{href}" '
            f'style="display:inline-block;background:{bg};color:{color};'
            f'padding:{padding_y}px {padding_x}px;text-decoration:none;'
            f'border-radius:{radius}px;font-weight:700;">'
            f'{text}</a></p>'
        )
    if block_type == 'list':
        ordered = bool(block.get('ordered'))
        tag = 'ol' if ordered else 'ul'
        items = block.get('items')
        if not isinstance(items, list):
            items = []
        rendered_items = '\n'.join(
            f'<li>{_escape_html(str(item))}</li>' for item in items if str(item).strip()
        )
        return f'<{tag}>\n{rendered_items}\n</{tag}>'
    if block_type == 'divider':
        color = _escape_html(str(block.get('color', '#d8dee6')))
        return f'<hr style="border:0;border-top:1px solid {color};" />'
    if block_type == 'spacer':
        height = _bounded_int(block.get('height'), default=24, minimum=4, maximum=200)
        return f'<div style="height:{height}px;line-height:{height}px;font-size:0;">&nbsp;</div>'
    if block_type == 'trust_signal':
        text = _escape_html(str(block.get('text', '')))
        return f'<p class="secondary-text" style="text-align:center;">{text}</p>'
    if block_type == 'fcra_disclosure':
        return (
            '<p class="secondary-text" style="font-size:11px;line-height:14px;">'
            'Required disclosure content.</p>'
        )
    return f'<!-- unknown block type: {_escape_html(block_type)} -->'


def _bounded_int(value: object, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(str(value))
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(parsed, maximum))


def _one_of(value: object, allowed: set[str], default: str) -> str:
    parsed = str(value or '')
    return parsed if parsed in allowed else default


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    parsed = str(value)
    return parsed or None


def _escape_html(value: str) -> str:
    return (
        value.replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('"', '&quot;')
        .replace("'", '&#39;')
    )
