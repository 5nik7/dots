"""Go build metadata is identity evidence; binaries themselves are never executed."""
import json
import os
import re
from pathlib import Path
from .common import Error, Package, query, validate_names, remaining


def local(args):
    result = query(['go', *args], env={'GOTOOLCHAIN': 'local', 'GOWORK': 'off', 'GO111MODULE': 'off'})
    if result.returncode: raise Error('Go metadata query failed: ' + result.stderr.strip())
    return result.stdout


def directory():
    env = json.loads(local(['env', '-json', 'GOBIN', 'GOPATH']))
    value = env.get('GOBIN') or str(Path(env['GOPATH'].split(os.pathsep)[0]) / 'bin')
    return Path(value).resolve()


def installed():
    root = directory()
    if not root.is_dir(): return []
    rows = []
    for path in sorted(root.iterdir()):
        remaining()
        if not path.is_file() or path.is_symlink(): continue
        try: text = local(['version', '-m', str(path)])
        except Error: continue  # Non-Go files are not owned by this adapter.
        package, version, module, source = '', '', '', False
        for line in text.splitlines()[1:]:
            fields = line.strip().split('\t')
            if fields[0] == 'path' and len(fields) > 1: package = fields[1]
            elif fields[0] == 'mod' and len(fields) > 2: module, version = fields[1:3]
            elif fields[0] == '=>' or fields[0] == 'build' and len(fields)>1 and fields[1].startswith('vcs.'):
                source = True
        if not package: continue
        reason = ('local development build or replaced module' if source or version in ('', '(devel)') or
                  package == 'command-line-arguments' else '')
        canonical = re.sub(r'/v[2-9][0-9]*$', '', package).rsplit('/', 1)[-1]
        if path.name != canonical or path.name.startswith('-'):
            reason = 'renamed Go binary; reinstall its canonical command explicitly'
        try: validate_names([package], 'go')
        except Error: reason = 'unrecoverable Go install identity'
        rows.append(Package(package, version, installed=True, installed_version=version,
                            details={'binary': path.name, 'binary_path': str(path), 'module': module, 'disabled_reason': reason}))
    for p in rows:
        if sum(other.name == p.name for other in rows) > 1:
            p.details['disabled_reason'] = 'multiple binaries have this Go identity; select a unique installation'
    return rows


def select(names, rows):
    selected = []
    for name in names:
        matches = [p for p in rows if name in (p.name, p.details['binary'])]
        if len(matches) != 1: raise Error('Unknown or ambiguous installed Go tool: ' + name)
        p = matches[0]
        if p.details['disabled_reason']: raise Error(name+': '+p.details['disabled_reason'])
        selected.append(p)
    return selected


def transactions(action, names, flags=(), rows=None):
    if action == 'install':
        result = []
        for name in validate_names(names, 'go'):
            if '/' not in name: raise Error('Go install requires a full module package path')
            result.append(['go', 'install', *flags, name if '@' in name else name+'@latest'])
        return result
    if action != 'upgrade': raise Error('Go supports install, upgrade and installed inventory; no removal or registry search')
    selected = select(names, installed() if rows is None else rows)
    return [['go', 'install', *flags, p.name+'@latest'] for p in selected]
