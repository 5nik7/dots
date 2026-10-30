"""Explicit installed-font discovery and conservative source ownership."""
from pathlib import Path
import os
import shutil
import tempfile

from fonts.model import Library,token,exists,metadata,license_file,digest,parents_safe
from fonts import operations as ops


def path_key(path):return os.path.normcase(os.path.abspath(path))


def user_roots(library):
    if library.platform=='windows':return [ops.install_root(library)]
    return [ops.install_root(library).parent,library.home/'.fonts']


def can_adopt(library,path):
    path=Path(path)
    try:
        parents_safe(path)
        if path.is_symlink() or not path.is_file():return False
        if hasattr(os,'getuid') and path.stat().st_uid!=os.getuid():return False
        return any(path.is_relative_to(root) for root in user_roots(library)) or (
            library.platform=='termux' and path==library.home/'.termux/font.ttf')
    except (ValueError,OSError):return False


def snapshot(library, *, external=True):
    user=library if not library.directory else Library(platform=library.platform)
    rows={};notices=[];managed={}
    for identity,family in user.families.items():
        installed=family.get('installed') or {}
        for item in installed.get('files',[]):
            managed[path_key(item['path'])]=dict(managed_id=identity,version=installed['version'],face=item['font']['file'])
    for item in user.document.get('adoptions',{}).values():
        managed[path_key(item['path'])]=dict(managed_id=item['id'],version=item['version'],face=item['face'],adopted=True)
    def add(path,name='',face='',source='managed',**extra):
        path=Path(path)
        if not path.is_absolute():return
        key=path_key(path)
        if key in rows:rows[key].update(extra);return
        known=managed.get(key,{})
        supported=path.suffix.lower() in ('.ttf','.otf')
        reason=None
        if not supported:reason='unsupported format; select a regular TTF/OTF'
        elif not path.is_file():reason='font file is missing or inaccessible'
        ownership='managed' if known else 'user' if source!='system' and can_adopt(user,path) else 'system'
        rows[key]=dict(id='installed:'+token(key),name=name or path.stem,face=face,path=str(path),
            source=source,ownership=ownership,migratable=ownership in ('managed','user') and reason is None,
            supported=reason is None,reason=reason,**extra)
        rows[key].update(known)
    for path,known in managed.items():
        family=user.families.get(known['managed_id'],{})
        add(path,family.get('name',''),known['face'])
    if external:
        try:
            from fonts_cli import system_fonts
            for row in system_fonts(user):
                path=Path(os.path.expandvars(row['path']))
                if user.platform=='windows' and not path.is_absolute():
                    path=(Path(os.environ.get('WINDIR',os.environ.get('SystemRoot','C:/Windows')))/'Fonts'/path)
                add(path,row.get('name',''),row.get('face',''),row.get('source','external'))
        except (ValueError,OSError) as error:notices.append(str(error))
    termux=user.home/'.termux/font.ttf'
    if user.platform=='termux' and exists(termux):
        ref=user.document['targets'].get('termux')
        add(termux,'Current Termux font',source='termux')
        if ref:rows[path_key(termux)].update(managed_id=ref['id'],version=ref['version'],face=ref['face'],ownership='managed',migratable=True)
    return sorted(rows.values(),key=lambda r:(r['name'].casefold(),r['path'])),notices


def select(rows,queries):
    selected=[]
    for query in queries:
        exact=[r for r in rows if query in (r['id'],r['path'])]
        matches=exact or [r for r in rows if query.casefold()==r['name'].casefold()]
        if len(matches)!=1:raise ValueError('installed font is ambiguous or missing; use an ID from fonts installed')
        if not matches[0]['supported']:raise ValueError(matches[0]['reason'])
        if matches[0] not in selected:selected.append(matches[0])
    return selected


def import_row(workspace,row,rows, *, family=False):
    """Validate selected sources; only matched managed checksums establish provenance."""
    plan=workspace.user
    path=Path(row['path']);plan.guard(path)
    resolved=path.resolve(strict=True);parents_safe(resolved);plan.guard(resolved)
    if row.get('managed_id'):
        identity,version=row['managed_id'],row['version']
        record=plan.document['families'][identity]['versions'][version]
        face=next(f for f in record['fonts'] if f['file']==row['face'])
        from fonts.model import sha
        if sha(resolved)!=face['sha256']:raise ValueError('installed font changed; preserve and review it')
        plan.file(identity,version,face)
        return identity,version,face['file']
    meta=metadata(resolved)
    selected=[(path,resolved,meta)]
    if family:
        from fontTools.ttLib import TTFont
        def revision(file):
            with TTFont(file,lazy=True) as font:return font['name'].getDebugName(5)
        version_name=revision(resolved)
        for candidate in rows:
            candidate_path=Path(candidate['path'])
            if candidate_path==path or not candidate['supported'] or candidate.get('managed_id'):continue
            # Native inventories give the family without parsing every font.
            if meta['family'] not in candidate['name'].split(','):continue
            try:
                real=candidate_path.resolve(strict=True);parents_safe(real)
                item=metadata(real)
                if item['family']!=meta['family'] or item['variant']!=meta['variant'] or revision(real)!=version_name:continue
            except (OSError,ValueError):continue
            plan.guard(candidate_path);plan.guard(real);selected.append((candidate_path,real,item))
    source=Path(tempfile.mkdtemp(prefix='installed-',dir=workspace.temporary))
    originals=[]
    for original,real,item in selected:
        dest=source/real.name
        if dest.exists() and digest(dest)!=digest(real):raise ValueError('installed family contains colliding filenames')
        shutil.copy2(real,dest);originals.append(str(original))
        for license in real.parent.iterdir():
            if not license_file(license.name) or not license.is_file() or license.is_symlink():continue
            if license.stat().st_size>1024*1024:continue
            target=source/license.name
            plan.guard(license)
            if target.exists() and digest(target)!=digest(license):raise ValueError('installed fonts have conflicting licenses')
            shutil.copy2(license,target)
    identity,version=ops.import_files(plan,source,workspace.temporary)
    record=plan.document['families'][identity]['versions'][version]
    record['provenance']=dict(source=originals[0],sources=originals,revision=None,upstream_version='unknown')
    return identity,version,meta['file']


def migrate(workspace,row,identity,version,face):
    plan=workspace.user;path=Path(row['path']);key=row['id']
    previous=plan.document.get('adoptions',{}).get(key)
    if previous:
        if previous['after']!=digest(path):raise ValueError('migrated font changed; review its ownership')
        plan.items.append(dict(id=key,action='already migrated'));return
    if row.get('managed_id'):
        plan.items.append(dict(id=key,action='already managed; retain a directory copy'));return
    if not row['migratable'] or not can_adopt(plan.library,path):raise ValueError('system, package-owned or uncertain fonts are copy-only')
    font=next(f for f in plan.document['families'][identity]['versions'][version]['fonts'] if f['file']==face)
    source=plan.file(identity,version,font)
    persistent=plan.library.folder(identity,version)/face
    plan.guard(path)
    if plan.library.platform=='windows':
        # Preserve the registered lookup path; adopt only a matching HKCU value.
        import font_registry
        name=font['full_name']+(' (TrueType)' if path.suffix.lower()=='.ttf' else ' (OpenType)')
        current=font_registry.read(name)
        if current is None or path_key(current)!=path_key(path):raise ValueError('Windows migration requires a matching current-user registration')
        receipt=plan.library.state/'fonts/registrations'/(token(name)+'.json')
        spec=dict(name=name,before=current,after=current);font_registry.validate(spec)
        plan.put(receipt,data=dict(schema=1,name=name,path=str(path)),font_registry=spec)
        plan.put(path,source=source);after=digest(source)
    elif path==plan.library.home/'.termux/font.ttf':
        plan.put(path,source=source)
        plan.items.append(dict(id=key,version=version,action='adopt current Termux selection',path=str(path)))
        return
    else:
        plan.put(path,link=str(persistent));after=ops.link_digest(persistent)
    plan.document.setdefault('adoptions',{})[key]=dict(id=identity,version=version,face=face,path=str(path),after=after)
    plan.items.append(dict(id=key,version=version,action='migrate with original lookup path preserved',path=str(path)))
    plan.refresh.add('fonts')
