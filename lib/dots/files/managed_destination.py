"""Explicit catalog translation for writes below a managed directory link.

This does not authorize arbitrary symlink traversal. The Store always receives
an ordinary physical path, plus guards for the exact catalog and lexical link.
The parent link itself is observed, never adopted by translating a child.
"""
import os
from pathlib import Path

from transactions import digest, exists, parents_safe


def physical(path, records, guards, *, planned=()):
    path = Path(path).absolute()
    matches = [r for r in records if r.get('enabled') and r.get('applicable')
               and r.get('strategy') == 'directory-link' and r.get('target')
               and r.get('status') not in ('conflict', 'replaced', 'source-missing', 'source-broken-link')
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
