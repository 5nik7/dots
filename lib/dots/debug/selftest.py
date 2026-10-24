"""Small curated diagnostics using owned roots, never unrestricted test discovery."""
import json
import os
from pathlib import Path
from types import SimpleNamespace
import subprocess
import sys
import time
from .fixtures import fixture

SUITES={'profiles':'Inheritance, invalid definitions and cycle refusal',
        'environment':'Explicit overrides and private-value redaction',
        'dispatch':'Longest-prefix resolution without executing commands',
        'startup':'Native startup events and completion in an isolated shell'}


def run_tests(root,suite=None,list_only=False):
    if list_only: return dict(version=1,rows=[dict(name=k,description=v) for k,v in SUITES.items()])
    checks=[]
    for name in [suite] if suite else SUITES:
        started=time.perf_counter()
        try:
            with fixture(root) as (checkout,env,base):
                if name=='profiles':
                    from profiles import resolve
                    p=checkout/'profiles/linux/distros/demo';p.mkdir(parents=True);(p/'profile.json').write_text('{"schema":1,"id":"linux/demo"}')
                    layers=resolve(checkout,dict(platform='wsl',distro='demo',family=[]))['layers']
                    assert [r['id'] for r in layers]==['linux','linux/demo','wsl'], 'inheritance order'
                    (p/'profile.json').write_text('{"schema":1,"id":"linux/demo","extends":["linux/demo"]}')
                    try: resolve(checkout,dict(platform='linux',distro='demo',family=[]))
                    except ValueError: pass
                    else: raise AssertionError('cycle accepted')
                elif name=='environment':
                    env.update(EDITOR='fixture-editor',FIXTURE_SECRET='do-not-report',DOTS_ENV_HOOKS='FIXTURE_SECRET:private-local:1:set;')
                    result=subprocess.run([sys.executable,'-B',str(checkout/'lib/dots/environment.py'),'--json'],env=env,capture_output=True,text=True,timeout=10)
                    assert result.returncode==0, 'environment controller failed'
                    data=json.loads(result.stdout);assert data['values']['EDITOR']['value']=='fixture-editor','override lost'
                    assert 'do-not-report' not in result.stdout,'private value exposed'
                elif name=='dispatch':
                    from command_metadata import resolve
                    directory=base/'routes';directory.mkdir()
                    for route in ('fixture','fixture-child'):
                        (directory/('dots-'+route)).write_text('DO NOT EXECUTE')
                    stem,path,count=resolve([directory],['fixture','child','arg'])
                    assert stem=='fixture-child' and count==2,'longest prefix'
                else:
                    from .startup import one_run
                    shell='powershell' if os.name=='nt' else 'bash'
                    result=one_run(checkout,env,shell,False,30,True,base)
                    if result['status']=='unavailable':
                        checks.append(dict(name=name,status='skipped',detail='Native shell unavailable'))
                        continue
                    assert result['exit_code']==0,'isolated shell did not finish'
                    assert any(e['kind'] in ('module','inlined') for e in result['events']),'module events missing'
            checks.append(dict(name=name,status='passed',elapsed_ms=round((time.perf_counter()-started)*1000,3),detail=SUITES[name]))
        except (AssertionError,ValueError,OSError,KeyError,subprocess.SubprocessError) as error:
            checks.append(dict(name=name,status='failed',elapsed_ms=round((time.perf_counter()-started)*1000,3),detail=str(error)))
    return dict(version=1,checks=checks)
