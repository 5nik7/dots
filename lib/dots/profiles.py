"""Literal platform profiles: inspection never executes profile code."""
import argparse
import json
import os
from pathlib import Path
import re
import sys
from platform_info import detect

PLATFORMS = ('linux', 'wsl', 'termux', 'windows')
IDENTITY = re.compile(r'(?:linux|wsl|termux|windows)(?:/[a-z0-9][a-z0-9_.-]*)?\Z')
SENSITIVE = re.compile(r'(?:TOKEN|PASSWORD|PASSWD|SECRET|CREDENTIAL|PRIVATE_KEY|API_KEY)', re.I)
DIRECTORIES = ('config', 'bin', 'scripts', 'lib', 'shells', 'docs', 'skills', 'fonts')


def directory(root, identity):
    if not IDENTITY.fullmatch(identity): raise ValueError('invalid profile identity')
    parts = identity.split('/')
    path = Path(root) / 'profiles' / parts[0]
    if len(parts) == 2 and parts[0] not in ('linux','wsl'): raise ValueError('distro profiles require Linux or WSL')
    if len(parts) == 2: path = path / 'distros' / parts[1]
    if not path.resolve().is_relative_to(Path(root).resolve()): raise ValueError('profile escapes checkout')
    return path


def definition(root, identity, data=None):
    path = directory(root, identity) / 'profile.json'
    if not path.is_file(): return None
    if not path.resolve().is_relative_to(Path(root).resolve()): raise ValueError('profile manifest escapes checkout')
    if data is None:
        if path.is_symlink() or path.stat().st_size > 4 * 1024 * 1024:
            raise ValueError('profile manifest must be a bounded regular file')
        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result: raise ValueError('duplicate profile field: ' + key)
                result[key] = value
            return result
        data = json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique)
    if not isinstance(data, dict): raise ValueError('profile manifest must be an object')
    if data.get('schema') != 1 or data.get('id') != identity: raise ValueError('invalid profile manifest: ' + identity)
    if set(data) - {'schema', 'id', 'description', 'extends', 'environment', 'path', 'replaces_commands', 'settings', 'files', 'alias'}:
        raise ValueError('unknown profile field: ' + identity)
    if 'alias' in data and (not isinstance(data['alias'], str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', data['alias'])):
        raise ValueError('profile alias must be a shell identifier')
    if not isinstance(data.get('description', ''), str): raise ValueError('profile description must be a string')
    if not isinstance(data.get('extends', []), list): raise ValueError('profile extends must be a list')
    for parent in data.get('extends', []):
        if not isinstance(parent, str) or not IDENTITY.fullmatch(parent): raise ValueError('invalid parent profile')
        owner = identity.split('/')[0]
        if parent.split('/')[0] not in ({'wsl','linux'} if owner == 'wsl' else {owner}): raise ValueError('parent crosses platform boundary')
    if not isinstance(data.get('environment', {}), dict): raise ValueError('profile environment must be an object')
    from profile_config import validate_settings
    validate_settings(data.get('settings', {}))
    files = data.get('files', {})
    if not isinstance(files, dict) or any(not re.fullmatch(r'[a-z][a-z0-9_-]*', key) or not isinstance(rows, list) for key, rows in files.items()):
        raise ValueError('profile files must map repository IDs to resource lists')
    for field in ('path', 'replaces_commands'):
        if field in data and (not isinstance(data[field], list) or any(not isinstance(v, str) for v in data[field])): raise ValueError('profile ' + field + ' must be a string list')
    for key, value in data.get('environment', {}).items():
        if key in ('DOTRUBY','RUBYCOMP','DOTS','DOTBIN','DOTSCRIPTS','DOTFILES','DOTCONFIG','DOTSHHHH','SHELLS','ZSH','PWSH','DOTHEMES','THEMES','PATH','DOTS_PLATFORM','DOTS_PROFILE','DOTS_PROFILE_CHECKOUT','DOTS_PROFILE_BIN_PATHS','DOTS_PROFILE_PATHS','DOTS_PROFILE_LAYERS','DOTS_DISTRO','DOTS_ARCH','DOTS_RUNTIME') or not re.fullmatch(r'[A-Z][A-Z0-9_]*', key) or not isinstance(value, str) or '\x00' in value:
            raise ValueError('invalid profile environment declaration')
    for relative in data.get('path', ['bin', 'scripts']):
        p = Path(relative)
        if p.is_absolute() or '..' in p.parts or not (path.parent / p).resolve().is_relative_to(path.parent.resolve()):
            raise ValueError('profile path escapes profile')
    for command in data.get('replaces_commands', []):
        if not re.fullmatch(r'[a-z][a-z0-9]*(?:-[a-z][a-z0-9]*)*', command): raise ValueError('invalid command replacement')
    return dict(data, root=str(path.parent))


def resolve(root, facts=None):
    facts = detect() if facts is None else facts
    layers, visiting, loaded = [], set(), set()
    def add(identity, required=False):
        if identity in visiting: raise ValueError('profile inheritance cycle: ' + identity)
        if identity in loaded: return
        row = definition(root, identity)
        if row is None:
            if required: raise ValueError('missing parent profile: ' + identity)
            return
        visiting.add(identity)
        for parent in row.get('extends', []): add(parent, True)
        visiting.remove(identity)
        loaded.add(identity)
        layers.append(row)
    platforms = ['linux', 'wsl'] if facts['platform'] == 'wsl' else [facts['platform']]
    for selected in platforms:
        add(selected)
        if selected in ('linux', 'wsl'):
            # An exact definition may explicitly inherit a family definition.
            for distro in (facts['distro'], *facts.get('family', [])):
                identity = selected + '/' + distro
                if definition(root, identity):
                    add(identity)
                    break
    current = layers[-1]['id'] if layers else facts['platform']
    return dict(version=1, facts=facts, current=current, layers=layers)


def available(root):
    rows = []
    for selected in PLATFORMS:
        base = definition(root, selected)
        if base: rows.append(base)
        path = Path(root) / 'profiles' / selected / 'distros'
        if path.is_dir():
            for child in sorted(path.iterdir()):
                if child.is_dir() and IDENTITY.fullmatch(selected + '/' + child.name):
                    row = definition(root, selected + '/' + child.name)
                    if row: rows.append(row)
    # Validate even inactive inheritance without executing anything.
    by_id = {row['id']: row for row in rows}
    def visit(identity, stack):
        if identity in stack: raise ValueError('profile inheritance cycle: ' + identity)
        if identity not in by_id: raise ValueError('missing parent profile: ' + identity)
        for parent in by_id[identity].get('extends', []): visit(parent, stack | {identity})
    for identity in by_id: visit(identity, set())
    return rows


def public_report(value):
    """Redact credential declarations in reports without changing resolver data."""
    if isinstance(value, list): return [public_report(row) for row in value]
    if not isinstance(value, dict): return value
    result = {key: public_report(item) for key, item in value.items()}
    if isinstance(value.get('environment'), dict):
        result['environment'] = {key: '[redacted]' if SENSITIVE.search(key) or any(SENSITIVE.search(name) for name in re.findall(r'\$\{([A-Z][A-Z0-9_]*)\}', template)) else template for key, template in value['environment'].items()}
    return result


def command_roots(root, facts=None):
    return [Path(row['root']) / 'bin' for row in reversed(resolve(root, facts)['layers']) if (Path(row['root']) / 'bin').is_dir()]


def replaces(path, stem):
    manifest = Path(path).parent.parent / 'profile.json'
    if not manifest.is_file(): return False
    data = json.loads(manifest.read_text())
    return stem in data.get('replaces_commands', [])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    if argv is None: argv = sys.argv[1:]
    if argv and argv[0] == '__roots':
        root = Path(os.environ.get('DOTS') or Path(__file__).resolve().parents[2]).resolve()
        for path in command_roots(root): print(path)
        return
    if argv and argv[0] == '__replaces':
        sys.exit(0 if len(argv) == 3 and replaces(argv[1], argv[2]) else 1)
    if argv == ['__names']:
        for row in available(Path(os.environ.get('DOTS') or Path(__file__).resolve().parents[2]).resolve()): print(row['id'])
        return 0
    from profile_views import main as views
    return views(argv)


if __name__ == '__main__':
    try: sys.exit(main())
    except (ValueError, OSError) as error:
        print('dots profile: ' + str(error), file=sys.stderr); sys.exit(2)
