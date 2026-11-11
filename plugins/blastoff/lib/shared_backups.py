"""Blastoff metadata over the shared Bak catalog; legacy pairs stay read-only here."""
from copy import deepcopy
import hashlib
import os
from pathlib import Path
import sys


def backend():
    shared = Path(__file__).resolve().parents[3] / 'lib/dots'
    for directory in (shared, shared / 'files'):
        if str(directory) not in sys.path:
            sys.path.insert(0, str(directory))
    from backup_catalog import BackupPlan
    return BackupPlan


def plan():
    factory = backend()
    from config_values import Controls
    from profile_config import checkout
    controls = Controls(checkout())
    values = controls.values.get('apps', {}).get('bak', {})
    result = factory(directory=values.get('store', '~/.bakstore'), location=values.get('location', 'store'))
    for path in controls.paths:
        result.guard(path)
    return result


def owner(root):
    return os.path.normcase(os.path.abspath(root))


def entries(root, catalog=None):
    catalog = catalog if catalog is not None else backend()()
    return {ident: entry for ident, entry in catalog.document['entries'].items()
            if entry.get('blastoff_owner') == owner(root) and isinstance(entry.get('blastoff'), dict)}


def snapshot(core, app, source, kind, transaction=None):
    transaction = transaction if transaction is not None else plan()
    source = Path(source)
    # App restore historically restores content into the active config. Bak also
    # keeps the exact destination link when linked_apply replaces that object.
    physical = source.resolve(strict=True)
    transaction.guard(physical)
    data = core.read(source, links=True)
    record = transaction.snapshot(physical, origin='blastoff', original=source)
    metadata = dict(id=record['id'], created=record['created'], kind=kind, source=str(source),
                    sha256=hashlib.sha256(data).hexdigest(),
                    symlink_target=os.readlink(source) if source.is_symlink() else None)
    if kind == 'config':
        if app.configured_config.is_symlink():
            metadata['symlink_target'] = os.readlink(app.configured_config)
        metadata.update(configured_config=str(app.configured_config), resolved_config=str(app.config),
                        active_links=[dict(path=str(p), target=fp[-1]) for p, fp in app._active.links],
                        provenance=app._backup_origin if hasattr(app, '_backup_origin') else
                        core.ui_module('provenance').read_record(core, app)[0])
    record.update(blastoff_owner=owner(app.root), blastoff=metadata)
    return record['id']


def create(core, app, source, kind):
    transaction = plan()
    ident = snapshot(core, app, source, kind, transaction)
    transaction.apply('blastoff-backup')
    app.diagnostic('Created '+kind+' backup '+ident)
    return ident


def inspect(core, root, ident, *, verify=True, catalog=None):
    catalog = catalog if catalog is not None else backend()()
    entry = entries(root, catalog).get(ident)
    if entry is None:
        return None
    payload = Path(entry['path'])
    # Catalog paths are canonical physical paths. A newly introduced parent link
    # must not redirect verification or deletion to another tree.
    core.inspect_parents(payload.parent)
    metadata = deepcopy(entry['blastoff'])
    metadata['created'] = entry['created']
    if metadata.get('id') != ident or metadata.get('kind') not in ('config', 'stored') or not core.re.fullmatch('[a-f0-9]{64}', str(metadata.get('sha256', ''))):
        raise core.Failure('Malformed backup metadata: '+ident)
    size = core.regular(payload).st_size if core.exists(payload) else None
    before = core.fingerprint(payload) if verify else (True if core.exists(payload) else None)
    if verify and before is not None:
        try:
            catalog.verified_payload(entry)
        except ValueError as error:
            raise core.Failure(str(error)) from error
        if hashlib.sha256(core.read(payload)).hexdigest() != metadata['sha256']:
            raise core.Failure('Backup checksum mismatch: '+ident)
    if verify and core.fingerprint(payload) != before:
        raise core.Failure('Backup changed during inspection: '+ident)
    return dict(id=ident, metadata=metadata, missing_payload=before is None,
                expected=(before, deepcopy(entry)), size_bytes=size, payload=payload, shared=True)
