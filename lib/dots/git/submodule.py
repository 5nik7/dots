#!/usr/bin/env python3
"""Named navigation over registered edges; actions retain their existing controllers."""
import os
from pathlib import Path
import subprocess
import sys

LIB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LIB))
from command_metadata import read

ROOT = LIB.parents[1]
ACTIONS = ('info', 'status', 'publish', 'submodules', 'submodule')
HEADERS = {'info': 'info', 'status': 'submodules-status', 'publish': 'submodules-publish',
           'submodules': 'submodules', 'submodules info': 'submodules-info',
           'submodules status': 'submodules-status', 'submodules publish': 'submodules-publish'}


def metadata(action):
    data = read(ROOT / 'bin' / ('dots-git-' + HEADERS[action]))
    if action == 'publish':
        data['option'] = [r for r in data['option'] if r[0] != '--all-submodules']
    return data


def options():
    return {flag: row for action in HEADERS for row in metadata(action)['option']
            for flag in row[:2] if flag}


def parse(words, partial=False):
    """Separate options without treating their literal values as route words."""
    known = options()
    positionals, flags = [], []
    directory = os.environ.get('DOTS', str(ROOT))
    expected, literal = None, False
    for word in words:
        if expected:
            if expected[0] == '--directory': directory = word
            else: flags.append(word)
            expected = None
        elif not literal and word == '--': literal = True
        elif not literal and word.startswith('-'):
            flag, sep, value = word.partition('=')
            row = known.get(flag)
            if row is None: raise ValueError('unknown option: ' + flag)
            if sep and row[2] == 'flag': raise ValueError(flag + ' does not take a value')
            if row[0] != '--directory': flags.append(word)
            if row[2] != 'flag':
                if sep:
                    if row[0] == '--directory': directory = value
                else: expected = row
        else: positionals.append(word)
    if expected and not partial: raise ValueError(expected[0] + ' requires a value')
    return positionals, flags, directory, expected


def route(positionals, partial=False):
    if not positionals: return [], 'info', [], True
    names = [positionals[0]]
    index = 1
    while index < len(positionals) and positionals[index] == 'submodule':
        index += 1
        if index == len(positionals):
            if partial: return names, 'info', [], True
            raise ValueError('submodule requires a child NAME')
        names.append(positionals[index]); index += 1
    tail = positionals[index:]
    action = tail.pop(0) if tail else 'info'
    if action not in ACTIONS: raise ValueError('unknown submodule action: ' + action)
    if action == 'submodules' and tail and tail[0] in ('info', 'status', 'publish'):
        action += ' ' + tail.pop(0)
    if tail and action not in ('submodules status', 'submodules publish'):
        raise ValueError('unexpected argument: ' + tail[0])
    if len(tail) > 1: raise ValueError('select one registered PATH')
    return names, action, tail, False


def resolve(base, names):
    import inspection
    parent, selected = base, None
    for depth, name in enumerate(':'.join(names).split(':'), 1):
        if not name or name in ('.', '..') or any(c in name for c in '/\\'):
            raise ValueError('NAME must be a direct-child basename; use colons for nested submodules')
        if selected and selected['availability'] != 'available':
            raise ValueError('cannot navigate an unavailable submodule')
        candidates = [r for r in inspection.edges(parent, base, depth) if Path(r['path']).name == name]
        if len(candidates) > 1:
            paths = ', '.join(r['relative_path'] for r in candidates)
            raise ValueError('ambiguous submodule ' + name + '; use git submodules status/publish PATH: ' + paths)
        if not candidates: raise ValueError('no registered direct child named ' + name)
        selected = candidates[0]
        if selected['availability'] == 'blocked': raise ValueError(selected['reason'])
        parent = Path(selected['path'])
    return selected


def help_view(words):
    # Static syntax and headers only: even nonexistent names require no Git.
    from files.catalog import Presentation
    positional, _, _, _ = parse(words)
    names, action, _, pending = route(positional, partial=True)
    ui = Presentation()
    label = 'dots git submodule' + (' ' + ' submodule '.join(names) if names else '')
    if names: label += ' submodule' if pending else ' ' + action
    ui.heading(label)
    if not names or pending:
        ui.detail('Usage', label + ' NAME [ACTION] [OPTIONS]')
        for value in ACTIONS: ui.detail(value, 'Navigate a child' if value == 'submodule' else metadata(value)['summary'])
        ui.detail('-C, --directory', 'Initial repository directory')
    else:
        data = metadata(action)
        ui.emit('  ' + data['summary'])
        ui.detail('Usage', label + (' [PATH]' if action == 'submodules status' else ' PATH|--all-submodules' if action == 'submodules publish' else '') + ' [OPTIONS]')
        for long, short, _, description in data['option']:
            ui.detail(', '.join(v for v in (long, short) if v), description)
        if len(positional) == 2 * len(names) - 1:
            for value in ACTIONS: ui.detail(value, 'Submodule action')
    return 0


def complete(words):
    current = words[-1] if words else ''
    prior = words[:-1]
    def emit(value, description=''):
        if value.startswith(current) and not any(ord(c) < 32 or ord(c) == 127 for c in value + description):
            print('candidate\t' + value + '\t' + description)
    try:
        positional, _, directory, expected = parse(prior, partial=True)
        names, action, tail, pending = route(positional, partial=True)
        if expected:
            if expected[2] in ('directory', 'file'): print(expected[2] + '\t\t')
            return 0
        if current.startswith('-') and '--' not in prior:
            for long, short, _, description in metadata(action)['option']:
                emit(long, description)
                if short: emit(short, description)
            emit('--help', 'Show contextual help')
            return 0
        if pending:
            import inspection
            base = inspection.context(directory)
            prefix, sep, _ = current.rpartition(':')
            chain = names + ([prefix] if sep else [])
            selected = resolve(base, chain) if chain else None
            if selected and selected['availability'] != 'available': return 0
            parent = Path(selected['path']) if selected else base
            rows = inspection.edges(parent, base, 1)
            counts = {}
            for row in rows:
                name = Path(row['path']).name
                counts[name] = counts.get(name, 0) + 1
            for row in rows:
                name = Path(row['path']).name
                if counts[name] == 1 and ':' not in name and row['availability'] != 'blocked':
                    emit((prefix + ':' if sep else '') + name, row['relative_path'])
        elif action in ('submodules status', 'submodules publish') and not tail:
            import inspection
            base = inspection.context(directory)
            selected = resolve(base, names)
            if selected['availability'] == 'available':
                for row in inspection.discover(Path(selected['path']))[0]:
                    if row['availability'] != 'blocked': emit(row['relative_path'])
        elif positional[-1:] == ['submodules']:
            for value in ('info', 'status', 'publish'): emit(value, metadata('submodules ' + value)['summary'])
        elif len(positional) == 2 * len(names) - 1:
            for value in ACTIONS: emit(value, 'Submodule action')
    except (ValueError, OSError):
        pass
    return 0


def main(argv=None):
    words = list(sys.argv[1:] if argv is None else argv)
    native = words[:1] == ['--frontend=native']
    if native: words.pop(0)
    if words[:1] == ['--complete']: return complete(words[1:])
    explicit_help = words[:1] == ['--help-context']
    if explicit_help: words.pop(0)
    boundary = words.index('--') if '--' in words else len(words)
    if explicit_help or not words or any(w in ('--help', '-h') for w in words[:boundary]):
        return help_view([w for i, w in enumerate(words) if i >= boundary or w not in ('--help', '-h')])
    positional, flags, directory, _ = parse(words)
    names, action, tail, _ = route(positional)
    if not names: raise ValueError('submodule requires a NAME')
    allowed = {f for row in metadata(action)['option'] for f in row[:2] if f}
    # Reparse by arity so values beginning with dashes remain literal.
    index = 0
    known = options()
    while index < len(flags):
        flag, sep, _ = flags[index].partition('=')
        if flag not in allowed: raise ValueError(flag + ' is not valid for ' + action)
        index += 2 if not sep and known[flag][2] != 'flag' else 1
    import inspection
    base = inspection.context(directory)
    selected = resolve(base, names)
    if action == 'info':
        return inspection.main(['info', '-C', str(base), *flags], info_edge=selected)
    if action == 'status':
        return inspection.main(['status', '-C', str(base), *flags, '--', selected['relative_path']])
    if action == 'publish':
        args = ['-C', str(base), *flags, '--', selected['relative_path']]
    else:
        if selected['availability'] != 'available': raise ValueError('cannot navigate an unavailable submodule')
        args = ['-C', selected['path'], *flags, *(['--', *tail] if tail else [])]
        if action != 'submodules publish':
            return inspection.main([{'submodules': 'submodules', 'submodules info': 'submodules-info', 'submodules status': 'status'}[action], *args])
    command = [sys.executable, '-B', str(LIB / 'git/cli.py')] if native else ['bash', str(LIB / 'git/main.bash')]
    return subprocess.call([*command, 'submodules-publish', *args])


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError) as error:
        from files.catalog import Presentation
        Presentation(sys.stderr).detail('Error', str(error), '91')
        sys.exit(2)
    except KeyboardInterrupt:
        sys.exit(130)
