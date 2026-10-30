"""Partial family retention with immutable file identities and additive expansion."""
from copy import deepcopy
from pathlib import Path
import shutil
import tempfile

from fonts.model import digest, relative, sha


def folder(plan, identity, version):
    return plan.payloads.get((identity,version),plan.library.folder(identity,version))


def merge(plan, identity, version, payload, record, temporary):
    old=plan.document['families'][identity]['versions'][version]
    known={f['file']:deepcopy(f) for f in old.get('known_fonts',old['fonts'])}
    names={name.casefold():name for name in known}
    for font in record.get('known_fonts',record['fonts']):
        name=relative(font['file'])
        if name.casefold() in names and names[name.casefold()]!=name:
            raise ValueError('font version has colliding filenames')
        if name in known and known[name]!=font:
            raise ValueError('font version already exists with different contents or metadata')
        known[name]=deepcopy(font);names[name.casefold()]=name
    if old.get('fingerprint') and record.get('fingerprint') and old['fingerprint']!=record['fingerprint']:
        raise ValueError('font release fingerprint changed')
    if not old.get('partial') and not record.get('partial'):
        raise ValueError('font version already exists with different contents')
    if temporary is None:raise ValueError('partial font expansion needs a staged operation')
    destination=Path(tempfile.mkdtemp(prefix='merge-',dir=temporary))
    fonts={}
    if old.get('available',True):
        for font in old['fonts']:plan.file(identity,version,font)
        shutil.copytree(folder(plan,identity,version),destination,dirs_exist_ok=True)
        fonts.update({f['file']:f for f in old['fonts']})
    for source in Path(payload).rglob('*'):
        if source.is_symlink():raise ValueError('font payload contains a symlink')
        target=destination/source.relative_to(payload)
        if source.is_dir():target.mkdir(parents=True,exist_ok=True);continue
        if target.exists() and sha(target)!=sha(source):raise ValueError('font version contains a conflicting file')
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    fonts.update({f['file']:f for f in record['fonts']})
    result=deepcopy(old);result.update(fonts=list(fonts.values()),known_fonts=list(known.values()),
        partial=not set(known)<=set(fonts),licenses=sorted({*old.get('licenses',[]),*record.get('licenses',[])}))
    # An uninstalled payload may have licenses that are no longer available.
    result['licenses']=[name for name in result['licenses'] if (destination/relative(name)).is_file()]
    if 'available' in result:result['available']=True
    result['payload_digest']=digest(destination)
    return destination,result


def retain(source, target, identity, version, temporary, *, faces=None):
    """Copy a whole version or selected faces, including available licenses."""
    from fonts import operations as ops
    record=source.document['families'][identity]['versions'][version]
    if record.get('available') is False:raise ValueError('font version is uninstalled in the selected source')
    for font in record['fonts']:source.file(identity,version,font)
    target.guards.update(source.guards)
    payload=folder(source,identity,version)
    copied=deepcopy(record);copied.pop('available',None)
    if faces is not None:
        chosen=[f for f in record['fonts'] if f['file'] in faces]
        if len(chosen)!=len(set(faces)) or not chosen:raise ValueError('selected font faces are unavailable')
        selected=Path(tempfile.mkdtemp(prefix='retain-',dir=temporary))
        for name in [f['file'] for f in chosen]+record.get('licenses',[]):
            source_path=payload/relative(name);source.guard(source_path)
            if source_path.is_symlink() or not source_path.is_file():raise ValueError('font/license is unavailable')
            dest=selected/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source_path,dest)
        copied.update(fonts=chosen,known_fonts=record.get('known_fonts',record['fonts']))
        copied['partial']={f['file'] for f in chosen}!={f['file'] for f in copied['known_fonts']}
        payload=selected
    target.guards.update(source.guards)
    ops.stage(target,identity,version,payload,copied,source.document['families'][identity]['name'],temporary=temporary)
    return version
