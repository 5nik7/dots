"""Explicit goal-to-Codex launch, recoverable local links and popup handoff."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import time
import uuid

from todo_core import Goals
from file_platform import state_root, open_nofollow, lock, sync_dir
from transactions import parents_safe
from resources import clean


def thread_name(selected, goal):
    project = Path(selected['root']).name if selected['root'] else 'global'
    alias = (goal['alias'] + ' — ') if goal.get('alias') else ''
    return ('[' + clean(project) + '] ' + alias + clean(goal['title']))[:256]


def window_name():
    from style_config import icon
    return clean(icon('status.todo', '󰄬', app='tmux')) or 'todo'


class Link:
    def __init__(self, selected, identity):
        self.scope = str(Path(selected['path']).resolve())
        self.goal = identity
        key = hashlib.sha256((self.scope + '\0' + identity).encode()).hexdigest()
        self.path = state_root() / 'todo/codex' / (key + '.json')

    def read(self):
        parents_safe(self.path)
        try:
            fd = open_nofollow(self.path, os.O_RDONLY | getattr(os, 'O_NONBLOCK', 0))
        except FileNotFoundError:
            return None
        with os.fdopen(fd, 'r', encoding='utf-8') as stream:
            info = os.fstat(stream.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_size > 16384 or
                    os.name != 'nt' and (info.st_uid != os.getuid() or info.st_mode & 0o077)):
                raise ValueError('Unsafe Todo Codex link')
            try: data = json.load(stream)
            except (ValueError, UnicodeError): raise ValueError('Invalid Todo Codex link') from None
        if (not isinstance(data, dict) or data.get('schema') != 1 or data.get('scope') != self.scope or
                data.get('goal') != self.goal or not isinstance(data.get('thread'), str) or
                not re.fullmatch(r'[a-zA-Z0-9_-]{1,128}', data['thread']) or
                not isinstance(data.get('backend'), str) or not isinstance(data.get('cwd'), str) or
                not os.path.isabs(data['cwd']) or '\0' in data['cwd']):
            raise ValueError('Invalid Todo Codex link')
        submission = data.get('submission')
        if submission is not None and (not isinstance(submission, dict) or
                submission.get('state') not in ('sending', 'accepted')):
            raise ValueError('Invalid Todo Codex submission receipt')
        return data

    @contextmanager
    def locked(self):
        parents_safe(self.path)
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        info = self.path.parent.stat()
        if os.name != 'nt' and (info.st_uid != os.getuid() or info.st_mode & 0o077):
            raise ValueError('Todo Codex link directory must be private')
        path = self.path.with_suffix('.lock')
        fd = open_nofollow(path, os.O_RDWR | os.O_CREAT | getattr(os, 'O_NONBLOCK', 0), 0o600)
        with os.fdopen(fd, 'r+b') as stream:
            info = os.fstat(stream.fileno())
            if (not stat.S_ISREG(info.st_mode) or os.name != 'nt' and
                    (info.st_uid != os.getuid() or info.st_mode & 0o077)):
                raise ValueError('Unsafe Todo Codex launch lock')
            if not info.st_size:
                stream.write(b'0'); stream.flush()
            try: lock(stream)
            except OSError: raise ValueError('This goal is already being launched; try again shortly') from None
            yield

    def write(self, data):
        self.read()  # Reject unsafe replacement targets, including links/special files.
        fd, temporary = tempfile.mkstemp(prefix='.link-', dir=self.path.parent)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                json.dump(data, stream, ensure_ascii=True)
                stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
            os.replace(temporary, self.path)
            sync_dir(self.path.parent)
        finally:
            if os.path.exists(temporary): os.unlink(temporary)


def unchanged(store, identity):
    current = Goals(store.scope)
    if current.guard != store.guard:
        raise ValueError('Goals changed since selection; review the refreshed goal before launching')
    return current.find(identity, False)


def prepare(store, goal, link, backend, rpc, new=False):
    from todo_brief import body
    goal = unchanged(store, goal['id'])
    previous = link.read()
    record = None if new else previous
    if record and record['backend'] != backend.identity:
        raise ValueError('The linked thread belongs to another Codex backend; use --new to create a new association')
    cwd = (store.scope['root'] or (record['cwd'] if record else str(Path.cwd().resolve())))
    if not Path(cwd).is_dir():
        raise ValueError('The linked working directory is unavailable; use --new from an existing directory')
    # Check the explicit capability before creating a conversation.
    presets = rpc.call('collaborationMode/list').get('data', [])
    plan = next((p for p in presets if p.get('mode') == 'plan'), None)
    if plan is None:
        raise ValueError('This Codex server does not expose Plan Mode')
    if record:
        session = rpc.call('thread/resume', dict(threadId=record['thread'], cwd=cwd, excludeTurns=True))
    else:
        session = rpc.call('thread/start', dict(cwd=cwd))
        thread = session.get('thread', {}).get('id')
        if not isinstance(thread, str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,128}', thread):
            raise ValueError('Codex did not return a valid thread ID')
        record = dict(schema=1, scope=link.scope, goal=goal['id'], thread=thread,
                      backend=backend.identity, cwd=cwd, submission=None)
        if previous: record['previous_thread'] = previous['thread']
        link.write(record)  # Retain the association even if naming/submission fails.
    thread_data = session.get('thread', {})
    status = thread_data.get('status', {}).get('type')
    if thread_data.get('id') != record['thread'] or status not in ('active', 'idle'):
        raise ValueError('Codex did not confirm the linked thread is ready; inspect it before retrying')
    rpc.call('thread/name/set', dict(threadId=record['thread'], name=thread_name(store.scope, goal)))
    active = status == 'active'
    uncertain = (record.get('submission') or {}).get('state') == 'sending'
    if not active and not uncertain:
        unchanged(store, goal['id'])
        config = rpc.call('config/read', dict(cwd=cwd, includeLayers=False)).get('config', {})
        effort = (config.get('plan_mode_reasoning_effort') or session.get('reasoningEffort')
                  or plan.get('reasoning_effort'))
        text = body(store, goal)
        model = session.get('model')
        if not isinstance(model, str) or not model:
            raise ValueError('Codex did not expose the effective model for Plan Mode')
        request = dict(key=str(uuid.uuid4()), state='sending',
                       brief_hash=hashlib.sha256(text.encode()).hexdigest())
        record['submission'] = request
        link.write(record)
        result = rpc.call('turn/start', dict(threadId=record['thread'],
            clientUserMessageId=request['key'], input=[dict(type='text', text=text)],
            collaborationMode=dict(mode='plan', settings=dict(model=model,
                reasoning_effort=effort,
                developer_instructions=None))))
        turn = result.get('turn', {}).get('id')
        if not isinstance(turn, str) or not turn:
            raise ValueError('Codex did not confirm submission; resume the linked thread before retrying')
        request.update(state='accepted', turn=turn)
        link.write(record)
        # Resume exposes the server's actual selected mode to the interactive TUI.
        check = rpc.call('thread/resume', dict(threadId=record['thread'], excludeTurns=True))
        if check.get('collaborationMode', {}).get('mode') != 'plan':
            rpc.call('turn/interrupt', dict(threadId=record['thread'], turnId=turn))
            raise ValueError('Codex did not retain Plan Mode; the planning turn was interrupted')
        record['_started_turn'] = turn  # Invocation-local; never written into the link.
    elif uncertain:
        print('todo: previous submission was interrupted; attaching without resending. Review the thread before sending another /plan brief.', file=sys.stderr)
    return record


def launch(store, goal, *, new=False, dry_run=False):
    from interaction import terminal
    from platform_info import detect
    link = Link(store.scope, goal['id'])
    if dry_run:
        record = None if new else link.read()
        from files.catalog import Presentation
        ui = Presentation(detail_indent=2)
        ui.heading('Plan in Codex · preview')
        for label, value in [('Goal', goal['id']), ('Thread name', thread_name(store.scope, goal)),
                ('Thread', record['thread'] if record else 'New conversation'),
                ('Directory', store.scope['root'] or (record['cwd'] if record else str(Path.cwd()))),
                ('Connection', 'Existing Termux runit server' if detect()['platform'] == 'termux' else 'Native Codex local daemon'),
                ('Mode', 'Plan'), ('Subgoals', str(sum(not g['removed'] for g in store.descendants(goal['id']))))]:
            ui.detail(label, value)
        return 0
    if not terminal():
        raise ValueError('todo plan requires an interactive terminal; use --dry-run or todo brief ID')
    from todo_codex import Backend
    backend = Backend()
    with backend.connect() as rpc:
        with link.locked():
            record = prepare(store, goal, link, backend, rpc, new)
        try:
            code = subprocess.call(backend.argv(record['thread'], record['cwd']), cwd=record['cwd'],
                                   env=backend.environment)
        except OSError:
            if record.get('_started_turn'):
                rpc.call('turn/interrupt', dict(threadId=record['thread'], turnId=record['_started_turn']))
            raise ValueError('Codex terminal could not start; the linked thread is retained for resume') from None
        if code and record.get('_started_turn'):
            rpc.call('turn/interrupt', dict(threadId=record['thread'], turnId=record['_started_turn']))
        return 128 - code if code < 0 else code


def window(store, goal, context):
    """Start a controller-owned process; no keys are sent into an existing pane."""
    from menu_tmux import request_file
    unchanged(store, goal['id'])
    context.verify()
    with request_file(dict(schema=1, scope=store.scope, goal=goal['id'], guard=store.guard,
                           environment=dict(os.environ))) as request:
        result = subprocess.run(context.command('new-window', '-d', '-P', '-F', '#{window_id}',
            '-t', context.session + ':', '-n', window_name().replace('#', '##'),
            '-c', (store.scope['root'] or context.cwd).replace('#', '##'),
            sys.executable, '-B', str(Path(__file__).resolve()), 'worker', str(request)),
            capture_output=True, text=True, timeout=5)
        identity = result.stdout.strip()
        if result.returncode or not re.fullmatch(r'@[0-9]+', identity):
            raise ValueError('Could not open the Codex tmux window')
        ready = request.with_suffix('.accepted')
        deadline = time.monotonic() + 5
        while not ready.exists() and time.monotonic() < deadline:
            time.sleep(.02)
        if not ready.exists():
            raise ValueError('Codex window did not accept the handoff; inspect the new window')
        context.verify()
        context.observe('switch-client', '-c', context.client, '-t', identity)
    return 0


def worker(path):
    from menu_tmux import read_request
    data = read_request(path)
    environment = data['environment']
    if (not isinstance(environment, dict) or not all(isinstance(k, str) and isinstance(v, str)
            and k and '=' not in k and '\0' not in k + v for k, v in environment.items())):
        raise ValueError('Invalid Codex window environment')
    # Retain this new pane's tmux identity, not the originating pane's identity.
    tmux = {k: os.environ[k] for k in ('TMUX', 'TMUX_PANE') if k in os.environ}
    os.environ.clear(); os.environ.update(environment); os.environ.update(tmux)
    for key in ('DOTS_MENU_CONTEXT', 'DOTS_MENU_SPOOL_DIR', 'DOTS_MENU_READER_HANDOFF', 'DOTS_KEYS_TARGET_PANE'):
        os.environ.pop(key, None)
    store = Goals(data['scope'])
    if store.guard != data['guard']:
        raise ValueError('Goals changed before the Codex window opened; reopen the goal')
    goal = store.find(data['goal'], False)
    Path(path).with_suffix('.accepted').touch(mode=0o600, exist_ok=False)
    return launch(store, goal)


if __name__ == '__main__':
    try:
        if len(sys.argv) != 3 or sys.argv[1] != 'worker': raise ValueError('Invalid private Codex handoff')
        code = worker(sys.argv[2])
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print('todo: ' + clean(str(error)), file=sys.stderr)
        try: input('Press Enter to close. ')
        except (EOFError, KeyboardInterrupt): pass
        code = 1
    except KeyboardInterrupt:
        code = 130
    sys.exit(code)
