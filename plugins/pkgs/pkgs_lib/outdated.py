"""Read-only update queries. Never execute transactions or configured recipes."""
import json
import re
import sys
import tempfile

from .common import Error, budget, clean, query, validate_names
from .detect import SYSTEM, available
from . import policies, scopes, workflows


def fetch(argv, *, allowed=(0,), env=None, cwd=None):
    result = query(argv, env=env, cwd=cwd)
    if result.returncode not in allowed or result.returncode and result.stderr.strip() and not result.stdout.strip():
        raise Error(clean(result.stderr or result.stdout)[-600:] or f'query exited {result.returncode}')
    return result.stdout


def semver(value):
    """Go module versions use SemVer, including pseudo-version prereleases."""
    if not isinstance(value, str): raise Error('invalid Go module version metadata')
    match = re.fullmatch(r'v(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?', value)
    if not match: raise Error('unrecognized Go module version: '+clean(value))
    pre = match[4]
    return (*map(int, match.group(1, 2, 3)), pre is None,
            tuple((0, int(p)) if p.isdigit() else (1, p) for p in (pre or '').split('.')))


def candidates(backend, installed):
    """Return name/current/candidate records from a manager's native query."""
    manager = backend.name
    rows = []
    current = {p.name: p.installed_version or p.version for p in installed}
    def add(name, old, new):
        if not all(isinstance(v, str) and v for v in (name, old, new)):
            raise Error('incomplete update metadata')
        if old != new: rows.append(dict(name=name, current=old, candidate=new))
    if manager == 'winget':
        for package in installed:
            if package.details.get('update_available'):
                add(package.name, package.installed_version, package.version)
    elif manager == 'npm':
        # Explicit names avoid querying policy-skipped aliases as registry names.
        data = json.loads(fetch(['npm','outdated','--json', *(['--global'] if backend.global_scope else []),
                                 '--', *current], allowed=(0, 1)))
        if not isinstance(data, dict) or 'error' in data: raise Error('npm outdated failed: '+clean(data)[:600])
        for name, item in data.items(): add(name, item['current'], item['wanted'])
    elif manager == 'pip':
        data = json.loads(fetch([sys.executable,'-m','pip','list','--outdated','--format=json','--disable-pip-version-check']))
        for item in data: add(item['name'], item['version'], item['latest_version'])
    elif manager == 'go':
        latest = {}
        # Explicit module queries run outside the user's project and cannot
        # download a toolchain or edit go.mod/go.sum in the working directory.
        with tempfile.TemporaryDirectory(prefix='pkgs-go-query-') as directory:
            for package in installed:
                module = package.details.get('module')
                if not module: raise Error('Go module identity unavailable for '+package.name)
                validate_names([module], 'go')
                if module not in latest:
                    data = json.loads(fetch(['go','list','-m','-json',module+'@latest'], cwd=directory,
                                            env={'GOTOOLCHAIN':'local','GOWORK':'off','GO111MODULE':'on','GOFLAGS':''}))
                    if not isinstance(data, dict) or not isinstance(data.get('Version'), str):
                        raise Error('Go update version unavailable for '+module)
                    latest[module] = data['Version']
                version = latest[module]
                if semver(version) > semver(current[package.name]): add(package.name, current[package.name], version)
    else:
        commands = {
            'apt': ['apt','list','--upgradable'],
            'pacman': ['pacman','-Qu'], 'paru': ['paru','-Qu'], 'yay': ['yay','-Qu'],
            'dnf': [backend.bin,'-q','--cacheonly','repoquery','--upgrades','--qf','%{name}.%{arch}\t%{version}-%{release}'],
            'xbps': ['xbps-install','-un'],
            'uv-tool': ['uv','tool','list','--outdated','--color','never','--no-progress'],
            'gem': ['gem','outdated'],
        }
        text = fetch(commands[manager], env=getattr(backend,'operation_env',None),
                     allowed=(0, 1) if manager in ('pacman','paru','yay') else (0,))
        for line in text.splitlines():
            line = line.strip()
            if not line: continue
            if manager == 'apt':
                if line.startswith('Listing...'): continue
                match = re.fullmatch(r'(\S+?)/\S+\s+(\S+)\s+\S+\s+\[upgradable from: (.+)\]', line)
                if not match: raise Error('unrecognized apt update row: '+clean(line))
                add(match[1], match[3], match[2])
            elif manager in ('pacman','paru','yay'):
                match = re.fullmatch(r'(\S+)\s+(\S+)\s+->\s+(\S+)(?:\s+\[ignored\])?', line)
                if not match: raise Error('unrecognized update row: '+clean(line))
                if not line.endswith('[ignored]'): add(*match.groups())
            elif manager == 'dnf':
                name, new = line.split('\t')
                if name in current: add(name, current[name], new)
            elif manager == 'xbps':
                fields = line.split()
                if len(fields) != 6: raise Error('unrecognized XBPS dry-run row: '+clean(line))
                if fields[1] != 'update': continue
                name, _, new = fields[0].rpartition('-')
                if name in current: add(name, current[name], new)
            elif manager == 'uv-tool':
                if line.startswith('- '): continue  # Executable names, not packages.
                match = re.fullmatch(r'(\S+) v(\S+) \[latest: ([^\]]+)\]', line)
                if not match: raise Error('unrecognized uv update row: '+clean(line))
                add(*match.groups())
            elif manager == 'gem':
                match = re.fullmatch(r'(\S+) \((\S+) < (\S+)\)', line)
                if not match: raise Error('unrecognized RubyGems update row: '+clean(line))
                add(*match.groups())
    return rows


def inspect(backend, args, cfg, *, bulk=False):
    inventory = scopes.inventory(backend, owned=backend.name == 'pip' and bulk)
    names = validate_names(args.names, backend.name)
    selected = {policies.identity(n, backend.name) for n in names}
    identities = lambda p: {policies.identity(p.name, backend.name), p.details.get('binary', '')} | (
        {p.name.partition(':')[0]} if backend.name == 'apt' else set())
    known = set().union(*(identities(p) for p, _, _ in inventory))
    if selected - known: raise Error('Not installed in selected scope: '+', '.join(sorted(selected-known)))
    eligible, skipped = [], []
    skip = {policies.identity(n, backend.name) for n in cfg.get('policies',{}).get(backend.name,{}).get('skip',[])}
    for package, _, reason in inventory:
        ident = policies.identity(package.name, backend.name)
        if selected and not selected.intersection(identities(package)): continue
        if ident in skip and not args.ignore_skip: reason = 'skipped by policy'
        if reason: skipped.append(dict(package=package.name, reason=reason))
        else: eligible.append(package)
    rows = candidates(backend, eligible) if eligible else []
    ids = {policies.identity(p.name, backend.name) for p in eligible}
    # APT list may omit the native architecture suffix from dpkg identities.
    if backend.name == 'apt': ids |= {n.partition(':')[0] for n in ids}
    rows = [r for r in rows if policies.identity(r['name'], backend.name) in ids]
    rows.sort(key=lambda p: p['name'].casefold())
    return dict(manager=backend.name, scope=scopes.scope_id(backend), packages=rows,
                skipped=skipped, error='', status='ok')


def display(group, cfg):
    from .reports import report
    ui = report(explicit=cfg.get('_explicit_color'), fallback=cfg.get('color','auto'))
    manager = group['manager']
    title = manager+' · '+group['scope']
    status = 'unavailable' if group['error'] else str(len(group['packages']))+' upgradable' if group['packages'] else 'up to date'
    if group['skipped']: status += ' · '+str(len(group['skipped']))+' skipped'
    if ui: ui.row([(manager, 'identity'), (' · '+group['scope']+' · ', 'muted'),
                   (status, 'error' if group['error'] else 'value')])
    else: print('  '+title+' · '+status)
    for row in group['packages']:
        value = row['name']+'  '+row['current']+' → '+row['candidate']
        if ui: ui.row([(value, 'value')], indent=4)
        else: print('    '+clean(value))
    if group['error']:
        if ui: ui.row([(group['error'], 'error')], indent=4)
        else: print('    '+clean(group['error']))


def cli(args, cfg):
    if args.query: raise Error('upgrade --list does not accept --query')
    bulk = args.manager in (None, 'auto') and not args.names
    if bulk and args.global_scope: raise Error('--global requires --manager npm')
    if args.global_scope and args.manager != 'npm': raise Error('--global requires --manager npm')
    if bulk:
        with budget(45): selection = scopes.bulk(cfg)
    else:
        from .cli import choose_manager
        with budget(45): backend = choose_manager(args, cfg)
        selection = [(backend.name, scopes.scope_id(backend))]
    groups = []
    if not args.json:
        from .reports import report
        ui = report(explicit=cfg.get('_explicit_color'), fallback=cfg.get('color','auto'))
        if ui: ui.heading('Upgradable packages')
        else: print('Upgradable packages')
    for manager, scope in selection:
        try:
            with budget(45), workflows.progress('Checking updates · '+manager, cfg):
                if not available(manager): raise Error('manager unavailable')
                backend = scopes.make(manager, scope)
                group = inspect(backend, args, cfg, bulk=bulk)
        except (Error, OSError, ValueError, KeyError, TypeError) as error:
            fallback_scope = scope or ('system' if manager in SYSTEM else 'base' if manager == 'pip' else 'tools')
            group = dict(manager=manager, scope=fallback_scope,
                         packages=[], skipped=[], error=clean(error)[:600], status='error')
        groups.append(group)
        if not args.json: display(group, cfg)
    if args.json: print(json.dumps(dict(schema=1, groups=groups), indent=2, ensure_ascii=False))
    elif not groups: print('  No supported managers selected.')
    return int(any(g['error'] for g in groups))
