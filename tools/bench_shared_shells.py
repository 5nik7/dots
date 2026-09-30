#!/usr/bin/env python3
"""Sequential public-fixture Bash/Zsh startup comparison; never source live rc files."""
import argparse
import json
from pathlib import Path
import shutil
import statistics
import subprocess
import time
from bash_fixture import fixture as bash_fixture
from public_fixture import copy_public_tree
from test_shell_init import InitTests
from zsh_fixture import fixture as zsh_fixture, run, REPO


def benchmark(baseline, samples):
    fixtures = []
    cases = {}
    minimal = []
    try:
        for version, source in [('before', baseline), ('after', REPO)]:
            root, repo, env = zsh_fixture(source)
            fixtures.append(root)
            cases[('zsh_public_plugins', version)] = lambda env=env: run(env)
            root, repo, env = bash_fixture(source)
            fixtures.append(root)
            def bash(env=env):
                return subprocess.run([shutil.which('bash'), '--noprofile', '--norc', '-ic',
                                       'source "$DOTS/shells/bash/.bashrc"'], env=env,
                                      cwd=env['HOME'], capture_output=True, timeout=60)
            cases[('bash_native_tools', version)] = bash
            t=InitTests();t.setUp();t.minimal_tools();minimal.append(t)
            if version == 'before':
                shutil.rmtree(t.repo / 'shells/bash')
                copy_public_tree(source / 'shells/bash', t.repo / 'shells/bash', repo=source, fixture=t.repo, aliases=(REPO,))
            code=t.generated('bash')
            cases[('bash_minimal_tools',version)] = lambda t=t, code=code: t.shell('bash', code, interactive=True)
        timings={key:[] for key in cases}
        for case in cases.values():
            p=case()
            assert p.returncode == 0,p.stderr
        for i in range(samples):
            for mode in ('zsh_public_plugins','bash_native_tools','bash_minimal_tools'):
                for version in (('before','after') if i%2==0 else ('after','before')):
                    start=time.perf_counter();p=cases[(mode,version)]();elapsed=time.perf_counter()-start
                    assert p.returncode == 0,p.stderr
                    timings[(mode,version)].append(elapsed*1000)
        result={'mode':'native interactive startup without PTY; sequential alternating warm samples',
                'samples':samples, 'fixtures':[str(p) for p in fixtures],
                'median_ms':{mode:{version:round(statistics.median(timings[(mode,version)]),3)
                                  for version in ('before','after')}
                             for mode in ('zsh_public_plugins','bash_native_tools','bash_minimal_tools')}}
        (fixtures[-1] / 'shared-shell-timing.json').write_text(json.dumps(result,indent=2))
        print(json.dumps(result,indent=2))
    finally:
        for t in minimal:t.doCleanups()


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline',type=Path,required=True)
    parser.add_argument('--samples',type=int,default=5)
    args=parser.parse_args()
    if args.samples < 1:parser.error('--samples must be positive')
    benchmark(args.baseline.resolve(),args.samples)
