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

from verify_core import environments, tool

REPO = Path(__file__).resolve().parents[1]

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['check', 'build', 'bench'])
    args = p.parse_args()
    go = tool('go')
    with tempfile.TemporaryDirectory(prefix='anodize-verify-') as tmp:
        root = Path(tmp)
        env, _ = environments(root, go)
        source = root / 'module'
        shutil.copytree(REPO / 'anodize', source, ignore=shutil.ignore_patterns('.build'))
        binary = root / 'bin/anodize-engine'
        def run(command):
            subprocess.run(command, cwd=source, env=env, check=True, timeout=600)
        run([go, 'build', '-trimpath', '-o', str(binary), './cmd/anodize-engine'])
        if args.action == 'build':
            output = REPO / 'anodize/.build'
            output.mkdir(exist_ok=True)
            staged = output / 'anodize-engine.new'
            shutil.copy2(binary, staged)
            staged.replace(output / 'anodize-engine')
            print('Built', output / 'anodize-engine')
            return
        if args.action == 'bench':
            run([go, 'test', '-run=^$', '-bench=.', '-benchmem', '-count=3', './...'])
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
        subprocess.run([sys.executable, '-B', str(REPO / 'tools/test_anodize.py')], env=env, check=True, cwd=REPO)

if __name__ == '__main__':
    main()
