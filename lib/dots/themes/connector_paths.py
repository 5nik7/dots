"""Plan profile-declared links into the active theme without publishing anything."""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import uuid
from typing import Optional

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / 'files'))
from app_paths import connector_directory
from catalog import Catalog, platform, read_json, atomic_json
from file_platform import native_link_text, state_root
from managed_destination import physical, points_to, yazi_flavor_directory
from transactions import Store, digest, parents_safe

YAZI_CHILD_IDS = {'flavor.toml': 'theme:yazi-flavor', 'tmtheme.xml': 'theme:yazi-syntax'}
YAZI_FILES = tuple(YAZI_CHILD_IDS)


@dataclass
class Connection:
    identity: str
    app: str
    artifact: str
    logical: Optional[Path]
    target: Optional[Path]
    eligible: bool
    supported: bool = True
    create_parent: bool = False
    legacy_parent: bool = False
    directory: bool = False
    required: bool = True
    error: Optional[str] = None
    split_directory: bool = False


def legacy_rows(selected, *, inspect=False):
    """Compatibility for checkouts predating flat profile mappings."""
    windows = selected == 'windows'
    home = Path(os.environ.get('HOME') or Path.home())
    config = Path(os.environ.get('XDG_CONFIG_HOME') or home / '.config')
    rows = [line.split('\t') for line in (HERE / 'connectors.tsv').read_text().splitlines()]
    rows.extend([('codex', 'themes/dots.tmTheme', 'bat.tmTheme'), ('pi', 'themes/dots.json', 'pi.json'),
                 ('claude-code', 'themes/dots.json', 'claude-code.json')])
    if not windows:
        rows.append(('termux', 'colors.properties', 'termux.properties'))
    for app, suffix, artifact in rows:
        supported = windows if app == 'windows-terminal' else not windows or app in {
            'yazi', 'git', 'vivid', 'eza', 'television', 'leaf', 'wezterm', 'claude-code', 'codex', 'pi'}
        error = None
        try:
            if app == 'termux':
                base = home / '.termux'
            elif app in ('eza', 'leaf', 'television', 'windows-terminal', 'claude-code', 'pi', 'codex') or windows and app in ('yazi', 'wezterm'):
                base = connector_directory(app, selected)
            else:
                base = config / app
        except (ValueError, OSError):
            if not inspect:
                raise
            base, error = None, 'Invalid or unreadable application directory.'
        yield dict(id='theme:' + app + (':' + artifact if app == 'leaf' else ''), app=app,
                   target=str(base/suffix) if base else None, artifact=artifact, supported=supported, error=error,
                   required=app not in ('claude-code', 'pi', 'codex', 'termux'))



def profile_catalog(root, selected):
    if not (root / '.dots/sources.json').is_file():
        return None
    return Catalog(root, selected)


def uses_profile(catalog):
    return catalog is not None and catalog.flat


def app_names(root, selected):
    """Completion reads only declared app names, with no destination inspection."""
    catalog = profile_catalog(root, selected)
    if uses_profile(catalog):
        source = next(s for s in catalog.sources if s['id'] == 'theme')
        return {row['app'] for row in catalog.manifest(source)['resources'] if row.get('enabled', True)}
    return {line.split('\t')[0] for line in (HERE/'connectors.tsv').read_text().splitlines()} | {'claude-code','codex','pi','termux'}


def installation_receipt(path, guards):
    parents_safe(path)
    before = digest(path)
    if guards.setdefault(str(path), before) != before:
        raise ValueError('Yazi installation receipt changed after preview')
    if before is None:
        return None
    receipt = read_json(path)
    if not isinstance(receipt.get('entries'), dict) or digest(path) != before:
        raise ValueError('invalid or changed Yazi installation receipt')
    return receipt


def plan(root, selected, *, catalog=None, records=None, planned=(), planned_targets=(), inspect=False):
    catalog = catalog if catalog is not None else profile_catalog(root, selected)
    modern = uses_profile(catalog)
    guards = {}
    if modern:
        for p in catalog.input_paths():
            guards[str(p)] = digest(p)
        if records is None:
            records = catalog.records()
        declarations = []
        for row in records:
            spec = row.get('source_spec', '')
            if not spec.startswith('${THEME}/') or not row['enabled'] or not row['applicable'] or row['status'] == 'replaced':
                continue
            if row['status'] == 'conflict' and not inspect:
                raise ValueError('conflicting profile theme connector: ' + row['id'])
            if row['strategy'] not in ('link', 'directory-link'):
                raise ValueError('theme publication requires a link strategy: ' + row['id'])
            declarations.append(dict(row, artifact=spec[len('${THEME}/'):], supported=True))
    else:
        declarations = list(legacy_rows(selected, inspect=inspect))
        if catalog is not None and records is None and not inspect:
            records = catalog.records()
    records = records or []
    active = state_root() / 'current/theme'
    # A regular-file installation may create an app directory (Television's
    # config.toml is one example). Such an app is configured on this first apply.
    future_directories = {parent for path in planned_targets for parent in path.parents}
    def present(path):
        return path.is_dir() or path in future_directories
    result = []
    for row in declarations:
        app, artifact = row['app'], row['artifact']
        logical = Path(row['target']) if row['target'] else None
        if logical is None:
            result.append(Connection(row['id'], app, artifact, None, None, False, row['supported'],
                                     required=row.get('required', True), error=row.get('error')))
            continue
        yazi_child = app == 'yazi' and artifact in ('yazi/' + n for n in YAZI_FILES) and logical.parent.name == 'dots.yazi'
        directory = row.get('strategy') == 'directory-link' if modern else artifact == 'yazi'
        yazi_directory = modern and yazi_flavor_directory(row)
        # Inspecting may report links via arbitrary parents. Publishing translates
        # only an exact directory owned by the selected catalog.
        target = logical
        if not inspect and row['supported']:
            if (app == 'clink' and artifact == 'dots.clinktheme'
                    and points_to(logical.parent, root / 'profiles/windows/config/clink/themes')):
                raise ValueError('Clink still uses the old themes directory link; review '
                                 'dots files uninstall --component files --resource windows:clink-themes --dry-run')
            endpoint = logical.parent if yazi_child else logical
            endpoint = physical(endpoint, records, guards, planned=planned)
            target = endpoint / logical.name if yazi_child else endpoint
            if modern and ((logical == root or root in logical.parents) or
                           any(part.casefold() in ('.git', '.dots') for part in target.parts)):
                raise ValueError('theme connector cannot replace repository metadata or sources: ' + str(logical))
            if target == state_root() or state_root() in target.parents:
                raise ValueError('theme connector destination overlaps generated state: ' + str(logical))
        if any(ord(c) < 32 or ord(c) == 127 for c in str(target)):
            raise ValueError('theme connector path contains a control character')
        if modern and not inspect:
            for ancestor in target.parents:
                if ancestor == root:
                    break
                if (ancestor / '.git').exists() or (ancestor / '.git').is_symlink():
                    raise ValueError('theme connector enters another Git checkout: ' + str(logical))
        parent = target.parent
        convert = False
        if yazi_child and parent.is_symlink():
            old = Path(os.path.abspath(parent.parent / native_link_text(os.readlink(parent))))
            if old == active / 'yazi':
                convert = True
            elif not inspect:
                raise ValueError('unmanaged Yazi flavor link; preserve and review: ' + str(parent))
        create = (not parent.exists() and not parent.is_symlink() and (
            yazi_child and (present(parent.parent) or parent.parent.name == 'flavors' and present(parent.parent.parent))
            or yazi_directory and present(parent.parent)
            or app in ('leaf', 'television', 'bat', 'clink') and parent.name == 'themes' and present(parent.parent)))
        eligible = row['supported'] and (present(parent) or create or convert)
        split = False
        if eligible and not inspect and not convert:
            parents_safe(target)
            if yazi_directory and os.path.lexists(target) and not points_to(target, active/'yazi'):
                if target.is_symlink() or not target.is_dir() or {p.name for p in target.iterdir()} != set(YAZI_FILES):
                    raise ValueError('unmanaged Yazi flavor destination; preserve and review: ' + str(logical))
                before = digest(target)
                if (not all(points_to(target/name, active/'yazi'/name) for name in YAZI_FILES)
                        or {p.name for p in target.iterdir()} != set(YAZI_FILES) or digest(target) != before):
                    raise ValueError('unmanaged Yazi flavor destination; preserve and review: ' + str(logical))
                guards[str(target)] = before
                split = True
            if not split and target.exists() and not (target.is_symlink() or target.is_file()):
                raise ValueError('cannot replace a real theme connector directory: ' + str(logical))
        result.append(Connection(row['id'], app, artifact, logical, target, eligible, row['supported'], create, convert,
                                 directory, required=row.get('required', True), split_directory=split))
        if eligible and yazi_directory and not inspect:
            receipt_path = active.parents[1]/'installation.json'
            receipt = installation_receipt(receipt_path, guards)
            if receipt is not None:
                entries = receipt['entries'].copy()
                if split:
                    if receipt.get('root') != str(root):
                        raise ValueError('another checkout owns this installation')
                    consolidate_yazi_receipt(result[-1], entries, active, guards)
                elif any({logical, target}.intersection(Path(key).parents) for key in entries):
                    raise ValueError('old Yazi child receipts require the original split directory: ' + str(logical))
                else:
                    owned = [entries[key] for key in {str(logical), str(target)} if key in entries]
                    if (len(owned) > 1 or owned and (owned[0]['id'] not in ('theme:yazi', row['id'])
                                                     or owned[0]['after'] != digest(target))):
                        raise ValueError('old Yazi installation receipt changed; preserve and review: ' + str(logical))
    for parent in {c.target.parent for c in result if c.legacy_parent}:
        pair = {c.target.name: c.artifact for c in result if c.legacy_parent and c.target.parent == parent}
        if not inspect and pair != {n:'yazi/' + n for n in YAZI_FILES}:
            raise ValueError('replacing the old Yazi flavor link requires both profile mappings: ' + str(parent))
    return result, guards


def populate_yazi(directory, active):
    directory.mkdir(mode=0o700)
    for name in YAZI_FILES:
        (directory / name).symlink_to(active / 'yazi' / name)


def targets(links):
    """A legacy flavor directory is replaced in one filesystem operation."""
    return {row.target.parent if row.legacy_parent else row.target for row in links if row.eligible}


def validate_artifacts(links, generation):
    for row in links:
        if not row.eligible:
            continue
        path = generation / row.artifact
        parents_safe(path)
        if path.is_symlink() or not (path.is_dir() if row.directory else path.is_file()):
            raise ValueError('profile theme artifact is missing, unsafe or mismatches its strategy: ' + row.artifact)


def consolidate_yazi_receipt(row, entries, active, guards):
    """Fold historical whole/flavor-child setup ownership under the declared directory.

    Keep the first uninstall baseline for a parent receipt. Separate child receipts
    retain their individual backups and any unowned sibling's lexical link text.
    An unowned split directory needs no receipt change during theme publication.
    """
    roots = {row.target, row.logical}
    candidates = {Path(key): entry for key, entry in entries.items()
                  if Path(key) in roots or roots.intersection(Path(key).parents)}
    if not candidates:
        return None
    parents = [path for path in candidates if path in roots]
    children = {}
    for path, child in candidates.items():
        if path in parents:
            continue
        if (path.parent not in roots or path.name in children or path.name not in YAZI_CHILD_IDS
                or child['id'] != YAZI_CHILD_IDS[path.name] or not points_to(row.target/path.name, active/'yazi'/path.name)
                or child['after'] != digest(row.target/path.name)):
            raise ValueError('old Yazi child installation receipt changed; preserve and review: ' + str(path))
        children[path.name] = child
    before = guards[str(row.target)]
    if len(parents) > 1 or parents and children:
        raise ValueError('overlapping old Yazi installation receipts: ' + str(row.logical))
    if parents:
        entry = dict(candidates[parents[0]])
        if entry['id'] not in ('theme:yazi', row.identity) or entry['after'] != before:
            raise ValueError('old Yazi installation receipt changed; preserve and review: ' + str(parents[0]))
    else:
        # Child-only ownership uses the child payloads for eventual uninstall.
        # The original journal continues to own any initially missing parent.
        first = next(iter(children.values()))
        entry = dict(before=before, backup=first['backup'], index=first['index'], after=before,
                     yazi_children=children, yazi_mode=stat.S_IMODE(row.target.stat().st_mode),
                     yazi_unowned={name: os.readlink(row.target/name) for name in YAZI_FILES if name not in children})
    from backup_catalog import original_payload
    if ('yazi_children' in entry and not entry['yazi_unowned']
            and all(child['before'] is None for child in entry['yazi_children'].values())):
        from backup_catalog import created_setup_parent
        created_setup_parent(active.parents[1], entry['yazi_children'].values(), roots, guards)
    for path, item in candidates.items():
        if path in parents and 'yazi_children' in item:
            for name, child in item['yazi_children'].items():
                if name not in YAZI_CHILD_IDS or child.get('id') != YAZI_CHILD_IDS[name]:
                    raise ValueError('invalid Yazi child baseline: ' + str(path))
                original_payload(child, row.target/name, active.parents[1], guards)
        else:
            original_payload(item, path, active.parents[1], guards)
    if digest(row.target) != before:
        raise ValueError('Yazi flavor directory changed after preview: ' + str(row.logical))
    entry.update(id=row.identity, catalog_ids=[row.identity])
    if row.logical != row.target:
        entry['logical_path'] = str(row.logical)
    for path in candidates:
        del entries[str(path)]
    entries[str(row.target)] = entry
    return entry


def operations(links, active, staging, guards, checkout):
    """Prepare link/old-flavor replacement operations and retained receipt migration."""
    changes = []
    replacements = {}
    for row in links:
        if not row.eligible:
            continue
        if row.legacy_parent:
            parent = row.target.parent
            if parent not in replacements:
                payload = staging / ('yazi-' + str(len(replacements)))
                populate_yazi(payload, active)
                replacements[parent] = (row.logical.parent, payload)
                changes.append(dict(path=str(parent), source=str(payload)))
        elif not points_to(row.target, active / row.artifact) or row.artifact in ('pi.json', 'claude-code.json'):
            changes.append(dict(path=str(row.target), link=str(active / row.artifact), directory=row.directory))
    split = [row for row in links if row.eligible and row.split_directory]
    if replacements or split:
        receipt_path = active.parents[1] / 'installation.json'
        receipt = installation_receipt(receipt_path, guards)
        if receipt is not None:
            if receipt.get('root') != str(checkout):
                raise ValueError('another checkout owns this installation')
            changed = False
            for row in split:
                entry = consolidate_yazi_receipt(row, receipt['entries'], active, guards)
                if entry:
                    preview = staging / 'yazi-directory-link'
                    if not preview.is_symlink():
                        preview.symlink_to(active/'yazi', target_is_directory=True)
                    entry['after'] = digest(preview)
                    changed = True
            for parent, (logical, payload) in replacements.items():
                for key in {str(parent), str(logical)}:
                    entry = receipt['entries'].get(key)
                    if not entry:
                        continue
                    if entry['id'] != 'theme:yazi' or entry['after'] != guards[str(parent)]:
                        raise ValueError('old Yazi installation receipt changed; preserve and review: ' + key)
                    entry['after'] = digest(payload)
                    entry['catalog_ids'] = sorted(row.identity for row in links if row.legacy_parent and row.target.parent == parent)
                    if key != str(parent):
                        entry['logical_path'] = key
                        receipt['entries'][str(parent)] = receipt['entries'].pop(key)
                    changed = True
            if changed:
                changes.append(dict(path=str(receipt_path), data=receipt))
    return changes


def restore(store, marker):
    parents_safe(marker)
    if not marker.exists():
        return
    record = read_json(marker)
    identity = record['transaction']
    if not isinstance(identity, str) or len(identity) != 32 or any(c not in '0123456789abcdef' for c in identity):
        raise ValueError('invalid connector transaction identity')
    if not (store.root / identity / 'journal.json').is_file():
        return
    doc = store.load(identity)
    with store.locked(doc.get('catalogs', ())):
        doc = store.load(identity)
        if doc['action'] != 'theme-connectors':
            raise ValueError('invalid connector transaction')
        if doc['status'] == 'rolled-back':
            return
        if doc['status'] == 'complete':
            store.inverse(identity)  # preflight drift across every destination before restoring any
        store.rollback(doc)


def managed_generation(value, state):
    generation = Path(value)
    if generation.parent != state/'themes/generations' or not re.fullmatch(r'g\.[a-zA-Z0-9]+', generation.name):
        raise ValueError('invalid connector generation')
    parents_safe(generation / 'status')
    return generation


def main(args):
    root = Path(os.environ.get('DOTS') or HERE.parents[2]).resolve()
    active = state_root() / 'current/theme'
    store = Store(active.parents[1])
    if args[0] == 'restore':
        restore(store, managed_generation(args[1], store.state) / 'connectors' / 'transaction.json')
        return
    catalog = profile_catalog(root, platform())
    if not uses_profile(catalog):
        if args != ['plan']:
            raise ValueError('profile declarations changed during theme publication')
        print('legacy')
        return
    links, guards = plan(root, platform(), catalog=catalog)
    for target in targets(links):
        before = digest(target)
        if guards.setdefault(str(target), before) != before:
            raise ValueError('theme connector changed after preview: ' + str(target))
    selected = [(str(r.target), r.artifact, r.legacy_parent, r.split_directory) for r in links if r.eligible]
    fingerprint = hashlib.sha256(json.dumps([guards, selected], sort_keys=True).encode()).hexdigest()
    if args == ['plan']:
        current = all(points_to(r.target, active/r.artifact) and (active/r.artifact).exists()
                      for r in links if r.eligible)
        print('profile\t' + fingerprint + '\t' + ('current' if current else 'changed'))
        for row in links:
            if row.eligible:
                print('link\t' + str(row.target) + '\t' + row.artifact)
        return
    action, directory, expected = args
    if fingerprint != expected:
        raise ValueError('profile theme links changed after preview')
    generation = managed_generation(directory, store.state)
    status = generation / 'status'
    if status.is_symlink() or not status.is_file() or status.stat().st_size > 256:
        raise ValueError('invalid connector publication marker')
    expected_status = b'staged' if action == 'verify' else b'prepared'
    if status.read_bytes().strip() != expected_status:
        raise ValueError('invalid connector publication phase')
    validate_artifacts(links, generation)
    if action == 'verify':
        return
    token = store.state/'themes/current'
    if (action != 'apply' or not points_to(active, generation) or token.is_symlink() or not token.is_file()
            or token.stat().st_size > 256 or token.read_bytes().strip() != generation.name.encode('ascii')):
        raise ValueError('profile connectors require the active prepared theme generation')
    with tempfile.TemporaryDirectory(prefix='dots-connectors-') as work:
        ops = operations(links, active, Path(work), guards, root)
        if ops:
            identity = uuid.uuid4().hex
            marker = generation / 'connectors' / 'transaction.json'
            marker.parent.mkdir()
            atomic_json(marker, dict(schema=1, transaction=identity))
            from file_platform import sync_dir
            sync_dir(generation)
            from events import OperationOutput
            store.observer = OperationOutput(os.environ.get('DOTS_OPERATION_VERBOSE') == '1')
            store.apply('theme-connectors', ops, guards, retain=True, identity=identity,
                        catalogs=catalog.lock_paths(), publication_locked=True)


if __name__ == '__main__':
    try:
        main(sys.argv[1:])
    except (ValueError, OSError) as exc:
        sys.exit('dots theme: ' + str(exc))
