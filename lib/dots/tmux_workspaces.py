"""Managed tmux workspace identities and event-driven project reconciliation.

Private adapter shared by the launcher, session picker and shell/tmux hooks.
Observation is separate from reconciliation; status rendering never mutates.
"""
from contextlib import contextmanager
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unicodedata
import uuid


PREFIX = '@dots-workspace-'
IDENTITY = re.compile(r'(?:[0-9]+-[0-9]+|[0-9a-f]{12})\Z')
SESSION = re.compile(r'\$[0-9]+\Z')


def literal(value):
    value = str(value)
    return value[:-1] + r'\;' if value.endswith(';') else value


def display_name(root):
    name = Path(root).name or 'project'
    return ''.join('?' if unicodedata.category(c).startswith('C') else c for c in name)


def name_prefix(label):
    return re.sub(r'[.:\x00-\x1f\x7f]', '-', label).strip() or 'project'


def configured_projects(config=None):
    roots = [Path(os.environ.get('DOTS') or Path(__file__).resolve().parents[2])]
    config = Path(config) if config is not None else Path(os.environ.get('XDG_CONFIG_HOME') or Path.home() / '.config') / 'dots/projects.json'
    if config.exists():
        data = json.loads(config.read_text())
        if (not isinstance(data, dict) or type(data.get('schema')) is not int or data['schema'] != 1
                or set(data) - {'schema', 'roots', 'projects'}):
            raise ValueError('invalid project configuration')
        for key in ('roots', 'projects'):
            values = data.get(key, [])
            if not isinstance(values, list):
                raise ValueError('invalid project configuration')
            for value in values:
                if not isinstance(value, str) or '\0' in value or not Path(value).expanduser().is_absolute():
                    raise ValueError('invalid configured project path')
                if key == 'projects':
                    roots.append(Path(value).expanduser())
    return tuple(root.resolve() for root in roots if root.is_dir())


def project_root(directory, configured=None, timeout=1):
    """Deepest explicit project or Git worktree root; never scan directories."""
    path = Path(directory).resolve()
    if not path.is_dir():
        raise ValueError('workspace directory is unavailable')
    candidates = [root for root in (configured_projects() if configured is None else configured)
                  if path == root or root in path.parents]
    git = shutil.which('git')
    if git:
        env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        env.update(GIT_OPTIONAL_LOCKS='0', GIT_TERMINAL_PROMPT='0', LC_ALL='C')
        result = subprocess.run([git, '-C', str(path), 'rev-parse', '--show-toplevel'],
                                env=env, capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0:
            root = Path(result.stdout.removesuffix('\n')).resolve()
            if root.is_dir() and (root == path or root in path.parents):
                candidates.append(root)
        elif not result.stderr.startswith('fatal: not a git repository'):
            raise ValueError('workspace Git root could not be observed')
    elif any((parent / '.git').exists() for parent in (path, *path.parents)):
        raise ValueError('Git is unavailable for this workspace')
    return max(candidates, key=lambda root: len(root.parts)) if candidates else None


class Workspaces:
    def __init__(self, executable=None, socket=None):
        self.deadline = None
        self.executable = executable or shutil.which('tmux')
        inherited = os.environ.get('TMUX', '').rsplit(',', 2)
        self.socket = socket or (inherited[0] if len(inherited) == 3 else None)
        if not self.executable or os.name == 'nt':
            raise ValueError('tmux workspaces are unavailable')
        self.base = [self.executable, '-u', '-N'] + (['-S', self.socket] if self.socket else [])
        identity = self.read('display-message', '-p', '#{pid}\n#{socket_path}').split('\n', 1)
        if len(identity) != 2 or not identity[0].isdecimal():
            raise ValueError('invalid tmux server identity')
        self.pid, self.socket = int(identity[0]), identity[1].removesuffix('\n')
        self.base = [self.executable, '-u', '-N', '-S', self.socket]

    def raw(self, args):
        result = subprocess.run([*self.base, *args], capture_output=True, text=True, timeout=self.remaining(5))
        if result.returncode:
            raise ValueError('tmux workspace operation failed: ' + result.stderr.strip())
        return result.stdout

    def remaining(self, maximum):
        remaining = maximum if self.deadline is None else min(maximum, self.deadline - time.monotonic())
        if remaining <= 0:
            raise ValueError('workspace update timed out')
        return remaining

    @contextmanager
    def bounded(self, seconds=3):
        previous, self.deadline = self.deadline, time.monotonic() + seconds
        try:
            yield
        finally:
            self.deadline = previous

    def read(self, *args):
        return self.raw([literal(arg) for arg in args])

    def batch(self, commands):
        arguments = []
        for command in commands:
            if arguments:
                arguments.append(';')
            arguments.extend(literal(arg) for arg in command)
        if arguments:
            self.raw(arguments)

    @contextmanager
    def locked(self):
        import fcntl
        runtime = os.environ.get('XDG_RUNTIME_DIR') or os.environ.get('TMPDIR') or tempfile.gettempdir()
        directory = Path(runtime) / f'dots-tmux-workspaces-{os.getuid()}'
        directory.mkdir(mode=0o700, exist_ok=True)
        info = directory.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError('unsafe workspace lock directory')
        key = hashlib.sha256(f'{self.socket}:{self.pid}'.encode()).hexdigest()
        fd = os.open(directory / key, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise ValueError('unsafe workspace lock')
            # Queue time must not consume the later observation/work budget.
            deadline = time.monotonic() + self.remaining(15)
            while True:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise ValueError('workspace update is busy')
                    time.sleep(.02)
            if self.read('display-message', '-p', '#{pid}').strip() != str(self.pid):
                raise ValueError('tmux server changed')
            yield
        finally:
            os.close(fd)

    def sessions(self):
        rows = self.read('list-sessions', '-F', '#{session_id}\t#{session_created}').splitlines()
        values = []
        for row in rows:
            ident, created = row.split('\t')
            if not SESSION.fullmatch(ident) or not created.isdecimal():
                raise ValueError('invalid session inventory')
            values.append((ident, int(created)))
        return [ident for ident, _ in sorted(values, key=lambda value: (value[1], int(value[0][1:])))]

    def option(self, session, option):
        return self.read('show-options', '-qv', '-t', session + ':', option).removesuffix('\n')

    def name(self, session):
        return self.read('display-message', '-p', '-t', session + ':', '#{session_name}').removesuffix('\n')

    def metadata(self, session):
        value = self.option(session, PREFIX + 'data')
        if not value:
            return None
        data = json.loads(value)
        if (not isinstance(data, dict) or type(data.get('schema')) is not int or data['schema'] != 1
                or not isinstance(data.get('id'), str) or not IDENTITY.fullmatch(data['id'])
                or not isinstance(data.get('expected'), str) or type(data.get('auto')) is not bool
                or not isinstance(data.get('projects'), list)
                or any(not isinstance(p, str) or not Path(p).is_absolute() for p in data['projects'])
                or (data.get('origin') is not None and
                    (not isinstance(data['origin'], str) or not re.fullmatch(r'[0-9]+-[0-9]+', data['origin'])))):
            raise ValueError('invalid workspace metadata')
        return data

    def store(self, session, data, label=None, rename=None):
        commands = [['set-option', '-t', session + ':', PREFIX + 'data', json.dumps(data, ensure_ascii=True)],
                    ['set-option', '-t', session + ':', PREFIX + 'auto', '1' if data['auto'] else '0'],
                    ['set-option', '-t', session + ':', PREFIX + 'expected', data['expected']]]
        if label is not None:
            commands.append(['set-option', '-t', session + ':', PREFIX + 'label', label])
        if rename is not None:
            commands.append(['rename-session', '-t', session, '--', rename.replace('#', '##')])
        self.batch(commands)

    def register(self, session, identity=None, origin=None):
        identity = identity or uuid.uuid4().hex[:12]
        if not IDENTITY.fullmatch(identity):
            raise ValueError('invalid workspace identity')
        data = dict(schema=1, id=identity, origin=origin, auto=True,
                    expected=self.name(session), projects=[])
        self.store(session, data)
        return data

    def renumber(self):
        from menu_projects import discover, number_group
        sessions = self.sessions()
        projects = discover()
        groups = {}
        for session in sessions:
            record = SimpleNamespace(id=session, name=self.name(session))
            groups.setdefault(number_group(self, record, projects), []).append(session)
        # Observe every group and previous value before changing any numbers.
        commands = []
        for members in groups.values():
            for index, session in enumerate(members, 1):
                number = str(index) if len(members) > 1 else ''
                if self.option(session, '@dots-session-number') != number:
                    commands.append(['set-option', '-t', session + ':', '@dots-session-number', number])
        self.batch(commands)

    def refresh_numbers(self):
        # A bad unrelated observation must not abort creation or a completed
        # project reconciliation. Explicit `numbers` still reports the error.
        try:
            with self.bounded(15):
                self.renumber()
        except (ValueError, OSError, subprocess.SubprocessError):
            print('dots: session numbers retained after an incomplete group inventory', file=sys.stderr)

    def reconcile_one(self, session, configured):
        data = self.metadata(session)
        if data is None:
            return True  # Unmanaged picker associations can follow pane paths.
        actual = self.name(session)
        renamed = actual != data['expected']
        if renamed:
            data['auto'] = False
            data['expected'] = actual
            self.store(session, data)
        panes = self.read('list-panes', '-s', '-t', session, '-F', '#{pane_id}\t#{pane_dead}').splitlines()
        projects = set()
        directories = set()
        for row in panes:
            pane, dead = row.split('\t')
            if not re.fullmatch(r'%[0-9]+', pane) or dead not in ('0', '1'):
                raise ValueError('invalid pane inventory')
            if dead == '0':
                directories.add(self.read('display-message', '-p', '-t', pane,
                                          '#{pane_current_path}').removesuffix('\n'))
        for directory in directories:
            root = project_root(directory, configured, timeout=self.remaining(1))
            if root is not None:
                projects.add(str(root))
        projects = sorted(projects)
        label = '' if not projects else display_name(projects[0]) if len(projects) == 1 else 'multi'
        expected = name_prefix(label or 'termux') + '-' + data['id'] if data['auto'] else actual
        if projects == data.get('projects') and expected == actual and self.option(session, PREFIX + 'label') == label:
            return renamed
        # A collision with an unrelated manual name must never merge workspaces.
        if expected != actual and any(self.name(other) == expected for other in self.sessions() if other != session):
            raise ValueError('workspace name is occupied by another session')
        data.update(projects=projects, expected=expected)
        self.store(session, data, label, expected if expected != actual else None)
        return True

    def reconcile(self, pane=None, adopt=False, session=None):
        with self.locked(), self.bounded(15 if adopt else 3):
            sessions = self.sessions()
            if session is not None and (not SESSION.fullmatch(session) or session not in sessions):
                raise ValueError('workspace session is unavailable')
            if adopt:
                for target in ([session] if session else sessions):
                    if self.metadata(target) is None and self.option(target, '@dots-termux-default') == '1':
                        match = re.fullmatch(r'termux-([0-9]+-[0-9]+)', self.name(target))
                        if match:
                            self.register(target, match[1], match[1])
            targets = sessions
            if pane:
                if not re.fullmatch(r'%[0-9]+', pane):
                    raise ValueError('invalid originating pane')
                window = self.read('display-message', '-p', '-t', pane, '#{window_id}').strip()
                rows = self.read('list-windows', '-a', '-F', '#{session_id}\t#{window_id}').splitlines()
                targets = {row.split('\t')[0] for row in rows if row.split('\t')[1] == window}
            elif session:
                # Include sessions sharing a live window, including after a pane exits.
                rows = [row.split('\t') for row in self.read('list-windows', '-a', '-F',
                        '#{session_id}\t#{window_id}').splitlines()]
                windows = {window for owner, window in rows if owner == session}
                targets = {owner for owner, window in rows if window in windows} | {session}
            configured = configured_projects()
            changed = adopt
            for session in targets:
                changed = self.reconcile_one(session, configured) or changed
            if changed:
                self.refresh_numbers()

    def create(self, directory, identity=None, origin=None):
        if not Path(directory).is_dir():
            raise ValueError('workspace directory is unavailable')
        with self.locked(), self.bounded(15):
            identity = identity or uuid.uuid4().hex[:12]
            if not IDENTITY.fullmatch(identity):
                raise ValueError('invalid workspace identity')
            if origin:
                matches = [s for s in self.sessions() if (self.metadata(s) or {}).get('origin') == origin]
                if len(matches) > 1:
                    raise ValueError('multiple workspaces claim this Termux identity')
                if matches:
                    return matches[0]
            root = project_root(directory)
            label = display_name(root) if root else 'termux'
            name = name_prefix(label) + '-' + identity
            session = self.read('new-session', '-d', '-P', '-F', '#{session_id}', '-s', name.replace('#', '##'),
                                '-c', str(directory).replace('#', '##')).strip()
            if not SESSION.fullmatch(session):
                raise ValueError('created workspace could not be identified')
            self.register(session, identity, origin)
            if origin:
                self.read('set-option', '-t', session + ':', '@dots-termux-default', '1')
            self.reconcile_one(session, configured_projects())
            self.refresh_numbers()
            return session


def main(argv=None):
    parser = argparse.ArgumentParser(description='Internal tmux workspace event adapter')
    parser.add_argument('action', choices=('reconcile', 'numbers', 'create', 'adopt'))
    parser.add_argument('--socket')
    parser.add_argument('--pane')
    parser.add_argument('--session')
    parser.add_argument('--client')
    args = parser.parse_args(argv)
    try:
        server = Workspaces(socket=args.socket)
        if args.action == 'numbers':
            with server.locked(), server.bounded(15):
                server.renumber()
        elif args.action in ('reconcile', 'adopt'):
            server.reconcile(args.pane, args.action == 'adopt', args.session)
        else:
            from menu_tmux import TmuxContext
            context = TmuxContext.capture(client=args.client, pane=args.pane)
            if context.socket != server.socket:
                raise ValueError('originating server changed')
            directory = server.read('display-message', '-p', '-t', context.pane,
                                    '#{pane_current_path}').removesuffix('\n')
            ident = server.create(directory)
            context.verify()
            server.read('switch-client', '-c', context.client, '-t', ident)
        return 0
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print('dots: ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
