#!/usr/bin/env python3
"""Offline, isolated Anodize build/test/benchmark entry point."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import statistics
import time

from anodize_build_support import environment, tool

REPO = Path(__file__).resolve().parents[1]

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['check', 'build', 'bench'])
    args = p.parse_args()
    go = tool('go')
    with tempfile.TemporaryDirectory(prefix='anodize-verify-') as tmp:
        root = Path(tmp)
        env = environment(root, go)
        source = root / 'module'
        shutil.copytree(REPO / 'plugins/anodize/engine', source, ignore=shutil.ignore_patterns('.build'))
        name = 'anodize-engine.exe' if os.name == 'nt' else 'anodize-engine'
        binary = root / 'bin' / name
        def run(command):
            subprocess.run(command, cwd=source, env=env, check=True, timeout=600)
        run([go, 'build', '-trimpath', '-o', str(binary), './cmd/anodize-engine'])
        if args.action == 'build':
            output = REPO / 'plugins/anodize/engine/.build'
            output.mkdir(exist_ok=True)
            staged = output / (name + '.new')
            shutil.copy2(binary, staged)
            staged.replace(output / name)
            print('Built', output / name)
            return
        if args.action == 'bench':
            run([go, 'test', '-run=^$', '-bench=.', '-benchmem', '-count=3', './...'])
            if os.name == 'nt':
                print('Native engine benchmarks complete; Bash frontend timings apply only to POSIX hosts.')
                return
            # Reuse the integration fixture, including isolated CLI state and paths.
            os.environ['ANODIZE_ENGINE'] = str(binary)
            from test_anodize import Anodize, BASH
            fixture = Anodize()
            try:
                fixture.setUp()
                for label, command in (
                    ('standalone help', [BASH, str(fixture.repo / 'bin/anodize'), '--help']),
                    ('standalone modes', [BASH, str(fixture.repo / 'bin/anodize'), 'modes', '--json']),
                    ('dots modes', [BASH, str(fixture.repo / 'bin/dots'), 'anodize', 'modes', '--json']),
                    ('CLI one-pixel extract', [BASH, str(fixture.repo / 'bin/anodize'), 'extract', str(fixture.image), '--json']),
                ):
                    samples = []
                    for i in range(23):
                        start = time.perf_counter()
                        fixture.run_command(command)
                        if i >= 3:
                            samples.append((time.perf_counter() - start) * 1000)
                    print(f'{label}: median={statistics.median(samples):.2f}ms p95={sorted(samples)[18]:.2f}ms (20 warm samples)', flush=True)
            finally:
                fixture.doCleanups()
            return
        run([go, 'test', './...'])
        run([go, 'vet', './...'])
        env.update(PATH=os.environ.get('PATH', ''), ANODIZE_ENGINE=str(binary))
        if os.environ.get('LD_PRELOAD'):
            env['LD_PRELOAD'] = os.environ['LD_PRELOAD']
        if os.environ.get('DOTS_TEST_FZF_TAB'):
            env['DOTS_TEST_FZF_TAB'] = os.environ['DOTS_TEST_FZF_TAB']
        tests = ['test_native_anodize.py'] if os.name == 'nt' else ['test_anodize.py', 'test_anodize_interactive.py', 'test_anodize_logo.py']
        for test in tests:
            subprocess.run([sys.executable, '-B', str(REPO / 'tools' / test)], env=env, check=True, cwd=REPO)

if __name__ == '__main__':
    main()
