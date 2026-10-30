"""Directory storage and explicit activation through the existing font plans."""
from copy import deepcopy
from pathlib import Path

from fonts.model import Library,Plan,digest,exists
from fonts import operations as ops


def resolve(library, query):
    rows=dict(library.catalog['families'])
    rows.update(library.collection['families']);rows.update(library.families)
    if query in rows:return query
    needle=query.casefold().replace(' ','')
    matches=[key for key,row in rows.items() if needle in (key+' '+row.get('name','')).casefold().replace(' ','')]
    if len(matches)!=1:raise ValueError('font selection is ambiguous' if matches else 'font not found; search, update or import first')
    return matches[0]


def copy_version(plan, source, identity, version, temporary=None):
    if plan.library.guard!=source.guard:raise ValueError('font collection changed while selecting a source')
    version,record=source.version(identity,version)
    source_plan=Plan(source)
    for font in record['fonts']:source_plan.file(identity,version,font)
    plan.guards.update(source_plan.guards)
    payload=source.folder(identity,version)
    record={k:v for k,v in record.items() if k!='available'}
    ops.stage(plan,identity,version,payload,record,source.families[identity]['name'],temporary=temporary)
    return version


def store(plan, identity, version, temporary, *, dry_run=False, keep_archive=False):
    library=plan.library
    catalog=library.catalog['families'].get(identity,{})
    local=library.collection['families'].get(identity,{})
    saved=plan.document['families'].get(identity,{})
    version=version or catalog.get('latest') or saved.get('preferred') or (local.get('installed') or {}).get('version') or local.get('preferred')
    if not version:raise ValueError('no version is available; refresh the catalog or import a font')
    existing=saved.get('versions',{}).get(version)
    if existing and existing.get('available',True) and not existing.get('partial'):
        for font in existing['fonts']:plan.file(identity,version,font)
        plan.items.append(dict(id=identity,version=version,action='already stored',path=str(library.directory)))
        return version
    if version in local.get('versions',{}) and (not local['versions'][version].get('partial') or version not in catalog.get('versions',{})):
        copy_version(plan,Library(platform=library.platform),identity,version,temporary)
        return version
    spec=catalog.get('versions',{}).get(version)
    if not spec:raise ValueError('version is unavailable in the user library or saved catalog; import it or refresh its release')
    if dry_run:
        plan.items.append(dict(id=identity,version=version,action='download, validate and store',path=str(library.directory)))
        return version
    from fonts.providers import download
    payload=Path(temporary)/('payload-'+str(len(plan.payloads)))
    record=download(identity,spec,payload,keep_archive=keep_archive)
    ops.stage(plan,identity,version,payload,record,catalog['name'],temporary=temporary)
    return version


def uninstall(plan, identity, version):
    if not version:raise ValueError('directory uninstall/remove requires an exact --version')
    row=plan.document['families'][identity]
    if version not in row['versions']:raise ValueError('unknown directory version')
    if row.get('pin')==version:raise ValueError('cannot uninstall a pinned version; unpin it first')
    record=row['versions'][version]
    folder=plan.library.folder(identity,version)
    if not record.get('available',True):
        if exists(folder):raise ValueError('uninstalled version path is occupied; preserve and review it')
        return
    for font in record['fonts']:plan.file(identity,version,font)
    plan.put(folder,delete=True)
    record['available']=False
    if row.get('preferred')==version:
        row['preferred']=next((v for v,r in reversed(row['versions'].items()) if r.get('available',True)),None)
    plan.items.append(dict(id=identity,version=version,action='uninstall directory copy; retain version history',path=str(folder)))


def upgrade(plan, identity, temporary, *, dry_run=False, version=None):
    explicit=identity is not None
    identities=[identity] if identity else list(plan.document['families'])
    for identity in identities:
        row=plan.document['families'].get(identity,{})
        if not explicit and not any(r.get('available',True) for r in row.get('versions',{}).values()):
            plan.items.append(dict(id=identity,action='skip uninstalled'));continue
        if row.get('pin'):
            plan.items.append(dict(id=identity,action='skip pinned',version=row['pin']));continue
        catalog=plan.library.catalog['families'].get(identity)
        if not catalog:
            plan.items.append(dict(id=identity,action='skip unknown upstream version'));continue
        candidate=version or catalog['latest']
        if candidate not in catalog['versions']:raise ValueError('version is not cataloged')
        fingerprint=catalog['versions'][candidate].get('fingerprint')
        if not version and fingerprint and any(r.get('available',True) and r.get('fingerprint')==fingerprint for r in row.get('versions',{}).values()):
            plan.items.append(dict(id=identity,action='up to date',version=row.get('preferred')));continue
        store(plan,identity,candidate,temporary,dry_run=dry_run)


def activate(library, identity, args, temporary=None):
    """Copy into the user library, then explicitly register/apply in one journal."""
    row=library.families[identity]
    version,record=library.version(identity,args.version or row.get('pin'))
    if row.get('pin') and row['pin']!=version:raise ValueError('family is pinned; unpin before switching versions')
    user=Library(platform=library.platform)
    plan=Plan(user)
    copy_version(plan,library,identity,version,temporary)
    if args.config and len(args.target or [])!=1:raise ValueError('--config requires a single --target')
    if args.app_profile and args.target!=['windows-terminal']:raise ValueError('--app-profile requires the windows-terminal target only')
    if args.config and args.target==['termux']:raise ValueError('--config applies only to desktop targets')
    if args.action=='set' and not args.target:raise ValueError('set requires an explicit --target')
    if args.action=='rollback' and not user.families.get(identity,{}).get('installed') and any(r['id']==identity for r in user.document['targets'].values()):
        ops.replace_active(plan,identity,version)
    elif not args.target or any(t!='termux' for t in args.target):
        ops.install(plan,identity,version,args.variant)
    if args.target:
        from fonts.config import configure
        variant=args.variant or (plan.document['families'][identity].get('installed') or {}).get('variant')
        face=ops.face_for(record,args.face,variant)
        for target in dict.fromkeys(args.target):
            configure(plan,identity,version,face,target,explicit=args.config,app_profile=args.app_profile)
    installed=plan.document['families'][identity].get('installed')
    if installed and installed['version']==version:installed['directory']=library.directory_key
    for ref in plan.document['targets'].values():
        if ref['id']==identity and ref['version']==version:ref['directory']=library.directory_key
    selected=deepcopy(library.document)
    selected['families'][identity]['preferred']=version
    plan.document.setdefault('directories',{})[library.directory_key]=selected
    plan.items.append(dict(id=identity,version=version,action='activate stored version',path=str(library.directory)))
    from fonts.workspace import Workspace
    from fonts.defaults import synchronize
    workspace=Workspace(user,temporary,plan=plan)
    synchronize(workspace)
    return workspace.finish()


def action(library, args, temporary):
    plan=Plan(library)
    name=args.action
    identity=resolve(library,args.operand) if args.operand and name!='import' else None
    if name in ('use','set','rollback','uninstall','remove','pin','unpin') and identity not in library.families:
        raise ValueError('font is not stored in this directory; install or import it first')
    if name=='update' and args.source:raise ValueError('--source applies to catalog refresh; omit it when updating a directory font')
    if name in ('use','set','rollback'):
        if args.file:raise ValueError('import the file into the selected directory before activating it')
        if not identity:raise ValueError('select a stored font')
        if name=='rollback' and not args.version:raise ValueError('rollback requires an exact --version')
        return activate(library,identity,args,temporary)
    if name in ('install','download'):
        if args.variant:raise ValueError('directory storage retains every variant; choose --variant when using it')
        store(plan,identity,args.version,temporary,dry_run=args.dry_run,keep_archive=args.keep_archive)
    elif name in ('uninstall','remove'):uninstall(plan,identity,args.version)
    elif name in ('upgrade','update'):upgrade(plan,identity,temporary,dry_run=args.dry_run,version=args.version)
    elif name=='import':ops.import_files(plan,args.operand,temporary)
    elif name in ('pin','unpin'):
        row=plan.document['families'][identity]
        version=library.version(identity,args.version)[0] if name=='pin' else None
        row['pin']=version;plan.items.append(dict(id=identity,action=name,version=version))
    else:raise ValueError('unsupported directory operation')
    return plan.finish()
