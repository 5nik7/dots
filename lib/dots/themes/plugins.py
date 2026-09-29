#!/usr/bin/env python3
"""Explicit local theme plugins. Downloaded themes are never executable roots."""
import argparse
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import subprocess
import sys

LIB = Path(__file__).resolve().parent
sys.path.insert(0, str(LIB.parent))
sys.path.insert(0, str(LIB.parent / 'files'))
from catalog import Presentation, atomic_json, read_json
from transactions import exists, parents_safe, private_directory
from progress import Progress, configure

PATTERN = re.compile(r'([0-9]+)-([a-z][a-z0-9-]*)\.sh\Z')
BUNDLED = {'gtk': ('gtk-launch', 'gtk-3.0'), 'qt6ct': ('qt6ct', 'qt6ct')}


def roots():
    home = Path(os.environ['HOME'])
    config = Path(os.environ.get('XDG_CONFIG_HOME') or home / '.config')
    state = Path(os.environ.get('XDG_STATE_HOME') or home / '.local/state')
    for path in (home, config, state):
        if not path.is_absolute() or any(ord(c) < 32 for c in str(path)):
            raise ValueError('HOME and XDG roots must be absolute paths without control characters')
    return home, config, state / 'dots'


def safe_file(path, optional=False):
    parents_safe(path)
    if optional and not exists(path):
        return
    if not exists(path) or not stat.S_ISREG(path.lstat().st_mode):
        raise ValueError(f'expected a regular file, not a link or special file: {path}')


def selection(config):
    path = config / 'dots/theme-plugins.json'
    safe_file(path, optional=True)
    data = read_json(path) if exists(path) else {'schema': 1, 'enabled': {}}
    if set(data) != {'schema', 'enabled'} or not isinstance(data['enabled'], dict):
        raise ValueError('invalid theme plugin selection')
    for name, identity in data['enabled'].items():
        if (not re.fullmatch('[a-z][a-z0-9-]*', name) or not isinstance(identity, str)
                or identity.split('/', 1)[0] not in ('bundled', 'user')
                or not PATTERN.fullmatch(identity.split('/', 1)[-1])
                or PATTERN.fullmatch(identity.split('/', 1)[-1])[2] != name):
            raise ValueError('invalid enabled plugin identity')
    return path, data


def discover(config, selected):
    rows = []
    for origin, directory in [('bundled', LIB / 'plugins'), ('user', config / 'dots/hooks/theme-set.d')]:
        parents_safe(directory / 'placeholder')
        if not directory.exists():
            continue
        if not directory.is_dir():
            raise ValueError(f'not a hook directory: {directory}')
        for path in sorted(directory.iterdir()):
            match = PATTERN.fullmatch(path.name)
            if not match:
                continue
            identity = origin + '/' + path.name
            row = {'name': match[2], 'origin': origin, 'file': path.name,
                   'path': str(path), 'order': int(match[1]), 'identity': identity,
                   'enabled': selected.get(match[2]) == identity, 'problems': []}
            if not stat.S_ISREG(path.lstat().st_mode):
                row['problems'].append('hook must be a regular file, not a link or special file')
            rows.append(row)
    for row in rows:
        if sum(other['name'] == row['name'] for other in rows) != 1:
            row['problems'].append('ambiguous plugin name; rename the conflicting user hook')
    known = {row['identity'] for row in rows}
    for name, identity in selected.items():
        if identity not in known:
            rows.append({'name': name, 'origin': identity.split('/')[0], 'file': identity.split('/')[1],
                         'path': '', 'order': 0, 'identity': identity, 'enabled': True,
                         'problems': ['enabled hook is missing; disable it or restore its file']})
    return sorted(rows, key=lambda row: (row['order'], row['file'], row['origin']))


def availability(row, config):
    if row['problems']:
        return 'invalid', '; '.join(row['problems'])
    if os.name != 'posix' or sys.platform not in ('linux', 'android'):
        return 'unavailable', 'execution requires Linux, WSL, or Termux'
    if not shutil.which('bash'):
        return 'unavailable', 'missing dependency: bash'
    if row['origin'] == 'bundled':
        command, directory = BUNDLED[row['name']]
        if not shutil.which(command):
            return 'unavailable', 'missing optional app: ' + command
        if not (config / directory).is_dir():
            return 'unavailable', 'app configuration directory is absent: ' + directory
    return 'available', ''


@contextmanager
def locked(path):
    safe_file(path, optional=True)
    private_directory(path.parent)
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError('invalid lock file')
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('another theme or plugin operation is running; retry when it finishes') from None
        yield
    finally:
        os.close(fd)


def published(state):
    active = state / 'current/theme'
    parents_safe(active)
    if not active.is_symlink():
        raise ValueError('no published theme; apply a theme first')
    generation = Path(os.readlink(active))
    if (generation.parent != state / 'themes/generations'
            or not re.fullmatch(r'g\.[a-zA-Z0-9]+', generation.name)):
        raise ValueError('invalid published theme pointer')
    palette = generation / 'palette.json'
    safe_file(palette)
    safe_file(generation / 'status')
    if (generation / 'status').read_text().strip() != 'committed':
        raise ValueError('theme publication is incomplete; refresh to recover it first')
    data = read_json(palette)
    colors = data.get('colors', {})
    if not isinstance(colors, dict):
        raise ValueError('invalid normalized color map in published palette')
    required = ['background', 'foreground', 'cursor', 'selection_background', 'selection_foreground']
    required += ['color' + str(i) for i in range(16)]
    if any(not isinstance(colors.get(k), str) or not re.fullmatch('#[a-fA-F0-9]{6}', colors[k]) for k in required):
        raise ValueError('published palette lacks normalized colors; run dots theme refresh')
    if (not isinstance(data.get('id'), str) or not re.fullmatch('[a-z][a-z0-9_-]*', data['id'])
            or data.get('mode') not in ('light', 'dark')):
        raise ValueError('invalid published theme identity')
    return generation, data


def environment(state, generation, data, reason):
    env = {k: v for k, v in os.environ.items()
           if k not in ('BASH_ENV', 'ENV') and not k.startswith('BASH_FUNC_')}
    env.update(DOTS_THEME_PLUGIN_RUNNING='1', DOTS_THEME_DIR=str(generation),
               DOTS_THEME_CURRENT=str(state / 'current/theme'),
               DOTS_THEME_PALETTE=str(generation / 'palette.json'),
               DOTS_THEME_ID=data['id'], DOTS_THEME_MODE=data['mode'], DOTS_THEME_REASON=reason,
               DOTS_THEME_PLUGIN_PYTHON=sys.executable, DOTS_THEME_PLUGIN_MANAGER=str(LIB / 'plugins.py'),
               PYTHONDONTWRITEBYTECODE='1', DOTS_PROGRESS='never')
    names = {'primary_background': 'background', 'primary_foreground': 'foreground', 'cursor_color': 'cursor',
             'selection_background': 'selection_background', 'selection_foreground': 'selection_foreground'}
    ansi = ['black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white']
    names.update({prefix + name: 'color' + str(offset + i)
                  for prefix, offset in [('normal_', 0), ('bright_', 8)] for i, name in enumerate(ansi)})
    for name, key in names.items():
        value = data['colors'][key][1:].lower()
        env[name] = value
        env['rgb_' + name] = ', '.join(str(int(value[i:i+2], 16)) for i in (0, 2, 4))
    return env


def child(argv, env, cwd):
    # Drain both streams, but retain at most 16 KiB. No persistent hook logs.
    process = subprocess.Popen(argv, env=env, cwd=cwd, stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               close_fds=True, start_new_session=True)
    output = bytearray()
    try:
        while block := process.stdout.read(4096):
            output.extend(block[:max(0, 16384 - len(output))])
        return process.wait(), output.decode('utf-8', errors='replace')
    finally:
        process.stdout.close()
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()


def run(rows, config, state, reason):
    if any(row['problems'] for row in rows):
        raise ValueError('invalid plugin catalog; run dots theme plugins doctor')
    generation, data = published(state)
    env = environment(state, generation, data, reason)
    results = []
    for row in rows:
        if not row['enabled']:
            continue
        available, detail = availability(row, config)
        result = {'name': row['name'], 'status': 'skipped', 'detail': detail}
        if available == 'available':
            try:
                safe_file(Path(row['path']))
                with Progress('Running theme plugin ' + row['name']) as progress:
                    progress.update('Running theme plugin ' + row['name'])
                    code, output = child([shutil.which('bash'), '--noprofile', '--norc', '--', row['path']],
                                         dict(env, DOTS_THEME_PLUGIN=row['name']), roots()[0])
                result.update(status='success' if code == 0 else 'skipped' if code == 77 else 'failure', exit_code=code)
                if row['origin'] == 'bundled' and code in (0, 77):
                    report = json.loads(output)
                    if not isinstance(report, dict) or report.get('status') not in ('success', 'skipped'):
                        raise ValueError('invalid bundled adapter result')
                    result.update(report)
                elif output:
                    result['_diagnostics'] = output.rstrip()
                if code not in (0, 77):
                    result['detail'] = 'hook failed; retry with dots theme plugins run ' + row['name']
            except (ValueError, OSError, subprocess.SubprocessError) as error:
                result.update(status='failure', detail=str(error))
        results.append(result)
    return results


def inspect(rows, config, state):
    try:
        generation, _ = published(state)
        palette_problem = ''
    except (ValueError, OSError) as error:
        generation, palette_problem = None, str(error)
    for row in rows:
        row['availability'], row['detail'] = availability(row, config)
        row['checks'] = []
        if palette_problem:
            row['checks'].append(palette_problem)
        if not row['problems']:
            env = {k: v for k, v in os.environ.items() if k not in ('BASH_ENV', 'ENV') and not k.startswith('BASH_FUNC_')}
            bash = shutil.which('bash')
            if bash:
                code, _ = child([bash, '--noprofile', '--norc', '-n', '--', row['path']], env, roots()[0])
                if code:
                    row['problems'].append('Bash syntax check failed')
            if row['origin'] == 'bundled' and generation and row['availability'] == 'available':
                from plugin_apps import prepare
                try:
                    changed, _, _, _, _ = prepare(row['name'], config, state, generation)
                    row['targets'] = [str(path) for path in changed]
                    row['checks'].append('Would update: ' + ', '.join(row['targets']) if changed else 'App files unchanged')
                except (ValueError, OSError) as error:
                    row['problems'].append(str(error))
                if row['name'] == 'qt6ct' and os.environ.get('QT_QPA_PLATFORMTHEME') != 'qt6ct':
                    row['checks'].append('session QT_QPA_PLATFORMTHEME is not qt6ct; configure your desktop session to use it')
    return rows


def emit(action, rows, as_json):
    if as_json:
        print(json.dumps({'schema': 1, 'action': action, 'plugins': rows}, ensure_ascii=False))
        return
    ui = Presentation()
    ui.heading('Theme plugins')
    if not rows:
        ui.detail('Status', 'No enabled plugins' if action == 'run' else 'No plugins')
    for row in rows:
        status = row.get('status', 'enabled' if row.get('enabled') else 'disabled')
        color = '91' if status == 'failure' or row.get('problems') else '92' if status in ('success', 'enabled') else '90'
        ui.emit('  ' + ui.paint(row['name'], '94') + '  ' + ui.paint(status, color)
                + ('  ' + ui.clean(row['origin']) if 'origin' in row else ''))
        for detail in [row.get('availability', ''), row.get('detail', ''), *row.get('problems', []), *row.get('checks', [])]:
            if detail:
                ui.detail('', detail)
        if row.get('transaction'):
            ui.detail('Transaction', row['transaction'])


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    action = args.pop(0) if args else 'list'
    parser = argparse.ArgumentParser(prog='dots theme plugins ' + action, add_help=False)
    parser.add_argument('name', nargs='?')
    parser.add_argument('--json', action='store_true')
    opt = parser.parse_args(args)
    automatic = action == '__automatic'
    if action not in ('list', 'doctor', 'run', 'enable', 'disable', '__automatic', '__names', '__app'):
        raise ValueError('unknown plugin action')
    if action in ('enable', 'disable', '__app') and not opt.name:
        raise ValueError('a plugin name is required')
    if action in ('list', '__names', '__automatic') and opt.name:
        raise ValueError('this action takes no plugin name')
    if opt.json and action not in ('list', 'doctor', 'run'):
        parser.error('--json is available for list, doctor and run')
    home, config, state = roots()
    if action == '__app':
        if not os.environ.get('DOTS_THEME_PLUGIN_RUNNING') or opt.name not in BUNDLED:
            raise ValueError('internal app adapter requires a plugin run')
        from plugin_apps import apply
        generation, _ = published(state)
        if str(generation) != os.environ.get('DOTS_THEME_DIR'):
            raise ValueError('published theme changed during plugin run')
        print(json.dumps(apply(opt.name, config, state, generation)))
        return 0
    if action in ('run', '__automatic', 'enable', 'disable') and os.environ.get('DOTS_THEME_PLUGIN_RUNNING'):
        raise ValueError('recursive theme plugin mutation is refused; read-only commands are allowed')
    path, data = selection(config)
    rows = discover(config, data['enabled'])
    if action == '__names':
        print('\n'.join(row['name'] for row in rows if not row['problems']))
        return 0
    if opt.name:
        rows = [row for row in rows if row['name'] == opt.name]
        if not rows:
            raise ValueError('unknown plugin: ' + opt.name)
        if action == 'run' and len(rows) == 1 and not rows[0]['enabled']:
            raise ValueError('plugin is disabled; use dots theme plugins enable ' + opt.name)
    if action in ('enable', 'disable'):
        with locked(state / 'theme-plugins/lock'):
            path, data = selection(config)
            rows = [row for row in discover(config, data['enabled']) if row['name'] == opt.name]
            if len(rows) != 1 or (action == 'enable' and rows[0]['problems']):
                raise ValueError('invalid or ambiguous plugin; run dots theme plugins doctor')
            previous = dict(data['enabled'])
            if action == 'enable':
                data['enabled'][opt.name] = rows[0]['identity']
            else:
                data['enabled'].pop(opt.name, None)
            if previous != data['enabled']:
                private_directory(path.parent)
                safe_file(path, optional=True)
                atomic_json(path, data)
            rows[0]['enabled'] = action == 'enable'
        emit(action, rows, opt.json)
        return 0
    if action in ('list', 'doctor'):
        if action == 'doctor':
            inspect(rows, config, state)
        else:
            for row in rows:
                row['availability'], row['detail'] = availability(row, config)
        emit(action, rows, opt.json)
        return int(any(row['problems'] for row in rows))
    def execute():
        with locked(state / 'theme-plugins/lock'):
            _, latest = selection(config)
            catalog = discover(config, latest['enabled'])
            if any(row['problems'] for row in catalog):
                raise ValueError('invalid plugin catalog; run dots theme plugins doctor')
            targets = [row for row in catalog if not opt.name or row['name'] == opt.name]
            if opt.name and (not targets or not targets[0]['enabled']):
                raise ValueError('plugin is disabled; use dots theme plugins enable ' + opt.name)
            configure(not opt.json)
            with Progress('Running theme plugins'):
                results = run(targets, config, state, os.environ.get('DOTS_THEME_PLUGIN_REASON', 'set') if automatic else 'manual')
            for result in results:
                diagnostics = result.pop('_diagnostics', '')
                if diagnostics:
                    Presentation(sys.stderr).detail(result['name'], diagnostics)
            emit('run', results, opt.json)
            return int(any(row['status'] == 'failure' for row in results))
    if automatic:
        # Only the shared publisher supplies FD 9. Verify and retain its lock.
        lock = state / 'themes/lock'
        safe_file(lock)
        if not os.path.samestat(os.fstat(9), lock.stat()):
            raise ValueError('automatic plugin run requires the publisher lock')
        fcntl.flock(9, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return execute()
    published(state)  # Refuse absent/invalid publication before creating lock state.
    with locked(state / 'themes/lock'):
        return execute()


def interrupted(signum, frame):
    raise KeyboardInterrupt


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, interrupted)
    try:
        sys.exit(main())
    except (ValueError, OSError, KeyError) as error:
        Presentation(sys.stderr).detail('Theme plugins', str(error))
        sys.exit(1)
    except KeyboardInterrupt:
        Presentation(sys.stderr).detail('Theme plugins', 'Interrupted; inspect file history/recovery before retrying')
        sys.exit(130)
