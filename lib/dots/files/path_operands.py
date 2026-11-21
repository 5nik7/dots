"""Literal path operands for managed files. No environment or shell evaluation."""
import os
from pathlib import Path
import re

from catalog import relative


class UnknownLocation(ValueError):
    """An input does not belong to a declared destination location."""


class SourceRequired(ValueError):
    """An unmanaged input needs a user-chosen source layout."""


def operand(catalog, value):
    value = str(value)
    if value.startswith('${'):
        if re.match(r'^\$\{(DOTS|PROFILE|THEME)\}(?:/|$)', value):
            return catalog.resolve_source(value)
        destination = catalog.target(value)
        if not destination:
            raise ValueError('destination token is unavailable on this platform')
        return Path(destination)
    return Path(os.path.abspath(os.path.expanduser(value)))


def link_operands(parser, args):
    """Choose ID mode or bind the remaining positional path to its open role."""
    if args.action != 'link':
        return False
    qualified = re.compile(r'[a-z][a-z0-9_-]*:[a-z][a-z0-9_-]*\Z')
    if args.source is None and args.target is None and all(qualified.fullmatch(value) for value in args.values):
        return False
    if args.pick or args.repo:
        parser.error('path linking uses a source and target without --pick or --repo')
    values = iter(args.values)
    source = args.source if args.source is not None else next(values, None)
    target = args.target if args.target is not None else next(values, None)
    if not source or not target or next(values, None) is not None:
        parser.error('link requires exactly one source and one target, or qualified resource IDs')
    args.values = [source]
    args.target = target
    return True


def adoption(resolver, path, args, selected_source=None):
    """Map an unmanaged live file to the selected repository or profile."""
    manager = resolver.manager
    catalog = manager.catalog
    from mappings import target_spec
    try:
        loc, original, destination = manager.mapping(path, args.repo)
    except UnknownLocation as error:
        loc = None
        destination = target_spec(catalog, str(path))
        if not selected_source:
            raise SourceRequired('No known source layout for ' + str(path) + '; supply --source or choose one interactively.') from error
    if args.repo:
        owner = next((row for row in catalog.sources if row['id'] == args.repo and row['status'] == 'available'), None)
        if not owner:
            raise ValueError('unavailable source owner: ' + args.repo)
    elif getattr(args, 'global_files', False):
        owner = next(row for row in catalog.sources if row['id'] == 'dots')
    elif catalog.flat:
        owner = catalog.profile_owner()
    elif loc:
        owner = next(row for row in catalog.sources if row['id'] == loc['repository'])
    else:
        owner = catalog.profile_owner()
    base = Path(owner['root'])
    if selected_source:
        value = str(selected_source)
        source = operand(catalog, value) if value.startswith(('${', '~')) or Path(value).is_absolute() else base / relative(value)
    else:
        source = base / original.relative_to(loc['root'])
    found = resolver.owner(source, owner['id'])
    if not found:
        raise ValueError('import source must be within the selected source root')
    return owner, source, destination, owner['platforms'] if not loc or owner['id'] != loc['repository'] else loc['platforms']
