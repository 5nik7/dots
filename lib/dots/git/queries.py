"""Local Git field queries shared by the POSIX and native Dots frontends."""
import argparse
import json
import os
from pathlib import Path
import re
import string
import sys
from urllib.parse import quote_from_bytes

import inspection
from inspection import core
from git_identity import host_icon

REMOTE_FIELDS = ('root', 'remote', 'url', 'https_url', 'protocol', 'host', 'owner', 'repo', 'owned', 'icon')
PATH_FIELDS = ('current', 'parent', 'outermost', 'parent_dirname', 'parent_basename', 'submodule_prefix',
               'submodule_basename', 'cwd_prefix', 'path_parent', 'path_outermost', 'chain_length',
               'chain_repos', 'chain_paths', 'is_submodule')
SHORTCUTS = {'-o': 'owner', '--owner': 'owner', '-H': 'host', '--host': 'host', '-r': 'repo',
             '--repo': 'repo', '-p': 'protocol', '--protocol': 'protocol', '-R': 'url', '--url': 'url',
             '-i': 'icon', '--icon': 'icon'}
SELECTORS = (*SHORTCUTS, '--get', '--format', '-f', '--list-fields', '--https', '-n', '--no-newline')


def is_field_query(words):
    options = iter(words)
    for word in options:
        if word == '--':
            break
        if word.partition('=')[0] in SELECTORS:
            return True
        if word in ('-C', '--directory', '--remote', '--view'):
            next(options, None)
    return False


def parse_remote(url, aliases):
    """Remove credentials and helper payloads before projecting any public field."""
    url = re.split(r'[?#]', url, maxsplit=1)[0]
    safe, protocol, path, host, https = url, 'local', url, '', ''
    uri = re.match(r'^([a-zA-Z][a-zA-Z0-9+.-]*)://([^/]*)(?:/(.*))?$', url, re.S)
    helper = re.match(r'^([a-zA-Z][a-zA-Z0-9+.-]*)::', url)
    scp = re.match(r'^(?:[^/@:]+@)?(\[[\da-fA-F:.]+\]|[^/:@]+):([^:].*)$', url, re.S)
    valid_authority = False
    authority_pattern = r'(?:[a-zA-Z0-9._-]+|\[[0-9a-fA-F:.]+\])(?::[0-9]+)?'
    if uri:
        protocol = uri[1].lower()
        authority = uri[2].rsplit('@', 1)[-1]
        valid_authority = re.fullmatch(authority_pattern, authority) is not None
        path = uri[3] or ''
        safe = f'{protocol}://{authority}/{path}'
        host = authority.partition(']')[0] + ']' if authority.startswith('[') else authority.partition(':')[0]
    elif helper:
        safe, protocol, path = helper[0], helper[1].lower(), ''
    elif scp and not (os.name == 'nt' and os.path.splitdrive(url)[0]):
        host, path, protocol = scp[1], scp[2], 'ssh'
        valid_authority = re.fullmatch(authority_pattern, host) is not None
        safe = f'{host}:{path}'
    host = aliases.get(host.lower(), host.lower()).lower()
    path = path.lstrip('/').rstrip('/')
    if valid_authority and host and path and not any(ord(ch) < 32 or ord(ch) == 127 for ch in path):
        if protocol == 'https':
            https = safe
        elif protocol == 'ssh' and re.fullmatch(r'[\w.-]+|\[[\da-fA-F:.]+\]', host, re.ASCII):
            chunks = re.split(r'(%[\da-fA-F]{2})', path) if uri else [path]
            encoded = ''.join(chunk if i % 2 else quote_from_bytes(os.fsencode(chunk), safe="/!$&'()*+,;=:@")
                              for i, chunk in enumerate(chunks))
            https = f'https://{host}/{encoded}'
    owner, _, repo = path.rpartition('/')
    return dict(protocol=protocol, host=host, owner=owner, repo=repo.removesuffix('.git'), url=safe, https_url=https)


def remote_fields(base, branch, explicit, aliases):
    name = explicit
    if not name and branch:
        name = core.text(base, 'config', '--get', 'branch.' + branch + '.remote', required=False)
    if not name or name == '.' and not explicit:
        name = 'origin'
    url = core.text(base, 'remote', 'get-url', '--', name, required=False)
    if not url and explicit:
        raise core.GitError('requested remote does not exist')
    if not url and name != 'origin':
        name = 'origin'
        url = core.text(base, 'remote', 'get-url', '--', name, required=False)
    return dict(remote=name if url else '', **parse_remote(url, aliases))


def ancestry(base, target):
    chain, hops = [base], []
    while chain[-1].parent != chain[-1]:
        child = chain[-1]
        parent = core.root(child.parent)
        if not parent or parent in chain:
            break
        relative = child.relative_to(parent).as_posix()
        if not any(row['path'] == str(child) and row['availability'] == 'available'
                   for row in inspection.edges(parent, parent, 1)):
            break
        chain.append(parent)
        hops.append(relative)
    chain.reverse()
    hops.reverse()
    outer = chain[0]
    relative = base.relative_to(outer)
    return dict(current=str(base), parent=str(chain[-2]) if hops else '', outermost=str(outer),
                parent_dirname=str(outer.parent), parent_basename=outer.name,
                submodule_prefix=relative.parent.as_posix(), submodule_basename=base.name,
                cwd_prefix=target.relative_to(base).as_posix() if target != base else '',
                path_parent=hops[-1] if hops else '.', path_outermost=relative.as_posix(),
                chain_length=len(chain), chain_repos=list(map(str, chain)), chain_paths=hops, is_submodule=bool(hops))


def scalar(value):
    if isinstance(value, list):
        return '\n'.join(value)
    if isinstance(value, bool):
        return str(value).lower()
    return str(value)


def formatted(template, fields):
    result = []
    for literal, field, spec, conversion in string.Formatter().parse(template):
        result.append(literal)
        if field is not None:
            if spec or conversion or field not in fields:
                raise ValueError('invalid format field')
            result.append(''.join(f'\\x{ord(c):02x}' if ord(c) < 32 or ord(c) == 127 else c for c in scalar(fields[field])))
    return ''.join(result)


def main(argv=None):
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('command', choices=['info', 'path'])
    parser.add_argument('-C', '--directory', default=os.environ.get('DOTS') or str(core.LIB.parents[1]))
    parser.add_argument('--remote')
    parser.add_argument('--no-wiki', action='store_true', help=argparse.SUPPRESS)
    group = parser.add_mutually_exclusive_group()
    for key in REMOTE_FIELDS:
        opts = [option for option, name in SHORTCUTS.items() if name == key]
        if opts:
            group.add_argument(*opts, action='store_const', const=key, dest='field')
    group.add_argument('--get', choices=REMOTE_FIELDS + PATH_FIELDS, dest='field')
    group.add_argument('--list-fields', action='store_true')
    group.add_argument('--json', action='store_true')
    group.add_argument('-f', '--format')
    parser.add_argument('--https', action='store_true')
    parser.add_argument('-n', '--no-newline', action='store_true')
    args = parser.parse_args(argv)
    if args.https:
        if args.format is not None or args.json or args.list_fields or args.field not in (None, 'url', 'https_url'):
            parser.error('--https requires URL output')
        args.field = 'https_url'
    if args.list_fields:
        print(*REMOTE_FIELDS, *PATH_FIELDS, sep='\n')
        return 0
    target = Path(args.directory).resolve()
    try:
        base = inspection.context(target)
    except core.GitError as error:
        if str(error) == 'not inside a Git worktree' and (args.field == 'icon' or args.format is not None):
            return 0
        raise
    fields = {'root': str(base)}
    if args.field in REMOTE_FIELDS[1:] or args.json or args.format is not None or args.remote:
        reader = inspection.Inspection(base)
        branch = core.text(base, 'symbolic-ref', '--quiet', '--short', 'HEAD', required=False)
        fields.update(remote_fields(base, branch, args.remote, reader.aliases))
        fields.update(owned=fields['protocol'] != 'file' and fields['host'] + '/' + fields['owner'] in reader.owners,
                      icon=host_icon(fields['host']))
    if args.field in PATH_FIELDS or args.json or args.format is not None:
        fields.update(ancestry(base, target))
    if args.json:
        output = json.dumps(fields)
    elif args.format is not None:
        try:
            output = formatted(args.format, fields)
        except ValueError as error:
            parser.error(str(error))
    else:
        output = scalar(fields[args.field or 'root'])
    sys.stdout.write(output + ('' if args.no_newline else '\n'))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, core.GitError) as error:
        print('dots git: ' + str(error), file=sys.stderr)
        sys.exit(3)
