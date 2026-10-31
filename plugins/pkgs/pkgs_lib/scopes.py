"""User-wide manager selection and local inventory evidence."""
import json
import os
import re
from pathlib import Path
import sys
from .backends import Backend
from .common import Error, Package, run, query
from .detect import SYSTEM, available, default_manager, termux
from .policies import identity


def scope_id(backend):
    if backend.name in SYSTEM: return 'system'
    if backend.name == 'npm': return 'global' if backend.global_scope else 'project'
    if backend.name == 'pip': return 'venv' if sys.prefix != sys.base_prefix or os.environ.get('VIRTUAL_ENV') else 'base'
    if backend.name == 'gem': return 'user' if getattr(backend, 'operation_env', None) else 'active'
    return 'tools'


def make(manager, scope=None):
    backend = Backend(manager, manager == 'npm' and scope == 'global')
    if manager == 'gem' and scope == 'user':
        path = run(['ruby', '-rrubygems', '-e', 'print Gem.user_dir']).strip()
        if not path or not Path(path).is_absolute(): raise Error('RubyGems user directory is unavailable')
        backend.operation_env = {'GEM_HOME': path, 'GEM_PATH': path}
        backend.scope = 'RubyGems user ' + path
        backend.cache_key += '|user|'+path
    if manager == 'go': backend.scope = 'Go installed tools'
    return backend


def bulk(cfg):
    requested = cfg.get('upgrade', {}).get('managers', 'auto')
    if requested == 'auto':
        requested = []
        try:
            system = default_manager()
            preferred = cfg.get('manager')
            if system == 'pacman' and not termux():
                system = preferred if preferred in ('paru','yay') and available(preferred) else next(
                    (m for m in ('paru','yay') if available(m)), 'pacman')
            requested.append(system)
        except Error: pass
        requested += [m for m in ('npm','uv-tool','pip','gem','go') if available(m)]
    seen, result = set(), []
    for manager in sorted(requested, key=lambda m: 0 if m in SYSTEM else 1):
        database = 'pacman' if manager in ('pacman','paru','yay') else manager
        if database in seen: continue
        seen.add(database)
        if manager == 'pip' and (sys.prefix != sys.base_prefix or os.environ.get('VIRTUAL_ENV')): continue
        if manager == 'gem' and os.environ.get('BUNDLE_GEMFILE'): continue
        # Delay scope probing so a failure stays isolated to this manager.
        result.append((manager, 'global' if manager == 'npm' else 'user' if manager == 'gem' else None))
    return result


def pip_rows(backend, *, roots=False, owned=False):
    result = query([sys.executable, '-m', 'pip', 'inspect', '--local'])
    if result.returncode:
        if owned: raise Error('pip ownership requires pip inspect; select explicit packages or update pip separately')
        return [(p, 'inferred', '') for p in backend.installed()]
    data = json.loads(result.stdout)
    if data.get('version') != '1': raise Error('unsupported pip inspect schema')
    items = [item for item in data['installed'] if not (roots and item.get('requested') is False)]
    system = None
    if owned:
        try: system = Backend(default_manager())
        except Error: pass
    targets = {}
    if system:
        for item in items:
            location = item.get('metadata_location')
            if item.get('installer') != 'pip' or item.get('direct_url') or not location: continue
            root = Path(location)
            target = root if root.is_file() else next((root/n for n in ('METADATA','PKG-INFO','INSTALLER') if (root/n).is_file()), None)
            if target is not None: targets[location] = str(target)
    owners = system.owners(targets.values()) if system else {}
    rows = []
    for item in items:
        meta = item['metadata']
        p = Package(meta['name'], meta['version'], installed=True, installed_version=meta['version'])
        reason = ''
        if item.get('direct_url'): reason = 'source or editable install; retain original source'
        if owned:
            if item.get('installer') != 'pip': reason = 'not proven pip-owned'
            location = item.get('metadata_location')
            if not location: reason = 'ownership location unavailable'
            elif system and not reason:
                # INSTALLER can be pip-authored even inside a distro package.
                # Query its actual distribution metadata, not an absent marker.
                owner = owners.get(targets.get(location))
                if owner is None: reason = 'system ownership could not be checked'
                elif owner: reason = 'owned by the system package manager'
        rows.append((p, 'explicit' if item.get('requested') is True else 'inferred', reason))
    return rows


def gem_versions(rows):
    for p in rows:
        versions = p.details.get('versions') or re.findall(r'(?:^|,\s*)(?:default:\s*)?([0-9][^,\s]*)', p.installed_version)
        p.details['versions'] = versions
        if p.installed_version not in versions: p.installed_version = versions[0] if versions else ''
    return rows


def inventory(backend, *, roots=False, owned=False, portable=False):
    if backend.name == 'pip': return pip_rows(backend, roots=roots, owned=owned)
    rows = backend.installed()
    if backend.name == 'gem': rows = gem_versions(rows)
    if backend.name == 'uv-tool' and portable:
        result = query(['uv','tool','list','--show-version-specifiers','--show-extras','--show-with'])
        metadata = {line.split(' ',1)[0]: line for line in result.stdout.splitlines() if re.match(r'^\S+ v\S+',line)}
        for p in rows:
            line = metadata.get(p.name, '')
            reason = ('tool requirements unavailable; review restore identity' if result.returncode or not line else
                      'source, extras or additional requirements need an explicit recipe' if
                      '[extras:' in line or '[with:' in line or re.search(r'\[required:\s*(?:@|/|file:|git\+|https?:)',line) else '')
            p.details['disabled_reason'] = reason
        return [(p,'explicit',p.details['disabled_reason']) for p in rows]
    if backend.name in ('go','npm'):
        return [(p, 'explicit' if roots or backend.name == 'go' else 'all', p.details.get('disabled_reason', '')) for p in rows]
    if not roots: return [(p, 'all', '') for p in rows]
    n = backend.name
    commands = {'apt': ['apt-mark','showmanual'], 'pacman': ['pacman','-Qqe'],
                'paru': ['pacman','-Qqe'], 'yay': ['pacman','-Qqe'],
                'dnf': [backend.bin,'-q','--cacheonly','repoquery','--userinstalled','--qf','%{name}'],
                'xbps': ['xbps-query','-m']}
    if n in commands:
        try:
            explicit = set(run(commands[n]).splitlines())
            if n == 'xbps': explicit = {s.rpartition('-')[0] for s in explicit}
            return [(p, 'explicit', '') for p in rows if p.name in explicit or p.name.partition(':')[0] in explicit
                    or n == 'dnf' and p.name.rpartition('.')[0] in explicit]
        except Error:
            return [(p, 'inferred', '') for p in rows]
    # npm depth=0 and uv tool list already identify requested roots. RubyGems
    # lacks durable install-reason evidence, so retain its scope for editing.
    return [(p, 'explicit' if n in ('npm','uv-tool') else 'inferred', '') for p in rows]
