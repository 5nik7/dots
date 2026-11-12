"""Trusted Termux rules. No arbitrary paths, plugins, downloads or shell evaluation."""
from pathlib import Path
import json
import os
import selectors
import shutil
import signal
import stat
import subprocess
import time

from .core import Target, inside, inventory, safe_path

GROUPS = {
    'downloads': ('Downloaded packages', 'low', 'npm, pip and cached APT installers'),
    'builds': ('Build and dependency caches', 'low', 'Go, Cargo and uv; future builds may download dependencies'),
    'logs': ('Build leftovers and diagnostics', 'moderate', 'CPAN builds and named Neovim diagnostic logs; diagnostic history is lost'),
    'project-checkpoints': ('Project checkpoints', 'high', 'Permanently loses saved project versions and rollback points'),
    'sensitive-checkpoints': ('Sensitive checkpoints', 'high', 'Includes backed-up authentication, configuration or history'),
    'unclassified-checkpoints': ('Unclassified checkpoints', 'high', 'Original scope is uncertain; may contain recoverable or sensitive data'),
}
ORDINARY = tuple(list(GROUPS)[:3])
CHECKPOINTS = tuple(list(GROUPS)[3:])
LOGS = ('log', 'mason.log', 'lsp.log', 'conform.log', 'nvim.log', 'luasnip.log', 'noice.log')


def command(argv, env, cwd, timeout=120, limit=1024 * 1024):
    """Bound time/output and terminate only our own child process group."""
    child = subprocess.Popen(argv, env=env, cwd=cwd, stdin=subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
    output = bytearray()
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(child.stdout, selectors.EVENT_READ)
            deadline = time.monotonic() + timeout
            while selector.get_map():
                if time.monotonic() >= deadline:
                    raise ValueError('cleanup helper timed out')
                for key, _ in selector.select(min(.1, max(0, deadline - time.monotonic()))):
                    part = os.read(key.fileobj.fileno(), 65536)
                    if not part:
                        selector.unregister(key.fileobj)
                    else:
                        output.extend(part)
                        if len(output) > limit:
                            raise ValueError('cleanup helper exceeded output limit')
            try:
                child.wait(timeout=max(.01, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                raise ValueError('cleanup helper timed out') from None
        if child.returncode:
            raise ValueError('helper failed (' + str(child.returncode) + '): ' + output.decode(errors='replace')[-1000:])
        return bytes(output)
    finally:
        if child.poll() is None:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            child.wait()
        child.stdout.close()


class Termux:
    def __init__(self, env=None):
        self.env = dict(os.environ if env is None else env)
        self.prefix = Path(self.env.get('TERMUX__PREFIX') or self.env.get('PREFIX', ''))
        if not self.prefix.is_absolute() or self.prefix.parts[-3:] != ('com.termux', 'files', 'usr'):
            raise ValueError('cleanup requires a validated Termux application prefix')
        self.boundary = self.prefix.parent.parent
        self.home = Path(self.env.get('HOME', str(self.prefix.parent / 'home')))
        safe_path(self.home, self.boundary)
        self.cache = self.location('XDG_CACHE_HOME', self.home / '.cache')
        self.state = self.location('XDG_STATE_HOME', self.home / '.local/state')
        self.checkpoints = self.home / '.pi/agent/ayu/checkpoints/sessions'

    def location(self, key, fallback):
        value = self.env.get(key) or str(fallback)
        path = Path(value)
        safe_path(path, self.boundary)
        if path in (self.home, self.prefix, self.prefix.parent) or inside(path, self.prefix):
            raise ValueError('unsafe cleanup location override: ' + key)
        for protected in (self.home / '.ssh', self.home / '.gnupg', self.home / '.codex', self.home / '.pi'):
            if inside(path, protected):
                raise ValueError('cleanup override enters protected application data: ' + key)
        tails = {'GOMODCACHE': ('pkg','mod'), 'GOCACHE': ('go-build',), 'UV_CACHE_DIR': ('uv',)}
        if key in tails and path.parts[-len(tails[key]):] != tails[key]:
            raise ValueError('cleanup override has an unrecognized cache layout: ' + key)
        if key == 'CARGO_HOME' and path.name not in ('cargo', '.cargo'):
            raise ValueError('cleanup override has an unrecognized Cargo layout')
        for parent in (path, *path.parents):
            if parent == self.home or not inside(parent, self.boundary): break
            if os.path.lexists(parent / '.git'):
                raise ValueError('cleanup override enters a project repository: ' + key)
        return path

    def candidates(self, groups, age_days, report=lambda *args: None):
        targets, issues = [], []

        def add(rule, group, path, mode='contents'):
            target = Target(rule, group, Path(path), mode)
            try:
                safe_path(target.path, self.boundary)
                if not os.path.lexists(target.path):
                    return
                target.entries = inventory(target, self.boundary)
                useful = {k: v for k, v in target.entries.items() if mode != 'contents' or k != '.'}
                if useful:
                    targets.append(target)
            except (ValueError, OSError) as error:
                issues.append(dict(group=group, rule=rule, path=str(path), reason=str(error)))
            report('Scanning ' + rule)

        if 'downloads' in groups:
            add('npm-cache', 'downloads', self.home / '.npm/_cacache')
            add('pip-cache', 'downloads', self.cache / 'pip')
            apt = self.boundary / 'cache/apt/archives'
            try:
                safe_path(apt, self.boundary)
                if apt.is_dir():
                    for path in sorted(apt.glob('*.deb')):
                        add('apt-archives', 'downloads', path, 'file')
            except (ValueError, OSError) as error:
                issues.append(dict(group='downloads', rule='apt-archives', path=str(apt), reason=str(error)))
        if 'builds' in groups:
            choices = (
                ('go-module-cache', 'GOMODCACHE', self.home / 'go/pkg/mod'),
                ('go-build-cache', 'GOCACHE', self.cache / 'go-build'),
                ('uv-cache', 'UV_CACHE_DIR', self.cache / 'uv'),
            )
            for rule, variable, fallback in choices:
                try:
                    add(rule, 'builds', self.location(variable, fallback))
                except (ValueError, OSError) as error:
                    issues.append(dict(group='builds', rule=rule, reason=str(error)))
            try:
                add('cargo-registry', 'builds', self.location('CARGO_HOME', self.home / '.cargo') / 'registry')
            except (ValueError, OSError) as error:
                issues.append(dict(group='builds', rule='cargo-registry', reason=str(error)))
        if 'logs' in groups:
            add('cpan-builds', 'logs', self.home / '.cpan/build')
            for name in LOGS:
                add('nvim-logs', 'logs', self.state / 'nvim' / name, 'file')
        if set(groups) & set(CHECKPOINTS):
            try:
                safe_path(self.checkpoints, self.boundary)
                children = sorted(self.checkpoints.iterdir()) if self.checkpoints.is_dir() else []
                for path in children:
                    safe_path(path, self.boundary)
                    if not path.is_dir() or not (path / '.git').is_dir():
                        continue
                    target = Target('pi-checkpoints', 'unclassified-checkpoints', path, 'root')
                    target.entries = inventory(target, self.boundary)
                    if max(v[6] for v in target.entries.values()) / 1e9 > time.time() - age_days * 86400:
                        continue
                    target.group = self.classify(path)
                    if target.group in groups:
                        targets.append(target)
                    report('Inspecting checkpoints')
            except (ValueError, OSError) as error:
                issues.append(dict(group='checkpoints', rule='pi-checkpoints', path=str(self.checkpoints), reason=str(error)))
        # Reject overlap, including a custom cache location pointing at another rule.
        conflicts = set()
        for i, target in enumerate(targets):
            for other in targets[i + 1:]:
                if inside(target.path, other.path) or inside(other.path, target.path):
                    conflicts.update((target.path, other.path))
        for target in targets:
            if target.path in conflicts:
                issues.append(dict(group=target.group, rule=target.rule, path=str(target.path), reason='overlapping cleanup targets'))
        return [t for t in targets if t.path not in conflicts], issues

    def classify(self, path):
        # Metadata and filenames only. Never surface firstUserMessage or auth payloads.
        try:
            if (path / '.git').is_symlink():
                return 'unclassified-checkpoints'
            manifest = path / 'manifest.json'
            if manifest.is_symlink() or not manifest.is_file() or manifest.stat().st_size > 65536:
                return 'unclassified-checkpoints'
            data = json.loads(manifest.read_text())
            cwd = data.get('cwd')
            if data.get('version') != 1 or not isinstance(cwd, str) or not Path(cwd).is_absolute():
                return 'unclassified-checkpoints'
            if inside(Path(cwd), self.home / '.pi/agent'):
                return 'sensitive-checkpoints'
            git = shutil.which('git', path=self.env.get('PATH'))
            if not git:
                return 'unclassified-checkpoints'
            env = {k: v for k, v in self.env.items() if not k.startswith('GIT_')}
            env.update(GIT_OPTIONAL_LOCKS='0', GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull)
            args = [git, '--no-optional-locks', '--git-dir=' + str(path / '.git')]
            commits = command([*args, 'rev-list', '--all', '--max-count=129'], env, self.home, 10, 16384).splitlines()
            if not commits or len(commits) > 128:
                return 'unclassified-checkpoints'
            sensitive = {'.ssh', '.gnupg', '.config', '.codex', '.pi', '.aws', '.kube',
                         'auth.json', 'credentials', 'credentials.json', '.netrc', '.npmrc',
                         '.pypirc', '.bash_history', '.zsh_history', 'sessions', 'id_rsa', 'id_ed25519'}
            for commit in commits:
                names = command([*args, 'ls-tree', '-r', '-z', '--name-only', commit.decode('ascii')], env, self.home, 10)
                for name in names.split(b'\0'):
                    parts = Path(name.decode(errors='replace')).parts
                    if set(parts) & sensitive or any(p.startswith('.env') or p.endswith(('.pem', '.key')) for p in parts):
                        return 'sensitive-checkpoints'
            return 'project-checkpoints'
        except (ValueError, OSError, UnicodeError):
            return 'unclassified-checkpoints'

    def native(self, target):
        if target.rule not in ('go-module-cache', 'go-build-cache', 'uv-cache'):
            return False
        name = 'uv' if target.rule == 'uv-cache' else 'go'
        exe = shutil.which(name, path=self.env.get('PATH'))
        if not exe:
            raise ValueError(name + ' is unavailable; cache retained')
        if inside(Path(exe).resolve(), target.path):
            raise ValueError('cleanup helper is stored in its own cleanup target')
        env = {k: v for k, v in self.env.items() if not k.startswith(('GO', 'UV_'))}
        if name == 'go':
            env.update(GOENV='off', GOTOOLCHAIN='local', GOWORK='off', GO111MODULE='off',
                       GOPROXY='off', GOSUMDB='off', GOPATH=str(self.home / 'go'),
                       GOMODCACHE=str(target.path if target.rule == 'go-module-cache' else self.home / 'go/pkg/mod'),
                       GOCACHE=str(target.path if target.rule == 'go-build-cache' else self.cache / 'go-build'))
            command([exe, 'clean', '-modcache' if target.rule == 'go-module-cache' else '-cache'], env, self.home)
        else:
            command([exe, 'cache', 'clean', '--cache-dir', str(target.path), '--offline', '--no-config', '--color', 'never'], env, self.home)
        return True
