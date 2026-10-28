#!/usr/bin/env python3
"""Offline warm startup sampling in isolated storage roots."""
import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
ROOT = Path(__file__).resolve().parent.parent
p = argparse.ArgumentParser()
p.add_argument('--samples', type=int, default=60)
p.add_argument('--only', action='append', help='repeatable command label for a focused latency investigation')
p.add_argument('--compare-root', type=Path, help='alternate each sample with a preserved source baseline on the same host')
p.add_argument('--features', action='store_true', help='also measure save dry-run and module show with 1000 local themes')
a = p.parse_args()
if not 5 <= a.samples <= 10000:
    p.error('samples must be 5–10000')
commands = {'python-version':[sys.executable,'-I',str(ROOT/'lib/blastoff.py'),'--version'], 'python-help':[sys.executable,'-I',str(ROOT/'lib/blastoff.py'),'--help']}
if shutil.which('bash'):
    commands['bash-version'] = ['bash',str(ROOT/'bin/blastoff'),'--version']
    commands['bash-help'] = ['bash',str(ROOT/'bin/blastoff'),'--help']
for entry, launcher in [('python', [sys.executable,'-I',str(ROOT/'lib/blastoff.py')]),
                        ('bash', ['bash',str(ROOT/'bin/blastoff')])]:
    if entry == 'bash' and not shutil.which('bash'):
        continue
    commands[entry+'-bare'] = launcher
    for label, arguments in [('list-human',['list']),
                             ('current',['current','--json']),
                             ('module-list',['module','list','--json']),
                             ('backup-list-human',['backup','list'])]:
        commands[entry+'-'+label] = launcher + arguments
if shutil.which('pwsh'):
    # A fresh shell includes host startup and module import. Document separately.
    module = str(ROOT/'powershell/blastoff.psd1').replace("'", "''")
    commands['powershell-process-version'] = ['pwsh','-NoProfile','-Command',"Import-Module '"+module+"'; blastoff --version; exit $LASTEXITCODE"]
if a.only:
    if a.features: p.error('--only cannot be combined with --features')
    unknown=set(a.only)-set(commands)
    if unknown: p.error('unknown command labels: '+', '.join(sorted(unknown)))
    commands={k:v for k,v in commands.items() if k in a.only}
with tempfile.TemporaryDirectory() as root:
    env = dict(os.environ, HOME=root, USERPROFILE=root, XDG_CONFIG_HOME=str(Path(root)/'xdg'), XDG_CACHE_HOME=str(Path(root)/'cache'), STARSHIP_CACHE=str(Path(root)/'starship-cache'), BLASTOFF_HOME=str(Path(root)/'store'), STARSHIP_CONFIG=str(Path(root)/'config/starship.toml'), BLASTOFF_PYTHON=sys.executable, NO_COLOR='1')
    results = {}
    comparisons = {}
    if a.features:
        store=Path(root)/'store'; (store/'themes').mkdir(parents=True); (store/'modules').mkdir()
        config=Path(root)/'config/starship.toml'; config.parent.mkdir(); config.write_text('[directory]\nstyle="purple"\n')
        (store/'modules/dir.toml').write_bytes(config.read_bytes())
        for index in range(1000): (store/'themes'/('theme'+str(index)+'.toml')).write_text('x=1\n')
        subprocess.run([sys.executable,'-I',str(ROOT/'lib/blastoff.py'),'theme','save','daily'],env=env,stdout=subprocess.DEVNULL,check=True)
        # Avoid benchmarking exhaustive current matching in this separate feature run.
        commands={k:v for k,v in commands.items() if not k.endswith('-current')}
        for entry, launcher in [('python',[sys.executable,'-I',str(ROOT/'lib/blastoff.py')]),('bash',['bash',str(ROOT/'bin/blastoff')])]:
            if entry=='bash' and not shutil.which('bash'): continue
            commands[entry+'-save-dry-run-1000']=launcher+['theme','save','--dry-run','--json']
            commands[entry+'-module-show']=launcher+['module','show','dir']
        before={str(p):p.read_bytes() for p in Path(root).rglob('*') if p.is_file()}
    for label, command in commands.items():
        samples=[]; baseline_samples=[]
        baseline=[str(word).replace(str(ROOT),str(a.compare_root.resolve())) for word in command] if a.compare_root else None
        for i in range(a.samples+5):
            paired=[(command,samples)] + ([(baseline,baseline_samples)] if baseline else [])
            if i % 2: paired.reverse()
            for invocation, measurements in paired:
                start=time.perf_counter_ns()
                subprocess.run(invocation,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,check=True,timeout=10)
                elapsed=(time.perf_counter_ns()-start)/1e6
                if i>=5: measurements.append(elapsed)
        for measurements,destination in [(samples,results), *(([(baseline_samples,comparisons)]) if baseline else [])]:
            values=sorted(measurements)
            destination[label]={'p50_ms':round(statistics.median(values),3),'p95_ms':round(values[max(0,(95*len(values)+99)//100-1)],3),'max_ms':round(max(values),3)}
    if a.features:
        import importlib.util
        def load_helper(name):
            spec=importlib.util.spec_from_file_location(name,ROOT/'lib'/(name+'.py'))
            helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper);return helper
        preview=load_helper('preview');picker=load_helper('picker_ui')
        with tempfile.TemporaryDirectory(prefix='blastoff-preview-benchmark-') as preview_tmp:
            session=Path(preview_tmp)
            (session/'choices.json').write_text(json.dumps({'choices':['module:dir'],'themes':str(store/'modules'),'color':False,'starship':None,'bat':None}))
            cases=[('picker-options-in-process',lambda:picker.inherited_options({'FZF_DEFAULT_OPTS':'--color=fg:#abcdef,bg:#123456 --layout=reverse --bind=ctrl-j:down'})),
                   ('preview-first-plain-in-process',lambda:preview.render(str(session),'0')),
                   ('preview-cached-in-process',lambda:preview.render(str(session),'0'))]
            for label,operation in cases:
                values=[]
                for index in range(a.samples+5):
                    if label=='preview-first-plain-in-process':
                        for filename in ('0.txt','cache-count'): (session/filename).unlink(missing_ok=True)
                    start=time.perf_counter_ns();operation();elapsed=(time.perf_counter_ns()-start)/1e6
                    if index>=5: values.append(elapsed)
                values.sort();results[label]={'p50_ms':round(statistics.median(values),3),'p95_ms':round(values[max(0,(95*len(values)+99)//100-1)],3),'max_ms':round(max(values),3)}
    if a.features:
        assert before=={str(p):p.read_bytes() for p in Path(root).rglob('*') if p.is_file()}
    else:
        assert not (Path(root)/'store').exists()
        assert not (Path(root)/'config').exists()
print(json.dumps({'host':platform.platform(),'machine':platform.machine(),'python':platform.python_version(),'samples':a.samples,'warmups':5,'feature_library_size':1000 if a.features else 0,'results':results,'comparison_results':comparisons,'comparison_root':str(a.compare_root.resolve()) if a.compare_root else None},indent=2,sort_keys=True))
