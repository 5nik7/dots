"""Project-aware interactive tmux navigation; read-only live-session data modes."""
import argparse
from dataclasses import dataclass
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from interaction import SelectionEnded, SelectionEvent, terminal
from menus import Entry, Menu, add_arguments, choose, show_message
from menu_tmux import TmuxContext, status, tmux_arg
from resources import clean


def native_windows():
    return os.name == 'nt'


def observe(command):
    # Stable diagnostics for recognizing an absent server, without starting one.
    return subprocess.run(command, capture_output=True, text=True, timeout=5,
                          env=dict(os.environ, LC_ALL='C'))


def absent_server(result):
    message = result.stderr.strip()
    return (message.startswith('no server running on ')
            or (message.startswith('error connecting to ')
                and message.endswith(('(No such file or directory)', '(Connection refused)'))))


def failure(result):
    return ValueError('tmux observation failed: ' + clean(result.stderr.strip() or 'no diagnostic'))


@dataclass(frozen=True)
class Session:
    id: str
    name: str
    windows: int
    attached_clients: int
    current: bool
    created: int

    def entry(self):
        unit = 'window' if self.windows == 1 else 'windows'
        description = f'{self.windows} {unit} · {self.attached_clients} attached'
        if self.current:
            description += ' · current'
        return Entry(self.id, self.name, description)

    def document(self):
        return dict(self.entry().document(), name=self.name, windows=self.windows,
                    attached_clients=self.attached_clients, current=self.current)


@dataclass(frozen=True)
class Server:
    executable: str
    socket: str
    pid: int

    def command(self, *args):
        return [self.executable, '-u', '-N', '-S', self.socket, *map(tmux_arg, args)]

    def read(self, *args):
        result = observe(self.command(*args))
        if result.returncode:
            raise failure(result)
        return result.stdout

    @classmethod
    def discover(cls):
        if native_windows():
            raise ValueError('tmux session menus are unavailable on native Windows; WSL is not invoked')
        executable = shutil.which('tmux')
        if not executable:
            raise ValueError('tmux is unavailable; install tmux to inspect or select sessions')
        # Without -u, tmux can replace Unicode and format delimiters with '_'
        # for an external client in a C locale, even on captured stdout.
        command = [os.path.abspath(executable), '-u', '-N']
        inherited = os.environ.get('TMUX')
        if inherited:
            parts = inherited.rsplit(',', 2)
            if len(parts) != 3 or not os.path.isabs(parts[0]):
                raise ValueError('invalid inherited tmux server')
            command += ['-S', parts[0]]
        result = observe([*command, 'display-message', '-p', '#{pid}\n#{socket_path}'])
        if result.returncode:
            if absent_server(result):
                return None
            raise failure(result)
        # The first field is numeric; the socket may itself contain newlines.
        pid, separator, socket = result.stdout.removesuffix('\n').partition('\n')
        if not separator or not pid.isdecimal() or int(pid) <= 0 or not os.path.isabs(socket):
            raise ValueError('invalid tmux server identity')
        return cls(command[0], socket, int(pid))

    def verify(self):
        if self.read('display-message', '-p', '#{pid}').strip() != str(self.pid):
            raise ValueError('tmux server changed; open the session menu again')

    def sessions(self):
        self.verify()
        result = observe(self.command('list-sessions', '-F', '#{session_id}\t#{session_windows}\t#{session_attached}\t#{session_created}'))
        if result.returncode and result.stderr.strip() != 'no sessions':
            raise failure(result)
        rows = result.stdout
        if not rows:
            self.verify()
            return ()
        pane = os.environ.get('TMUX_PANE') if os.environ.get('TMUX') else None
        current = self.read('display-message', '-p', '-t', pane, '#{session_id}').strip() if pane else ''
        sessions = []
        for row in rows.splitlines():
            fields = row.split('\t')
            if (len(fields) != 4 or not re.fullmatch(r'\$[0-9]+', fields[0])
                    or not all(field.isdecimal() for field in fields[1:])):
                raise ValueError('invalid tmux session inventory')
            ident, windows, attached, created = fields
            # A separate literal observation preserves tabs/newlines in names.
            # Names never enter a target expression or an action argument.
            name = self.read('display-message', '-p', '-t', ident, '#{session_name}').removesuffix('\n')
            if not name:
                raise ValueError('tmux session disappeared; open the session menu again')
            sessions.append(Session(ident, name, int(windows), int(attached), ident == current, int(created)))
        self.verify()
        return tuple(sessions)

    def validate(self, session, context=None):
        self.verify()
        identity = self.read('display-message', '-p', '-t', session.id, '#{session_id}\t#{session_created}').strip()
        if identity != f'{session.id}\t{session.created}':
            raise ValueError('tmux session disappeared or changed; open the session menu again')
        if context is not None:
            if context.socket != self.socket:
                raise ValueError('tmux menu server does not match its invoking client')
            context.verify()

    def select(self, session, context=None):
        self.validate(session, context)
        if context is not None:
            if session.id == context.session:
                return 0
            # Never let tmux infer the most recently used client.
            result = observe(self.command('switch-client', '-c', context.client, '-t', session.id))
            if result.returncode:
                raise failure(result)
            return 0
        if not terminal():
            raise ValueError('attaching a tmux session requires terminal input and output')
        return status(subprocess.call(self.command('attach-session', '-t', session.id)))


@dataclass(frozen=True)
class SessionOutcome:
    selected: bool = False
    code: int = 0
    message: str = ''


def valid_name(name):
    import unicodedata
    if (not name or not name.strip() or any(c in '.:' or unicodedata.category(c).startswith('C') for c in name)):
        raise ValueError('Use a nonempty session name without periods, colons or control characters.')
    return name


def suggested_name(directory, sessions):
    base = re.sub(r'[.:\x00-\x1f\x7f]', '-', Path(directory).name) or 'Work'
    names = {s.name for s in sessions}
    name, suffix = base, 2
    while name in names:
        name = f'{base}-{suffix}'; suffix += 1
    return name


def session_directory(server, session, fallback):
    server.validate(session)
    directory = server.read('display-message', '-p', '-t', session.id, '#{pane_current_path}').removesuffix('\n')
    return directory if directory and Path(directory).is_dir() else fallback


def create_session(server, name, directory, project=None, context=None):
    managed = name is None
    if not managed:
        valid_name(name)
    if not Path(directory).is_dir():
        raise ValueError('session starting directory is no longer available')
    if server:
        server.verify()
    if context:
        context.verify()
        if server is None or context.socket != server.socket:
            raise ValueError('tmux menu server does not match its invoking client')
    from tmux_workspaces import Workspaces, project_root, display_name, name_prefix
    import uuid
    identity = uuid.uuid4().hex[:12] if managed else None
    if managed:
        root = project_root(directory)
        name = name_prefix(display_name(root) if root else 'termux') + '-' + identity
    arguments = ['new-session', '-d', '-P', '-F', '#{session_id}', '-s',
                 name.replace('#', '##'), '-c', str(directory).replace('#', '##')]
    registered = managed and server is not None
    if registered:
        ident = Workspaces(server.executable, server.socket).create(directory, identity)
    elif server:
        ident = server.read(*arguments).strip()
    else:
        # Creation is explicit. Inspection never reaches this server-start path.
        executable = shutil.which('tmux')
        if not executable:
            raise ValueError('tmux is unavailable')
        command = [executable, '-u']
        if os.environ.get('TMUX'):
            command += ['-S', os.environ['TMUX'].rsplit(',', 2)[0]]
        result = observe([*command, *map(tmux_arg, arguments)])
        if result.returncode:
            raise failure(result)
        ident = result.stdout.strip()
        server = Server.discover()
    if server is None or not re.fullmatch(r'\$[0-9]+', ident):
        raise ValueError('created session could not be observed; reopen the menu')
    if managed and not registered:
        workspaces = Workspaces(server.executable, server.socket)
        with workspaces.locked():
            workspaces.register(ident, identity)
        workspaces.reconcile()
    session = next((s for s in server.sessions() if s.id == ident), None)
    if session is None:
        raise ValueError('created session closed before it could be opened')
    server.validate(session, context)
    if project and not managed:
        server.read('set-option', '-t', ident, '@dots-project-root', str(project.root))
    return server, session


def rename_session(server, session, name, context=None):
    valid_name(name)
    server.validate(session, context)
    server.read('rename-session', '-t', session.id, '--', name.replace('#', '##'))


def delete_session(server, session, context=None):
    server.validate(session, context)
    server.read('kill-session', '-t', session.id)


def action_menu(row, context, termux):
    entries = [Entry('open', 'switch / open', icon=''), Entry('new', 'new session', icon='󰐕')]
    if row and row.sessions:
        entries += [Entry('rename', 'rename', icon='󰏫'), Entry('delete', 'delete session', icon='󰆴')]
    if termux and row:
        entries.append(Entry('termux', 'new Termux', 'Attach in a new Termux tab', icon=''))
    if row is None:
        entries = [e for e in entries if e.id == 'new']
    try:
        entry = choose(Menu('session-actions', 'Session actions', tuple(entries)), mode='browse', context=context,
                       navigation={}, prompt='dots·tmux·actions')
    except SelectionEvent:
        return None
    return entry.id if entry else None


def confirm_delete(session, context):
    message = f'{session.windows} windows · {session.attached_clients} attached clients · stops their processes'
    menu = Menu('delete-session', 'Delete ' + clean(session.name), (
        Entry('cancel', 'Cancel', 'Keep this session'),
        Entry('delete', 'Delete ' + clean(session.name), message, icon='󰆴')))
    try:
        entry = choose(menu, mode='browse', context=context, navigation={}, prompt='dots·tmux·delete',
                       header=f'{session.windows} windows · {session.attached_clients} attached\n'
                              'Stops the session and its processes\nEnter: choose  Esc: back\nCtrl-C: quit')
    except SelectionEvent:
        return False
    return entry is not None and entry.id == 'delete'


def browse(context=None, query=''):
    """Interactive projects/actions; a completed handoff closes the launcher."""
    from menu_projects import Row, discover, inventory
    from menu_session_ui import pick, show_keys
    from menu_session_host import prompt, is_termux, launch_termux, termux_transport
    server = Server.discover()
    projects = discover()
    termux = is_termux()
    frame = dict(query=query)
    stack = [dict(project=None, frame=frame, action=None)]
    # Pin this server for the browser lifetime, including refresh after actions.
    while stack:
        sessions = server.sessions() if server else ()
        rows = inventory(server, sessions, projects)
        view = stack[-1]
        project = view['project']
        if project:
            parent = next((r for r in rows if r.project == project), None)
            rows = tuple(Row(s.id, s.name, project, (s,)) for s in parent.sessions) if parent else ()
            if not rows:
                stack.pop()
                continue
        try:
            selected = pick(rows, context=context, frame=view['frame'], termux=termux,
                            prompt='dots·tmux·sessions' + ('·' + project.label if project else ''),
                            intent=view['action'])
            if selected is None:
                return SessionOutcome()
            action = view['action'] or 'open'
            view['action'] = None
        except SelectionEvent as event:
            if event.action == 'keys':
                show_keys(context=context, termux=termux, intent=view['action'])
                continue
            if event.action == 'back':
                stack.pop()
                if not stack:
                    raise SelectionEnded(130) from None
                continue
            selected = rows[event.index] if event.index is not None else None
            action = action_menu(selected, context, termux) if event.action == 'actions' else event.action
        if action is None:
            continue
        view['action'] = None
        if selected is None and action != 'new':
            continue
        if selected and len(selected.sessions) > 1 and action != 'new':
            stack.append(dict(project=selected.project, frame={}, action=action))
            continue
        target = selected.sessions[0] if selected and selected.sessions else None
        project = selected.project if selected else project
        directory = str(project.root) if project else context.cwd if context else os.getcwd()
        try:
            transport = termux_transport() if action == 'termux' else None
            if action == 'new' or action in ('open', 'termux') and target is None:
                if project is None and target:
                    directory = session_directory(server, target, directory)
                server, target = create_session(server, None, directory, project, context)
                if action == 'new':
                    action = 'open'
            if action == 'open':
                return SessionOutcome(selected=True, code=server.select(target, context))
            if action == 'termux':
                server.validate(target, context)
                if project is None:
                    directory = session_directory(server, target, directory)
                launch_termux(server, target, directory, transport=transport)
                return SessionOutcome(selected=True)
            if action == 'rename' and target:
                name = prompt(target.name, 'Rename ' + clean(target.name), context)
                if name is not None:
                    rename_session(server, target, name, context)
            elif action == 'delete' and target:
                server.validate(target, context)
                # Refresh the counts shown in the explicit confirmation.
                refreshed = next((s for s in server.sessions() if s.id == target.id and s.created == target.created), None)
                if refreshed is None:
                    raise ValueError('tmux session disappeared or changed; reopen the menu')
                target = refreshed
                if confirm_delete(target, context):
                    delete_session(server, target, context)
                    if context is not None and target.id == context.session:
                        return SessionOutcome(selected=True)
                    if len(sessions) == 1:
                        server = None  # Last-session deletion may terminate the server.
        except (ValueError, OSError, subprocess.SubprocessError) as error:
            show_message(clean(str(error)), context=context, title='Tmux sessions', code=2)
            # Refuse stale origin/server identities instead of silently retargeting.
            if context:
                context.verify()
            if server:
                server.verify()
    return SessionOutcome()


def run(args):
    interactive = args.menu_mode == 'browse' or (args.menu_mode == 'auto' and terminal() and os.environ.get('TERM') != 'dumb')
    context = None
    if interactive:
        if os.environ.get('DOTS_MENU_CONTEXT'):
            context = TmuxContext.from_environment()
            if args.client and context.client != args.client:
                raise ValueError('requested tmux client differs from the inherited menu context')
        elif os.environ.get('TMUX'):
            context = TmuxContext.capture(client=args.client)
        elif args.client:
            raise ValueError('--client requires an inherited tmux server and pane')
        return browse(context, query=args.query).code
    server = Server.discover()
    sessions = server.sessions() if server else ()
    menu = Menu('tmux-sessions', 'Tmux sessions', tuple(s.entry() for s in sessions))
    if args.menu_mode == 'json':
        records = {s.id: s.document() for s in sessions}
        document = menu.document(args.query)
        document['items'] = [records[e.id] for e in menu.filtered(args.query)]
        print(json.dumps(document, ensure_ascii=True))
    else:
        choose(menu, mode='print', query=args.query)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog='dots menu tmux sessions', description='Browse projects and manage tmux sessions')
    add_arguments(parser)
    parser.add_argument('--client', help='Exact invoking tmux client (requires an inherited server and pane)')
    args = parser.parse_args(argv)
    try:
        return run(args)
    except SelectionEnded as error:
        return error.status
    except KeyboardInterrupt:
        return 130
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print('dots menu tmux sessions: ' + clean(str(error)), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
