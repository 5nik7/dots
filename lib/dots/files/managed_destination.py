"""Explicit catalog translation for writes below a managed directory link.

This does not authorize arbitrary symlink traversal. The Store always receives
an ordinary physical path, plus guards for the exact catalog and lexical link.
The parent link itself is observed, never adopted by translating a child.
"""
import os
from pathlib import Path
import re

from file_platform import native_link_text, open_nofollow
from transactions import Store, digest, exists, parents_safe


def points_to(path, source):
    """Match a link to its lexical endpoint, preserving active-theme indirection."""
    path = Path(path)
    return (path.is_symlink() and
            Path(os.path.abspath(path.parent / native_link_text(os.readlink(path)))) == Path(source))


def yazi_flavor_directory(row):
    return (row.get('repository') == 'theme' and row.get('source_spec') == '${THEME}/yazi'
            and row['strategy'] == 'directory-link' and row.get('target')
            and Path(*Path(row['target']).parts[-2:]) == Path('flavors/dots.yazi'))


def yazi_migration_reason(row, target, entries, guards):
    """A generic replacement cannot fold the old children's installation baselines."""
    if not yazi_flavor_directory(row):
        return None
    endpoints = {Path(row['target']), target}
    if points_to(target, row['source']):
        observed = digest(target)
        if not points_to(target, row['source']):
            raise ValueError('Yazi flavor changed during inspection: ' + str(target))
    elif exists(target) or any(endpoints.intersection(Path(key).parents) for key in entries):
        return ('Preserve the existing Yazi flavor and its installation history. Review the destination and preview '
                'its migration with dots files install --component files --resource ' + row['id'] + ' --dry-run.')
    else:
        observed = None
    if guards.setdefault(str(target), observed) != observed:
        raise ValueError('Yazi flavor changed during inspection: ' + str(target))
    return None


def _setup_published(active, guards):
    """Older POSIX setup retained a staged marker after committing its transaction."""
    from catalog import read_json
    state = active.parents[1]
    receipt_path = state / 'installation.json'
    parents_safe(receipt_path)
    if not receipt_path.is_file():
        return False

    def read_guarded(path):
        parents_safe(path)
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 4 * 1024 * 1024:
            raise ValueError('missing or unsafe theme installation record: ' + str(path))
        before = digest(path) if guards is not None else None
        data = read_json(path)
        if guards is not None and (guards.setdefault(str(path), before) != before or digest(path) != before):
            raise ValueError('theme installation record changed after preview')
        return data

    receipt = read_guarded(receipt_path)
    entries, transactions = receipt.get('entries'), receipt.get('transactions')
    if not isinstance(entries, dict) or not isinstance(transactions, list) or not transactions:
        return False
    entry = entries.get(str(active))
    if not isinstance(entry, dict) or entry.get('id') != 'theme:active' or entry.get('after') != digest(active):
        return False
    last = transactions[-1]
    if not isinstance(last, str) or not re.fullmatch('[0-9a-f]{32}', last):
        return False
    journal = read_guarded(Store(state).root / last / 'journal.json')
    return journal.get('id') == last and journal.get('status') == 'complete'


def published_generation(active, guards=None, *, required=True):
    """Resolve one committed generation through the validated publication pointer."""
    active = Path(active)
    parents_safe(active)
    before = digest(active) if guards is not None else None
    if guards is not None and guards.setdefault(str(active), before) != before:
        raise ValueError('active theme changed after preview')
    if not exists(active) and not required:
        return None
    if not active.is_symlink():
        raise ValueError('active theme has not been published or is not a managed link')
    generation = Path(os.path.abspath(active.parent / native_link_text(os.readlink(active))))
    base = active.parents[1] / 'themes'
    if generation.parent != base / 'generations' or not re.fullmatch(r'g\.[a-zA-Z0-9]+', generation.name):
        raise ValueError('active theme points outside managed generations')
    for marker, expected in ((generation / 'status', 'committed'), (base / 'current', generation.name)):
        parents_safe(marker)
        if marker.is_symlink() or not marker.is_file() or marker.stat().st_size > 256:
            raise ValueError('missing or unsafe theme publication marker: ' + str(marker))
        value = digest(marker) if guards is not None else None
        with os.fdopen(open_nofollow(marker, os.O_RDONLY), 'rb') as stream:
            content = stream.read(257)
        valid = len(content) <= 256 and content.strip() == expected.encode('ascii')
        if marker.name == 'status' and content.strip() == b'staged':
            valid = _setup_published(active, guards)
        if not valid or guards is not None and guards.setdefault(str(marker), value) != value:
            raise ValueError('theme publication changed or is incomplete')
    return generation


def theme_artifact(source, active, guards, *, required=True):
    """Guard the pointer separately from the artifact in the captured generation."""
    active = Path(active)
    suffix = Path(source).relative_to(active)
    from themes.artifact_names import identifier
    identifier(suffix.as_posix())
    generation = published_generation(active, guards, required=required)
    if generation is None:
        return None
    path = generation / suffix
    parents_safe(path)
    if path.is_symlink():
        raise ValueError('generated theme artifact is a symlink: ' + str(path))
    observed = digest(path)
    if guards.setdefault(str(path), observed) != observed or digest(active) != guards[str(active)]:
        raise ValueError('published theme changed after preview')
    if observed is None:
        if required:
            raise ValueError('generated theme artifact is missing: ' + str(path))
        return None
    return path


class GeneratedDirectoryMember(ValueError):
    """The requested destination is owned as part of a generated directory."""


def generated_boundaries(directories):
    """Include both names of a connector inside a catalog-mapped application directory."""
    logical = {Path(r['target']) for r in directories if r.get('repository') == 'theme'}
    if not logical:
        return set()
    endpoints = set(logical)
    for app in directories:
        if app.get('repository') == 'theme':
            continue
        target, source = Path(app['target']), Path(app['source'])
        for path in logical:
            if target in path.parents:
                endpoints.add(source / path.relative_to(target))
    return endpoints


def physical(path, records, guards, *, planned=()):
    path = Path(path).absolute()
    if '..' in path.parts:
        raise ValueError('destination contains path traversal: ' + str(path))
    directories = [r for r in records if r.get('enabled') and r.get('applicable')
                   and r.get('strategy') == 'directory-link' and r.get('target') and r.get('status') != 'replaced']
    boundaries = generated_boundaries(directories)

    def protect_members(destination):
        if boundaries and any(parent in boundaries for parent in destination.parents):
            raise GeneratedDirectoryMember('destination belongs to a generated directory mapping: ' + str(destination))

    protect_members(path)
    matches = [r for r in directories
               if r.get('status') not in ('conflict', 'source-missing', 'source-broken-link')
               and Path(r['target']) in path.parents]
    if not matches:
        parents_safe(path)
        return path
    row = max(matches, key=lambda r: len(Path(r['target']).parts))
    parent, source = Path(row['target']), Path(row['source'])
    parents_safe(parent)
    before = digest(parent)
    if parent.is_symlink():
        if not parent.exists() or parent.resolve() != source:
            raise ValueError('catalog directory link points elsewhere; preserve and review: ' + str(parent))
    elif str(parent) not in planned:
        parents_safe(path)
        return path
    parents_safe(source / 'placeholder')
    if not source.is_dir():
        raise ValueError('catalog directory source is unavailable: ' + str(source))
    guards.setdefault(str(parent), before)
    if guards[str(parent)] != before or digest(parent) != before:
        raise ValueError('catalog directory changed after preview: ' + str(parent))
    target = source / path.relative_to(parent)
    protect_members(target)
    parents_safe(target)
    return target


def catalog_target(root, platform, path, guards):
    """Font/other owner adapter for an existing exact catalog directory link."""
    from catalog import Catalog
    catalog = Catalog(root, platform)
    for source in catalog.input_paths():
        parents_safe(source)
        guards.setdefault(str(source), digest(source))
    return physical(path, catalog.records(), guards)
