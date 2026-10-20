"""Read the live framework's static headers without executing commands."""
from pathlib import Path
import os
import re

BUILTINS = ('help', 'commands', 'completion', 'init')
RESERVED = set(BUILTINS) | set('doctor version status spec plan apply undo history backup config bootstrap self __complete'.split())
LIB = Path(__file__).resolve().parent
ROUTE = re.compile(r'[a-z][a-z0-9]*(?:-[a-z][a-z0-9]*)*\Z')


def read(path):
    data = dict(summary='', usage='', hidden=False, option=[], argument=[], example=[])
    seen = set()
    size = 0
    position = 1
    rest_seen = False
    with Path(path).open(encoding='utf-8-sig') as stream:
        for number, line in enumerate(iter(lambda: stream.readline(16385), ''), 1):
            if line.strip() and not line.startswith('#'):
                break
            size += len(line.encode('utf-8'))
            if number > 128 or size > 16384:
                raise ValueError('metadata header exceeds limit: ' + str(path))
            if not line.startswith('# dots:'):
                continue
            key, sep, value = line.rstrip('\r\n')[7:].partition('=')
            if not sep or key not in data or not value or any(ord(c) < 32 or ord(c) == 127 for c in value):
                raise ValueError('invalid command metadata: ' + str(path))
            if key in ('option', 'argument'):
                fields = value.split('|')
                if len(fields) != (4 if key == 'option' else 3):
                    raise ValueError('invalid metadata fields: ' + str(path))
                if key == 'option':
                    if not re.fullmatch('--[a-z][a-z0-9-]*', fields[0]) or (fields[1] and not re.fullmatch('-[a-zA-Z0-9]', fields[1])):
                        raise ValueError('invalid option metadata: ' + str(path))
                    for flag in fields[:2]:
                        if flag and flag in seen:
                            raise ValueError('duplicate option: ' + flag)
                        if flag:
                            seen.add(flag)
                kind = fields[2] if key == 'option' else fields[1]
                allowed = {'flag','string','file','directory','theme','flavor','palette-color','color-format','file-resource','file-repository','theme-id','file-color-key','theme-color','anodize-theme','theme-plugin','dots-setting'}
                if kind not in allowed and not (kind.startswith('choice:') and all(kind[7:].split(','))):
                    raise ValueError('invalid metadata type: ' + kind)
                if not fields[-1]: raise ValueError('empty metadata description')
                if key == 'argument':
                    if rest_seen or fields[0] not in (str(position), '*') or kind == 'flag':
                        raise ValueError('invalid positional metadata')
                    rest_seen = fields[0] == '*'
                    position += 1
                data[key].append(fields)
            elif key == 'example':
                data[key].append(value)
            else:
                if key in seen:
                    raise ValueError('duplicate metadata field: ' + key)
                seen.add(key)
                if key == 'hidden' and value not in ('true', 'false'):
                    raise ValueError('invalid hidden metadata')
                data[key] = value == 'true' if key == 'hidden' else value
    return data


def roots(root, extras=()):
    result = []
    for path in (Path(root) / 'bin', Path(root) / 'local/bin', *map(Path, extras)):
        if path.is_dir() and path.resolve() not in [p.resolve() for p in result]:
            result.append(path)
    return result


def candidates(directory, stem):
    # First-party Bash headers also describe their shared native handlers.
    for suffix in ('', '.ps1', '.exe'):
        path = directory / ('dots-' + stem + suffix)
        if os.path.lexists(path):
            if not path.is_file():
                raise ValueError('command is not a regular file: ' + str(path))
            yield path


def resolve(directories, words):
    prefix = []
    for word in words:
        if not re.fullmatch('[a-z][a-z0-9]*', word):
            break
        prefix.append(word)
    for count in range(len(prefix), 0, -1):
        stem = '-'.join(prefix[:count])
        found = [p for d in directories for p in candidates(d, stem)]
        if len(found) > 1:
            raise ValueError('duplicate command route: ' + stem.replace('-', ' '))
        if found:
            return stem, found[0], count
    return '', None, 0


def catalog(directories):
    rows = {}
    for directory in directories:
        for path in sorted(directory.glob('dots-*')):
            stem = path.name[5:]
            if path.suffix in ('.ps1', '.exe'):
                stem = stem[:-len(path.suffix)]
            if not ROUTE.fullmatch(stem):
                continue
            if stem.split('-')[0] in RESERVED or stem in rows:
                raise ValueError('reserved or duplicate command route: ' + stem)
            if not path.is_file():
                raise ValueError('command is not a regular file: ' + str(path))
            metadata = path.with_suffix('.meta') if path.suffix == '.exe' else path
            rows[stem] = dict(read(metadata) if metadata.exists() else
                              dict(summary='', usage='', option=[], argument=[], example=[], hidden=False), path=path)
    return rows
