"""Private read-only filename protocol for Unix PowerShell lacking UnixMode.

Never reads TOML/metadata contents, starts tools, or creates directories/caches.
"""
import base64
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import time
sys.dont_write_bytecode = True


def names(root, kind):
    if kind not in ('themes','modules','backups') or os.name != 'posix': return []
    spec=importlib.util.spec_from_file_location('completion_core',Path(__file__).with_name('blastoff.py'))
    core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)
    directory=core.storage_root(core.path(root))/kind
    core.inspect_parents(directory)
    result=[];deadline=time.monotonic()+0.1
    with os.scandir(directory) as entries:
        for index, entry in enumerate(entries):
            if index>=4096 or time.monotonic()>=deadline: break
            if not entry.name.endswith('.toml') or not entry.is_file(follow_symlinks=False): continue
            name=entry.name[:-5]
            try: core.name(name)
            except core.Failure: continue
            if kind=='backups':
                try: core.regular(directory/(name+'.json'))
                except (core.Failure,OSError): continue
            result.append(name)
    return sorted(result)

if __name__=='__main__':
    try:
        if len(sys.argv)!=2 or len(sys.argv[1])>16384: raise ValueError('Invalid completion context')
        doc=json.loads(base64.b64decode(sys.argv[1],validate=True).decode('utf-8'))
        result=names(doc['root'],doc['kind'])
    except Exception:
        result=[]
    print(json.dumps({'names':result},ensure_ascii=True))
