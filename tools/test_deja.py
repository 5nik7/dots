#!/usr/bin/env python3
"""Opt-in native Deja acceptance; copies supplied public inputs into owned roots."""
import argparse
import json
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import time

from zsh_fixture import fixture, run
from zsh_interactive import Session


def exercise(binary, plugin, samples):
    root, repo, env = fixture()
    home = Path(env['HOME'])
    exe = home / '.local/bin/deja'
    shutil.copy2(binary, exe)
    dest = home / '.local/share/zinit/plugins/Giammarco-Ferranti---deja'
    dest.mkdir()
    shutil.copy2(plugin, dest / 'deja.plugin.zsh')
    env.pop('DOTS_ZSH_SUGGESTIONS', None)  # Exercise the default, not an override.
    env['DEJA_EMPTY'] = 'off'
    # Only fixture history is ever recorded. Start and own the daemon explicitly
    # so the integration never needs to create an untracked background daemon.
    def cli(*args):
        return subprocess.run([str(exe), *args], env=env, cwd=home,
                              text=True, capture_output=True, check=True, timeout=15)

    cli('record', '--command', 'echo DEJA_ACCEPTED_FIXTURE', '--dir', str(home))
    cli('init', 'zsh')
    log = (root / 'deja-daemon.log').open('w')
    daemon = subprocess.Popen([str(exe), 'daemon'], env=env, cwd=home,
                              stdout=log, stderr=log)
    session = None
    try:
        deadline = time.monotonic() + 10
        while not (home / '.local/share/deja/sock').exists():
            if daemon.poll() is not None or time.monotonic() > deadline:
                raise RuntimeError('Fixture daemon did not start: ' + str(root))
            time.sleep(0.05)
        query = cli('query', '--buffer', 'echo DEJA_ACC', '--dir', str(home)).stdout
        assert 'DEJA_ACCEPTED_FIXTURE' in query, query
        rc = repo / 'shells/zsh/zshrc'
        with rc.open('a') as stream:
            stream.write('''
autoload -Uz add-zle-hook-widget
_dots_test_ready() { print -r -- __DOTS_INPUT_READY__; }
add-zle-hook-widget line-init _dots_test_ready
''')
        session = Session(env, str(home))
        session.wait()
        session.send('''print -r -- "engine:$_DOTS_SUGGESTION_ENGINE conflict:${+functions[_zsh_autosuggest_start]}"; bindkey '^I'; print -r -- "highlight:$DEJA_HIGHLIGHT_STYLE"\r''')
        state = session.wait()
        assert b'engine:deja conflict:0' in state, state
        assert b'fzf-tab-complete' in state, state
        assert b'highlight:fg=' in state, state
        session.send('''bindkey -L > "$HOME/keys.before"; typeset -p precmd_functions preexec_functions > "$HOME/hooks.before"; rl; rl; bindkey -L > "$HOME/keys.after"; typeset -p precmd_functions preexec_functions > "$HOME/hooks.after"\r''')
        session.wait()
        for name in ('keys', 'hooks'):
            assert (home / (name + '.before')).read_bytes() == (home / (name + '.after')).read_bytes(), name
        # Wait for the actual ghost text, then accept with a real right arrow.
        session.send('echo DEJA_ACC')
        session.wait(marker=b'EPTED_FIXTURE', timeout=15)
        session.send('\x1b[C\r')
        accepted = session.wait()
        plain = re.sub(rb'\x1b\[[0-?]*[ -/]*[@-~]', b'', accepted)
        assert b'\r\nDEJA_ACCEPTED_FIXTURE\r\n' in plain, accepted
        session.send('\x1b')
        session.wait(marker=b'\x1b[1 q', timeout=10)
        session.send('i')
        session.wait(marker=b'\x1b[5 q', timeout=10)
        session.send(':\r')
        session.wait()
        # A single file candidate verifies real completion without opening a
        # picker or depending on a theme-specific FZF prompt glyph.
        (home / 'deja-completion-fixture').write_text('fixture\n')
        session.send('echo deja-completion-fix\t')
        session.wait(marker=b'ture', timeout=15)
        session.send('\r')
        completed = session.wait()
        plain = re.sub(rb'\x1b\[[0-?]*[ -/]*[@-~]', b'', completed)
        assert b'\r\ndeja-completion-fixture\r\n' in plain, completed
        session.close()
        session = None
        # Sequential, alternating order limits drift from mobile thermal load.
        values = {'autosuggestions': [], 'deja': []}
        for engine in values:
            assert run(dict(env, DOTS_ZSH_SUGGESTIONS=engine)).returncode == 0
        for index in range(samples):
            order = list(values) if index % 2 == 0 else list(reversed(values))
            for engine in order:
                start = time.perf_counter()
                result = run(dict(env, DOTS_ZSH_SUGGESTIONS=engine))
                assert result.returncode == 0, result.stderr
                values[engine].append(time.perf_counter() - start)
        timings = {engine: {'samples': times, 'median': statistics.median(times)}
                   for engine, times in values.items()}
        result = {'fixture': str(root), 'native_acceptance': 'passed', 'startup_seconds': timings}
        (root / 'deja-results.json').write_text(json.dumps(result, indent=2))
        print(json.dumps(result, indent=2))
    finally:
        if session is not None:
            session.close()
        daemon.terminate()
        try:
            daemon.wait(timeout=5)
        except subprocess.TimeoutExpired:
            daemon.kill()
            daemon.wait()
        log.close()
        print('Retained fixture:', root)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--plugin', type=Path, required=True)
    parser.add_argument('--samples', type=int, default=5)
    args = parser.parse_args()
    if args.samples < 1:
        parser.error('--samples must be positive')
    exercise(args.binary.resolve(strict=True), args.plugin.resolve(strict=True), args.samples)
