"""Public first-party command documentation from inert, revision-aware inputs."""
from pathlib import PurePosixPath
import re

from command_metadata import parse


def inventory(reader):
    rows = []
    names = reader.names('bin/') + reader.names('lib/dots/metadata/')
    for name in sorted(names):
        filename = PurePosixPath(name).name
        if not (name.startswith('bin/dots-') and '.' not in filename or
                name.startswith('lib/dots/metadata/') and name.endswith('.meta')):
            continue
        fields = parse(reader.read(name).decode('utf-8-sig').splitlines(True), name)
        if not fields['summary'] or fields['hidden']:
            continue
        stem = filename.removeprefix('dots-').removesuffix('.meta')
        rows.append(dict(fields, route='dots ' + stem.replace('-', ' ')))
    return rows


def global_options(reader):
    """Read the same literal option table as Bash help; never source the file."""
    name = 'lib/dots/catalog.bash'
    if name not in reader.names('lib/dots/'):
        return []  # Small documentation fixtures can omit the root frontend.
    text = reader.read(name).decode()
    match = re.search(r'^DOTS_GLOBAL_OPTIONS=\(\n(.*?)^\)', text, re.M | re.S)
    if not match:
        raise ValueError('missing static global option metadata')
    fields = []
    for line in match[1].splitlines():
        item = re.fullmatch(r"\s*'([^'\n]+)'\s*", line)
        if not item or len(item[1].split('|')) != 4:
            raise ValueError('invalid static global option metadata')
        fields.append(item[1].split('|'))
    return fields


def markdown(reader):
    result = ['# Command reference', '',
              'Generated from first-party static metadata. Extensions and private command directories are not executed or included.', '']
    options = global_options(reader)
    if options:
        result += ['## dots', '', '`dots [GLOBAL OPTIONS] COMMAND [ARGUMENTS]`', '',
                   'Global options precede the command. Native Windows uses `dots.ps1` with the same routes.', '']
        for long, short, kind, description in options:
            result += ['- `' + long + ('`, `' + short if short else '') + '`: ' + description]
        result.append('')
    for row in inventory(reader):
        route = row['route']
        result += ['## ' + route, '', row['summary'], '',
                   '`' + route + ' ' + row['usage'] + '`', '']
        for long, short, kind, description in row['option']:
            result += ['- `' + long + ('`, `' + short if short else '') + '`: ' + description]
        for position, kind, description in row['argument']:
            result += ['- Argument ' + position + ' (`' + kind + '`): ' + description]
        for example in row['example']:
            result += ['', '```sh', example, '```']
        result.append('')
    return '\n'.join(result)
