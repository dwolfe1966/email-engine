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
    class_attr = _class_attr(block.get('className', block.get('class')))
    if block_type == 'spokeo_logo':
        return (
            '<p style="text-align:center;">'
            '<a href="https://www.spokeo.com">'
            '<img '
            'src="https://image.mail4.spokeo.com/lib/fe3f15707564057c7d1475/m/1/'
            '3439b1f0-c8a5-43f6-8c07-d53e218d7070.png" '
            'alt="Spokeo Logo" width="150" '
            'style="display:inline-block;border:0;height:auto;max-width:150px;" />'
            '</a></p>'
        )
    if block_type in {'html', 'raw'}:
        return str(block.get('code', block.get('html', block.get('content', ''))))
    if block_type == 'section':
        styles = _style_attr(
            {
                'background': block.get('bg'),
                'padding': _px(block.get('padding_y')),
            }
        )
        children = _children_to_html(block)
        return f'<div{class_attr}{styles}>\n{_indent(children)}\n</div>'
    if block_type == 'columns':
        return _columns_to_html(block, class_attr)
    if block_type == 'heading' or block_type in {'h1', 'h2', 'h3'}:
        level = _bounded_int(block.get('level'), default=1, minimum=1, maximum=3)
        if block_type in {'h1', 'h2', 'h3'}:
            level = int(block_type[1])
        align = _one_of(block.get('align'), {'left', 'center', 'right'}, 'left')
        text = _escape_html(str(block.get('text', block.get('content', ''))))
        styles = _style_attr(_text_styles(block, f'text-align:{align};'))
        return f'<h{level}{class_attr}{styles}>{text}</h{level}>'
    if block_type == 'paragraph':
        html = _optional_str(block.get('html'))
        if html:
            return f'<p{class_attr}>{html}</p>'
        text = _escape_html(str(block.get('text', block.get('content', ''))))
        align = _one_of(block.get('align'), {'left', 'center', 'right'}, 'left')
        styles = _style_attr(_text_styles(block, f'text-align:{align};'))
        return f'<p{class_attr}{styles}>{text.replace(chr(10), "<br>")}</p>'
    if block_type == 'image':
        src = _escape_html(str(block.get('src', '')))
        alt = _escape_html(str(block.get('alt', '')))
        width = _bounded_int(block.get('width'), default=600, minimum=50, maximum=600)
        img = (
            f'<img{class_attr} src="{src}" alt="{alt}" width="{width}" '
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
        link_class_attr = class_attr or ' class="button"'
        return (
            f'<p class="email-action"><a{link_class_attr} href="{href}" '
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
        styles = _style_attr(_text_styles(block))
        return f'<{tag}{class_attr}{styles}>\n{rendered_items}\n</{tag}>'
    if block_type == 'divider':
        color = _escape_html(str(block.get('color', '#d8dee6')))
        return f'<hr{class_attr} style="border:0;border-top:1px solid {color};" />'
    if block_type == 'spacer':
        height = _bounded_int(block.get('height'), default=24, minimum=4, maximum=200)
        return (
            f'<div{class_attr} style="height:{height}px;line-height:{height}px;'
            'font-size:0;">&nbsp;</div>'
        )
    if block_type == 'trust_signal':
        text = _escape_html(str(block.get('text', '')))
        trust_class_attr = class_attr or ' class="secondary-text"'
        return f'<p{trust_class_attr} style="text-align:center;">{text}</p>'
    if block_type == 'conditional':
        variable = str(block.get('variable', block.get('condition', 'condition'))).strip()
        operator = str(block.get('operator', '')).strip()
        value = block.get('value')
        expression = variable
        if operator and value is not None:
            expression = f'{variable} {operator} {_jinja_literal(value)}'
        truthy = _children_to_html(block)
        fallback = block.get('else_children')
        fallback_html = ''
        if isinstance(fallback, list) and fallback:
            fallback_html = '\n{% else %}\n' + _blocks_to_html(fallback)
        return f'{{% if {expression} %}}\n{truthy}{fallback_html}\n{{% endif %}}'
    if block_type == 'loop':
        item_name = str(block.get('item_name', 'item')).strip() or 'item'
        collection = str(block.get('collection', 'items')).strip() or 'items'
        children = _children_to_html(block)
        fallback = block.get('else_children')
        fallback_html = ''
        if isinstance(fallback, list) and fallback:
            fallback_html = '\n{% else %}\n' + _blocks_to_html(fallback)
        return f'{{% for {item_name} in {collection} %}}\n{children}{fallback_html}\n{{% endfor %}}'
    if block_type == 'fcra_disclosure':
        return (
            '<p class="secondary-text" style="font-size:11px;line-height:14px;">'
            'Required disclosure content.</p>'
        )
    return f'<!-- unknown block type: {_escape_html(block_type)} -->'


def _columns_to_html(block: Mapping[str, object], class_attr: str) -> str:
    children = block.get('children')
    columns = children if isinstance(children, list) and children else [{}, {}]
    gap = _bounded_int(block.get('gap'), default=16, minimum=0, maximum=64)
    padding = _bounded_int(block.get('padding_y'), default=0, minimum=0, maximum=120)
    bg = _optional_str(block.get('bg'))
    mobile_stack = _one_of(block.get('mobile_stack'), {'stack', 'reverse', 'keep'}, 'stack')
    if not class_attr:
        mobile_class = {
            'stack': 'stack-mobile',
            'reverse': 'stack-mobile-reverse',
            'keep': 'keep-mobile',
        }[mobile_stack]
        class_attr = f' class="email-columns {mobile_class}"'
    table_style = 'width:100%;border-collapse:collapse;'
    if bg:
        table_style += f'background:{_escape_html(bg)};'
    explicit_total = sum(
        max(0, _bounded_int(column.get('width'), default=0, minimum=0, maximum=100))
        for column in columns
        if isinstance(column, Mapping)
    )
    default_width = max(1, int(100 / max(len(columns), 1)))
    cells: list[str] = []
    for column in columns:
        if not isinstance(column, Mapping):
            continue
        raw_width = _bounded_int(column.get('width'), default=0, minimum=0, maximum=100)
        width = (
            max(1, round((raw_width or default_width) / max(explicit_total, 1) * 100))
            if explicit_total
            else default_width
        )
        child_html = document_block_to_html(column)
        cells.append(
            f'<td width="{width}%" valign="top" '
            f'style="width:{width}%;vertical-align:top;padding:{gap // 2}px;">\n'
            f'{_indent(child_html, 6)}\n'
            '</td>'
        )
    table = (
        f'<table{class_attr} data-mobile-stack="{mobile_stack}" role="presentation" '
        f'width="100%" cellspacing="0" cellpadding="0" border="0" style="{table_style}">\n'
        '  <tr>\n'
        f'{_indent(chr(10).join(cells), 4)}\n'
        '  </tr>\n'
        '</table>'
    )
    if not padding:
        return table
    return f'<div style="padding:{padding}px;">\n{_indent(table)}\n</div>'


def _children_to_html(block: Mapping[str, object]) -> str:
    children = block.get('children')
    if not isinstance(children, list):
        return ''
    return _blocks_to_html(children)


def _blocks_to_html(blocks: list[object]) -> str:
    return '\n'.join(
        document_block_to_html(block) for block in blocks if isinstance(block, Mapping)
    )


def _class_attr(value: object) -> str:
    parsed = _optional_str(value)
    return f' class="{_escape_html(parsed)}"' if parsed else ''


def _style_attr(styles: Mapping[str, object] | list[str]) -> str:
    if isinstance(styles, list):
        style = ''.join(styles)
    else:
        style = ''.join(
            f'{name}:{_escape_html(str(value))};'
            for name, value in styles.items()
            if value not in (None, '')
        )
    return f' style="{style}"' if style else ''


def _text_styles(block: Mapping[str, object], base: str = '') -> list[str]:
    styles = [base] if base else []
    color = _optional_str(block.get('color'))
    bg = _optional_str(block.get('bg'))
    padding_y = block.get('padding_y')
    padding_x = block.get('padding_x')
    if color:
        styles.append(f'color:{_escape_html(color)};')
    if bg:
        styles.append(f'background:{_escape_html(bg)};')
    if padding_y is not None or padding_x is not None:
        y = _bounded_int(padding_y, default=0, minimum=0, maximum=120)
        x = _bounded_int(padding_x, default=0, minimum=0, maximum=120)
        styles.append(f'padding:{y}px {x}px;')
    return styles


def _px(value: object) -> str | None:
    if value in (None, ''):
        return None
    return f'{_bounded_int(value, default=0, minimum=0, maximum=120)}px'


def _indent(value: str, spaces: int = 2) -> str:
    prefix = ' ' * spaces
    return '\n'.join(f'{prefix}{line}' if line else line for line in value.split('\n'))


def _jinja_literal(value: object) -> str:
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, int | float):
        return str(value)
    return f'"{str(value).replace(chr(34), chr(92) + chr(34))}"'


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
