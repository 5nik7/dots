"""Private native-shell bridge to the shared completion grammar; never run shells."""
import contextlib
import io
import json
import os
from pathlib import Path
import re
import sys

LIB = Path(__file__).resolve().parent
sys.path.insert(0, str(LIB))

# These are entry-point identities, not another option/subcommand grammar.
# Every route delegates to its existing shared provider below.
STANDALONE = {
    'dots': (), 'theme': ('theme',), 'anodize': ('anodize',),
    'blastoff': ('blastoff',), 'pkgs': ('pkgs',),
    'todo': ('__todo_standalone',), 'fonts': ('fonts',),
    'bak': ('bak',), 'dots-bak': ('bak',), 'wttr': ('wttr',),
    'cpy': None, 'pst': None,
}
IDENTITY = re.compile(r'[a-z][a-z0-9_]*(?:-[a-z0-9_]+)*\Z')


def command_names():
    from utility_commands import NAMES
    names = [*STANDALONE, *NAMES]
    if os.name == 'nt':
        names = [name.casefold() for name in names]
    return [name + suffix for name in names for suffix in ('', '.ps1')]


def environment(root, env=None):
    from native_environment import document
    from shell.runtime import paths
    result = document(root, env)
    result['shell_paths'] = paths(root, env)
    result['completion_commands'] = command_names()
    return result


def theme_aliases(state):
    directory = Path(state) / 'themes/commands/current'
    mapping = directory / 'map.tsv'
    names = directory / 'names'
    path = mapping if mapping.is_file() else names
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 1024 * 1024:
        return {}
    result = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        pair = line.split('\t') if path == mapping else [line, line]
        if len(pair) == 2 and all(IDENTITY.fullmatch(value) for value in pair):
            result[pair[0]] = pair[1]
    return result


def path_candidates(kind, lead, current):
    """Expand trusted file/directory records without globbing or evaluation."""
    if lead and not current.startswith(lead):
        return []
    token = current[len(lead):]
    prefix, leaf = os.path.split(token)
    if prefix:
        prefix += os.sep if not prefix.endswith(os.sep) else ''
    directory = Path(os.path.expanduser(prefix or '.'))
    result = []
    try:
        with os.scandir(directory) as entries:
            for index, entry in enumerate(entries):
                if index >= 4096:
                    break
                if not entry.name.startswith(leaf) or (entry.name.startswith('.') and not leaf.startswith('.')):
                    continue
                if any(ord(c) < 32 or 127 <= ord(c) < 160 for c in entry.name):
                    continue
                is_dir = entry.is_dir()
                if kind == 'directory' and not is_dir:
                    continue
                result.append(dict(value=lead + prefix + entry.name + (os.sep if is_dir else ''),
                                   description='Directory' if is_dir else 'File'))
    except OSError:
        pass
    return sorted(result, key=lambda row: row['value'])


def complete(root, shell, words):
    if shell not in ('nu', 'xonsh', 'powershell') or len(words) < 2:
        return None
    name = re.split(r'[/\\]', words[0])[-1]
    if os.name == 'nt':
        name = name.casefold()
    name = name.removesuffix('.ps1')
    operands = words[1:]
    from utility_commands import NAMES, complete as utility_complete
    utility = next((item for item in NAMES
                    if (item.casefold() if os.name == 'nt' else item) == name), None)
    if utility:
        return candidate_records(utility_complete(utility, operands), operands[-1])
    if name in ('cpy', 'pst'):
        from clipboard import HELP_OPTIONS
        if '--' in operands[:-1]:
            return []
        return [dict(value=flag, description='Show help') for flag in HELP_OPTIONS if flag.startswith(operands[-1])]
    route = STANDALONE.get(name)
    if name not in STANDALONE:
        from shell.runtime import paths
        target = theme_aliases(paths(root)['state']).get(name)
        if target is None:
            return None
        route = ('theme', target)
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        if route == ('bak',):
            from bak_completion import complete as provider
            provider(operands, shell=shell)
        else:
            from cli import complete as provider
            from command_metadata import roots
            provider(root, roots(root), [*route, *operands])
    records = []
    for line in output.getvalue().splitlines():
        fields = line.split('\t', 2)
        if len(fields) < 2:
            continue
        records.append((fields[0], fields[1], fields[2] if len(fields) > 2 else ''))
    return candidate_records(records, operands[-1])


def candidate_records(records, current):
    result = []
    for kind, value, description in records:
        if kind == 'candidate':
            result.append(dict(value=value, description=description))
        elif kind in ('file', 'directory'):
            result.extend(path_candidates(kind, value, current))
    return list({row['value']: row for row in result}.values())


def main(args=None):
    args = list(sys.argv[1:] if args is None else args)
    root = Path(os.environ.get('DOTS') or LIB.parents[1]).resolve()
    if args == ['--environment']:
        result = environment(root)
    elif len(args) >= 4 and args[0] == '--complete':
        result = complete(root, args[1], args[2:])
    else:
        return 2
    print(json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError):
        raise SystemExit(1)
