from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from html.parser import HTMLParser


@dataclass
class HtmlNode:
    tag: str
    attrs: dict[str, str] = field(default_factory=dict)
    children: list[HtmlNode | str] = field(default_factory=list)
    self_closing: bool = False


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


def html_to_document(html: str) -> dict[str, object]:
    parser = _DesignHtmlParser()
    parser.feed(html)
    parser.close()
    blocks = _nodes_to_blocks(parser.root.children)
    return {'blocks': blocks or [{'type': 'html', 'code': html.strip()}]}


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
    if block_type == 'table':
        raw_headers = block.get('table_headers')
        headers = [str(item) for item in raw_headers] if isinstance(raw_headers, list) else []
        raw_rows = block.get('table_rows')
        rows = raw_rows if isinstance(raw_rows, list) and raw_rows else [['Label', 'Value']]
        normalized_rows = [
            [str(cell) for cell in row] if isinstance(row, list) else [str(row)]
            for row in rows
        ]
        column_count = max(
            [len(headers), *(len(row) for row in normalized_rows), 1]
        )
        padding_y = _bounded_int(block.get('padding_y'), default=10, minimum=0, maximum=48)
        padding_x = _bounded_int(block.get('padding_x'), default=12, minimum=0, maximum=64)
        bg = _escape_html(str(block.get('bg', '#f8fafc')))
        color = _escape_html(str(block.get('color', '#111827')))
        table_class_attr = class_attr or ' class="email-table"'
        cell_padding = f'{padding_y}px {padding_x}px'
        header_html = ''
        if headers:
            padded_headers = [*headers, *([''] * max(0, column_count - len(headers)))]
            header_html = (
                '<thead><tr>'
                + ''.join(
                    '<th style="border:1px solid #d8dee6;'
                    f'background:{bg};padding:{cell_padding};text-align:left;">'
                    f'{_escape_html(header)}</th>'
                    for header in padded_headers[:column_count]
                )
                + '</tr></thead>'
            )
        body_html = (
            '<tbody>'
            + ''.join(
                '<tr>'
                + ''.join(
                    '<td style="border:1px solid #d8dee6;'
                    f'padding:{cell_padding};vertical-align:top;">'
                    f'{_escape_html(str(row[index] if index < len(row) else ""))}</td>'
                    for index in range(column_count)
                )
                + '</tr>'
                for row in normalized_rows
            )
            + '</tbody>'
        )
        return (
            f'<table{table_class_attr} role="presentation" width="100%" cellspacing="0" '
            f'cellpadding="0" border="0" style="width:100%;border-collapse:collapse;'
            f'color:{color};">{header_html}{body_html}</table>'
        )
    if block_type == 'footer':
        footer_class_attr = class_attr or ' class="email-footer"'
        text = _escape_html(
            str(
                block.get(
                    'text',
                    'You are receiving this email because you subscribed to updates.',
                )
            )
        )
        href = _escape_html(str(block.get('href', '{{ unsubscribe_url }}')))
        align = _one_of(block.get('align'), {'left', 'center', 'right'}, 'center')
        styles = _style_attr(
            _text_styles(block, f'text-align:{align};font-size:12px;line-height:1.5;')
        )
        return f'<footer{footer_class_attr}{styles}>{text}<br><a href="{href}">Unsubscribe</a></footer>'
    if block_type == 'social_links':
        raw_links = block.get('social_links')
        links = raw_links if isinstance(raw_links, list) and raw_links else [
            {'label': 'LinkedIn', 'url': '{{ linkedin_url }}'},
            {'label': 'Instagram', 'url': '{{ instagram_url }}'},
        ]
        color = _escape_html(str(block.get('color', '#2563eb')))
        align = _one_of(block.get('align'), {'left', 'center', 'right'}, 'center')
        link_html = ' <span style="color:#cbd5e1;">|</span> '.join(
            f'<a href="{_escape_html(str(link.get("url", "#")))}" '
            f'style="color:{color};text-decoration:none;font-weight:700;">'
            f'{_escape_html(str(link.get("label", "Link")))}</a>'
            for link in links
            if isinstance(link, Mapping)
        )
        nav_class_attr = class_attr or ' class="email-social-links"'
        styles = _style_attr(
            _text_styles(block, f'text-align:{align};font-size:13px;line-height:1.5;')
        )
        return f'<nav{nav_class_attr}{styles}>{link_html}</nav>'
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


class _DesignHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.root = HtmlNode('root')
        self.stack: list[HtmlNode] = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = HtmlNode(tag.lower(), {key: value or '' for key, value in attrs})
        self.stack[-1].children.append(node)
        if node.tag not in {'br', 'hr', 'img', 'input', 'meta', 'link'}:
            self.stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = HtmlNode(
            tag.lower(),
            {key: value or '' for key, value in attrs},
            self_closing=True,
        )
        self.stack[-1].children.append(node)

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.lower()
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == normalized:
                del self.stack[index:]
                return

    def handle_data(self, data: str) -> None:
        if data:
            self.stack[-1].children.append(data)

    def handle_entityref(self, name: str) -> None:
        self.stack[-1].children.append(f'&{name};')

    def handle_charref(self, name: str) -> None:
        self.stack[-1].children.append(f'&#{name};')

    def handle_comment(self, data: str) -> None:
        self.stack[-1].children.append(f'<!--{data}-->')


def _nodes_to_blocks(nodes: list[HtmlNode | str]) -> list[dict[str, object]]:
    blocks: list[dict[str, object]] = []
    text_buffer: list[str] = []
    for node in nodes:
        if isinstance(node, str):
            if node.strip():
                text_buffer.append(node)
            continue
        if text_buffer:
            blocks.append({'type': 'paragraph', 'text': _collapse_text(''.join(text_buffer))})
            text_buffer = []
        block = _node_to_block(node)
        if block:
            blocks.append(block)
    if text_buffer:
        blocks.append({'type': 'paragraph', 'text': _collapse_text(''.join(text_buffer))})
    return blocks


def _node_to_block(node: HtmlNode) -> dict[str, object]:
    class_name = node.attrs.get('class', '')
    if node.tag == 'div' and 'email-document' in class_name.split():
        return {
            'type': 'section',
            'className': class_name,
            'children': _nodes_to_blocks(node.children),
        }
    if node.tag == 'div' and _is_section_like(node):
        block: dict[str, object] = {
            'type': 'section',
            'children': _nodes_to_blocks(node.children),
        }
        _copy_common_attrs(node, block)
        return block
    if node.tag in {'h1', 'h2', 'h3'}:
        block = {
            'type': 'heading',
            'level': int(node.tag[1]),
            'text': _collapse_text(_node_text(node)),
        }
        _copy_common_attrs(node, block)
        return block
    if node.tag == 'p':
        block = {'type': 'paragraph'}
        _copy_common_attrs(node, block)
        if _has_markup_children(node):
            block['html'] = _inner_html(node)
        else:
            block['text'] = _collapse_text(_node_text(node))
        return block
    if node.tag == 'a':
        return {
            'type': 'button',
            'text': _collapse_text(_node_text(node)) or 'Call to Action',
            'href': node.attrs.get('href', ''),
            'className': node.attrs.get('class', 'button'),
        }
    if node.tag == 'img':
        return {
            'type': 'image',
            'src': node.attrs.get('src', ''),
            'alt': node.attrs.get('alt', ''),
            'width': _bounded_int(node.attrs.get('width'), default=600, minimum=50, maximum=600),
            **({'className': node.attrs['class']} if node.attrs.get('class') else {}),
        }
    if node.tag in {'ul', 'ol'}:
        items = [
            _collapse_text(_node_text(child))
            for child in node.children
            if isinstance(child, HtmlNode) and child.tag == 'li'
        ]
        block = {
            'type': 'list',
            'ordered': node.tag == 'ol',
            'items': [item for item in items if item],
        }
        _copy_common_attrs(node, block)
        return block
    if node.tag == 'hr':
        block = {'type': 'divider'}
        _copy_common_attrs(node, block)
        return block
    if node.tag == 'table' and _is_columns_table(node):
        return _columns_table_to_block(node)
    if node.tag == 'table':
        return _table_to_block(node)
    if node.tag == 'footer':
        block = {
            'type': 'footer',
            'text': _collapse_text(_node_text_without_links(node))
            or 'You are receiving this email because you subscribed to updates.',
            'href': _first_link_href(node) or '{{ unsubscribe_url }}',
        }
        _copy_common_attrs(node, block)
        return block
    if node.tag == 'nav':
        links = [
            {
                'label': _collapse_text(_node_text(child)) or 'Link',
                'url': child.attrs.get('href', '#'),
            }
            for child in _child_elements(node, {'a'})
        ]
        block = {
            'type': 'social_links',
            'social_links': links or [
                {'label': 'LinkedIn', 'url': '{{ linkedin_url }}'},
                {'label': 'Instagram', 'url': '{{ instagram_url }}'},
            ],
        }
        _copy_common_attrs(node, block)
        return block
    return {'type': 'html', 'code': _outer_html(node)}


def _table_to_block(node: HtmlNode) -> dict[str, object]:
    rows = []
    header_row_indexes: set[int] = set()
    for row_index, row in enumerate(_child_elements(node, {'tr'})):
        cells = _child_elements(row, {'td', 'th'})
        if not cells:
            continue
        if any(cell.tag == 'th' for cell in cells):
            header_row_indexes.add(row_index)
        rows.append([_collapse_text(_node_text(cell)) for cell in cells])
    headers = rows[0] if rows and 0 in header_row_indexes else []
    body_rows = rows[1:] if headers else rows
    block: dict[str, object] = {
        'type': 'table',
        'table_headers': headers,
        'table_rows': body_rows,
    }
    _copy_common_attrs(node, block)
    return block


def _columns_table_to_block(node: HtmlNode) -> dict[str, object]:
    rows = _child_elements(node, {'tr'})
    if not rows:
        tbody = _child_elements(node, {'tbody'})
        rows = _child_elements(tbody[0], {'tr'}) if tbody else []
    cells = _child_elements(rows[0], {'td', 'th'}) if rows else []
    children = []
    for cell in cells:
        width = _bounded_int(
            cell.attrs.get('width', '').rstrip('%'), default=0, minimum=0, maximum=100
        )
        child: dict[str, object] = {'type': 'section', 'children': _nodes_to_blocks(cell.children)}
        if width:
            child['width'] = width
        children.append(child)
    block: dict[str, object] = {
        'type': 'columns',
        'children': children,
        'mobile_stack': node.attrs.get('data-mobile-stack', 'stack'),
    }
    _copy_common_attrs(node, block)
    return block


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


def _is_columns_table(node: HtmlNode) -> bool:
    class_name = node.attrs.get('class', '')
    return node.tag == 'table' and (
        'email-columns' in class_name.split()
        or node.attrs.get('data-mobile-stack') in {'stack', 'reverse', 'keep'}
    )


def _is_section_like(node: HtmlNode) -> bool:
    class_name = node.attrs.get('class', '')
    return 'email-section' in class_name.split() or 'email-column' in class_name.split()


def _copy_common_attrs(node: HtmlNode, block: dict[str, object]) -> None:
    class_name = node.attrs.get('class')
    if class_name:
        block['className'] = class_name


def _has_markup_children(node: HtmlNode) -> bool:
    return any(isinstance(child, HtmlNode) and child.tag != 'br' for child in node.children)


def _child_elements(node: HtmlNode, tags: set[str]) -> list[HtmlNode]:
    matches = [
        child for child in node.children if isinstance(child, HtmlNode) and child.tag in tags
    ]
    if matches:
        return matches
    nested: list[HtmlNode] = []
    for child in node.children:
        if isinstance(child, HtmlNode):
            nested.extend(_child_elements(child, tags))
    return nested


def _node_text(node: HtmlNode) -> str:
    parts: list[str] = []
    for child in node.children:
        if isinstance(child, str):
            parts.append(child)
        elif child.tag == 'br':
            parts.append('\n')
        else:
            parts.append(_node_text(child))
    return ''.join(parts)


def _node_text_without_links(node: HtmlNode) -> str:
    parts: list[str] = []
    for child in node.children:
        if isinstance(child, str):
            parts.append(child)
        elif child.tag == 'a':
            continue
        elif child.tag == 'br':
            parts.append('\n')
        else:
            parts.append(_node_text_without_links(child))
    return ''.join(parts)


def _first_link_href(node: HtmlNode) -> str:
    for child in node.children:
        if isinstance(child, HtmlNode):
            if child.tag == 'a' and child.attrs.get('href'):
                return child.attrs['href']
            href = _first_link_href(child)
            if href:
                return href
    return ''


def _collapse_text(value: str) -> str:
    return ' '.join(value.split())


def _inner_html(node: HtmlNode) -> str:
    return ''.join(_serialize_child(child) for child in node.children)


def _outer_html(node: HtmlNode) -> str:
    attrs = ''.join(
        f' {name}="{_escape_html(value)}"' if value else f' {name}'
        for name, value in node.attrs.items()
    )
    if node.self_closing or node.tag in {'br', 'hr', 'img', 'input', 'meta', 'link'}:
        return f'<{node.tag}{attrs} />'
    return f'<{node.tag}{attrs}>{_inner_html(node)}</{node.tag}>'


def _serialize_child(child: HtmlNode | str) -> str:
    if isinstance(child, str):
        return child
    return _outer_html(child)


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
