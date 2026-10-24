#!/usr/bin/env python3
"""Dots file and Git styles: literal configuration, portable exports and journaled edits."""
import argparse
import copy
import fnmatch
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parents[3]
LIMIT = 2 * 1024 * 1024
ATTRS = dict(bold=1, dim=2, italic=3, underline=4, blink=5, blink_rapid=6,
             reversed=7, hidden=8, crossed=9)
CORE = dict(file='fi', dir='di', symlink='ln', broken_symlink='or', missing='mi',
            hardlink='mh', fifo='pi', socket='so', door='do', block_device='bd',
            character_device='cd', setuid='su', setgid='sg', capability='ca',
            sticky_other_writable='tw', other_writable='ow', sticky='st', executable='ex')
VIVID = dict(file='regular_file', dir='directory', symlink='symlink',
             broken_symlink='broken_symlink', missing='missing_symlink_target',
             hardlink='multi_hard_link', fifo='fifo', socket='socket', door='door',
             block_device='block_device', character_device='character_device', setuid='setuid',
             setgid='setgid', capability='file_with_capability', sticky_other_writable='sticky_other_writable',
             other_writable='other_writable', sticky='sticky', executable='executable_file')
GROUPS = ('type', 'extension', 'mime', 'git')
HEX = re.compile(r'#[0-9a-fA-F]{6}\Z')
IDENT = re.compile(r'[a-z][a-z0-9_]*(?:-[a-z0-9_]+)*\Z')


def tmtheme_template_tokens(doc):
    """tmTheme foregrounds require RGB; terminal reset means normal theme text."""
    colors = doc['colors']
    return {'git_' + role + '_tmtheme': colors['foreground'] if colors['git'][role] == 'reset' else colors['git'][role]
            for role in ('added', 'deleted', 'modified')}


def leaf_template_tokens(palette):
    """Literal Leaf metadata and readable text on colored status badges."""
    light = palette['mode'] == 'light'
    return {'leaf_base': 'arctic' if light else 'ocean',
            'leaf_badge_foreground': palette['colors']['foreground' if light else 'background']}


def roots():
    sys.path.insert(0, str(ROOT / 'lib/dots/files'))
    from file_platform import config_root, state_root
    config, state = config_root() / 'dots', state_root()
    if not config.is_absolute() or not state.is_absolute():
        raise ValueError('Dots config and state roots must be absolute')
    return config, state


def regular(path):
    path = Path(path)
    if not stat.S_ISREG(path.lstat().st_mode):
        raise ValueError('expected regular data file: ' + str(path))
    with path.open('rb') as stream:
        data = stream.read(LIMIT + 1)
    if len(data) > LIMIT:
        raise ValueError('file exceeds size limit: ' + str(path))
    return data


def query(*args):
    if os.name == 'nt':
        from palette_native import Themes
        themes = Themes()
        if args[0] == 'current': return themes.current() + '\n'
        if args[0] == 'dir': return str(themes.directory(args[1])) + '\n'
        return json.dumps(themes.load(args[0])) + '\n'
    p = subprocess.run(['bash', str(ROOT / 'lib/dots/themes/colors-query.bash'), *args],
                       capture_output=True, text=True, timeout=30)
    if p.returncode:
        raise ValueError(p.stderr.strip() or 'could not resolve theme')
    return p.stdout


def validate_rule(group, key, value):
    if not isinstance(key, str) or not key or len(key) > 256 or any(ord(c) < 32 or ord(c) == 127 for c in key):
        raise ValueError('invalid rule key')
    if group in ('type', 'git') and not re.fullmatch(r'[a-z][a-z0-9_]*', key):
        raise ValueError('invalid ' + group + ' name')
    if group == 'extension' and (not key.startswith('.') or any(c in key for c in '/*?[]')):
        raise ValueError('extension must be a literal suffix beginning with a dot')
    if group == 'mime' and not re.fullmatch(r'[a-z0-9!#$&^_.+-]+/(?:[a-z0-9!#$&^_.+-]+|\*)', key):
        raise ValueError('MIME must be an exact type or a type/* group')
    if not isinstance(value, dict):
        raise ValueError('style must be a table')
    for field, val in value.items():
        if field in ATTRS:
            if type(val) is not bool:
                raise ValueError(field + ' must be true or false')
        elif field in ('fg', 'bg', 'use'):
            if not isinstance(val, str) or not (HEX.fullmatch(val) or re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', val)):
                raise ValueError('invalid color or style reference')
        else:
            raise ValueError('unknown style field: ' + field)


def read_rules(path):
    if not path.exists() and not path.is_symlink():
        return {}
    data = tomllib.loads(regular(path).decode())
    for group, rules in data.items():
        if group not in GROUPS or not isinstance(rules, dict):
            raise ValueError('unknown file-style group: ' + group)
        for key, value in rules.items():
            validate_rule(group, key, value)
    return data


def input_paths(identity, directory):
    config, _ = roots()
    return [ROOT / 'default/file-colors.toml', Path(directory) / 'file-colors.toml',
            config / 'file-colors.toml', config / 'file-colors' / identity / 'rules.toml']


def resolve(palette, directory, replacement=None):
    identity = palette['id']
    colors = {**palette.get('palette', {}), **palette.get('roles', {}), **palette['colors']}
    rules = {g: {} for g in GROUPS}
    origins = {g: {} for g in GROUPS}
    for path in input_paths(identity, directory):
        data = replacement[1] if replacement and path == replacement[0] else read_rules(path)
        for group, entries in data.items():
            for key, value in entries.items():
                rules[group].setdefault(key, {}).update(value)
                origins[group].setdefault(key, {}).update({field: str(path) for field in value})
    styles = {g: {} for g in GROUPS}

    def style(group, key, seen=()):
        marker = (group, key)
        if marker in seen:
            raise ValueError('cyclic style reference: ' + key)
        source = rules[group][key]
        value = {}
        if 'use' in source:
            if source['use'] not in rules['type']:
                raise ValueError('unknown style: ' + source['use'])
            value.update(style('type', source['use'], (*seen, marker)))
        for field, item in source.items():
            if field == 'use':
                continue
            if field in ('fg', 'bg') and item != 'reset':
                item = colors.get(item, item)
                if not HEX.fullmatch(item):
                    raise ValueError('unknown palette color: ' + source[field])
            value[field] = item
        return value

    for group, entries in rules.items():
        for key in entries:
            styles[group][key] = style(group, key)
    # Namespaces are explicit; native collisions remain accessible in palette.json.
    shortcuts = {k: v for k, v in colors.items() if k not in (*GROUPS, 'styles', 'metadata')}
    for group, entries in styles.items():
        shortcuts[group] = {k: v.get('fg', 'reset') for k, v in entries.items()}
    return dict(schema=1, id=identity, mode=palette['mode'], colors=shortcuts, styles=styles,
                provenance=origins, rules=rules)


def vivid_runtime():
    """Probe only while rendering/generating, never during shell startup."""
    executable = shutil.which('vivid')
    if not executable:
        return None, 'unavailable', True
    try:
        result = subprocess.run([executable, '--version'], capture_output=True,
                                text=True, timeout=5)
        match = re.fullmatch(r'vivid (\d+)\.(\d+)\.(\d+)(?:[-+][\w.-]+)?', result.stdout.strip())
        if result.returncode == 0 and match:
            version = tuple(map(int, match.groups()))
            return executable, '.'.join(match.groups()), version >= (0, 10, 0)
    except (OSError, subprocess.TimeoutExpired):
        pass
    # Unknown vendor builds get the conservative grammar, not a failed-tool
    # fallback: generate must still succeed before anything can be published.
    return executable, 'unknown version', False


def vivid_theme(doc, multiple_styles=True):
    result = {'colors': {}}
    styles = doc['styles']['type']

    def item(name):
        style = styles[name]
        value = {}
        for key, output in (('fg', 'foreground'), ('bg', 'background')):
            color = style.get(key)
            if color and color != 'reset':
                token = name + '_' + key
                result['colors'][token] = color.lstrip('#')
                value[output] = token
        # Vivid's font-style grammar is narrower than SGR; exact core and
        # explicit suffix styles are appended to LS_COLORS after generation.
        names = {'bold':'bold', 'dim':'faint', 'italic':'italic', 'underline':'underline',
                 'blink':'blink', 'blink_rapid':'rapid-blink'}
        attrs = [value for key,value in names.items() if style.get(key)]
        if attrs:
            value['font-style'] = attrs if multiple_styles and len(attrs) > 1 else attrs[0]
        return value

    result['core'] = {VIVID[k]: item(k) for k in CORE}
    result['core'].update(normal_text=item('file'), reset_to_normal=item('file'))
    result['text'] = item('text')
    result['text'].update(special=item('special'), todo=item('todo'), licenses=item('license'), configuration=item('configuration'))
    result['markup'] = item('markup')
    result['programming'] = item('programming')
    result['programming'].update(source=item('programming'), tooling=item('tooling'))
    for output, key in [('media', 'media'), ('office', 'office'), ('archives', 'archive'),
                        ('executable', 'executable'), ('unimportant', 'unimportant')]:
        result[output] = item(key)
    return result


def sgr(style):
    codes = ['0']
    codes.extend(str(code) for field, code in ATTRS.items() if style.get(field))
    for field, code in [('fg', 38), ('bg', 48)]:
        value = style.get(field)
        if value and value != 'reset':
            codes += [str(code), '2', *(str(int(value[i:i+2], 16)) for i in (1, 3, 5))]
    return ';'.join(codes)


def escape_key(key):
    return ''.join('\\' + c if c in '\\:=^' else c for c in key)


def split_escaped(text, delimiter):
    result, start, i = [], 0, 0
    while i < len(text):
        if text[i] in '\\^':
            i += 2
        elif text[i] == delimiter:
            result.append(text[start:i]); start = i + 1; i += 1
        else:
            i += 1
    result.append(text[start:])
    return result


def decode(text):
    out, i = [], 0
    escapes = {'a': '\a', 'b': '\b', 'e': '\x1b', 'f': '\f', 'n': '\n', 'r': '\r', 't': '\t', 'v': '\v', '?': '\x7f', '_': ' '}
    while i < len(text):
        c = text[i]; i += 1
        if c == '^':
            if i == len(text): raise ValueError('incomplete caret escape')
            out.append(chr(127 if text[i] == '?' else ord(text[i]) % 32)); i += 1
        elif c == '\\':
            if i == len(text): raise ValueError('incomplete escape')
            m = re.match(r'[0-7]{1,3}|x[0-9a-fA-F]{1,2}', text[i:])
            if m:
                token = m[0]; out.append(chr(int(token[1:], 16) if token[0] == 'x' else int(token, 8) % 256)); i += len(token)
            else:
                out.append(escapes.get(text[i], text[i])); i += 1
        else: out.append(c)
    return ''.join(out)


def parse_sgr(value):
    if not re.fullmatch(r'[0-9;]*', value): raise ValueError('invalid SGR')
    codes = [int(x or '0') for x in value.split(';')]
    attrs = {v: k for k, v in ATTRS.items()}
    removals = {22: ['bold', 'dim'], 23: ['italic'], 24: ['underline'], 25: ['blink', 'blink_rapid'],
                27: ['reversed'], 28: ['hidden'], 29: ['crossed']}
    result, i = {}, 0
    while i < len(codes):
        code = codes[i]; i += 1
        if code == 0: result = {}
        elif code in attrs: result[attrs[code]] = True
        elif code in removals:
            for key in removals[code]: result[key] = False
        elif code in (39, 49): result['fg' if code == 39 else 'bg'] = 'reset'
        elif 30 <= code <= 37 or 90 <= code <= 97: result['fg'] = code - (30 if code < 90 else 82)
        elif 40 <= code <= 47 or 100 <= code <= 107: result['bg'] = code - (40 if code < 100 else 92)
        elif code in (38, 48):
            key = 'fg' if code == 38 else 'bg'
            if i >= len(codes): raise ValueError('incomplete SGR')
            mode = codes[i]; i += 1
            count = {5: 1, 2: 3}.get(mode)
            if count is None or i + count > len(codes): raise ValueError('invalid SGR color')
            values = codes[i:i+count]; i += count
            if any(x > 255 for x in values): raise ValueError('invalid SGR channel')
            result[key] = values[0] if mode == 5 else '#%02x%02x%02x' % tuple(values)
        else: raise ValueError('unsupported SGR attribute')
    return result


def parse_ls(value):
    if len(value.encode()) > LIMIT: raise ValueError('LS_COLORS exceeds size limit')
    result = dict(schema=1, types={}, suffixes=[], invalid=[])
    for pair in split_escaped(value.strip('\n'), ':'):
        if not pair: continue
        try:
            fields = split_escaped(pair, '=')
            if len(fields) != 2: raise ValueError('expected key=value')
            key, sequence = map(decode, fields)
            if key in ('lc', 'rc', 'ec', 'cl'): continue
            style = {'target': True} if key == 'ln' and sequence == 'target' else parse_sgr(sequence)
            entry = dict(key=key, sequence=sequence, style=style)
            if key.startswith('*'): result['suffixes'].append(entry)
            else: result['types'][key] = entry
        except ValueError as error:
            result['invalid'].append(str(error))
    return result


def generate(doc, vivid_file=None, runtime=None, template_source=None):
    raw = ''
    doc['coverage'] = 'basic'
    runtime = runtime or vivid_runtime()
    executable, version, multiple_styles = runtime
    if executable:
        if vivid_file is None:
            with tempfile.TemporaryDirectory(prefix='dots-file-colors-') as tmp:
                path = Path(tmp) / 'theme.yml'
                path.write_text(json.dumps(vivid_theme(doc, multiple_styles)))
                return generate(doc, path, runtime, 'shared file styles')
        try:
            p = subprocess.run([executable, 'generate', str(vivid_file)], capture_output=True, text=True, timeout=20)
            failure = p.stderr.strip() if p.returncode else None
        except (OSError, subprocess.TimeoutExpired) as error:
            failure = str(error)
        if failure is not None:
            hint = (' Use scalar font-style values in this template or upgrade Vivid to 0.10+.'
                    if not multiple_styles else ' Check this template and the Vivid diagnostic.')
            raise ValueError(f'Vivid {version} could not generate file colors from '
                             f'{template_source or vivid_file}.{hint}\n{failure}')
        raw = p.stdout.strip()
        doc['coverage'] = 'vivid'
    else:
        raw = ':'.join(CORE[k] + '=' + sgr(doc['styles']['type'][k]) for k in CORE)
    # Core/suffix overrides retain exact attributes unsupported by Vivid's theme grammar.
    raw += ':' + ':'.join(CORE[k] + '=' + sgr(doc['styles']['type'][k]) for k in CORE)
    raw += ''.join(':' + escape_key('*' + key) + '=' + sgr(style) for key, style in doc['styles']['extension'].items())
    doc['ls_colors'] = raw
    doc['ls_rules'] = parse_ls(raw)
    return doc


def lua(value):
    if value is None: return 'nil'
    if value is True: return 'true'
    if value is False: return 'false'
    if isinstance(value, (int, float)): return str(value)
    if isinstance(value, str):
        return '"' + ''.join('\\%03d' % b if b < 32 or b >= 127 else '\\' + chr(b) if chr(b) in '\\"' else chr(b) for b in value.encode()) + '"'
    if isinstance(value, list): return '{' + ','.join(lua(v) for v in value) + '}'
    return '{' + ','.join('[' + lua(k) + ']=' + lua(v) for k, v in sorted(value.items())) + '}'


def write_snapshot(doc, out):
    (out / 'colors.json').write_text(json.dumps(doc, sort_keys=True) + '\n')
    (out / 'colors.lua').write_text('return ' + lua(doc) + '\n')
    (out / 'ls_colors').write_text(doc['ls_colors'] + '\n')
    git_rows = [key + '\t' + (sgr(style) or '0') + '\n'
                for key, style in doc['styles'].get('git', {}).items()]
    (out / 'git-styles.tsv').write_text('dots-git-styles\t1\n' + ''.join(git_rows))
    # A validated data projection for shell consumers; never sourced as code.
    sys.path.insert(0, str(ROOT / 'lib/dots'))
    from resources import suffix_rows
    rows = [('type', key, sgr(style) or '0', '-') for key, style in doc['styles']['type'].items()]
    rows += suffix_rows([(key, sgr(style)) for key, style in doc['styles']['extension'].items()], 'extension')
    mime = {'mime': [], 'default_mime': []}
    for key in sorted(doc['styles']['mime'], key=lambda k: ('*' in k, k)):
        custom = any(Path(s) != ROOT / 'default/file-colors.toml' for s in doc['provenance']['mime'][key].values())
        group = 'mime' if custom else 'default_mime'
        mime[group].append((group, key, sgr(doc['styles']['mime'][key]) or '0', '-'))
    rows += mime['mime']
    rows += suffix_rows([(e['key'][1:], e['sequence']) for e in doc['ls_rules']['suffixes']], 'suffix')
    rows += mime['default_mime']
    rows = [row for row in rows if row[1] and not any(ord(c) < 32 or ord(c) == 127 for c in row[1])]
    (out / 'file-styles.tsv').write_text('dots-file-styles\t1\n' + ''.join('\t'.join(row) + '\n' for row in rows))


def selected(theme=None, configured=False, generate_rules=True):
    _, state = roots()
    if theme is None and not configured:
        path = state / 'current/theme/colors.json'
        if path.exists():
            doc = json.loads(regular(path))
            if doc.get('schema') != 1: raise ValueError('unsupported file colors schema; refresh theme')
            return doc
    identity = theme or query('current').strip()
    palette = json.loads(query(identity))
    directory = query('dir', identity).strip()
    doc = resolve(palette, directory)
    return generate(doc) if generate_rules else doc


def selection_source(theme=None, configured=False):
    _, state = roots()
    return 'Published snapshot' if theme is None and not configured and (state / 'current/theme/colors.json').exists() else 'Configured sources'


def suffix_match(entries, name):
    """Match GNU suffix case collisions using the same priority as dots.yazi."""
    groups, ordered = {}, []
    for original in reversed(entries):
        entry = dict(original, suffix=original['key'][1:])
        entry['folded'] = entry['suffix'].lower()
        groups.setdefault(entry['folded'], []).append(entry)
        ordered.append(entry)
    for group in groups.values():
        for i, entry in enumerate(group):
            if entry.get('shadowed'): continue
            folded_match = False
            for older in group[i+1:]:
                if older.get('shadowed'): continue
                if entry['suffix'] == older['suffix'] or folded_match:
                    older['shadowed'] = True
                elif entry['sequence'] == older['sequence']:
                    older['shadowed'], folded_match = True, True
                else: entry['exact'] = older['exact'] = True
    for entry in ordered:
        if entry.get('shadowed'): continue
        if (name if entry.get('exact') else name.lower()).endswith(entry['suffix'] if entry.get('exact') else entry['folded']):
            return entry


def match(doc, path, mime=None):
    p = Path(path); info = p.lstat(); mode = info.st_mode
    types = doc['styles']['type']
    def colored(kind):
        return doc['ls_rules']['types'].get(CORE[kind], {}).get('sequence', '') not in ('', '0', '00')
    kind = 'file'
    if stat.S_ISLNK(mode): kind = 'broken_symlink' if not p.exists() and colored('broken_symlink') else 'symlink'
    elif stat.S_ISDIR(mode):
        kind = 'sticky_other_writable' if mode & stat.S_ISVTX and mode & stat.S_IWOTH and colored('sticky_other_writable') else 'other_writable' if mode & stat.S_IWOTH and colored('other_writable') else 'sticky' if mode & stat.S_ISVTX and colored('sticky') else 'dir'
    elif stat.S_ISFIFO(mode): kind = 'fifo'
    elif stat.S_ISSOCK(mode): kind = 'socket'
    elif stat.S_ISBLK(mode): kind = 'block_device'
    elif stat.S_ISCHR(mode): kind = 'character_device'
    elif mode & stat.S_ISUID and colored('setuid'): kind = 'setuid'
    elif mode & stat.S_ISGID and colored('setgid'): kind = 'setgid'
    elif mode & 0o111 and colored('executable'): kind = 'executable'
    elif info.st_nlink > 1 and colored('hardlink'): kind = 'hardlink'
    if kind != 'file': return dict(group='type', key=kind, style=types[kind], source=doc['provenance']['type'][kind])
    explicit = suffix_match([dict(key='*'+key, sequence=sgr(style), style=style) for key,style in doc['styles']['extension'].items()], p.name)
    if explicit:
        key = explicit['key'][1:]
        return dict(group='extension', key=key, style=explicit['style'], source=doc['provenance']['extension'][key])
    mime_keys = sorted(doc['styles']['mime'], key=lambda k: ('*' in k, k))
    def mime_match(custom):
        for key in mime_keys:
            sources = doc['provenance']['mime'][key].values()
            is_custom = any(Path(s) != ROOT / 'default/file-colors.toml' for s in sources)
            if is_custom == custom and mime and fnmatch.fnmatchcase(mime, key):
                return dict(group='mime', key=key, style=doc['styles']['mime'][key], source=doc['provenance']['mime'][key])
    found = mime_match(True)
    if found: return found
    entry = suffix_match(doc['ls_rules']['suffixes'], p.name)
    if entry: return dict(group='extension', key=entry['key'][1:], style=entry['style'], source='vivid')
    return mime_match(False) or dict(group='type', key='file', style=types['file'], source=doc['provenance']['type']['file'])


def toml_dump(data):
    lines = ['# Dots file and Git style overrides; edit directly or use theme colors set/reset.']
    for group in GROUPS:
        for key, values in data.get(group, {}).items():
            lines += ['', '[' + group + '.' + json.dumps(key) + ']']
            lines += [f'{field} = {str(value).lower() if isinstance(value, bool) else json.dumps(value)}' for field, value in values.items()]
    return '\n'.join(lines) + '\n'


def edit(args):
    from presentation import ColorView
    config, state = roots()
    if args.theme and not IDENT.fullmatch(args.theme): raise ValueError('invalid theme ID')
    target = config / 'file-colors' / args.theme / 'rules.toml' if args.theme else config / 'file-colors.toml'
    sys.path.insert(0, str(ROOT / 'lib/dots/files'))
    from transactions import Store, digest
    before = digest(target)
    data = read_rules(target)
    group = data.setdefault(args.group, {})
    if args.action == 'reset': group.pop(args.key, None)
    else:
        updates = {key: getattr(args, key) for key in ('fg', 'bg', 'use', *ATTRS) if getattr(args, key) is not None}
        if not updates: raise ValueError('provide a style field, for example --fg blue')
        updates = {k: v == 'true' if k in ATTRS else v for k, v in updates.items()}
        validate_rule(args.group, args.key, updates)
        group.setdefault(args.key, {}).update(updates)
    identity = args.theme or query('current').strip()
    palette = json.loads(query(identity))
    doc = resolve(palette, query('dir', identity).strip(), (target, data))
    content = toml_dump(data).encode()
    if args.dry_run:
        print(json.dumps(dict(status='preview', target=str(target), rules=data, resolved=doc['styles'][args.group].get(args.key)), sort_keys=True)); return
    view = ColorView(doc['colors'])
    if target.exists() and regular(target) == content:
        view.title('Theme styles unchanged.')
    else:
        with tempfile.TemporaryDirectory(prefix='dots-color-edit-') as tmp:
            stage = Path(tmp) / 'rules.toml'; stage.write_bytes(content)
            receipt = Store(state).apply('theme-file-colors', [{'path': str(target), 'source': str(stage)}], {str(target): before}, retain=True)
        view.title('Saved theme styles')
        view.fields([('Target', target), ('Journal', receipt.get('id', receipt.get('transaction', 'dots files history')))])
    if args.apply:
        command = [sys.executable, '-B', str(ROOT / 'lib/dots/cli.py'), 'theme', 'refresh'] if os.name == 'nt' else [str(ROOT / 'bin/dots-theme-refresh')]
        p = subprocess.run(command)
        if p.returncode: raise ValueError('styles saved but not published; retry theme refresh')
    else: view.line('Run theme refresh to publish saved styles.')


def parser():
    p = argparse.ArgumentParser(description='Query, customize and export Dots palette, file and Git styles.')
    sub = p.add_subparsers(dest='action')
    for group in GROUPS:
        q = sub.add_parser(group); q.add_argument('key', nargs='?'); q.add_argument('format', nargs='?', choices=['hex','rgb','ansi-24bit','esc'], default='hex')
        q.add_argument('--style', action='store_true')
    for action in ('set', 'reset'):
        q = sub.add_parser(action); q.add_argument('group', choices=GROUPS); q.add_argument('key')
        q.add_argument('--dry-run', action='store_true'); q.add_argument('--apply', action='store_true')
        if action == 'set':
            for field in ('fg', 'bg', 'use'): q.add_argument('--' + field)
            for field in ATTRS: q.add_argument('--' + field.replace('_','-'), choices=['true','false'])
    q = sub.add_parser('match'); q.add_argument('path'); q.add_argument('--mime')
    q = sub.add_parser('parse'); source = q.add_mutually_exclusive_group(); source.add_argument('--stdin', action='store_true'); source.add_argument('--env', action='store_true')
    q = sub.add_parser('export'); q.add_argument('format', choices=['lua','json','ls-colors'])
    # Shared flags work after the action; normalize before parse below.
    p.add_argument('--theme'); p.add_argument('--configured', action='store_true'); p.add_argument('--json', action='store_true')
    return p


def main(argv):
    if argv and argv[0] == '_show':
        from presentation import render_colors
        render_colors(resolve(json.load(sys.stdin), argv[1]), 'Configured sources', preview=True)
        return
    if argv and argv[0] == '_complete':
        words = argv[1:]
        action = words[0] if words else ''
        group = words[1] if len(words)>1 and action in ('set','reset') else action
        if action in ('set','reset') and len(words)==1: values = GROUPS
        elif action in GROUPS and len(words)>1: values = ('hex','rgb','ansi-24bit','esc')
        elif action == 'export': values = ('json','lua','ls-colors')
        elif group in GROUPS:
            values = list(read_rules(ROOT / 'default/file-colors.toml').get(group, {}))
            config, _ = roots()
            values += list(read_rules(config / 'file-colors.toml').get(group, {}))
        else: values = ()
        print('\n'.join(sorted(set(values))))
        return
    if argv and argv[0] in ('_vivid', '_build', '_starship_git', '_template_colors'):
        action, directory = argv[:2]
        palette = json.load(sys.stdin)
        doc = resolve(palette, directory)
        if action == '_vivid': print(json.dumps(vivid_theme(doc, vivid_runtime()[2]), indent=2))
        elif action == '_template_colors':
            for key, value in leaf_template_tokens(palette).items():
                print(key + '\t' + value)
            for key, value in tmtheme_template_tokens(doc).items():
                print(key + '\t' + value)
            colors = {k: v for k, v in doc['colors'].items() if isinstance(v, str) and HEX.fullmatch(v)}
            aliases = {'git_' + k: v for k, v in doc['colors']['git'].items()}
            for key, value in aliases.items():
                print(key + '\t' + value)
                print(key + '_delta\t' + ('normal' if value == 'reset' else value))
                print(key + '_eza\t' + ('default' if value == 'reset' else value))
            colors.update(aliases)
            background = doc['colors']['background']
            for key, value in colors.items():
                if value == 'reset':
                    value = background
                for percent in (10, 25):
                    mixed = '#' + ''.join(f'{(int(value[i:i+2], 16)*percent + int(background[i:i+2], 16)*(100-percent) + 50)//100:02x}' for i in (1, 3, 5))
                    print(f'{key}_blend_{percent}\t{mixed}')
        elif action == '_starship_git':
            for key, value in doc['colors']['git'].items():
                print('git_' + key + ' = ' + json.dumps(value))
        else:
            out = Path(argv[2])
            runtime = vivid_runtime()
            source = argv[3] if len(argv) > 3 else None
            write_snapshot(generate(doc, out / 'vivid.yml', runtime, source), out)
            # Private result channel; the owning human view renders the notice
            # after stopping progress. JSON/raw exports never print it.
            if runtime[0] and not runtime[2]:
                print(f'Vivid {runtime[1]}: generated category styles and direct '
                      'vivid generate dots output use one font attribute. Dots '
                      'preserves full core and explicit suffix styles in LS_COLORS. '
                      'Vivid 0.10+ supports combined category attributes.')
        return
    shared, rest = [], []
    i = 0
    while i < len(argv):
        arg = argv[i]; i += 1
        if arg in ('--json', '--configured'): shared.append(arg)
        elif arg == '--theme':
            if i == len(argv): raise ValueError('--theme requires an ID')
            shared += [arg, argv[i]]; i += 1
        elif arg.startswith('--theme='): shared.append(arg)
        elif arg.startswith('--color='):
            mode = arg.split('=',1)[1]
            if mode not in ('none','never','auto','always'): raise ValueError('invalid color mode')
            os.environ['DOTS_COLOR'] = 'never' if mode == 'none' else mode
        else: rest.append(arg)
    args = parser().parse_args(shared + rest)
    if args.action in ('set','reset'): edit(args); return
    if args.action == 'parse':
        raw = sys.stdin.read(LIMIT + 1) if args.stdin else os.environ.get('LS_COLORS', '')
        result = parse_ls(raw)
    else:
        doc = selected(args.theme, args.configured, generate_rules=args.action in ('export', 'match'))
        if args.action == 'export':
            print('return ' + lua(doc) if args.format == 'lua' else doc['ls_colors'] if args.format == 'ls-colors' else json.dumps(doc, sort_keys=True)); return
        if args.action in GROUPS:
            if args.action == 'git' and 'git' not in doc['styles']:
                raise ValueError('published snapshot has no Git styles; run theme refresh or use --configured')
            entries = doc['styles'][args.action]
            if args.key:
                key = args.key
                if args.action == 'mime' and key not in entries:
                    key = next((k for k in entries if fnmatch.fnmatchcase(key,k)), key)
                if key not in entries: raise ValueError('unknown ' + args.action + ': ' + args.key)
                style = entries[key]
                if args.json or args.style:
                    result = dict(theme=doc['id'], key=key, style=style, source=doc['provenance'][args.action][key])
                else:
                    value = style.get('fg', 'reset')
                    if args.format != 'hex':
                        if not isinstance(value, str) or not HEX.fullmatch(value): raise ValueError('color has no RGB value')
                        rgb = [int(value[i:i+2],16) for i in (1,3,5)]
                        value = ' '.join(map(str,rgb)) if args.format == 'rgb' else '38;2;' + ';'.join(map(str,rgb))
                        if args.format == 'esc': value = '\x1b[' + value + 'm'
                    print(value); return
            else: result = entries
        elif args.action == 'match': result = match(doc, args.path, args.mime)
        else: result = doc['colors']
    if args.json: print(json.dumps(result, sort_keys=True))
    else:
        from presentation import render_colors, render_parsed, color_enabled
        if args.action == 'parse':
            colors = None
            if color_enabled():
                # Parsing arbitrary LS_COLORS still works without an installed theme.
                try: colors = json.loads(query(args.theme or query('current').strip()))['colors']
                except (ValueError, OSError, KeyError, subprocess.TimeoutExpired): pass
            render_parsed(result, colors)
        else:
            context = {'Path': args.path} if args.action == 'match' else {'Requested rule': args.key} if args.action in GROUPS and args.key else None
            render_colors(doc, selection_source(args.theme, args.configured), args.action, result, context)


if __name__ == '__main__':
    try: main(sys.argv[1:])
    except (ValueError, OSError, KeyError, subprocess.TimeoutExpired) as error:
        print('dots colors: ' + str(error), file=sys.stderr); sys.exit(1)
