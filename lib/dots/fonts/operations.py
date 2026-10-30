"""Font lifecycle plans. No target mutation occurs until Plan.apply."""
from copy import deepcopy
import hashlib
import os
from pathlib import Path
import shutil
import subprocess

from fonts.model import Plan, metadata, token, sha, license_file, relative
from transactions import digest, exists, parents_safe


def stage(plan, identity, version, payload, record, name, *, temporary=None):
    for font in record['fonts']: relative(font['file'])
    record = dict(record, payload_digest=digest(payload))
    folder = plan.library.folder(identity, version)
    row = plan.document['families'].setdefault(identity, dict(name=name, provider=identity.split(':')[0], versions={}, pin=None, installed=None))
    if version in row['versions']:
        if row['versions'][version]['payload_digest'] != record['payload_digest']:
            from fonts.payloads import merge
            payload,record=merge(plan,identity,version,payload,record,temporary)
        if row['versions'][version].get('available',True) and row['versions'][version]['payload_digest']==record['payload_digest']:
            for font in record['fonts']: plan.file(identity, version, font)
            return
        if not row['versions'][version].get('available',True):
            if not plan.library.directory:raise ValueError('invalid unavailable user-library version')
            record=dict(record,available=True)
            if exists(folder):raise ValueError('uninstalled font destination is occupied without ownership')
    elif exists(folder): raise ValueError('font library destination is occupied without ownership')
    plan.payloads[(identity, version)] = payload
    plan.put(folder, source=payload)
    row['versions'][version] = record
    if plan.library.directory:record['available']=True
    row['preferred'] = version
    plan.items.append(dict(id=identity, version=version, action='save', fonts=len(record['fonts'])))


def import_files(plan, source, temporary):
    source = Path(source).expanduser().absolute()
    parents_safe(source)
    if source.is_symlink() or not source.exists(): raise ValueError('import source must be a regular file or directory')
    files = []
    for path in [source] if source.is_file() else source.rglob('*'):
        files.append(path)
        if len(files) > 5000: raise ValueError('import contains too many files')
    files.sort()
    selected = []
    for path in files:
        if path.is_symlink(): raise ValueError('import source contains a symlink; select regular fonts explicitly')
        if path.is_file() and (path.suffix.lower() in ('.ttf', '.otf') or license_file(path.name)):
            if path.stat().st_size > 64*1024*1024: raise ValueError('imported font/license exceeds 64 MiB')
            selected.append(path)
    if not selected: raise ValueError('no fonts found in import source')
    if sum(p.stat().st_size for p in selected)>1024*1024*1024: raise ValueError('import exceeds 1 GiB')
    import tempfile
    payload = Path(tempfile.mkdtemp(prefix='import-',dir=temporary))
    seen = set()
    for path in selected:
        if path.name.casefold() in seen: raise ValueError('import has colliding filenames; import families separately')
        seen.add(path.name.casefold()); plan.guard(path)
        shutil.copy2(path, payload / path.name)
    fonts = [metadata(path) for path in sorted(payload.iterdir()) if path.suffix.lower() in ('.ttf','.otf')]
    if not fonts: raise ValueError('import contains no usable fonts')
    fingerprint = hashlib.sha256(''.join(f['file'] + f['sha256'] for f in fonts).encode()).hexdigest()
    identity, version = 'local:' + fingerprint[:24], 'local-' + fingerprint[:24]
    record = dict(fonts=fonts, licenses=[p.name for p in payload.iterdir() if p.suffix.lower() not in ('.ttf','.otf')],
                  provider='local', fingerprint=fingerprint, provenance=dict(source=str(source), revision=None, upstream_version='unknown'))
    stage(plan, identity, version, payload, record, fonts[0]['family'],temporary=temporary)
    return identity, version


def version_for(plan, identity, version=None):
    row = plan.document['families'][identity]
    version = version or (row.get('installed') or {}).get('version') or row.get('preferred')
    if version not in row['versions']: raise ValueError('font version is not downloaded')
    return version, row['versions'][version]


def face_for(record, face=None, variant=None):
    fonts = [f for f in record['fonts'] if variant is None or f['variant'] == variant]
    if face:
        fonts = [f for f in fonts if face in (f['file'], f['full_name'])]
    else:
        regular = [f for f in fonts if f['style'].casefold() in ('regular','normal','book')]
        fonts = regular or fonts
    if len(fonts) != 1: raise ValueError('select an exact face with --face; see fonts show')
    return fonts[0]


def install_root(library):
    if library.platform == 'windows':
        root = Path(os.environ.get('LOCALAPPDATA', library.home / 'AppData/Local')) / 'Microsoft/Windows/Fonts'
    else:
        root = Path(os.environ.get('XDG_DATA_HOME') or library.home / '.local/share') / 'fonts/dots'
    if not root.is_absolute(): raise ValueError('font installation root must be absolute')
    return root


def link_digest(source):
    return hashlib.sha256(b'.\0' + b'511\0L' + os.fsencode(str(source)) + b'\0').hexdigest()


def registration(plan, font, path, previous=None):
    import font_registry
    name = font['full_name'] + (' (TrueType)' if Path(font['file']).suffix.lower() == '.ttf' else ' (OpenType)')
    before = font_registry.read(name)
    if before is not None and before != previous: raise ValueError('Windows font name is already registered outside this selection')
    spec = dict(name=name, before=before, after=str(path) if path else None)
    font_registry.validate(spec)
    receipt = plan.library.state / 'fonts/registrations' / (token(name) + '.json')
    if before == spec['after']: return name
    if path: plan.put(receipt, data=dict(schema=1, name=name, path=str(path)), font_registry=spec)
    else: plan.put(receipt, delete=True, font_registry=spec)
    return name


def owned_install(library, installed):
    for item in installed['files']:
        path = Path(item['path'])
        if path.parent != install_root(library): raise ValueError('invalid installed font location')
        parents_safe(path)
        if digest(path) != item['after']: raise ValueError('installed font changed; preserve and review: ' + str(path))


def install(plan, identity, version=None, variant=None):
    row = plan.document['families'][identity]
    version, record = version_for(plan, identity, version)
    old = row.get('installed')
    variants = {f['variant'] for f in record['fonts']}
    variant = variant or (old or {}).get('variant') or ('mono' if 'mono' in variants else 'original' if 'original' in variants else sorted(variants)[0])
    fonts = [f for f in record['fonts'] if f['variant'] == variant]
    if not fonts: raise ValueError('selected variant is unavailable; see fonts show')
    if row.get('pin') and row['pin'] != version: raise ValueError('family is pinned; unpin before switching versions')
    # Existing app choices must have an exact equivalent in the replacement.
    refs = [v for v in plan.document['targets'].values() if v['id'] == identity]
    replacements = []
    for ref in refs:
        previous = row['versions'][ref['version']]
        old_face = next(f for f in previous['fonts'] if f['file'] == ref['face'])
        matches = [f for f in fonts if f['family'] == old_face['family'] and f['style'] == old_face['style']]
        if len(matches) != 1: raise ValueError('replacement is missing an active face or changes its family; set another font first')
        replacements.append((ref, matches[0]))
    if old: owned_install(plan.library, old)
    adopted={k:r for k,r in plan.document.get('adoptions',{}).items() if r['id']==identity}
    for ref in adopted.values():
        validate_adoption(plan,ref)
    files = []; base = install_root(plan.library)
    for font in fonts:
        source = plan.file(identity, version, font)
        persistent = plan.library.folder(identity, version) / font['file']
        target = base / (token(identity) + '-' + token(version + '/' + font['file']) + source.suffix.lower())
        existing = next((f for f in (old or {}).get('files', []) if f['path'] == str(target)), None)
        if exists(target) and not existing: raise ValueError('font installation destination is occupied without ownership')
        for other_id, other in plan.document['families'].items():
            if other_id == identity or not other.get('installed'): continue
            other_record = other['versions'][other['installed']['version']]
            if any(f['full_name'] == font['full_name'] for f in other_record['fonts'] if f['variant'] == other['installed']['variant']):
                raise ValueError('another managed family has the same registered face name')
        if plan.library.platform == 'windows':
            plan.put(target, source=source)
            prior = next((f for f in (old or {}).get('files', []) if f['font']['full_name'] == font['full_name']), None)
            alias=next((r for r in adopted.values() if row['versions'][r['version']]['fonts'] and
                any(f['file']==r['face'] and f['full_name']==font['full_name'] for f in row['versions'][r['version']]['fonts'])),None)
            registration(plan, font, target, prior['path'] if prior else alias['path'] if alias else None)
            after = digest(source)
        else:
            plan.put(target, link=str(persistent))
            after = link_digest(persistent)
        files.append(dict(path=str(target), after=after, font=font))
    for item in (old or {}).get('files', []):
        if item['path'] not in {f['path'] for f in files}:
            if plan.library.platform == 'windows' and item['font']['full_name'] not in {f['full_name'] for f in fonts}:
                registration(plan, item['font'], None, item['path'])
            plan.put(item['path'], delete=True)
    row['installed'] = dict(version=version, variant=variant, files=files)
    for key,ref in adopted.items():
        if plan.library.platform=='windows':
            font=next(f for f in row['versions'][ref['version']]['fonts'] if f['file']==ref['face'])
            if font['full_name'] not in {f['full_name'] for f in fonts}:registration(plan,font,None,ref['path'])
        plan.put(ref['path'],delete=True)
        del plan.document['adoptions'][key]
    row['preferred'] = version
    from fonts.config import configure
    for ref, font in replacements:
        configure(plan, identity, version, font, ref['target'], explicit=ref.get('config'), app_profile=ref.get('app_profile'))
    plan.refresh.add('fonts')
    plan.items.append(dict(id=identity, version=version, action='install', variant=variant, fonts=len(files)))


def validate_adoption(plan,ref):
    from fonts.inventory import user_roots
    path=Path(ref['path'])
    if not path.is_absolute() or not any(path.is_relative_to(root) for root in user_roots(plan.library)):
        raise ValueError('invalid migrated font location')
    parents_safe(path)
    if digest(path)!=ref['after']:raise ValueError('migrated font changed; preserve and review it')
    plan.guard(path)


def uninstall(plan, identity):
    row = plan.document['families'][identity]
    if any(ref['id'] == identity for ref in plan.document['targets'].values()):
        raise ValueError('font is active in an application; select another font or undo its Set transaction first')
    old = row.get('installed')
    adopted={k:r for k,r in plan.document.get('adoptions',{}).items() if r['id']==identity}
    for key,ref in adopted.items():
        validate_adoption(plan,ref)
        if plan.library.platform=='windows':
            font=next(f for f in row['versions'][ref['version']]['fonts'] if f['file']==ref['face'])
            registration(plan,font,None,ref['path'])
        plan.put(ref['path'],delete=True);del plan.document['adoptions'][key]
    if not old:
        if adopted:plan.refresh.add('fonts')
        return
    owned_install(plan.library, old)
    for item in old['files']:
        if plan.library.platform == 'windows': registration(plan, item['font'], None, item['path'])
        plan.put(item['path'], delete=True)
    row['installed'] = None
    plan.refresh.add('fonts')
    plan.items.append(dict(id=identity, action='uninstall', version=old['version']))


def replace_active(plan, identity, version):
    """Switch an active Termux-only selection without adding desktop registration."""
    row=plan.document['families'][identity]
    if row.get('pin') and row['pin']!=version:raise ValueError('family is pinned; unpin before switching versions')
    _,record=version_for(plan,identity,version)
    refs=[ref for ref in plan.document['targets'].values() if ref['id']==identity]
    if not refs:raise ValueError('upgrade/rollback requires an installed or active family')
    from fonts.config import configure
    for ref in refs:
        if ref['target']!='termux':raise ValueError('desktop selection has no registered font; review its installation')
        previous=next(f for f in row['versions'][ref['version']]['fonts'] if f['file']==ref['face'])
        matches=[f for f in record['fonts'] if all(f[k]==previous[k] for k in ('family','style','variant'))]
        if len(matches)!=1:raise ValueError('replacement is missing an active face or changes its family; set another font first')
        configure(plan,identity,version,matches[0],'termux')
    row['preferred']=version


def remove(plan, identity, version):
    row = plan.document['families'][identity]
    version, record = version_for(plan, identity, version)
    if (row.get('pin') == version or (row.get('installed') or {}).get('version') == version
            or any(r['id']==identity and r['version']==version for r in plan.document.get('adoptions',{}).values())
            or any(r['id'] == identity and r['version'] == version for r in plan.document['targets'].values())):
        raise ValueError('cannot remove an installed, active or pinned version')
    for font in record['fonts']: plan.file(identity, version, font)
    plan.put(plan.library.folder(identity, version), delete=True)
    del row['versions'][version]
    if row.get('preferred') == version: row['preferred'] = next(reversed(row['versions']), None)
    if not row['versions']: del plan.document['families'][identity]
    plan.items.append(dict(id=identity, version=version, action='remove'))


def refresh(plan, *, no_reload=False):
    """Post-commit effects cannot invalidate the durable transaction result."""
    notices = []
    if 'fonts' in plan.refresh:
        if plan.library.platform == 'windows':
            try:
                import ctypes
                from ctypes import wintypes
                load = ctypes.windll.gdi32.AddFontResourceExW
                load.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_void_p)
                load.restype = ctypes.c_int
                unload = ctypes.windll.gdi32.RemoveFontResourceExW
                unload.argtypes = load.argtypes
                unload.restype = wintypes.BOOL
                broadcast = ctypes.windll.user32.SendMessageTimeoutW
                broadcast.argtypes = (wintypes.HWND,wintypes.UINT,ctypes.c_size_t,ctypes.c_ssize_t,
                                      wintypes.UINT,wintypes.UINT,ctypes.POINTER(ctypes.c_size_t))
                broadcast.restype = ctypes.c_ssize_t
                def installed_paths(document):
                    return {item['path'] for row in document['families'].values()
                            for item in (row.get('installed') or {}).get('files', [])} | {
                                ref['path'] for ref in document.get('adoptions',{}).values()}
                before=installed_paths(plan.library.document);after=installed_paths(plan.document)
                for path in before-after: unload(path,0,None)
                for path in after-before:
                    if not load(path, 0, None):
                        notices.append('Windows font load failed; restart the affected application or sign in again')
                result = ctypes.c_size_t()
                if not broadcast(0xFFFF, 0x001D, 0, 0, 2, 2000, ctypes.byref(result)):
                    notices.append('Windows font notification timed out; restart the affected applications')
            except (OSError, AttributeError): notices.append('Windows font refresh unavailable; restart the affected applications')
        elif shutil.which('fc-cache'):
            try:
                from fonts.inventory import user_roots
                roots=[str(root) for root in user_roots(plan.library) if root.is_dir()]
                if roots:
                    result = subprocess.run(['fc-cache', '-f', *roots], capture_output=True, timeout=30)
                    if result.returncode: notices.append('Font cache refresh failed; rerun fc-cache or restart the application')
            except (OSError, subprocess.SubprocessError): notices.append('Font cache refresh failed; retry it separately')
        else: notices.append('fc-cache unavailable; applications may require a restart')
    if 'termux' in plan.refresh:
        if no_reload: notices.append('Termux reload skipped (--no-reload)')
        elif shutil.which('termux-reload-settings'):
            try:
                result = subprocess.run(['termux-reload-settings'], capture_output=True, timeout=10)
                if result.returncode: notices.append('Termux reload failed; run termux-reload-settings separately')
            except (OSError, subprocess.SubprocessError): notices.append('Termux reload failed; retry it separately')
        else: notices.append('termux-reload-settings unavailable; restart Termux to load the font')
    return notices
