"""Native Xonsh tool activation. Generator output may depend on the session PATH."""
import os
import shutil


def activate(session, events):
    ctx, env = session.ctx, session.env
    ready = ctx.get('_dots_xonsh_tools', ())
    search_path = os.pathsep.join(env['PATH'])
    selected = ctx.get('dots_shell_tools')
    if selected is None:
        if 'zoxide' not in ready and 'z' not in session.aliases and 'zi' not in session.aliases:
            executable = shutil.which('zoxide', path=search_path)
            if executable and not any(shutil.which(cmd, path=search_path) for cmd in ('z', 'zi')):
                for cmd in ('z', 'zi'):
                    session.aliases[cmd] = _lazy_zoxide(session, executable, cmd)
        return
    if isinstance(selected, str):
        selected = selected.split()
    if not selected:
        return
    tools = [('zoxide', ('init', 'xonsh')), ('mise', ('activate', 'xonsh'))]
    if not any(env.is_manually_set(key) for key in ('PROMPT', 'RIGHT_PROMPT')):
        tools.append(('starship', ('init', 'xonsh', '--print-full-init')))
    tools.append(('atuin', ('init', 'xonsh', '--disable-ctrl-r', '--disable-up-arrow')))
    tools.append(('direnv', ()))
    for name, args in tools:
        if name in ready or (name not in selected and 'all' not in selected):
            continue
        executable = shutil.which(name, path=search_path)
        if not executable:
            continue
        if name == 'direnv':
            def apply_direnv(**event):
                _apply_direnv(executable, env)
            events.on_chdir(apply_direnv)
            _apply_direnv(executable, env)
        else:
            if name == 'atuin':
                from importlib.util import find_spec
                if not find_spec('prompt_toolkit'):
                    continue
            if not _generate(executable, args, session):
                continue
            search_path = os.pathsep.join(env['PATH'])
        ready = ctx.setdefault('_dots_xonsh_tools', set())
        ready.add(name)


def _lazy_zoxide(session, executable, name):
    def first_jump(args):
        previous = session.aliases[name]
        if not _generate(executable, ('init', 'xonsh'), session):
            return 1
        target = session.aliases[name]
        if target is previous or not callable(target):
            return 1
        session.ctx.setdefault('_dots_xonsh_tools', set()).add('zoxide')
        return target(args)

    first_jump.__xonsh_threadable__ = False
    return first_jump


def _generate(executable, args, session):
    import subprocess
    import sys

    try:
        result = subprocess.run([executable, *args], env=session.env.detype(), capture_output=True,
                                text=True, timeout=5)
        if result.returncode or not result.stdout.strip():
            return False
        session.execer.exec(result.stdout, glbs=session.ctx, locs=session.ctx)
        return True
    except Exception as error:
        # Exec errors can contain generated environment values.
        print(f'dots: {os.path.basename(executable)} initialization failed ({type(error).__name__})',
              file=sys.stderr)
        return False


def _apply_direnv(executable, env):
    import json
    import subprocess
    import sys

    try:
        result = subprocess.run([executable, 'export', 'json'], env=env.detype(), stdout=subprocess.PIPE,
                                text=True, encoding='utf-8', timeout=5)
        if result.returncode or not result.stdout.strip():
            return
        changes = json.loads(result.stdout)
        if changes is None:
            return
        if not isinstance(changes, dict) or any(
            not key or '=' in key or '\x00' in key or
            (value is not None and (not isinstance(value, str) or '\x00' in value))
            for key, value in changes.items()
        ):
            raise ValueError('invalid direnv export')
        # Xonsh converts PATH and other typed variables when assigned. Restore
        # earlier changes if one of those conversions fails.
        previous = {}
        try:
            for key, value in changes.items():
                previous[key] = (env.is_manually_set(key), env.get(key))
                if value is None:
                    env.pop(key, None)
                else:
                    env[key] = value
        except Exception:
            for key, (was_set, prior) in reversed(previous.items()):
                if was_set:
                    env[key] = prior
                else:
                    env.pop(key, None)
            raise
    except Exception as error:
        print(f'dots: direnv export failed ({type(error).__name__})', file=sys.stderr)
