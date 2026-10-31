"""Native WinGet boundary: structured discovery and literal, scoped mutations."""
import base64
import json
from pathlib import Path
import re
from .common import Error, Package, query, run, which, clean

MODULE_VERSION = '1.29.380'
NO_APPLICATIONS = 0x8a150014


def powershell():
    executable = which('pwsh.exe') or which('powershell.exe')
    if not executable: raise Error('WinGet needs native PowerShell 5.1 or 7')
    return executable


def bridge_command(action, **values):
    payload = base64.b64encode(json.dumps(dict(action=action, **values)).encode()).decode('ascii')
    return [powershell(), '-NoLogo', '-NoProfile', '-NonInteractive', '-File',
            str(Path(__file__).with_suffix('.ps1')), payload]


def bridge(action, **values):
    value = json.loads(run(bridge_command(action, **values)).lstrip('\ufeff'))
    if not isinstance(value, dict) or value.get('schema') != 1:
        raise Error('unsupported WinGet bridge response')
    return value


def exact_id(name):
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.+-]{0,255}', name):
        raise Error('WinGet requires an exact community package ID: '+clean(name))
    return name


class WinGetBackend:
    name = 'winget'
    global_scope = False
    termux = False
    remote_inventory = True

    def __init__(self, scope='user'):
        if scope not in ('user', 'machine'): raise Error('WinGet scope must be user or machine')
        self.install_scope = scope
        self.scope = 'WinGet community · '+scope
        self.cache_key = 'winget|community|'+scope
        self.bin = which('winget.exe') or 'winget.exe'
        self._rows = None

    def probe_scope(self, name, scope):
        # Exit status proves an exact match. Never parse localized display tables.
        result = query([self.bin, 'list', '--id', name, '--exact', '--source', 'winget',
                        '--scope', scope, '--disable-interactivity'])
        if result.returncode == 0: return True
        if result.returncode & 0xffffffff == NO_APPLICATIONS: return False
        raise Error('WinGet scope query failed: '+clean(result.stderr or result.stdout)[-600:])

    def installed(self):
        if self._rows is not None: return self._rows
        data = bridge('installed')['packages']
        counts = {}
        for row in data: counts[row['id'].casefold()] = counts.get(row['id'].casefold(), 0)+1
        rows = []
        for row in data:
            name, version = row['id'], row['installed_version']
            reason = ''
            scope = 'unknown'
            if row['source'] != 'winget' or name.startswith(('ARP\\', 'MSIX\\')):
                reason = 'not correlated to the WinGet community source'
            elif counts[name.casefold()] != 1:
                reason = 'multiple installed records; scope/version is ambiguous'
            else:
                exact_id(name)
                matches = [s for s in ('user', 'machine') if self.probe_scope(name, s)]
                if len(matches) == 1: scope = matches[0]
                else: reason = 'installation scope is ambiguous or unavailable'
            if scope not in ('unknown', self.install_scope): continue
            if not version or version.casefold() == 'unknown': reason = reason or 'installed version unavailable'
            rows.append(Package(name, row['version'], row['name'], True, version, repo=row['source'],
                details=dict(scope=scope, disabled_reason=reason, update_available=row['update_available'])))
        self._rows = rows
        return rows

    def inventory(self, query='', offline=False):
        if offline or not query: return []
        return [self.package(row) for row in bridge('search', query=query)['packages']]

    @staticmethod
    def package(row):
        if row['source'] != 'winget': raise Error('WinGet returned an unexpected source')
        return Package(exact_id(row['id']), row['version'], row['name'], repo='winget',
                       details=dict(versions=row['versions']))

    def info(self, package):
        rows = bridge('info', id=exact_id(package.name))['packages']
        if len(rows) != 1: raise Error('WinGet exact ID is unavailable or ambiguous: '+package.name)
        value = self.package(rows[0])
        value.installed, value.installed_version = package.installed, package.installed_version
        value.details.update(package.details)
        return value

    def transaction(self, action, names, yes=False):
        if action == 'refresh':
            self.revalidate()
            return [self.bin, 'source', 'update', '--name', 'winget', '--disable-interactivity']
        if action not in ('install', 'uninstall', 'upgrade') or len(names) != 1:
            raise Error('WinGet transactions require one exact ID')
        name = exact_id(names[0])
        if self.install_scope == 'machine':
            import os
            if os.name == 'nt':
                import ctypes
                if not ctypes.windll.shell32.IsUserAnAdmin():
                    raise Error('WinGet machine scope requires an already elevated shell; pkgs does not elevate')
        if action in ('uninstall', 'upgrade'):
            candidates = [p for p in self.installed() if p.name.casefold() == name.casefold()]
            if len(candidates) != 1 or candidates[0].details['disabled_reason']:
                raise Error('WinGet package is not uniquely owned by the selected scope: '+name)
            name = candidates[0].name
        else:
            package = self.info(Package(name))
            name = package.name
            pin = getattr(self, 'pins', {}).get(names[0])
            if pin and pin not in package.details['versions']:
                raise Error('WinGet exact version is unavailable: '+name+' '+pin)
        command = [self.bin, action, '--id', name, '--exact', '--scope', self.install_scope,
                   '--source', 'winget', '--disable-interactivity']
        pin = getattr(self, 'pins', {}).get(names[0])
        if pin: command += ['--version', pin]
        if yes and action in ('install', 'upgrade'): command += ['--accept-package-agreements']
        # Source trust, elevation, reboot, force and hash bypass are never implied.
        return command

    def revalidate(self):
        if bridge('capabilities').get('missing'):
            raise Error('Microsoft.WinGet.Client is required for native package operations')

    def database_fingerprint(self): return None
    def owner(self, path): return None
    def owners(self, paths): return {path: None for path in paths}
