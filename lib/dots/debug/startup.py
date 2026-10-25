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
from .changes import Snapshots, source_location

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
        stream=pid+(':observed' if kind=='observed-source' else '')
        if event=='end':
            stack=stacks.setdefault(stream,[])
            matched=next((i for i in reversed(stack) if events[i]['name']==label),None)
            if matched is not None:
                row=events[matched]
                elapsed=(when-row.pop('_start'))*1000
                row['duration_ms']=round(elapsed,3) if elapsed>=0 else None
                row['status']='completed' if status in ('','0') else 'returned-nonzero'
                row['exit_status']=int(status) if status.isdigit() else None
                stack.remove(matched)
            continue
        stack=stacks.setdefault(stream,[])
        row=dict(id=len(events)+1,parent_id=events[stack[-1]]['id'] if stack else None,name=label,kind=kind,offset_ms=round(offset,3) if offset is not None else None,duration_ms=None,
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


def one_run(root,env,shell,login,timeout,isolated,base,detail='files',changes='path,variables,functions,aliases,options',show_values=()):
    executable=shutil.which('pwsh') or shutil.which('powershell') if shell=='powershell' else shutil.which(shell)
    if not executable: return dict(status='unavailable',exit_code=1,events=[],shell=shell)
    records=[]; lock=threading.Lock();truncated=[False];ready=[None];retained=[0];start=time.time(); clock=time.perf_counter()
    budget=[0,0]
    snapshots=Snapshots(show_values, ';' if shell=='powershell' and os.name=='nt' else ':',budget=budget)
    def save(record):
        with lock:
            if record[0]=='change':
                try:
                    change=json.loads(record[4])
                    if change['category'] not in ('variables','functions','aliases','options'): return
                    change.update(time=float(record[1]),pid=record[5])
                    snapshots.keep_change(change)
                except (ValueError,KeyError,TypeError):pass
                return
            if snapshots.accept(record): return
            size=sum(len(value.encode('utf8')) for value in record)
            if snapshots.reserve(size):
                retained[0]+=size
                records.append(record)
                if record[0]=='ready': ready[0]=(time.perf_counter()-clock)*1000
            else: truncated[0]=True
    env=dict(env)
    env.update(DOTS_DEBUG_DETAIL=detail,DOTS_DEBUG_CHANGES=changes,DOTS_DEBUG_VALUES=','.join(show_values))
    env.pop('DOTS_DEBUG_RECORD',None)
    env.pop('DOTS_DEBUG_SESSION',None)
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
        if detail=='deep':
            condition='[[ ${functions[TRAPDEBUG]:-} == *_dots_trace_debug* ]]' if shell=='zsh' else '[[ $(trap -p DEBUG) == *_dots_trace_debug* ]]'
            code+='; if ! '+condition+'; then typeset -f _dots_debug_event >/dev/null && _dots_debug_event coverage "Deep trace unavailable: observer absent or replaced" phase; fi'
        command=[executable]
        if shell=='bash' and detail=='deep':
            env['DOTS_DEBUG_FUNCTRACE']='1'
        if shell=='zsh': command+=(['-d'] if isolated else [])+['-o','SOURCE_TRACE']
        elif isolated:
            if login:
                command+=['--noprofile','--norc']
                code='source "$HOME/.bash_profile"; '+code
            else: command+=['--noprofile','--rcfile',str(Path(env['HOME'])/'.bashrc')]
        if shell=='bash' and detail=='deep':command+=['-T']
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
            buffer=bytearray();fields=[];discard=False;bad=False
            with os.fdopen(read_fd,'rb') as stream:
                while True:
                    chunk=os.read(stream.fileno(),4096)
                    if not chunk: break
                    pieces=chunk.split(b'\0')
                    for index,piece in enumerate(pieces):
                        if not discard:
                            if len(buffer)+len(piece)>8*1024*1024:
                                buffer.clear();discard=True;bad=True;truncated[0]=True
                            else:buffer.extend(piece)
                        if index<len(pieces)-1:
                            fields.append(buffer.decode('utf8','replace'));buffer.clear();discard=False
                            if len(fields)==6:
                                if not bad:save(tuple(fields))
                                else:
                                    with lock:
                                        snapshots.pending.pop(fields[5],None);snapshots.previous.pop(fields[5],None)
                                fields=[];bad=False
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
    snapshots.close(time.time())
    events=finish_events(sorted([*records,*snapshots.observed],key=lambda r:float(r[1]) if r[1].replace('.','',1).isdigit() else 0),start)
    if any(row['name']=='Trace limit reached' for row in events):truncated[0]=True
    children_by_parent={};events_by_name={}
    for event in events:
        children_by_parent.setdefault(event.get('parent_id'),[]).append(event)
        events_by_name.setdefault(event['name'],[]).append(event)
    for event in events:
        if event['kind']=='observed-source':event['precision']='observed-interval'
        children=children_by_parent.get(event['id'],[])
        if event['duration_ms'] is not None and children and all(c['duration_ms'] is not None for c in children):
            own=event['duration_ms']-sum(c['duration_ms'] for c in children)
            if own>=0:event['self_ms']=round(own,3)
    maps={}
    for row in snapshots.changes:
        row['timestamp']=row.pop('time')
        row['offset_ms']=round(max(0,(row['timestamp']-start)*1000),3)
        original=(row['file'],row['line'])
        row['file'],row['line']=source_location(*original,maps)
        if original!=(row['file'],row['line']): row['generated_file'],row['generated_line']=original
        if row.get('observed_at_file'):
            row['observed_at_file'],row['observed_at_line']=source_location(row['observed_at_file'],row.get('observed_at_line'),maps)
        if detail=='changes':row['precision']='file-boundary'
        candidates=[e for e in events_by_name.get(row['file'],[]) if e['offset_ms'] is not None and e['offset_ms']<=row['offset_ms'] and (e['duration_ms'] is None or row['offset_ms']<=e['offset_ms']+e['duration_ms']+1)]
        row['parent_id']=candidates[-1]['id'] if candidates else None
    if any('unavailable:' in row['name'] for row in events if row['kind']=='phase'): exit_code=1;status='incomplete'
    measured=any(row['kind'] in ('inlined','module') for row in events)
    startup_ready=next((r['offset_ms'] for r in events if r['name']=='startup' and r['status']=='observed' and r['kind']=='phase'),None)
    return dict(status=status,exit_code=exit_code,checkout=str(root),events=events,startup_ms=startup_ready if startup_ready is not None else ready[0],process_ms=round((time.perf_counter()-clock)*1000,3),
                truncated=truncated[0] or snapshots.truncated,dots_instrumented=measured,changes=snapshots.changes,
                initial_path=next(iter(snapshots.initial_paths.values()),None),final_path=next(iter(snapshots.final_paths.values()),None),detail=detail,
                capabilities=dict(files=True,boundary_changes=True,line_observations=snapshots.observed_lines),
                coverage=('State changes from the first Dots observer; line attribution is an observation interval. ' if detail!='files' else '')+('Zsh source entries and Dots measured modules' if shell=='zsh' else 'Dots measured modules only'),
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
                sample=one_run(checkout,env,shell,args.login,args.timeout,args.isolated,runbase,getattr(args,'detail','files'),getattr(args,'changes','path,variables,functions,aliases,options'),getattr(args,'show_values',()))
                samples.append(sample)
                if sample['exit_code']: break
    values=[s['startup_ms'] for s in samples if s.get('startup_ms') is not None]
    return dict(version=1,mode='isolated' if args.isolated else 'live',shell=shell,login=args.login,runs=samples,
                summary=dict(samples=len(samples),median_ms=statistics.median(values) if values else None,min_ms=min(values) if values else None,max_ms=max(values) if values else None),
                exit_code=next((r['exit_code'] for r in samples if r['exit_code']),0))
