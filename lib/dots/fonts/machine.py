"""Build machine font operations from read-only personal and directory sources."""
import ntpath
from pathlib import Path, PureWindowsPath
import shutil
import tempfile

from fonts import operations
from fonts.model import Library, Plan, digest, metadata
from fonts.workspace import Workspace


def stage_faces(plan, source, identity, version, variant, temporary):
    """Validate the copied bytes before using a user-owned source as administrator."""
    staged = Path(tempfile.mkdtemp(prefix='system-faces-', dir=temporary))
    names = set()
    faces = []
    record = source.document['families'][identity]['versions'][version]
    for face in record['fonts']:
        if face['variant'] != variant:
            continue
        filename = face['file']
        relative = PureWindowsPath(filename)
        reserved = (ntpath.isreserved(filename) if hasattr(ntpath, 'isreserved')
                    else any(PureWindowsPath(part).is_reserved() for part in relative.parts))
        if relative.anchor or reserved or any(':' in part or part.endswith(('.', ' ')) for part in relative.parts):
            raise ValueError('unsafe Windows font filename')
        path = source.file(identity, version, face)
        copy = staged / filename
        copy.parent.mkdir(parents=True, exist_ok=True)
        if copy.exists():
            raise ValueError('duplicate Windows font filename: ' + filename)
        shutil.copyfile(path, copy)
        plan.guard(copy)
        actual = metadata(copy)
        if any(actual[key] != face[key] for key in ('full_name','variant','family','style','sha256')):
            raise ValueError('font metadata differs from the selected source: ' + str(path))
        name = actual['full_name'].casefold()
        if name in names:
            raise ValueError('duplicate Windows face name: ' + actual['full_name'])
        names.add(name)
        faces.append(dict(actual, file=filename))
    if not faces:
        raise ValueError('selected variant is unavailable; see fonts show')
    return staged, faces


def install(library, args, temporary):
    queries = list(dict.fromkeys(args.operand))
    if args.version and len(queries) != 1:
        raise ValueError('--version requires one family')
    sources = Workspace(Library(platform=library.platform), temporary)
    plan = Plan(library)
    selected = set()
    for query in queries:
        identity = sources.resolve(query, args.from_, catalog=True)
        if identity in selected:
            continue
        selected.add(identity)
        source, version = sources.obtain(identity, args.version, args.from_, dry_run=args.dry_run)
        if source is None:
            continue
        family = source.document['families'][identity]
        if family.get('pin') and family['pin'] != version:
            raise ValueError('selected source family is pinned to a different version')
        record = family['versions'][version]
        current = plan.document['families'].get(identity, {}).get('installed') or {}
        variants = {face['variant'] for face in record['fonts']}
        variant = args.variant or current.get('variant') or operations.default_variant(variants)
        if record.get('partial'):
            source, version = sources.obtain(identity, version, dry_run=args.dry_run, required_variant=variant)
            if source is None:
                continue
        staged, faces = stage_faces(plan, source, identity, version, variant, temporary)
        row = plan.document['families'].setdefault(identity, dict(name=faces[0]['family'], provider=identity.split(':')[0],
                                                                 versions={}, installed=None))
        previous = {face['file']: face for face in row['versions'].get(version, {}).get('fonts', [])}
        if any(face['file'] in previous and previous[face['file']] != face for face in faces):
            raise ValueError('an installed face of this version has different contents or metadata')
        row['versions'][version] = dict(fonts=faces, payload_digest=digest(staged))
        plan.payloads[identity, version] = staged
        plan.guards.update(source.guards)
        operations.install(plan, identity, version, variant)
        row['versions'] = {version: row['versions'][version]}
    plan.items.extend(item for item in sources.user.items if item['action'].startswith('download'))
    return plan.finish()
