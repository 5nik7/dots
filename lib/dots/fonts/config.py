"""Inert, bounded font-setting edits preserving surrounding configuration text."""
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat

from fonts.model import read, read_text
from transactions import digest, parents_safe, exists

TARGETS = {'termux': ('termux', 'font.ttf'), 'kitty': ('kitty', 'kitty.conf'),
           'wezterm': ('wezterm', 'wezterm.lua'), 'windows-terminal': ('wt', 'settings.json'),
           'vscode-editor': ('vscode', 'settings.json'), 'vscode-terminal': ('vscode', 'settings.json')}


@dataclass
class Node:
    start: int
    end: int
    value: object
    children: object = None


def json_tree(text):
    """Parse JSONC with offsets; duplicate unrelated keys remain untouched."""
    masked = re.sub(r'"(?:\\.|[^"\\])*"|//[^\r\n]*|/\*[\s\S]*?\*/',
        lambda m: m[0] if m[0].startswith('"') else re.sub(r'[^\r\n]', ' ', m[0]), text)
    decoder = json.JSONDecoder()
    def skip(i):
        while i < len(masked) and masked[i].isspace(): i += 1
        return i
    def parse(i, depth=0):
        if depth > 64: raise ValueError('configuration nesting is too deep')
        i = start = skip(i)
        if i >= len(masked): raise ValueError('incomplete JSON configuration')
        if masked[i] not in '[{':
            value, end = decoder.raw_decode(masked, i)
            return Node(start, end, value), end
        object_ = masked[i] == '{'; close = '}' if object_ else ']'
        children = {} if object_ else []; values = {} if object_ else []
        i = skip(i + 1)
        while i < len(masked) and masked[i] != close:
            if object_:
                key, i = decoder.raw_decode(masked, i)
                if not isinstance(key, str): raise ValueError('invalid JSON object key')
                i = skip(i)
                if masked[i:i+1] != ':': raise ValueError('invalid JSON object')
                i += 1
            node, i = parse(i, depth + 1)
            if object_:
                children.setdefault(key, []).append(node); values[key] = node.value
            else: children.append(node); values.append(node.value)
            i = skip(i)
            if masked[i:i+1] == ',': i = skip(i + 1)
            elif masked[i:i+1] != close: raise ValueError('invalid JSON separator')
        if i >= len(masked): raise ValueError('incomplete JSON object')
        return Node(start, i + 1, values, children), i + 1
    try:
        node, end = parse(0)
        if skip(end) != len(masked): raise ValueError('trailing JSON content')
        return node
    except (IndexError, json.JSONDecodeError): raise ValueError('invalid JSON configuration') from None


def child(node, key):
    rows = node.children.get(key, []) if isinstance(node.children, dict) else []
    if len(rows) > 1: raise ValueError('ambiguous repeated font setting: ' + key)
    return rows[0] if rows else None


def replace_json(text, path, transform):
    root = json_tree(text)
    node = root
    for index, key in enumerate(path):
        found = child(node, key)
        if found is None:
            value = transform(None)
            for suffix in reversed(path[index+1:]): value = {suffix: value}
            if not isinstance(node.children, dict): raise ValueError('font setting parent must be an object')
            # Insert before its close; preserve comments and an existing trailing comma.
            masked_body = re.sub(r'//[^\r\n]*|/\*[\s\S]*?\*/', '', text[node.start+1:node.end-1]).rstrip()
            prefix = ',' if node.children and not masked_body.endswith(',') else ''
            newline = '\r\n' if '\r\n' in text else '\n'
            added = prefix + newline + '  ' + json.dumps(key) + ': ' + json.dumps(value, ensure_ascii=False) + newline
            output = text[:node.end-1] + added + text[node.end-1:]
            json_tree(output)
            return output
        node = found
    return text[:node.start] + json.dumps(transform(node.value), ensure_ascii=False) + text[node.end:]


def family_list(value, family):
    if value is None: return family
    if not isinstance(value, str): raise ValueError('font family setting must be a string')
    # Preserve CSS-style fallback names, including quoted commas.
    match = re.match(r'''\s*(?:"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|[^,]*)(.*)\Z''', value, re.S)
    if not match: raise ValueError('ambiguous font family list')
    primary = "'" + family.replace('\\', '\\\\').replace("'", "\\'") + "'" if ',' in family else family
    return primary + match[1]


def edit(text, target, family, app_profile=None):
    if len(text.encode()) > 4 * 1024 * 1024: raise ValueError('application configuration is too large')
    if target.startswith('vscode-'):
        key = 'editor.fontFamily' if target == 'vscode-editor' else 'terminal.integrated.fontFamily'
        return replace_json(text, [key], lambda old: family_list(old, family))
    if target == 'windows-terminal':
        if app_profile:
            root = json_tree(text); profiles = child(root, 'profiles')
            listing = child(profiles, 'list') if profiles else None
            matches = [n for n in (listing.children if listing and isinstance(listing.children, list) else [])
                       if isinstance(n.value, dict) and n.value.get('guid') == app_profile]
            if len(matches) != 1: raise ValueError('select one exact Windows Terminal profile GUID')
            node = matches[0]
            return text[:node.start] + replace_json(text[node.start:node.end], ['font','face'], lambda old: family_list(old, family)) + text[node.end:]
        return replace_json(text, ['profiles','defaults','font','face'], lambda old: family_list(old, family))
    if target == 'kitty':
        matches = list(re.finditer(r'(?m)^([ \t]*font_family[ \t]+)([^\r\n]*)(\r?)$', text))
        if len(matches) != 1: raise ValueError('Kitty needs one literal font_family setting')
        match = matches[0]
        old = match[2]
        if re.search(r'\bfamily\s*=', old):
            new, count = re.subn(r'\bfamily\s*=\s*("(?:\\.|[^"\\])*"|\S+)', lambda m: 'family=' + json.dumps(family,ensure_ascii=False), old)
            if count != 1: raise ValueError('ambiguous Kitty font family')
        else:
            suffix = re.search(r'\s+#.*$', old)
            new = family + (suffix[0] if suffix else '')
        return text[:match.start(2)] + new + text[match.end(2):]
    if target == 'wezterm':
        # Find assignments outside comments and strings without executing Lua.
        literals = r'''(?:--)?\[(?P<equals>=*)\[[\s\S]*?\](?P=equals)\]|--[^\r\n]*|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*' '''.rstrip()
        masked = re.sub(literals,lambda m:re.sub(r'[^\r\n]',' ',m[0]),text)
        assignments = list(re.finditer(r'(?m)^[ \t]*config\.font[ \t]*=[ \t]*', masked))
        if len(assignments) != 1: raise ValueError('WezTerm needs one literal config.font assignment')
        start = assignments[0].end()
        tail = text[start:]
        literal = r'''("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')'''
        patterns = [r'wezterm\.font_with_fallback\s*\(\s*\{\s*\{\s*family\s*=\s*' + literal,
                    r'wezterm\.font_with_fallback\s*\(\s*\{\s*' + literal,
                    r'wezterm\.font\s*\(\s*(?:\{\s*family\s*=\s*)?' + literal]
        found = next((m for p in patterns if (m := re.match(p, tail))), None)
        if found is None: raise ValueError('computed WezTerm font expression requires manual configuration')
        if not re.match(r'\s*[,)}]',tail[found.end():]):
            raise ValueError('computed WezTerm font expression requires manual configuration')
        return text[:start+found.start(1)] + json.dumps(family, ensure_ascii=False) + text[start+found.end(1):]
    raise ValueError('unknown font target')


def text_digest(path, text):
    mode = stat.S_IMODE(Path(path).stat().st_mode)
    return hashlib.sha256(b'.\0' + str(mode).encode() + b'\0F' + text.encode('utf-8') + b'\0').hexdigest()


def destination(library, target, explicit=None):
    if target not in TARGETS: raise ValueError('unknown font target')
    if target == 'termux':
        if library.platform != 'termux': raise ValueError('Termux activation is available only on Termux')
        return dict(path=str(library.home / '.termux/font.ttf'), target=target, source='local')
    if target == 'windows-terminal' and library.platform != 'windows':
        raise ValueError('Windows Terminal settings require native Windows')
    if target == 'kitty' and library.platform == 'windows': raise ValueError('Kitty has no native Windows target')
    if explicit:
        path = Path(explicit).expanduser()
        if not path.is_absolute(): raise ValueError('--config requires an absolute file path')
        parents_safe(path)
        if path.is_symlink() or not path.is_file(): raise ValueError('explicit app configuration must be a regular file')
        return dict(path=str(path), target=target, source='explicit')
    from files.catalog import Catalog
    root = Path(os.environ.get('DOTS') or Path(__file__).resolve().parents[3]).resolve()
    catalog = Catalog(root, library.platform)
    app, filename = TARGETS[target]
    rows = [r for r in catalog.records() if r.get('app') == app and r['applicable'] and r.get('enabled', True)
            and r.get('target') and r['status'] != 'replaced']
    if len(rows) != 1: raise ValueError('app mapping is missing or ambiguous; provide --config explicitly')
    row = rows[0]
    if row['status'] in ('conflict', 'linked-elsewhere', 'source-missing', 'source-broken-link'):
        raise ValueError('app configuration ownership needs review: ' + row['status'])
    source, target_path = Path(row['source']), Path(row['target'])
    if not exists(target_path): raise ValueError('managed app destination is not installed; use dots files first')
    directory = source.is_dir()
    path = source / filename if directory else source
    active = target_path / filename if directory else target_path
    if not path.is_file() or path.is_symlink(): raise ValueError('managed app source is missing or not regular')
    parents_safe(path)
    linked = target_path.is_symlink() and target_path.resolve() == source.resolve()
    result = dict(path=str(path), active=str(active), target=target, source='managed',
                  linked=linked, catalog=catalog, resource=row['id'], destination=str(target_path))
    if exists(target_path) and not linked:
        if directory: raise ValueError('managed app directory is not linked; review dots files first')
        receipt_path = library.state / 'installation.json'
        receipt = read(receipt_path, dict(schema=1))
        owned = receipt.get('entries', {}).get(str(target_path))
        if (receipt.get('root') != str(root) or receipt.get('platform') != library.platform
                or not owned or owned.get('id') != row['id'] or owned.get('after') != digest(target_path)
                or target_path.is_symlink()):
            raise ValueError('app copy is unowned or changed; review dots files first')
        result.update(receipt=receipt, receipt_path=str(receipt_path))
    return result


def configure(plan, identity, version, font, target, *, explicit=None, app_profile=None):
    found = destination(plan.library, target, explicit)
    path = Path(found['path'])
    plan.guard(path)
    key = target + (':' + app_profile if app_profile else '')
    prior = plan.library.document['targets'].get(key)
    if prior and prior['path'] == str(path) and digest(path) != prior['after']:
        raise ValueError('active font configuration changed; review or undo it before setting again')
    if target == 'termux':
        source = plan.file(identity, version, font)
        if source.suffix.lower() != '.ttf': raise ValueError('Termux requires a TTF face')
        if path.is_symlink(): raise ValueError('Termux font is a symlink; review its ownership first')
        plan.put(path, source=source)
        after = digest(source)
        plan.refresh.add('termux')
    else:
        if found.get('catalog'):
            for input_path in found['catalog'].input_paths(): plan.guard(input_path)
            plan.guard(found['destination'])
        existing = next((op.get('text') for op in plan.operations if op['path'] == str(path)), None)
        old = existing if existing is not None else read_text(path)
        text = edit(old, target, font['family'], app_profile)
        plan.put(path, text=text)
        after = text_digest(path, text)
        # Both VS Code selectors can share a file; keep their receipts coherent.
        for selection in plan.document['targets'].values():
            if selection['path'] == str(path): selection['after'] = after
        if found.get('receipt'):
            active = Path(found['active'])
            plan.put(active, text=text)
            receipt_path = found['receipt_path']
            existing_receipt = next((op.get('data') for op in plan.operations if op['path'] == receipt_path), None)
            receipt = deepcopy(existing_receipt or found['receipt'])
            receipt['entries'][str(active)]['after'] = text_digest(active, text)
            plan.put(receipt_path, data=receipt)
    plan.document['targets'][key] = dict(id=identity, version=version, face=font['file'], family=font['family'],
        target=target, path=str(path), after=after, config=explicit, app_profile=app_profile)
    plan.items.append(dict(id=identity, version=version, target=key, path=str(path), action='set', face=font['file']))
