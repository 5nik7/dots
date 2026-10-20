"""Palette-only Starship/Blastoff adapter. No prompt or module commands are run."""
from contextlib import contextmanager
import copy
import json
import os
from pathlib import Path
import re
import stat
import tempfile
import tomllib

from transactions import Store, digest, parents_safe


def sections(text):
    """Find real TOML table boundaries, ignoring strings, comments and arrays."""
    found = []
    i, depth, line_start = 0, 0, True
    while i < len(text):
        char = text[i]
        if char == '\n':
            line_start = True
            i += 1
        elif line_start and char in ' \t\r\ufeff':
            i += 1
        elif char == '#':
            end = text.find('\n', i)
            i = len(text) if end < 0 else end
        elif char in "\"'":
            line_start = False
            size = 3 if text.startswith(char * 3, i) else 1
            i += size
            while i < len(text):
                if char == '"' and text[i] == '\\':
                    i += 2
                elif text.startswith(char * size, i):
                    i += size
                    if size == 3:
                        while i < len(text) and text[i] == char:
                            i += 1
                    break
                else:
                    i += 1
        elif line_start and char == '[' and depth == 0:
            end = text.find('\n', i)
            end = len(text) if end < 0 else end + 1
            header = tomllib.loads(text[i:end] + '\n__dots_marker__ = true\n')
            route, value = [], header
            while isinstance(value, (dict, list)):
                if isinstance(value, list):
                    value = value[0]
                elif '__dots_marker__' in value and value['__dots_marker__'] is True:
                    break
                else:
                    key, value = next(iter(value.items()))
                    route.append(key)
            found.append((text.rfind('\n', 0, i) + 1, end, tuple(route)))
            i, line_start = end, True
        else:
            line_start = False
            if char in '[{':
                depth += 1
            elif char in ']}':
                depth -= 1
            i += 1
    return [(start, end, found[n+1][0] if n+1 < len(found) else len(text), route)
            for n, (start, end, route) in enumerate(found)]


def update_palette(original, colors):
    text = original.decode('utf-8-sig')
    doc = tomllib.loads(text)
    if doc.get('palette') != 'dots':
        return original
    palettes = doc.get('palettes', {})
    if not isinstance(palettes, dict):
        raise ValueError('palettes must be a TOML table')
    old = palettes.get('dots', {})
    if not isinstance(old, dict) or any(not isinstance(v, str) for v in old.values()):
        raise ValueError('palettes.dots must contain only named color strings')
    desired = dict(old, **colors)
    if old == desired:
        return original
    spans = [(start, end, stop) for start, end, stop, route in sections(text)
             if route == ('palettes', 'dots')]
    if len(spans) > 1 or not spans and 'dots' in doc.get('palettes', {}):
        raise ValueError('palettes.dots requires one explicit TOML table')
    newline = '\r\n' if '\r\n' in text else '\n'
    body = ''.join(json.dumps(k) + ' = ' + json.dumps(v) + newline for k, v in desired.items())
    if spans:
        start, end, stop = spans[0]
        result = text[:end] + body + newline + text[stop:]
    else:
        result = text + ('' if text.endswith('\n') else newline) + newline + '[palettes.dots]' + newline + body
    expected = copy.deepcopy(doc)
    expected.setdefault('palettes', {})['dots'] = desired
    if tomllib.loads(result) != expected:
        raise ValueError('palette update would change unrelated Starship settings')
    return (b'\xef\xbb\xbf' if original.startswith(b'\xef\xbb\xbf') else b'') + result.encode('utf-8')


def resolve_path(value, guards):
    """Resolve configured links while guarding each link at its physical parent."""
    path = Path(value)
    if not path.is_absolute() or '..' in path.parts or any(ord(c) < 32 for c in str(path)):
        raise ValueError('app paths must be absolute without controls or parent traversal')
    pending = list(path.parts[1:])
    current, links = Path(path.anchor), 0
    while pending:
        current /= pending.pop(0)
        if current.is_symlink():
            links += 1
            if links > 40:
                raise ValueError('too many app path symlinks')
            before = digest(current)
            target = os.readlink(current)
            if digest(current) != before:
                raise ValueError('app path changed during resolution')
            guards[str(current)] = before
            target = Path(os.path.normpath(target if os.path.isabs(target) else current.parent / target))
            pending = list(target.parts[1:]) + pending
            current = Path(target.anchor)
    parents_safe(current)
    return current


def paths(guards):
    home = Path(os.environ.get('HOME') or Path.home())
    active = resolve_path(os.environ.get('STARSHIP_CONFIG') or home / '.config/starship.toml', guards)
    storage = resolve_path(os.environ.get('BLASTOFF_HOME') or home / '.config/blastoff', guards)
    saved = resolve_path(storage / 'themes/dots.toml', guards)
    return active, saved, storage


def prepare(config, state, generation):
    from plugin_apps import content
    source = generation / 'blastoff.toml'
    rendered = content(source)
    if rendered is None:
        raise ValueError('published Blastoff palette is missing; run dots theme refresh')
    palette = tomllib.loads(rendered.decode('utf-8'))
    palettes = palette.get('palettes', {})
    colors = palettes.get('dots') if isinstance(palettes, dict) else None
    if palette.get('palette') != 'dots' or not isinstance(colors, dict) or not colors:
        raise ValueError('invalid published Blastoff palette')
    if any(not isinstance(v, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}|reset', v) for v in colors.values()):
        raise ValueError('published Blastoff colors must be hex colors or reset')
    guards = {}
    active, saved, _ = paths(guards)
    changed = {}
    for path in dict.fromkeys((active, saved)):
        before = digest(path)
        original = content(path)
        if before != digest(path):
            raise ValueError('Starship configuration changed during inspection')
        guards[str(path)] = before
        if original is not None:
            updated = update_palette(original, colors)
            if updated != original:
                changed[path] = updated
    return changed, None, None, None, guards


@contextmanager
def blastoff_locks(active, storage):
    acquired = []
    locks = ([storage / '.operation.lock'] if storage.is_dir() else [])
    if active.parent.is_dir():
        locks.append(active.parent / ('.' + active.name + '.blastoff.lock'))
    try:
        for path in locks:
            parents_safe(path)
            try:
                path.mkdir(mode=0o700)
            except FileExistsError:
                raise ValueError('Blastoff operation or stale lock exists: ' + str(path)) from None
            acquired.append(path)
        yield
    finally:
        for path in reversed(acquired):
            path.rmdir()


def apply(config, state, generation):
    guards = {}
    active, _, storage = paths(guards)
    with blastoff_locks(active, storage):
        changed, _, _, _, observed = prepare(config, state, generation)
        # Retain the earlier link observations, binding the lock roots too.
        for path, value in guards.items():
            if observed.get(path) != value:
                raise ValueError('app path changed while acquiring locks')
        if not changed:
            return {'status': 'success', 'detail': 'unchanged (only palette = dots is updated)'}
        with tempfile.TemporaryDirectory(prefix='dots-starship-') as temporary:
            operations = []
            for i, (path, data) in enumerate(changed.items()):
                stage = Path(temporary) / str(i)
                stage.write_bytes(data)
                os.chmod(stage, stat.S_IMODE(path.stat().st_mode))
                observed[str(stage)] = digest(stage)
                operations.append({'path': str(path), 'source': str(stage)})
            result = Store(state).apply('theme-plugin-starship', operations, observed, retain=True)
        return {'status': 'success', 'detail': 'Dots palettes updated; visible at the next prompt',
                'transaction': result['id']}
