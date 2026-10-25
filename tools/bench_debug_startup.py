#!/usr/bin/env python3
"""Sequential owned-fixture comparison with/without disabled diagnostic calls."""
import argparse
from contextlib import ExitStack
import json
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'lib/dots'))
from debug.fixtures import fixture


def benchmark(samples, recording=False):
    results={}
    with ExitStack() as stack:
        cases={}
        for label in (('disabled_tracing','path_recording') if recording else ('without_calls','disabled_tracing')):
            root,env,_=stack.enter_context(fixture(ROOT))
            if label=='path_recording':env['DOTS_DEBUG_RECORD']='path'
            if label=='without_calls':
                for name in ('startup.bash','environment_runtime.bash'):
                    p=root/'lib/dots/shell'/name
                    p.write_text('\n'.join(line for line in p.read_text().splitlines() if '_dots_debug_event' not in line and 'source "$DOTS/lib/dots/shell/debug.bash"' not in line)+'\n')
                p=root/'lib/dots/startup.py';s=p.read_text();start=s.index('    def module(');end=s.index('    def expand(',start)
                s=s[:start]+'    def module(self, relative, body, kind="module"):\n        return body\n\n'+s[end:];p.write_text(s)
            for shell in ('bash','zsh'):
                executable=shutil.which(shell)
                if not executable: continue
                args=[executable,'-d','-ic',':'] if shell=='zsh' else [executable,'--noprofile','--rcfile',str(Path(env['HOME'])/'.bashrc'),'-ic',':']
                cases[(shell,label)]=(args,env)
        for args,env in cases.values():
            p=subprocess.run(args,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=30)
            if p.returncode or b'preparation unavailable' in p.stderr: raise RuntimeError('fixture warmup failed')
        timings={key:[] for key in cases}
        for index in range(samples):
            for key in (list(cases) if index%2==0 else list(reversed(cases))):
                args,env=cases[key];started=time.perf_counter()
                p=subprocess.run(args,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=30)
                if p.returncode or b'preparation unavailable' in p.stderr: raise RuntimeError('fixture sample failed')
                timings[key].append((time.perf_counter()-started)*1000)
        for (shell,label),values in timings.items(): results.setdefault(shell,{})[label]=round(statistics.median(values),3)
    return dict(samples=samples,mode='Sequential alternating warm public fixtures; optional plugins absent; milliseconds',median_ms=results)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--samples',type=int,default=7)
    parser.add_argument('--recording',action='store_true',help='Compare disabled tracing with opted-in PATH recording')
    args=parser.parse_args()
    if not 3<=args.samples<=30: parser.error('--samples must be 3–30')
    print(json.dumps(benchmark(args.samples,args.recording),indent=2))
