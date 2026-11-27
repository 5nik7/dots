"""Merge a rendered Windows Terminal scheme into a user's JSONC document."""
import json
import re

from fonts.config import json_tree


def rendered_scheme(text):
    fragment = json.loads(text)
    schemes = fragment.get('schemes') if isinstance(fragment, dict) else None
    if isinstance(schemes, list):
        matches = [s for s in schemes if isinstance(s, dict) and isinstance(s.get('name'), str)
                   and s['name'].casefold() == 'dots']
        if len(matches) == 1:
            return matches[0]
    raise ValueError('windows-terminal.json must contain one scheme named Dots')


def _indent_unit(text, parent, indent):
    children = parent.children
    if isinstance(children, dict):
        children = [node for nodes in children.values() for node in nodes]
    for node in children:
        start = text.rfind('\n', 0, node.start) + 1
        if start > parent.start:
            child_indent = re.match(r'[ \t]*', text[start:node.start])[0]
            if child_indent.startswith(indent) and len(child_indent) > len(indent):
                return child_indent[len(indent):]
    indents = re.findall(r'(?m)^([ \t]+)(?=["{\[])', text)
    return min(indents, key=len, default='    ')


def _append(text, parent, entries):
    """Append JSON entries before the closing delimiter, retaining trailing trivia."""
    children = parent.children
    if isinstance(children, dict):
        children = [node for nodes in children.values() for node in nodes]
    close = parent.end - 1
    last = max((node.end for node in children), default=parent.start + 1)
    tail = re.sub(r'//[^\r\n]*|/\*[\s\S]*?\*/', '', text[last:close])
    trailing_comma = ',' in tail
    comma = ',' if children and not trailing_comma else ''
    newline = '\r\n' if '\r\n' in text else '\n'
    line = text[text.rfind('\n', 0, parent.start) + 1:parent.start]
    indent = re.match(r'[ \t]*', line)[0]
    close_line = text[text.rfind('\n', 0, close) + 1:close]
    insert = close
    if not close_line.strip():
        indent = close_line
        insert -= len(indent)
    unit = _indent_unit(text, parent, indent)
    lines = []
    for line in entries.splitlines():
        stripped = line.lstrip(' ')
        depth = (len(line) - len(stripped)) // 4
        lines.append(indent + unit * (depth + 1) + stripped)
    formatted = newline.join(lines)
    if close_line.strip():
        formatted = newline + formatted
    suffix = (',' if trailing_comma else '') + newline
    if insert == close:
        suffix += indent
    return text[:last] + comma + text[last:insert] + formatted + suffix + text[insert:]


def upsert_scheme(text: str, scheme: dict) -> str:
    """Insert the named scheme or update its palette while keeping its name spelling."""
    return _upsert(text, 'schemes', scheme)


def upsert_terminal_theme(text: str, theme: dict) -> str:
    """Merge the named UI theme and select it in the same settings document."""
    if not isinstance(theme, dict) or not isinstance(theme.get('name'), str) or theme['name'].casefold() != 'dots':
        raise ValueError('expected a Windows Terminal UI theme named dots')
    return _upsert(text, 'themes', dict(theme, name='dots'))


def _upsert(text, collection, definition):
    name = definition.get('name') if isinstance(definition, dict) else None
    if not isinstance(name, str) or not name:
        raise ValueError('Windows Terminal ' + collection + ' entry must have a name')
    bom = '\ufeff' if text.startswith('\ufeff') else ''
    original = text[len(bom):]
    updated, name = _merge_named(original, collection, definition)
    if collection == 'themes':
        root = json_tree(updated)
        updated = _merge_fields(updated, root, {'theme': name})
    if updated != original:
        json_tree(updated)
    return bom + updated


def _merge_named(text, collection, definition):
    root = json_tree(text)
    if not isinstance(root.children, dict):
        raise ValueError('Windows Terminal settings must be an object')
    arrays = root.children.get(collection, [])
    if len(arrays) > 1:
        raise ValueError('ambiguous repeated Windows Terminal ' + collection + ' property')
    name = definition['name']
    if not arrays:
        return _merge_fields(text, root, {collection: [definition]}), name
    array = arrays[0]
    if not isinstance(array.children, list):
        raise ValueError('Windows Terminal ' + collection + ' must be an array')
    matches = []
    for entry in array.children:
        names = entry.children.get('name', []) if isinstance(entry.children, dict) else []
        if any(isinstance(n.value, str) and n.value.casefold() == name.casefold() for n in names):
            if len(names) != 1:
                raise ValueError('ambiguous repeated name in Windows Terminal ' + collection)
            matches.append(entry)
    if len(matches) > 1:
        raise ValueError('multiple matching Windows Terminal ' + collection)
    if not matches:
        return _append(text, array, json.dumps(definition, indent=4)), name
    entry = matches[0]
    if collection == 'schemes':
        fields = {key: value for key, value in definition.items() if key != 'name'}
        return _merge_fields(text, entry, fields), entry.value['name']
    return _merge_fields(text, entry, definition), name


def _merge_fields(text, entry, updates):
    edits = []
    missing = []
    for key, value in updates.items():
        fields = entry.children.get(key, [])
        if len(fields) > 1:
            raise ValueError('ambiguous repeated Windows Terminal field: ' + key)
        if not fields:
            missing.append(json.dumps(key) + ': ' + json.dumps(value, indent=4))
        else:
            old = fields[0].value
            # Terminal normalizes saved hex colors to uppercase.
            if (isinstance(old, str) and isinstance(value, str)
                    and re.fullmatch(r'#[0-9A-Fa-f]{6}', value) and old.lower() == value.lower()):
                continue
            edits.append((fields[0], value))
    if missing:
        text = _append(text, entry, ',\n'.join(missing))
    # Walk backward so each node's offsets remain valid after later sibling edits.
    for node, value in sorted(edits, key=lambda pair: pair[0].start, reverse=True):
        if isinstance(value, dict) and isinstance(node.children, dict):
            text = _merge_fields(text, node, value)
        elif type(node.value) is not type(value) or node.value != value:
            replacement = json.dumps(value)
            if isinstance(value, (dict, list)):
                indent = re.match(r'[ \t]*', text[text.rfind('\n', 0, node.start) + 1:node.start])[0]
                parent_indent = re.match(r'[ \t]*', text[text.rfind('\n', 0, entry.start) + 1:entry.start])[0]
                unit = _indent_unit(text, entry, parent_indent)
                newline = '\r\n' if '\r\n' in text else '\n'
                replacement = json.dumps(value, indent=unit).replace('\n', newline + indent)
            text = text[:node.start] + replacement + text[node.end:]
    return text
