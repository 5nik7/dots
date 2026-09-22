#!/usr/bin/env python3
"""Native PTY acceptance and prompt timing in the disposable public fixture."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import pty
import select
import shutil
import statistics
import struct
import subprocess
import termios
import time

from zsh_fixture import REPO, ZSH, fixture

MARK = b'__DOTS_INPUT_READY__'


class Session:
    def __init__(self, env, cwd):
        master, slave = pty.openpty()
        self.master = master
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 30, 120, 0, 0))
        def terminal():
            os.setsid()
            fcntl.ioctl(slave, termios.TIOCSCTTY, 0)
        self.process = subprocess.Popen([ZSH, '-di'], stdin=slave, stdout=slave, stderr=slave,
                                        env=env, cwd=cwd, preexec_fn=terminal)
        os.close(slave)
        self.output = bytearray()
        self.log = Path(env['HOME']).parent / 'pty.log'

    def wait(self, marker=MARK, timeout=90):
        data = bytearray()
        deadline = time.monotonic() + timeout
        while marker not in data:
            if time.monotonic() > deadline:
                raise RuntimeError('PTY timeout: ' + bytes(data[-3000:]).decode(errors='replace'))
            if select.select([self.master], [], [], 0.2)[0]:
                try:
                    chunk = os.read(self.master, 65536)
                except OSError:
                    chunk = b''
                if not chunk:
                    raise RuntimeError('PTY exited: ' + bytes(data[-3000:]).decode(errors='replace'))
                data.extend(chunk)
                self.output.extend(chunk)
                self.log.write_bytes(self.output)
        return bytes(data)

    def send(self, command):
        os.write(self.master, command.encode())

    def close(self):
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
        os.close(self.master)


def exercise(source, samples, baseline=False):
    root, repo, env = fixture(source)
    if (repo / 'lib/dots').is_dir():
        probe = repo / 'bin/dots-fixture'
        probe.write_text('#!' + shutil.which('bash') + '\n'
                         '# dots:option=--flavor||choice:mocha,latte|Palette\n'
                         'printf "DOTS_ARG<%s>\\n" "$@"\n')
        probe.chmod(0o700)
    # Copy public vivid input into owned config so its lookup matches a linked installation.
    shutil.copytree(repo / 'configs/vivid', Path(env['XDG_CONFIG_HOME']) / 'vivid')
    # Representative Git contexts are owned copies, never the live repository.
    small = root / 'small-repo'
    small.mkdir()
    (small / 'example.txt').write_text('fixture\n')
    for directory in (small, repo):
        for args in (['init', '-q'], ['add', '.'],
                     ['-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                      '-c', 'commit.gpgsign=false', 'commit', '-qm', 'fixture']):
            subprocess.run(['git', *args], env=env, cwd=directory,
                           check=True, capture_output=True)
        (directory / 'untracked fixture.txt').write_text('untracked\n')
    rc = repo / 'shells/zsh/zshrc'
    rc.write_text(rc.read_text() + '''
autoload -Uz add-zle-hook-widget
_dots_test_ready() { print -r -- __DOTS_INPUT_READY__; }
add-zle-hook-widget line-init _dots_test_ready
''')
    # Warm application-generated caches, then measure actual input-ready prompts.
    first = time.perf_counter()
    session = Session(env, env['HOME'])
    try:
        session.wait()
        print('First prompt ready', flush=True)
        first = time.perf_counter() - first
        # Exercise a fresh shell reading the persisted dump, not just the shell
        # that generated it. Invalid autoload names can break only this path.
        (root / 'first-pty.log').write_bytes(session.output)
        session.close()
        session = Session(env, env['HOME'])
        session.wait()
        session.send("print -r -- __BINDINGS__; bindkey '^R'; bindkey '^I'; bindkey -M viins '^R'; print -r -- __HOOKS__; print -rl -- $precmd_functions; print -r -- __END__;\r")
        bindings = session.wait().decode(errors='replace')
        print('Bindings captured', flush=True)
        # State snapshots contain only fixture-local public state.
        snapshot = '''bindkey -L >| "$HOME/keys.before"; typeset -p precmd_functions preexec_functions chpwd_functions >| "$HOME/hooks.before"; print -r -- "$FZF_DEFAULT_OPTS" >| "$HOME/fzf.before"; print -rl -- $fpath >| "$HOME/fpath.before"; rl; rl; bindkey -L >| "$HOME/keys.after"; typeset -p precmd_functions preexec_functions chpwd_functions >| "$HOME/hooks.after"; print -r -- "$FZF_DEFAULT_OPTS" >| "$HOME/fzf.after"; print -rl -- $fpath >| "$HOME/fpath.after"; print -r -- __RELOADED__'''
        session.send(snapshot + '\r')
        session.wait()
        print('Reload captured', flush=True)
        reload_equal = {}
        for item in ('hooks', 'fzf', 'fpath', 'keys'):
            a = Path(env['HOME']) / (item + '.before')
            b = Path(env['HOME']) / (item + '.after')
            reload_equal[item] = a.exists() and b.exists() and a.read_bytes() == b.read_bytes()
        session.send("rlcs; bindkey '^I'; print -r -- __COMPLETION_REFRESHED__\r")
        refreshed = session.wait()
        if b'fzf-tab-complete' not in refreshed:
            raise RuntimeError('Completion refresh lost the Tab widget')
        if (repo / 'lib/dots').is_dir():
            session.send('dots fixture --flavor m\t')
            session.wait(marker=b'mocha', timeout=30)
            session.send('\r')
            completed = session.wait()
            if b'DOTS_ARG<mocha>' not in completed:
                raise RuntimeError('dots completion did not integrate with FZF-tab')
        # Wait for the picker's actual prompt before sending cancellation;
        # initialization can exceed a fixed sleep on mobile hardware.
        for label, keys in (('Tab', 'ls \t'), ('cd Tab', 'cd \t'), ('history', '\x12')):
            print('Testing ' + label + ' picker', flush=True)
            session.send(keys)
            session.wait(marker='󰅂'.encode(), timeout=30)
            if label == 'Tab':
                session.send('\x18')  # toggle the configured preview
                time.sleep(0.2)
            session.send('\x03')
            session.wait(marker=b'\x1b[?2004l', timeout=15)
            session.send('\x15:\r')
            session.wait(timeout=20)
        # Actual vi-mode cursor transitions, without changing the live terminal.
        session.send('\x1b')
        session.wait(marker=b'\x1b[1 q', timeout=10)
        session.send('i')
        session.wait(marker=b'\x1b[5 q', timeout=10)
        session.send(':\r')
        session.wait()
        prompt_contexts = {}
        for label, directory in (('home', Path(env['HOME'])), ('small_repo', small), ('public_config_repo', repo)):
            import shlex
            session.send('builtin cd -- ' + shlex.quote(str(directory)) + '\r')
            session.wait()
            elapsed = []
            for _ in range(samples):
                start = time.perf_counter()
                session.send(':\r')
                session.wait()
                elapsed.append(time.perf_counter() - start)
            prompt_contexts[label] = elapsed
        prompts = prompt_contexts['home']
        for diagnostic in (b'bad pattern:', b'command not found:', b'No command _'):
            if diagnostic in session.output:
                raise RuntimeError('Completion/startup diagnostic: ' + diagnostic.decode())
        (root / 'pty.log').write_bytes(session.output)
    finally:
        (root / 'pty.log').write_bytes(session.output)
        session.close()
    starts = []
    for _ in range(samples):
        start = time.perf_counter()
        session = Session(env, env['HOME'])
        try:
            session.wait()
            starts.append(time.perf_counter() - start)
        finally:
            session.close()
    result = {'fixture': str(root), 'first_input_ready_seconds': first,
              'warm_input_ready_seconds': starts,
              'warm_input_ready_median_seconds': statistics.median(starts),
              'prompt_seconds': prompts, 'prompt_median_seconds': statistics.median(prompts),
              'prompt_contexts_seconds': prompt_contexts,
              'reload_equal': reload_equal, 'bindings_and_hooks': bindings}
    (root / 'interactive.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    if not baseline and not all(reload_equal.values()):
        raise RuntimeError('Reload changed public shell state: ' + repr(reload_equal))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=REPO)
    parser.add_argument('--samples', type=int, default=5)
    parser.add_argument('--baseline', action='store_true', help='Report historical reload differences without requiring equality')
    args = parser.parse_args()
    exercise(args.source.resolve(), args.samples, args.baseline)
