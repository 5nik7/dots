"""Bounded native startup runs; only structured source/timing events survive."""
import json
import os
from pathlib import Path
import re
import shutil
import signal
import shlex
import statistics
import subprocess
import tempfile
import threading
import time
from contextlib import nullcontext
from .fixtures import fixture

LIMIT=10000


def shell_choice(request=None):
    if request: return request
    try:
        parent=Path('/proc')/str(os.getppid())/'comm'
        invoking=parent.read_text().strip().lower()
        if invoking in ('bash','zsh'): return invoking
        if invoking in ('pwsh','powershell'): return 'powershell'
    except OSError: pass
    # Fall back to the configured login shell, then the platform default.
    candidate=Path(os.environ.get('SHELL','')).name.lower()
    if candidate in ('bash','zsh'): return candidate
    return 'powershell' if os.name=='nt' else 'bash'


def source_plan(root,shell,login=False):
    from profiles import resolve
    context=resolve(root)
    if shell in ('bash','zsh'):
        from startup import Compiler
        compiler=Compiler(root,shell);body,_=compiler.build()
        steps=[dict(name=parts[2],kind=parts[3]) for line in body.splitlines() if line.startswith('_dots_debug_event begin ') for parts in [shlex.split(line)]]
        steps=list({(row['name'],row['kind']):row for row in steps}.values())
        modules=[row['name'] for row in steps if row['kind'] in ('inlined','source')]
    else: modules=['shells/powershell/profile.ps1','shells/powershell/init.ps1','shells/powershell/environment.ps1','lib/dots/shell/init.ps1','shells/powershell/interactive.ps1']
    if shell=='powershell': steps=[dict(name=name,kind='source') for name in modules]
    return dict(version=1,mode='plan',shell=shell,login=login,execution=False,profile=context['current'],
                note='Declared module traversal; runtime conditions and user rc files may change actual order.',
                modules=modules,steps=steps,profile_hooks=[str(Path(r['root'])/'shells'/('init.'+shell)) for r in context['layers']] if shell!='powershell' else [])


def finish_events(records, start):
    events=[]; stacks={}
    for record in records:
        event,when,label,kind,status,pid=record
        if event not in ('begin','end','ready','cache','source','coverage'): continue
        try: when=float(when)
        except ValueError: continue
        if not (0<=when<10**12): continue
        offset=max(0,(when-start)*1000) if when>start-10 else None
        if event=='end':
            stack=stacks.setdefault(pid,[])
            matched=next((i for i in reversed(stack) if events[i]['name']==label),None)
            if matched is not None:
                row=events[matched]
                elapsed=(when-row.pop('_start'))*1000
                row['duration_ms']=round(elapsed,3) if elapsed>=0 else None
                row['status']='completed' if status in ('','0') else 'returned-nonzero'
                row['exit_status']=int(status) if status.isdigit() else None
                stack.remove(matched)
            continue
        stack=stacks.setdefault(pid,[])
        row=dict(name=label,kind=kind,offset_ms=round(offset,3) if offset is not None else None,duration_ms=None,
                 depth=len(stack),timestamp='observer' if event=='source' else 'shell',status='incomplete' if event=='begin' else 'observed',pid=pid,_start=when)
        events.append(row)
        if event=='begin': stack.append(len(events)-1)
    for row in events: row.pop('_start',None)
    return events


def stop(process):
    if os.name=='nt':
        subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5)
    else:
        try: os.killpg(process.pid,signal.SIGTERM)
        except ProcessLookupError: return
        try: process.wait(timeout=0.5)
        except subprocess.TimeoutExpired: pass
        try: os.killpg(process.pid,signal.SIGKILL)
        except ProcessLookupError: pass


def one_run(root,env,shell,login,timeout,isolated,base):
    executable=shutil.which('pwsh') or shutil.which('powershell') if shell=='powershell' else shutil.which(shell)
    if not executable: return dict(status='unavailable',exit_code=1,events=[],shell=shell)
    records=[]; lock=threading.Lock();truncated=[False];ready=[None];retained=[0];start=time.time(); clock=time.perf_counter()
    def save(record):
        with lock:
            size=sum(len(value.encode('utf8')) for value in record)
            if len(records)<LIMIT and retained[0]+size<=8*1024*1024:
                retained[0]+=size
                records.append(record)
                if record[0]=='ready': ready[0]=(time.perf_counter()-clock)*1000
            else: truncated[0]=True
    env=dict(env)
    threads=[];read_fd=write_fd=None
    if shell=='powershell':
        event_file=base/'events.jsonl';event_file.touch(mode=0o600)
        env['DOTS_DEBUG_EVENTS']=str(event_file)
        code="if (Get-Command Write-DotsDebugEvent -ErrorAction Ignore) { Write-DotsDebugEvent ready startup phase 0 }; exit 0"
        if isolated:
            profile=str(root/'shells/powershell/profile.ps1').replace("'","''")
            owned=str(Path(env['HOME'])/'Documents/profile.ps1').replace("'","''")
            code="$PROFILE.CurrentUserAllHosts='"+owned+"'; $PROFILE.CurrentUserCurrentHost='"+owned+"'; . '"+profile+"'; "+code
        command=[executable,'-NoLogo','-NoExit']+(['-NoProfile'] if isolated else [])+['-Command',code]
        kwargs={} if os.name=='nt' else dict(start_new_session=True)
    else:
        read_fd,write_fd=os.pipe();env['DOTS_DEBUG_FD']=str(write_fd)
        env['PS4']='DOTS_SOURCE:%x:%I> '
        code="if typeset -f _dots_debug_event >/dev/null; then _dots_debug_event ready startup phase 0; else printf '%s\\0' ready \"${EPOCHREALTIME:-0}\" startup phase 0 \"$$\" >&\"$DOTS_DEBUG_FD\"; fi"
        if shell=='zsh': code += '; if [[ ! -o sourcetrace || $PS4 != DOTS_SOURCE:* ]]; then typeset -f _dots_debug_event >/dev/null && _dots_debug_event coverage source-tracing-disabled phase; fi'
        command=[executable]
        if shell=='zsh': command+=(['-d'] if isolated else [])+['-o','SOURCE_TRACE']
        elif isolated:
            if login:
                command+=['--noprofile','--norc']
                code='source "$HOME/.bash_profile"; '+code
            else: command+=['--noprofile','--rcfile',str(Path(env['HOME'])/'.bashrc')]
        if login: command+=['-l']
        command+=['-i','-c',code]
        kwargs=dict(pass_fds=(write_fd,),start_new_session=True)
    try:
        process=subprocess.Popen(command,env=env,cwd=env.get('HOME') if isolated else None,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,**kwargs)
    except OSError:
        for descriptor in (read_fd,write_fd):
            if descriptor is not None: os.close(descriptor)
        raise
    close_job=None
    if os.name=='nt':
        from .windows import own
        close_job=own(process)
    if write_fd is not None: os.close(write_fd)
    def stderr_reader():
        buffer=b''
        while True:
            chunk=os.read(process.stderr.fileno(),4096)
            if not chunk: break
            buffer+=chunk
            while b'\n' in buffer:
                line,buffer=buffer.split(b'\n',1)
                match=re.fullmatch(rb'DOTS_SOURCE:(.{1,8192}):[0-9]+> <sourcetrace>\r?',line)
                if match: save(('source',str(time.time()),match[1].decode('utf8','replace'),'source-entry','',str(process.pid)))
            if len(buffer)>16384: buffer=b''
    thread=threading.Thread(target=stderr_reader,daemon=True);thread.start();threads.append(thread)
    if read_fd is not None:
        def event_reader():
            buffer=b'';fields=[]
            with os.fdopen(read_fd,'rb') as stream:
                while True:
                    chunk=os.read(stream.fileno(),4096)
                    if not chunk: break
                    buffer+=chunk
                    while b'\0' in buffer:
                        value,buffer=buffer.split(b'\0',1);fields.append(value.decode('utf8','replace'))
                        if len(fields)==6:
                            if all(len(v)<=8192 for v in fields): save(tuple(fields))
                            fields=[]
                    if len(buffer)>16384: buffer=b'';fields=[];truncated[0]=True
        thread=threading.Thread(target=event_reader,daemon=True);thread.start();threads.append(thread)
    status='completed'
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        status='timeout';stop(process)
    except KeyboardInterrupt:
        status='interrupted';stop(process)
    finally:
        if close_job: close_job()
        # Descendants holding event pipes must not outlive the diagnostic run.
        if os.name!='nt':
            try: os.killpg(process.pid,signal.SIGTERM)
            except ProcessLookupError: pass
        for thread in threads: thread.join(timeout=0.5)
        if os.name!='nt':
            try: os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError: pass
        for thread in threads: thread.join(timeout=0.5)
    if not any(thread.is_alive() for thread in threads): process.stderr.close()
    if shell=='powershell' and event_file.is_file():
        with event_file.open() as stream:
            for index,line in enumerate(iter(lambda: stream.readline(65537),'')):
                if index>=LIMIT or len(line)>65536: truncated[0]=True;break
                try:
                    row=json.loads(line);save(tuple(str(row[k]) for k in ('event','time','name','kind','status','pid')))
                except (ValueError,KeyError,TypeError): continue
    exit_code=124 if status=='timeout' else 130 if status=='interrupted' else (0 if process.returncode==0 else 1)
    if exit_code and status=='completed': status='failed'
    events=finish_events(records,start)
    measured=any(row['kind'] in ('inlined','module') for row in events)
    startup_ready=next((r['offset_ms'] for r in events if r['name']=='startup' and r['status']=='observed' and r['kind']=='phase'),None)
    return dict(status=status,exit_code=exit_code,checkout=str(root),events=events,startup_ms=startup_ready if startup_ready is not None else ready[0],process_ms=round((time.perf_counter()-clock)*1000,3),
                truncated=truncated[0],dots_instrumented=measured,coverage='Zsh source entries and Dots measured modules' if shell=='zsh' else 'Dots measured modules only',
                note=('No Dots module markers observed. ' if not measured else '')+'Inclusive instrumented timings; no prompt rendering. Child input/output is redirected; terminal-dependent startup may differ.')


def run(root,args):
    shell=shell_choice(args.shell)
    if not args.live and not args.isolated: return source_plan(root,shell,args.login)
    context=fixture(root) if args.isolated else nullcontext((root,dict(os.environ),None))
    samples=[]
    with context as (checkout,env,base):
        with tempfile.TemporaryDirectory(prefix='dots-trace-') as temp:
            for index in range(args.runs):
                runbase=Path(temp)/str(index);runbase.mkdir()
                sample=one_run(checkout,env,shell,args.login,args.timeout,args.isolated,runbase)
                samples.append(sample)
                if sample['exit_code']: break
    values=[s['startup_ms'] for s in samples if s.get('startup_ms') is not None]
    return dict(version=1,mode='isolated' if args.isolated else 'live',shell=shell,login=args.login,runs=samples,
                summary=dict(samples=len(samples),median_ms=statistics.median(values) if values else None,min_ms=min(values) if values else None,max_ms=max(values) if values else None),
                exit_code=next((r['exit_code'] for r in samples if r['exit_code']),0))
