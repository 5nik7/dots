"""Home-scoped Linux/WSL cache rules using the guarded POSIX deletion engine."""
from pathlib import Path
import os

from .core import Target, inside, inventory, safe_path, directory_fd
from .termux import Termux, ORDINARY, CHECKPOINTS, LOGS


class Linux:
    supported_groups = ORDINARY
    can_delete = True

    def __init__(self, env=None, platform='linux'):
        if os.name == 'nt':
            raise ValueError('Linux cleanup requires a native POSIX runtime')
        self.platform = platform
        self.env = dict(os.environ if env is None else env)
        self.home = Path(self.env.get('HOME', ''))
        if (not self.home.is_absolute() or self.home == Path(self.home.anchor)
                or '..' in self.home.parts or not self.home.is_dir()
                or self.home.stat().st_uid != os.getuid()):
            raise ValueError('cleanup requires an owned native home directory')
        descriptor = directory_fd(self.home)
        os.close(descriptor)
        self.boundary = self.home
        self.cache = self.location('XDG_CACHE_HOME', self.home/'.cache')
        self.state = self.location('XDG_STATE_HOME', self.home/'.local/state')

    def location(self, key, fallback):
        path = Path(self.env.get(key) or fallback)
        safe_path(path, self.boundary)
        tails = {'XDG_CACHE_HOME': ('cache', '.cache'), 'XDG_STATE_HOME': ('state', '.state'),
                 'GOCACHE': ('go-build',), 'UV_CACHE_DIR': ('uv',),
                 'CARGO_HOME': ('cargo', '.cargo'), 'PIP_CACHE_DIR': ('pip',),
                 'npm_config_cache': ('.npm', 'npm-cache')}
        if key in tails and path.name not in tails[key]:
            raise ValueError('unrecognized cleanup location: ' + key)
        if key == 'GOMODCACHE' and path.parts[-2:] != ('pkg', 'mod'):
            raise ValueError('unrecognized Go module cache location')
        for protected in ('.ssh', '.gnupg', '.codex', '.pi', '.config', '.local/share'):
            if inside(path, self.home/protected):
                raise ValueError('cleanup override enters protected data: ' + key)
        for parent in (path, *path.parents):
            if parent == self.home:
                break
            if os.path.lexists(parent/'.git'):
                raise ValueError('cleanup override enters a project repository: ' + key)
        return path

    def candidates(self, groups, age_days, report=lambda *args: None):
        targets, issues = [], []
        def add(rule, group, path, mode='contents'):
            try:
                target = Target(rule, group, path, mode)
                target.entries = inventory(target, self.boundary)
                if any(name != '.' or mode != 'contents' for name in target.entries):
                    targets.append(target)
            except (OSError, ValueError) as error:
                issues.append(dict(group=group, rule=rule, path=str(path), reason=str(error)))
            report('Scanning ' + rule)
        def located(rule, group, key, fallback, child=None):
            try:
                path = self.location(key, fallback)
                add(rule, group, path/child if child else path)
            except (OSError, ValueError) as error:
                issues.append(dict(group=group, rule=rule, reason=str(error)))
        if 'downloads' in groups:
            located('npm-cache','downloads','npm_config_cache',self.home/'.npm','_cacache')
            located('pip-cache','downloads','PIP_CACHE_DIR',self.cache/'pip')
        if 'builds' in groups:
            for rule, key, fallback in (
                ('go-module-cache','GOMODCACHE',self.home/'go/pkg/mod'),
                ('go-build-cache','GOCACHE',self.cache/'go-build'),
                ('uv-cache','UV_CACHE_DIR',self.cache/'uv')):
                located(rule,'builds',key,fallback)
            located('cargo-registry','builds','CARGO_HOME',self.home/'.cargo','registry')
        if 'logs' in groups:
            for name in LOGS:
                add('nvim-logs','logs',self.state/'nvim'/name,'file')
        for group in groups:
            if group in CHECKPOINTS:
                issues.append(dict(group=group, reason='Checkpoint cleanup is not implemented for ' + self.platform))
        conflicts = {target.path for target in targets for other in targets
                     if target is not other and (inside(target.path, other.path) or inside(other.path, target.path))}
        for target in targets:
            if target.path in conflicts:
                issues.append(dict(group=target.group, rule=target.rule, reason='overlapping cleanup targets'))
        return [target for target in targets if target.path not in conflicts], issues

    def native(self, target):
        # The existing helper contract fixes explicit cache roots, disables
        # downloads/configuration and bounds execution; no shell is involved.
        return Termux.native(self, target)
