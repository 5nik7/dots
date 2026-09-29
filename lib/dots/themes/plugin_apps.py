"""Bounded GTK/Qt adapters; every installed byte and receipt uses the shared Store."""
import hashlib
import os
from pathlib import Path
import re
import stat
import tempfile

from catalog import read_json
from transactions import Store, digest, exists, parents_safe

GTK_BLOCK = '/* dots theme plugin: begin */\n@import url("dots-theme.css");\n/* dots theme plugin: end */\n'


def content(path):
    parents_safe(path)
    if not exists(path):
        return None
    if not stat.S_ISREG(path.lstat().st_mode) or path.stat().st_size > 4 * 1024 * 1024:
        raise ValueError(f'expected a bounded regular file (symlinks require manual review): {path}')
    return path.read_bytes()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def gtk_registration(original, previous):
    text = (original or b'').decode('utf-8')
    begin, end = '/* dots theme plugin: begin */', '/* dots theme plugin: end */'
    if begin in text or end in text:
        if (not previous or text.count(begin) != 1 or text.count(end) != 1
                or text.count(GTK_BLOCK) != 1):
            raise ValueError('GTK managed import changed or is ambiguous; restore it or undo the plugin transaction')
        return original
    if previous:
        raise ValueError('GTK managed import was removed; restore it or undo the plugin transaction')
    # Keep an optional CSS charset directive first. All user bytes remain intact.
    offset = 1 if text.startswith('\ufeff') else 0
    charset = re.match(r'^@charset\s+"[^"\n]+";[^\S\n]*\n?', text[offset:])
    offset += charset.end() if charset else 0
    return (text[:offset] + GTK_BLOCK + text[offset:]).encode('utf-8')


def qt_registration(original, previous, path):
    bom = b'\xef\xbb\xbf' if (original or b'').startswith(b'\xef\xbb\xbf') else b''
    text = (original or b'').decode('utf-8-sig')
    lines = text.splitlines(keepends=True)
    newline = '\r\n' if '\r\n' in text else '\n'
    sections = [i for i, line in enumerate(lines) if re.fullmatch(r'\s*\[Appearance\]\s*', line)]
    if len(sections) > 1:
        raise ValueError('ambiguous Qt6ct Appearance section')
    start = sections[0] + 1 if sections else len(lines)
    end = next((i for i in range(start, len(lines)) if re.match(r'\s*\[', lines[i])), len(lines))
    values = {'custom_palette': 'true', 'color_scheme_path': '"' + str(path).replace('\\', '\\\\').replace('"', '\\"') + '"'}
    indices = {}
    for key in values:
        found = [i for i in range(start, end) if re.match(r'\s*' + key + r'\s*=', lines[i])]
        if len(found) > 1:
            raise ValueError('ambiguous Qt6ct palette key: ' + key)
        indices[key] = found[0] if found else None
        if previous:
            current = lines[found[0]].split('=', 1)[1].strip() if found else None
            if current != previous.get(key):
                raise ValueError('Qt6ct managed selection changed; restore it or undo the plugin transaction')
    if not sections:
        if lines and not lines[-1].endswith('\n'):
            lines[-1] += newline
        lines.append('[Appearance]' + newline)
        end = len(lines)
    additions = []
    for key, value in values.items():
        line = key + '=' + value + newline
        if indices[key] is None:
            additions.append(line)
        else:
            lines[indices[key]] = line
    if additions and end and not lines[end - 1].endswith('\n'):
        lines[end - 1] += newline
    lines[end:end] = additions
    return bom + ''.join(lines).encode('utf-8'), values


def prepare(name, config, state, generation):
    receipt_path = state / 'theme-plugins' / (name + '.json')
    old_receipt_bytes = content(receipt_path)
    old = read_json(receipt_path) if old_receipt_bytes is not None else None
    if old and (old.get('plugin') != name or not isinstance(old.get('generated'), str)
                or not isinstance(old.get('registration'), dict)):
        raise ValueError('invalid plugin ownership receipt')
    if name == 'gtk':
        target = config / 'gtk-3.0/dots-theme.css'
        registration = config / 'gtk-3.0/gtk.css'
        source = generation / 'gtk.css'
    elif name == 'qt6ct':
        target = config / 'qt6ct/colors/dots.conf'
        registration = config / 'qt6ct/qt6ct.conf'
        source = generation / 'qt6ct.conf'
    else:
        raise ValueError('unknown bundled app')
    if not registration.parent.is_dir():
        raise ValueError('app configuration directory disappeared')
    rendered = content(source)
    if rendered is None:
        raise ValueError('published app template is missing; run dots theme refresh')
    # Guards bind precisely the bytes read to the transaction preview.
    guards = {}
    def observed(path):
        before = digest(path)
        data = content(path)
        if before != digest(path):
            raise ValueError('file changed during inspection: ' + str(path))
        guards[str(path)] = before
        return data
    current = observed(target)
    original = observed(registration)
    if observed(receipt_path) != old_receipt_bytes:
        raise ValueError('plugin receipt changed during inspection')
    if old:
        if current is None or sha(current) != old['generated']:
            raise ValueError('generated plugin file drift; restore it or undo the plugin transaction: ' + str(target))
    elif current is not None:
        raise ValueError('unowned generated-file collision: ' + str(target))
    if name == 'gtk':
        registered = gtk_registration(original, old)
        owned = {'block': GTK_BLOCK}
    else:
        registered, owned = qt_registration(original, old['registration'] if old else None, target)
    receipt = {'schema': 1, 'plugin': name, 'generated': sha(rendered), 'registration': owned}
    desired = {target: rendered, registration: registered}
    changed = {path: data for path, data in desired.items()
               if data != (current if path == target else original)}
    return changed, receipt_path, receipt, old, guards


def apply(name, config, state, generation):
    changed, receipt_path, receipt, old, guards = prepare(name, config, state, generation)
    if not changed and receipt == old:
        return {'status': 'success', 'detail': 'unchanged'}
    with tempfile.TemporaryDirectory(prefix='dots-theme-plugin-') as temporary:
        operations = []
        for i, (path, data) in enumerate(changed.items()):
            stage = Path(temporary) / str(i)
            stage.write_bytes(data)
            os.chmod(stage, stat.S_IMODE(path.stat().st_mode) if exists(path) else 0o644)
            operations.append({'path': str(path), 'source': str(stage)})
            guards[str(stage)] = digest(stage)
        if receipt != old:
            operations.append({'path': str(receipt_path), 'data': receipt})
        result = Store(state).apply('theme-plugin-' + name, operations, guards, retain=True)
    return {'status': 'success', 'detail': 'applied; restart affected apps to see changes', 'transaction': result['id']}
