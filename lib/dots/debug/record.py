"""Code generation and read-only access to opted-in shell PATH histories."""
import json
import os
from pathlib import Path
import shlex
import stat
from .changes import path_changes, source_location


def snippet(root, action, shell):
    if shell == 'powershell':
        path=str(root/'lib/dots/shell/trace.ps1').replace("'", "''")
        return ". '"+path+"'\n"+('Start-DotsPathRecording' if action=='start' else 'Stop-DotsPathRecording')+'\n'
    path=shlex.quote(str(root/'lib/dots/shell/record.bash'))
    return ('_dots_record_existing_debug=$(trap -p DEBUG)\n' if shell=='bash' and action=='start' else '')+'source '+path+'\n_dots_record_'+action+'\n'


def alive(pid):
    if os.name == 'nt':
        import ctypes
        kernel=ctypes.windll.kernel32
        kernel.OpenProcess.restype=ctypes.c_void_p
        handle=kernel.OpenProcess(0x1000,False,int(pid))
        if not handle:return False
        code=ctypes.c_ulong()
        try:return bool(kernel.GetExitCodeProcess(ctypes.c_void_p(handle),ctypes.byref(code))) and code.value==259
        finally:kernel.CloseHandle(ctypes.c_void_p(handle))
    try:os.kill(int(pid),0);return True
    except (OSError,ValueError):return False


def history():
    value=os.environ.get('DOTS_DEBUG_SESSION')
    result=dict(version=1,status='unrecorded',history=[],note='No current-session recording; inherited origins are unknown.')
    if not value:return result
    path=Path(value)
    if path.is_symlink() or path.parent.is_symlink():raise ValueError('unsafe recording path')
    try:
        descriptor=os.open(path,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_NONBLOCK',0))
    except FileNotFoundError:
        result.update(status='stale',note='Recording is unavailable; no historical attribution.');return result
    with os.fdopen(descriptor,'rb') as stream:
        info=os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size>9*1024*1024:raise ValueError('invalid recording file')
        if os.name!='nt' and (info.st_uid!=os.getuid() or info.st_mode&0o077):raise ValueError('recording must be private and owned by this user')
        raw=stream.read(9*1024*1024)
    fields=raw.decode('utf8','replace').split('\0');rows=[]
    if path.suffix=='.jsonl':
        for line in raw.decode('utf8').splitlines():
            row=json.loads(line);rows.append(tuple(str(row[k]) for k in ('event','time','file','line','path','pid')))
    else:rows=[tuple(fields[i:i+6]) for i in range(0,len(fields)-6,6)]
    if not rows or rows[0][0]!='baseline' or not rows[0][5].isdigit() or not alive(rows[0][5]):
        result.update(status='stale',note='Recording owner is no longer running.');return result
    owner=rows[0][5];base=float(rows[0][1]);previous=None;events=[];maps={};status='active';truncated=False
    for event,when,file,line,current,pid in rows:
        if pid!=owner:continue
        if event=='baseline':previous=current;status='active';continue
        if event=='stop':status='stopped';continue
        if event=='limit':status='truncated';truncated=True;continue
        if event!='path' or previous is None:continue
        source,number=source_location(file,int(line) if line.isdigit() else None,maps)
        for item in path_changes(previous,current):
            item.update(file=source,line=number,offset_ms=round((float(when)-base)*1000,3),timestamp=float(when),precision='observation-interval',pid=pid)
            events.append(item)
        previous=current
    result.update(status=status,truncated=truncated,history=events,initial_path=rows[0][4],final_path=previous,pid=owner,
                  note='Recorded PATH changes; locations identify observation intervals. Pre-recording history is unknown.')
    return result
