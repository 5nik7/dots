"""Small terminal input and the explicitly requested Termux tab handoff."""
import base64
from dataclasses import asdict
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.parse import quote

from interaction import SelectionEnded, terminal
from menu_tmux import read_request, request_file
from resources import clean


def input_name(initial, title):
    if not terminal():
        raise ValueError('session names require a terminal')
    if shutil.which('gum') and os.environ.get('TERM') != 'dumb':
        from resources import Resources, read_data
        environment = dict(os.environ)
        from files.catalog import Presentation
        if Presentation().color:
            environment.pop('NO_COLOR', None)
            for line in read_data(Resources().root / 'gum_env.sh').splitlines():
                match = re.fullmatch(r"export (GUM_[A-Z_]+)='(#[a-fA-F0-9]{6})'", line)
                if match:
                    environment[match[1]] = match[2]
        else:
            environment['NO_COLOR'] = '1'
        result = subprocess.run(['gum', 'input', '--header=' + clean(title), '--prompt=Name: ',
                                 '--value=' + initial], stdout=subprocess.PIPE, text=True, env=environment)
        if result.returncode:
            raise SelectionEnded(130 if result.returncode in (1, 130, -2) else 2)
        return result.stdout.removesuffix('\n')
    # readline is optional. Its startup hook only inserts literal editable text.
    try:
        import readline
    except ImportError:
        print(clean(title) + '\nDefault: ' + clean(initial))
        value = input('Name (blank uses default, Esc cancels): ')
        if value == '\x1b':
            raise SelectionEnded(130)
        return value or initial
    print(clean(title) + '\nCtrl-C: cancel')
    readline.set_startup_hook(lambda: readline.insert_text(initial))
    try:
        value = input('Name: ')
        if '\x1b' in value:
            raise SelectionEnded(130)
        return value
    finally:
        readline.set_startup_hook(None)


def prompt(initial, title, context=None):
    try:
        if context is None:
            return input_name(initial, title)
        with request_file(dict(schema=1, initial=initial, title=title)) as path:
            columns, lines = context.verify()
            code = context.popup([sys.executable, '-B', str(Path(__file__).resolve()), 'input', str(path)],
                                 size=(min(72, columns - 2), min(8, lines - 2)))
            answer = path.with_suffix('.answer')
            if not answer.exists():
                if code not in (0, 1, 130, -1, 129):
                    raise ValueError('session name input failed')
                return None
            data = read_request(answer)
            if not isinstance(data.get('value'), str):
                raise ValueError('invalid session name response')
            return data['value']
    except (SelectionEnded, KeyboardInterrupt, EOFError) as error:
        if isinstance(error, SelectionEnded) and error.status != 130:
            raise
        return None


def is_termux():
    from platform_info import detect
    return detect()['platform'] == 'termux'


def legacy_am():
    """Only the app-installed compatibility adapter, never Android's system am."""
    prefix = os.environ.get('TERMUX__PREFIX') or os.environ.get('PREFIX', '')
    root = Path(prefix)
    if not root.is_absolute() or not prefix.rstrip('/').endswith('/files/usr'):
        return None
    candidate = root / 'bin/am'
    if candidate.is_file() and os.access(candidate, os.X_OK) and candidate.resolve().parent == (root / 'bin').resolve():
        return str(candidate)
    return None


def transport_detail(text, secrets=()):
    # Adapter errors can echo an Intent containing the entire private handoff.
    # Keep useful diagnostics, but never reproduce commands, paths or payloads.
    text = text or ''
    for secret in sorted((s for s in secrets if s), key=len, reverse=True):
        text = text.replace(secret, '[private]')
    lines = []
    for line in text.splitlines():
        if re.search(r'(?i)intent\s*\{|com\.termux\.execute|service_execute|\b(?:dat|cmp|extras)=', line):
            continue
        line = re.sub(r'[A-Za-z0-9_-]{80,}={0,2}', '[private]', line)
        line = re.sub(r'(?<!\w)/(?:[^\s,:;]+)', '[path]', line)
        line = clean(line).strip()
        if line:
            lines.append(line[:240])
        if len(lines) == 2:
            break
    return '; '.join(lines) or 'no diagnostic supplied'


def termux_transport():
    if not is_termux():
        raise ValueError('New Termux is only available in Termux')
    failures = []
    for executable, flag, name in ((shutil.which('termux-am'), '--am-help', 'termux-am'),
                                    (legacy_am(), '--help', 'am')):
        if not executable:
            failures.append(name + ': unavailable')
            continue
        try:
            result = subprocess.run([executable, flag], capture_output=True, text=True, timeout=4)
        except subprocess.TimeoutExpired:
            failures.append(name + ': help probe timed out')
        except OSError as error:
            failures.append(name + ': ' + transport_detail(error.strerror))
        else:
            if result.returncode == 0 and 'startservice' in result.stdout:
                return executable
            failures.append(f'{name}: help probe status {result.returncode}; ' +
                            transport_detail(result.stderr or result.stdout))
    raise ValueError('No working Termux launch adapter. ' + ' | '.join(failures))


def launch_termux(server, session, cwd, *, transport=None):
    if not is_termux():
        raise ValueError('New Termux is only available in Termux')
    executable = transport or termux_transport()
    server.validate(session)
    payload = base64.urlsafe_b64encode(json.dumps(dict(schema=1, server=asdict(server),
        session=asdict(session)), ensure_ascii=True).encode()).decode()
    # Android's --esa uses comma-separated args (backslash escapes commas).
    # Base64 carries all observed strings as data, never interpolated shell code.
    args = ['-B', str(Path(__file__).resolve()), 'attach', payload]
    encoded_args = ','.join(arg.replace(',', '\\,') for arg in args)
    package = os.environ.get('TERMUX_APP__PACKAGE_NAME', 'com.termux')
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)+', package):
        raise ValueError('invalid Termux package identity')
    command = [executable, 'startservice', '-n', package + '/com.termux.app.TermuxService',
               '-a', 'com.termux.service_execute', '-d', 'com.termux.file:' + quote(sys.executable, safe='/'),
               '--esa', 'com.termux.execute.arguments', encoded_args,
               '--es', 'com.termux.execute.cwd', cwd,
               '--ez', 'com.termux.execute.background', 'false',
               '--es', 'com.termux.execute.session_action', '0']
    name = Path(executable).name
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=15)
    except subprocess.TimeoutExpired:
        raise ValueError(f'Termux {name} launch timed out; no retry was sent. The tmux session is still available.') from None
    except OSError as error:
        raise ValueError(f'Termux {name} launch failed: {transport_detail(error.strerror)}. The tmux session is still available.') from None
    if result.returncode or re.search(r'(?im)^\s*(?:error|exception|securityexception)\b', result.stdout + '\n' + result.stderr):
        detail = transport_detail(result.stderr + '\n' + result.stdout,
                                  (payload, encoded_args, cwd, server.socket, str(Path(__file__).resolve())))
        raise ValueError(f'Termux {name} launch status {result.returncode}: {detail}. The tmux session is still available.')
    return 0


def attach(encoded):
    from menu_sessions import Server, Session
    try:
        data = json.loads(base64.b64decode(encoded, altchars=b'-_', validate=True))
        if data.get('schema') != 1:
            raise ValueError()
        server, session = Server(**data['server']), Session(**data['session'])
        if (not os.path.isabs(server.executable) or not os.path.isabs(server.socket)
                or type(server.pid) is not int or server.pid <= 0
                or not re.fullmatch(r'\$[0-9]+', session.id) or type(session.created) is not int):
            raise ValueError()
    except (ValueError, TypeError, KeyError):
        raise ValueError('invalid Termux session handoff') from None
    # This is a new terminal process, not a client nested inside the old session.
    os.environ.pop('TMUX', None)
    os.environ.pop('TMUX_PANE', None)
    os.environ.pop('DOTS_MENU_CONTEXT', None)
    return server.select(session)


def main():
    try:
        if len(sys.argv) != 3:
            return 2
        if sys.argv[1] == 'input':
            path = Path(sys.argv[2]); data = read_request(path)
            value = input_name(data['initial'], data['title'])
            fd = os.open(path.with_suffix('.answer'), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                json.dump(dict(schema=1, value=value), stream)
            return 0
        if sys.argv[1] == 'attach':
            return attach(sys.argv[2])
        return 2
    except (SelectionEnded, KeyboardInterrupt, EOFError):
        return 130
    except (ValueError, OSError, subprocess.SubprocessError):
        print('dots: session input or Termux handoff failed; reopen the session menu.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
