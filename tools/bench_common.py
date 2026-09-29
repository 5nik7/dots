#!/usr/bin/env python3
"""Sequential warm common-helper microbenchmarks in owned Bash/Zsh homes (advisory)."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import statistics
import subprocess
import tempfile
import time

REPO = Path(__file__).resolve().parents[1]
CASES = {
    'load': 'source "$DOTS/bin/lib/common.sh"',
    'path_membership': 'prepath "$HOME/existing"; extpath "$HOME/existing"',
    'dirname': 'dirout -r "$HOME/existing/file"',
    'case_conversion': 'upper "a sample value"; lower "A SAMPLE VALUE"',
    'source_file': 'so "$HOME/input"',
}


def benchmark(sources, samples, iterations):
    root = Path(tempfile.mkdtemp(prefix='dots-common-bench-'))
    result = {'platform': platform.platform(), 'machine': platform.machine(),
              'mode': 'native warm batches; one warmup; includes shell process startup',
              'samples': samples, 'iterations_per_batch': iterations, 'sources': {}, 'results': {}}
    for label, source in sources.items():
        home = root / label
        (home / 'repo/bin/lib').mkdir(parents=True)
        (home / 'existing').mkdir()
        (home / 'input').write_text('fixture_loaded=1\n')
        util = home / 'repo/bin/lib/common.sh'
        shutil.copy2(source, util)
        result['sources'][label] = {'path': str(source), 'sha256': hashlib.sha256(util.read_bytes()).hexdigest()}
        env = {'HOME': str(home), 'DOTS': str(home / 'repo'), 'ZDOTDIR': str(home),
               'TMPDIR': str(home), 'TERM': 'dumb', 'buggin': '0',
               'PATH': os.environ['PATH'], 'ITERATIONS': str(iterations)}
        for kind in ('CONFIG', 'DATA', 'STATE', 'CACHE'):
            env[f'XDG_{kind}_HOME'] = str(home / kind.lower())
        if os.environ.get('LD_PRELOAD'):
            env['LD_PRELOAD'] = os.environ['LD_PRELOAD']
        result['results'][label] = {}
        for shell in ('bash', 'zsh'):
            executable = shutil.which(shell)
            if not executable:
                result['results'][label][shell] = {'skipped': 'interpreter unavailable'}
                continue
            flags = ['--noprofile', '--norc', '-c'] if shell == 'bash' else ['-dfc']
            measurements = result['results'][label][shell] = {}
            for case, body in CASES.items():
                code = ('source "$DOTS/bin/lib/common.sh"\n'
                        'PATH="$HOME/existing:$PATH"\n'
                        'for ((i=0; i<ITERATIONS; i++)); do\n' + body + '\n done\n')
                elapsed = []
                for _ in range(samples + 1):
                    start = time.perf_counter()
                    subprocess.run([executable, *flags, code], cwd=home, env=env,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                   check=True, timeout=120)
                    elapsed.append((time.perf_counter() - start) * 1000)
                values = elapsed[1:]
                measurements[case] = {'median_ms': statistics.median(values), 'samples_ms': values}
            print(label, shell, {k: round(v['median_ms'], 3) for k, v in measurements.items()}, flush=True)
    (root / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    print('Retained source snapshots and results:', root)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=REPO / 'bin/lib/common.sh')
    parser.add_argument('--before', type=Path, help='Saved helper with the same utility API (also accepts the former bin/util)')
    parser.add_argument('--samples', type=int, default=5)
    parser.add_argument('--iterations', type=int, default=100)
    args = parser.parse_args()
    if args.samples < 1 or args.iterations < 1:
        parser.error('samples and iterations must be positive')
    sources = {'before': args.before.resolve()} if args.before else {}
    sources['after'] = args.source.resolve()
    benchmark(sources, args.samples, args.iterations)
