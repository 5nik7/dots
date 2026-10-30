"""Explicit profile font preferences and transactional application retention."""
from copy import deepcopy
from pathlib import Path

from fonts import operations as ops
from fonts.config import configure, destination, TARGETS
from fonts.destinations import Destinations
from fonts.model import read, digest, sha, relative
from fonts.payloads import retain
from fonts.workspace import Workspace


def preferences(workspace):
    destinations=Destinations()
    archive=workspace.store('PROFILEFONTS')
    path=archive.library.directory.parent/'fonts.json'
    workspace.user.guards.update(destinations.guards)
    before=workspace.user.guard(path)
    if path.is_symlink():raise ValueError('profile fonts.json must be a regular file')
    document=read(path,dict(schema=1,applications={}))
    if digest(path)!=before:raise ValueError('font preferences changed while reading')
    if document.get('schema')!=1 or not isinstance(document.get('applications'),dict):raise ValueError('invalid font preferences')
    return archive,path,document


def rows(library):
    workspace=Workspace(library,None)
    _,path,document=preferences(workspace)
    return dict(schema=1,path=str(path),items=[dict(selection=k,**v) for k,v in document['applications'].items()])


def preserve_termux(workspace,archive,new_font):
    plan=workspace.user;path=plan.library.home/'.termux/font.ttf'
    if not path.exists():return
    plan.guard(path)
    if path.is_symlink():raise ValueError('Termux font is a symlink; review its ownership first')
    if sha(path)==new_font['sha256']:return
    previous=plan.library.document['targets'].get('termux')
    if previous:
        if digest(path)!=previous['after']:raise ValueError('active font configuration changed; preserve and review it')
        identity,version,face=previous['id'],previous['version'],previous['face']
    else:
        identity,version=ops.import_files(plan,path,workspace.temporary)
        face=plan.document['families'][identity]['versions'][version]['fonts'][0]['file']
    retain(plan,archive,identity,version,workspace.temporary,faces=[face])


def synchronize(workspace):
    """Retain configured app choices, even when an older selection is unchanged."""
    plan=workspace.user
    configured={item['target'] for item in plan.items if item.get('action')=='set'}
    changed={k:r for k,r in plan.document['targets'].items()
             if k in configured or r!=plan.library.document['targets'].get(k)}
    if not changed:return
    archive,path,document=preferences(workspace)
    for key,ref in changed.items():
        identity,version=ref['id'],ref['version']
        record=plan.document['families'][identity]['versions'][version]
        face=next(f for f in record['fonts'] if f['file']==ref['face'])
        selected=[face] if ref['target']=='termux' else [f for f in record['fonts'] if f['variant']==face['variant']]
        if ref['target']=='termux':preserve_termux(workspace,archive,face)
        retain(plan,archive,identity,version,workspace.temporary,faces=[f['file'] for f in selected])
        ref['directory']=archive.library.directory_key
        installed=plan.document['families'][identity].get('installed')
        if installed and installed['version']==version and installed['variant']==face['variant']:
            installed['directory']=archive.library.directory_key
        spec=plan.library.catalog['families'].get(identity,{}).get('versions',{}).get(version)
        document['applications'][key]=dict(id=identity,version=version,face=face['file'],variant=face['variant'],
            target=ref['target'],config=ref.get('config'),app_profile=ref.get('app_profile'),directory='PROFILEFONTS',
            files={f['file']:f['sha256'] for f in selected},upstream=deepcopy(spec),
            name=plan.document['families'][identity]['name'])
    plan.put(path,data=document)


def choose(workspace,identity,version,source,args, *, saved=None):
    plan=workspace.user
    targets=list(dict.fromkeys(args.target or []))
    if not targets:raise ValueError('set requires at least one --target')
    if args.config and (len(targets)!=1 or targets==['termux']):raise ValueError('--config requires one desktop target')
    if args.app_profile and targets!=['windows-terminal']:raise ValueError('--app-profile requires the windows-terminal target only')
    for target in targets:destination(plan.library,target,args.config)
    origin,version=workspace.obtain(identity,version,source,dry_run=args.dry_run)
    if origin is None:return
    record=origin.document['families'][identity]['versions'][version]
    pin=origin.document['families'][identity].get('pin')
    if pin and pin!=version:raise ValueError('family is pinned; unpin before switching versions')
    variants={f['variant'] for f in record['fonts']}
    installed=plan.document['families'].get(identity,{}).get('installed') or {}
    variant=args.variant or installed.get('variant') or ('mono' if 'mono' in variants else 'original' if 'original' in variants else sorted(variants)[0])
    face=ops.face_for(record,args.face,args.variant if args.face else variant)
    variant=face['variant']
    if any(t!='termux' for t in targets) and record.get('partial'):
        origin,version=workspace.obtain(identity,version,None,dry_run=args.dry_run,required_variant=variant)
        if origin is None:return
        record=origin.document['families'][identity]['versions'][version]
        face=ops.face_for(record,face['file'],variant)
    if saved:
        actual={f['file']:f['sha256'] for f in record['fonts']}
        if not saved.get('files') or any(actual.get(relative(n))!=checksum for n,checksum in saved['files'].items()):
            raise ValueError('saved default font contents differ; restore the exact saved files')
    if origin is not plan:retain(origin,plan,identity,version,workspace.temporary)
    row=plan.document['families'][identity]
    if row.get('pin') and row['pin']!=version:raise ValueError('family is pinned; unpin before switching versions')
    if any(t!='termux' for t in targets):ops.install(plan,identity,version,variant)
    for target in targets:configure(plan,identity,version,face,target,explicit=args.config,app_profile=args.app_profile)


def set_font(library,args,temporary):
    workspace=Workspace(library,temporary)
    source=str(library.directory) if library.directory else None
    if bool(args.operand)==bool(args.file):raise ValueError('set requires a FONT or --file, but not both')
    if args.file:
        if args.version:raise ValueError('--version cannot assign an upstream version to a local import')
        identity,version=ops.import_files(workspace.user,args.file,temporary);source='personal'
    elif args.operand.startswith('installed:'):
        from fonts.inventory import snapshot,select,import_row
        installed,_=snapshot(workspace.user.library)
        row=select(installed,[args.operand])[0]
        identity,version,face=import_row(workspace,row,installed,family=any(t!='termux' for t in args.target or []))
        args=deepcopy(args);args.face=args.face or face;source='personal'
    else:
        identity=workspace.resolve(args.operand,source,catalog=True);version=args.version
    choose(workspace,identity,version,source,args)
    synchronize(workspace)
    return workspace.finish()


def restore(library,args,temporary):
    workspace=Workspace(library,temporary)
    _,_,document=preferences(workspace)
    selections=args.operand or list(document['applications'])
    for key in selections:
        saved=document['applications'].get(key)
        if not saved:raise ValueError('no saved default for '+key)
        if saved.get('target') not in TARGETS or key!=saved['target']+(':'+saved['app_profile'] if saved.get('app_profile') else ''):
            raise ValueError('invalid saved application target')
        identity,version=saved['id'],saved['version']
        # Saved official source descriptions allow exact recovery after catalog refresh.
        if saved.get('upstream'):
            catalog=workspace.user.library.catalog['families']
            entry=catalog.setdefault(identity,dict(name=saved['name'],provider=identity.split(':')[0],latest=version,versions={}))
            entry['versions'].setdefault(version,deepcopy(saved['upstream']))
        selected=deepcopy(args)
        selected.target=[saved['target']];selected.config=saved.get('config');selected.app_profile=saved.get('app_profile')
        selected.variant=saved['variant'];selected.face=saved['face']
        choose(workspace,identity,version,None,selected,saved=saved)
    synchronize(workspace)
    return workspace.finish()
