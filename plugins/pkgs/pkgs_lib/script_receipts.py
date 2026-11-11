"""Evidence of completed scripts; a receipt can skip work, never authorize it."""
import hashlib
import json
import os
from pathlib import Path
import stat
import time

from .common import atomic


def location(spec):
    base = (Path(os.environ.get('LOCALAPPDATA', Path.home()/'AppData/Local')) if os.name=='nt'
            else Path(os.environ.get('XDG_STATE_HOME', Path.home()/'.local/state')))
    return base/'pkgs/npm-scripts'/(hashlib.sha256(spec.encode()).hexdigest()+'.json')


def fingerprint(records):
    """Bounded metadata walk detects reinstalls and changed/missing build outputs.

    Do not follow symlinks or read arbitrary installed file contents. Include inode,
    ctime and mtime so same-version reinstalls and output edits invalidate receipts.
    """
    digest=hashlib.sha256(); deadline=time.monotonic()+3; count=0
    try:
        for record in records:
            metadata=json.loads(record); root=Path(metadata['path'])
            if not root.is_absolute() or root.is_symlink() or not (root/'package.json').is_file(): return None
            digest.update(record.encode())
            pending=[root]
            while pending:
                path=pending.pop(); count+=1
                if count>100000 or time.monotonic()>deadline: return None
                info=path.lstat()
                digest.update(json.dumps([str(path.relative_to(root)),info.st_dev,info.st_ino,info.st_mode,
                                          info.st_size,info.st_mtime_ns,info.st_ctime_ns]).encode())
                if stat.S_ISLNK(info.st_mode):
                    if not path.resolve().is_relative_to(root.resolve()): return None
                    digest.update(os.readlink(path).encode())
                elif stat.S_ISDIR(info.st_mode): pending.extend(sorted(path.iterdir(),reverse=True))
                elif not stat.S_ISREG(info.st_mode): return None
        return digest.hexdigest() if records else None
    except (OSError,ValueError,TypeError,KeyError,RuntimeError): return None


def matches(spec, proof):
    if not proof: return False
    try:
        path=location(spec)
        if path.is_symlink() or path.stat().st_size>1024: return False
        return json.loads(path.read_text())=={'schema':1,'fingerprint':proof}
    except (OSError,ValueError): return False


def save(spec, proof):
    if proof: atomic(location(spec),json.dumps({'schema':1,'fingerprint':proof})+'\n')
