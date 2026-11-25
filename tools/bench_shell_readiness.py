#!/usr/bin/env python3
"""Compare interactive first input and first directory completion in public PTYs."""
import argparse
from contextlib import ExitStack, contextmanager
import json
import os
from pathlib import Path
import select
import shutil
import statistics
import sys
import subprocess
import time

from test_shell_init import executable
from zsh_interactive import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib/dots'))
from debug.fixtures import copy_tree, fixture
from bootstrap_snippet import installed_nu_entry


@contextmanager
def interactive_fixture(source, shell, *, installed, with_tools=False, enable_native_tools=False):
    with fixture(source) as (repo, env, base):
        home = Path(env['HOME'])
        env.update(ZDOTDIR=str(home), DOTS_INIT_COMPLETION='1', PYTHONDONTWRITEBYTECODE='1',
                   XONSH_DATA_DIR=str(home/'xonsh-data'), XONSH_CACHE_DIR=str(home/'xonsh-cache'),
                   XONTRIBS_AUTOLOAD_DISABLED='*', TERM='xterm-256color')
        env['PREFIX'] = env['TERMUX__PREFIX'] = str(base/'prefix/usr') if 'TERMUX_VERSION' in env else str(base/'prefix')
        # No vendor profiles, remote Git providers or personal plugins.
        names = ['fish', 'nu', 'uv', 'uvx', 'pip', 'basename', 'ls', 'which', 'env', 'stty']
        if with_tools:
            names.extend(('zoxide', 'direnv', 'starship', 'fzf'))
            env.update(STARSHIP_CONFIG=str(home/'starship.toml'), _ZO_DATA_DIR=str(home/'zoxide'),
                       DIRENV_CONFIG=str(home/'direnv'), STARSHIP_CACHE=str(home/'starship-cache'))
            (home/'starship.toml').write_text('format = "$character"\n')
        for name in names:
            provider = executable(name)
            if provider and not (base/'commands'/name).exists():
                (base/'commands'/name).symlink_to(provider)
        (home/'readiness-directory').mkdir()
        for provider in ('bash', 'zsh', '_patina'):
            completion = Path('plugins/anodize/completion')/provider
            if (source/completion).is_file():
                (repo/completion).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source/completion, repo/completion)
        for rel in ('default', 'shells/fish', 'shells/nushell', 'shells/xonsh'):
            if rel == 'default':
                (repo/rel).mkdir(exist_ok=True)
                for item in ('config.json', 'colors.toml', 'icons.toml'):
                    if (source/rel/item).is_file():
                        shutil.copy2(source/rel/item, repo/rel/item)
            else:
                copy_tree(source/rel, repo/rel, source, repo)
        (home/'dots').symlink_to(repo, target_is_directory=True)
        locations = dict(bash=home/'.bashrc', zsh=home/'.zshrc', xonsh=home/'.xonshrc',
                         fish=Path(env['XDG_CONFIG_HOME'])/'fish/config.fish',
                         nu=Path(env['XDG_CONFIG_HOME'])/'nushell/config.nu')
        entry = locations[shell]
        if shell in ('fish','nu','xonsh'):
            family, source_name = {'fish': ('fish','config.fish'), 'nu': ('nushell','config.nu'),
                                   'xonsh': ('xonsh','.xonshrc')}[shell]
            entry.parent.mkdir(parents=True, exist_ok=True)
            entry.symlink_to(repo/'shells'/family/source_name)
        if installed:
            templates = source/'shells/bootstrap'
            helper = home/'.local/share/dots/bootstrap'
            helper.mkdir(parents=True)
            for helper_name in ('locate.sh', 'locate.ps1'):
                shutil.copy2(source/'lib/dots/shell/bootstrap'/helper_name, helper/helper_name)
            (helper/'checkout').write_text(str(repo) + '\n')
            (helper/'entry.nu').write_text(installed_nu_entry(repo), encoding='utf-8')
            entry.unlink()
            name = dict(bash='rc.sh', zsh='rc.sh', fish='config.fish', nu='config.nu', xonsh='rc.xsh')[shell]
            shutil.copy2(templates/name, entry)
            if enable_native_tools and shell in ('fish', 'nu', 'xonsh'):
                filename, setting = {'fish': ('init.fish', 'set -g dots_shell_tools all'),
                                     'nu': ('init.nu', "$env.dots_shell_tools = ['all']"),
                                     'xonsh': ('init.xsh', "dots_shell_tools = ['all']")}[shell]
                for platform in ('termux', 'linux'):
                    directory = repo/'profiles'/platform/'shells'
                    directory.mkdir(parents=True, exist_ok=True)
                    (directory/filename).write_text(setting + '\n')
        engine = executable(shell)
        if shell == 'zsh':
            argv = [engine, '-di']
        elif shell == 'bash':
            argv = [engine, '--noprofile', '--rcfile', str(entry), '-i']
        elif shell == 'fish':
            argv = [engine, '--no-config', '-i', '-C', 'source "$XDG_CONFIG_HOME/fish/config.fish"']
        elif shell == 'nu':
            argv = [engine, '--no-history', '--config', str(entry), '-i']
        elif shell == 'xonsh':
            argv = [engine, '--shell-type', 'readline', '--rc', str(entry), '-i']
        uv = base/'commands/uv'
        version = subprocess.check_output([uv, '--version'], env=env, cwd=home).strip() if uv.is_file() else None
        yield env, home, argv, version


def wait_for_output(session, marker, timeout=45):
    deadline = time.monotonic() + timeout
    data = bytearray()
    while marker not in data:
        if time.monotonic() > deadline:
            raise RuntimeError(f'PTY timeout for {marker!r}: {data[-8000:]!r}')
        if not select.select([session.master], [], [], .1)[0]:
            continue
        chunk = os.read(session.master, 32768)
        if not chunk:
            raise RuntimeError('Shell exited before reporting the expected output')
        data.extend(chunk)
        # Reedline and prompt_toolkit query a real terminal for cursor position.
        if b'\x1b[6n' in chunk:
            session.send('\x1b[1;1R')
        if b'\x1b[c' in chunk or b'\x1b[0c' in chunk:
            session.send('\x1b[?1;2c')
    return bytes(data)


def measure(shell, prepared, *, ready_timeout=45, command_latency=False):
    env, home, argv, uv_version = prepared
    command = """printf '__READY_%s__\\n' "$DOTBIN" """
    if shell == 'nu':
        command = "print ('__READY_' + $env.DOTBIN + '__')"
    elif shell == 'xonsh':
        command = "print('__READY_'+$DOTBIN+'__')"
    start = time.monotonic()
    session = Session(env, home, argv=argv)
    try:
        # Echoed input cannot contain the assembled marker. Measuring the first
        # accepted command includes starting the editor and rendering its prompt.
        if shell == 'xonsh':
            # The readline backend clears typeahead while probing the terminal.
            wait_for_output(session, b'\x1b[?2004h')
            session.send('\x15')
        session.send(command + '\r')
        marker = os.fsencode('__READY_' + str(Path(env['DOTS'])/'bin') + '__')
        output = wait_for_output(session, marker, timeout=ready_timeout)
        ready = time.monotonic()
        if b'preparation unavailable' in output or b'preparation failed' in output:
            raise RuntimeError('Dots startup failed in readiness fixture')
        if shell == 'xonsh':
            if b'\x1b[?2004h' not in output.split(marker, 1)[1]:
                wait_for_output(session, b'\x1b[?2004h')
            session.send('\x15')
        if shell == 'nu' and b'\x1b]133;B' not in output.split(marker, 1)[1]:
            wait_for_output(session, b'\x1b]133;B')
        command_done = ready
        if command_latency:
            probe = {"nu": "print ('__COMMAND_' + 'ok__')",
                     "xonsh": "print('__COMMAND_' + 'ok__')"}.get(shell, "printf '__COMMAND_%s__\\n' ok")
            session.send(probe + '\r')
            output = wait_for_output(session, b'__COMMAND_ok__')
            command_done = time.monotonic()
            if shell == 'xonsh' and b'\x1b[?2004h' not in output.split(b'__COMMAND_ok__', 1)[1]:
                wait_for_output(session, b'\x1b[?2004h')
            if shell == 'nu' and b'\x1b]133;B' not in output.split(b'__COMMAND_ok__', 1)[1]:
                wait_for_output(session, b'\x1b]133;B')
        session.send('cd readiness-dir\t')
        wait_for_output(session, b'ectory', timeout=12)
        session.send('\r')
        # The absolute path is emitted only after the editor inserts the full
        # directory and executes the original command.
        session.send(('print($PWD)' if shell == 'xonsh' else 'pwd') + '\r')
        wait_for_output(session, os.fsencode(home/'readiness-directory'))
        completed = time.monotonic()
        result = dict(input_ms=round((ready-start)*1000, 2),
                      first_tab_cd_ms=round((completed-command_done)*1000, 2))
        if command_latency:
            result['command_ms'] = round((command_done-ready)*1000, 2)
        if uv_version and shell in ('bash','zsh'):
            session.send('uv --versi\t\r')
            wait_for_output(session, uv_version, timeout=15)
            result['first_uv_tab_ms'] = round((time.monotonic()-completed)*1000, 2)
        return result
    finally:
        session.send('exit\r')
        try:
            session.process.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            pass
        session.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', required=True, type=Path)
    parser.add_argument('--samples', type=int, default=7)
    parser.add_argument('--cold-samples', type=int, default=3)
    parser.add_argument('--layout', choices=('standalone', 'linked', 'upgrade'), default='standalone',
                        help='installation layout for both checkouts; upgrade compares linked to standalone')
    parser.add_argument('--command-latency', action='store_true', help='time one additional command before using Tab')
    parser.add_argument('--with-tools', action='store_true', help='include locally available zoxide, direnv, Starship and fzf')
    parser.add_argument('--enable-native-tools', action='store_true', help='select all optional Fish/Nu/Xonsh integrations in the new profile')
    parser.add_argument('--shell', action='append', choices=('bash','zsh','fish','nu','xonsh'))
    args = parser.parse_args()
    if min(args.samples, args.cold_samples) < 1:
        parser.error('samples must be positive')
    if args.enable_native_tools and not args.with_tools:
        parser.error('--enable-native-tools requires --with-tools')
    result = {}
    for shell in args.shell or ('bash','zsh','fish','nu','xonsh'):
        if not executable(shell):
            result[shell] = {'skipped': 'native executable or interpreter unavailable'}
            continue
        with ExitStack() as stack:
            fixtures = {}
            initial = {'before': [], 'after': []}
            roots = {'before': args.baseline.resolve(), 'after': ROOT}
            for index in range(args.cold_samples):
                order = list(roots) if index % 2 == 0 else reversed(roots)
                for name in order:
                    installed = args.layout == 'standalone' or args.layout == 'upgrade' and name == 'after'
                    case = interactive_fixture(roots[name], shell, installed=installed, with_tools=args.with_tools,
                                               enable_native_tools=args.enable_native_tools and name == 'after')
                    if index == args.cold_samples - 1:
                        fixtures[name] = stack.enter_context(case)
                        initial[name].append(measure(shell, fixtures[name], command_latency=args.command_latency))
                    else:
                        with case as prepared:
                            initial[name].append(measure(shell, prepared, command_latency=args.command_latency))
            samples = {name: [] for name in fixtures}
            for i in range(args.samples):
                for name in (list(fixtures) if i % 2 == 0 else reversed(fixtures)):
                    samples[name].append(measure(shell, fixtures[name], command_latency=args.command_latency))
            medians = {name: {key: round(statistics.median(row[key] for row in rows), 2)
                             for key in rows[0]} for name, rows in samples.items()}
            result[shell] = dict(empty_application_cache=initial, warm_median=medians, warm_samples=samples)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
