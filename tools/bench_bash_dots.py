#!/usr/bin/env python3
"""Sequential, disposable Bash CLI scaling measurements; not a hard timing gate."""
import argparse
import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import tempfile
import time

REPO = Path(__file__).resolve().parents[1]


def benchmark(samples):
    root = Path(tempfile.mkdtemp(prefix='dots-bash-bench-'))
    repo = root / 'repo'
    (repo / 'bin').mkdir(parents=True)
    home = root / 'home'; home.mkdir()
    shutil.copy2(REPO / 'bin/dots', repo / 'bin/dots')
    shutil.copy2(REPO / 'logo.txt', repo / 'logo.txt')
    shutil.copytree(REPO / 'lib/dots', repo / 'lib/dots')
    env = {'HOME': str(home), 'DOTS': str(repo), 'PATH': os.environ['PATH'], 'TERM': 'dumb',
           'TMPDIR': str(root), 'XDG_CONFIG_HOME': str(home / 'config'),
           'XDG_CACHE_HOME': str(home / 'cache'), 'XDG_STATE_HOME': str(home / 'state'),
           'XDG_DATA_HOME': str(home / 'data')}
    if os.environ.get('LD_PRELOAD'): env['LD_PRELOAD'] = os.environ['LD_PRELOAD']
    bash = shutil.which('bash')
    cases = {'help': ['--help'], 'dir': ['--dir'], 'dispatch': ['probe'],
             'catalog': ['commands'], 'completion': ['__complete', 'bash', '1', '--', 'dots', ''],
             'completion_prefix': ['__complete', 'bash', '1', '--', 'dots', 'pr']}
    probe = repo / 'bin/dots-probe'; probe.write_text('#!' + bash + '\nexit 0\n'); probe.chmod(0o700)
    results = {}
    for count in (0, 100, 1000):
        for i in range(count):
            p = repo / ('bin/dots-c' + str(i))
            p.write_text('#!' + bash + '\n# dots:summary=Fixture command\nexit 0\n')
            p.chmod(0o700)
        results[str(count)] = {}
        for label, args in cases.items():
            values = []
            for _ in range(samples + 3):
                start = time.perf_counter()
                subprocess.run([str(repo / 'bin/dots'), *args], env=env, cwd=home,
                               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                values.append(time.perf_counter() - start)
            values = values[3:]
            results[str(count)][label] = {'median_ms': statistics.median(values) * 1000,
                                         'samples_seconds': values}
        print(count, {k: round(v['median_ms'], 3) for k, v in results[str(count)].items()}, flush=True)
    # Measure adapter registration cost in fresh shells separately from Tab queries.
    startup = {}
    for shell in ('bash', 'zsh', 'fish'):
        executable = shutil.which(shell)
        flags = ['--noprofile', '--norc'] if shell == 'bash' else ['-df'] if shell == 'zsh' else ['--no-config']
        startup[shell] = {}
        for label, code in [('bare', ':'), ('adapter', 'source "$DOTS/lib/dots/completion/' + shell + '"; :')]:
            values = []
            for _ in range(samples + 3):
                start = time.perf_counter()
                subprocess.run([executable, *flags, '-c', code], env=env, cwd=home,
                               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                values.append(time.perf_counter() - start)
            startup[shell][label] = {'median_ms': statistics.median(values[3:]) * 1000,
                                     'samples_seconds': values[3:]}
    (root / 'results.json').write_text(json.dumps({'extra_command_counts': results, 'shell_startup': startup}, indent=2))
    print(root)
    print('Startup:', {s: {k: round(v['median_ms'], 3) for k, v in times.items()} for s, times in startup.items()})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--samples', type=int, default=20)
    args = parser.parse_args()
    if args.samples < 1: parser.error('--samples must be positive')
    benchmark(args.samples)
