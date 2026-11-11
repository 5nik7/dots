"""Private read-only catalog/filename protocol for shell completion.

Never reads backup payloads, starts tools, or creates directories/caches.
Backup completion also reads the bounded shared catalog.
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
    if kind not in ('themes','modules','backups'): return []
    spec=importlib.util.spec_from_file_location('completion_core',Path(__file__).with_name('blastoff.py'))
    core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)
    directory=core.storage_root(core.path(root))/kind
    core.inspect_parents(directory)
    result=list(core.ui_module('shared_backups').entries(directory.parent))[:4096] if kind == 'backups' else []
    if not directory.exists(): return sorted(result)
    deadline=time.monotonic()+0.1
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
        if len(sys.argv)==3 and sys.argv[1]=='--shared':
            spec=importlib.util.spec_from_file_location('completion_core',Path(__file__).with_name('blastoff.py'))
            core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)
            root=core.storage_root(core.path(sys.argv[2]))
            print('\n'.join(sorted(core.ui_module('shared_backups').entries(root))[:4096]))
            sys.exit(0)
        if len(sys.argv)!=2 or len(sys.argv[1])>16384: raise ValueError('Invalid completion context')
        doc=json.loads(base64.b64decode(sys.argv[1],validate=True).decode('utf-8'))
        result=names(doc['root'],doc['kind'])
    except Exception:
        if '--shared' in sys.argv: sys.exit(0)
        result=[]
    print(json.dumps({'names':result},ensure_ascii=True))
