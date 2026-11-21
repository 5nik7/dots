"""Bounded discovery and review of existing links into managed sources."""
from pathlib import Path
import sys

from file_platform import check_object
from interaction import gum_confirm
from managed_destination import GeneratedDirectoryMember, physical, points_to
from path_operands import operand
from registration import Registration, within
from transactions import digest, exists, parents_safe


def default_roots(resolver):
    catalog = resolver.catalog
    roots = {}
    def include(path, recursive):
        roots[path] = recursive or roots.get(path, False)
    for loc in resolver.locations:
        include(Path(loc['path']), loc['kind'] == 'root')
    if catalog.flat:
        for row in resolver.records:
            if not (row['enabled'] and row['applicable'] and row.get('target')) or row['status'] == 'replaced':
                continue
            path = Path(row['target'])
            if row['strategy'] == 'directory-link':
                include(path, True)
            elif row['target_spec'].startswith('${APP_CONFIG:') and '}/' in row['target_spec']:
                include(path.parent, True)
            else:
                include(path, False)
        # These application roots can be external to XDG and have no file-
        # adoption registry. Limit discovery to their theme directories.
        for app in ('codex', 'pi'):
            try:
                path = catalog.target('${APP_CONFIG:' + app + '}/themes')
            except (OSError, ValueError):
                continue
            if path:
                include(Path(path), True)
    home = Path(catalog.target('${HOME}'))
    return [(root, roots[root]) for root in sorted(roots) if not within(home, root)]


def discover(manager, roots):
    resolver = Registration(manager)
    locations = resolver.locations
    explicit = bool(roots)
    starts = [(operand(manager.catalog, root), True) for root in roots] if explicit else default_roots(resolver)
    rows, seen = [], set()
    claims = {}
    for row in resolver.records:
        if row.get('target'):
            target = Path(row['target'])
            claims.setdefault(target, []).append(row)
    theme = getattr(manager.catalog, 'theme_root', None)
    for start, recursive in starts:
        if explicit and not exists(start):
            raise ValueError('search path does not exist: ' + str(start))
        if not exists(start):
            continue
        # Only an exact catalog directory-link may be crossed, including when
        # the caller starts directly at a child inside that directory.
        try:
            initial = physical(start, resolver.records, resolver.guards)
        except GeneratedDirectoryMember:
            continue
        except (OSError, ValueError):
            if explicit:
                raise
            continue
        pending = [(start, initial, start != initial)]
        while pending:
            logical, actual, in_directory_mapping = pending.pop()
            if logical in seen:
                continue
            seen.add(logical)
            if within(actual, manager.store.state) or not manager.allowed(logical):
                continue
            scopes = [loc for loc in locations if within(logical, loc['path'])]
            if scopes:
                loc = max(scopes, key=lambda row: len(Path(row['path']).parts))
                suffix = logical.relative_to(loc['path'])
                if any(suffix.match(pattern) for pattern in loc['exclusions']):
                    continue
            try:
                check_object(actual)
                claimed = claims.get(logical, [])
                if actual.is_symlink():
                    matched = [r for r in claimed if points_to(actual, r['source'])]
                    if matched:
                        # A verified app directory can contain separately declared
                        # theme links; other links/ordinary children are covered.
                        directory = next((r for r in matched if r['strategy'] == 'directory-link'
                            and r['enabled'] and r['applicable'] and r['status'] == 'linked'
                            and r['repository'] != 'theme'), None)
                        if recursive and directory and not in_directory_mapping:
                            source = Path(directory['source'])
                            parents_safe(source / 'placeholder')
                            resolver.guards[str(actual)] = digest(actual)
                            pending.extend((logical / child.name, child, True)
                                           for child in sorted(source.iterdir(), reverse=True))
                        continue
                    row = resolver.candidate(logical)
                    if not row or row['status'] != 'register-existing-link':
                        continue
                    if in_directory_mapping and not (theme and within(row['source'], theme)):
                        continue
                    if row['strategy'] == 'directory-link':
                        claimed = [*claimed, *(r for path, rows in claims.items() if logical in path.parents
                                               for r in rows if r['enabled'] and r['applicable'])]
                    if claimed:
                        ids = ', '.join(sorted(r['id'] for r in claimed))
                        row.update(status='conflict', reason='Destination overlaps existing mappings: ' + ids)
                    rows.append(row)
                elif recursive and actual.is_dir() and (in_directory_mapping or not within(actual, manager.root)):
                    # A generated directory owns all its members, including in
                    # an old installation that still has individual file links.
                    if any(r['repository'] == 'theme' and r['strategy'] == 'directory-link'
                           and r['applicable'] and r['enabled'] and r['status'] != 'replaced' for r in claimed):
                        continue
                    pending.extend((logical / child.name, child, in_directory_mapping)
                                   for child in sorted(actual.iterdir(), reverse=True))
            except (OSError, ValueError):
                # Non-Dots links, broken links, inaccessible paths and unsupported
                # objects never become registration proposals.
                continue
    resolver.assign_ids([row for row in rows if row['status'] == 'register-existing-link'])
    return sorted(rows, key=lambda row: row['target']), resolver.guards


def review(rows, yes, json_mode):
    ready = [row for row in rows if row['status'] == 'register-existing-link']
    if yes or not ready:
        return ready
    if not sys.stdin.isatty():
        raise ValueError('use --dry-run or --json to inspect, or --yes to add discovered links without a terminal')
    from catalog import Presentation
    ui = Presentation(sys.stderr)
    accepted = []
    for row in ready:
        ui.resource_detail('Source', row['source'])
        ui.resource_detail('Target', row['target'])
        decision = None if json_mode else gum_confirm('Add this existing link to the profile?')
        if decision is None:
            print('Add this link? [y/N] ', file=sys.stderr, end='', flush=True)
            decision = input().strip().lower() in ('y', 'yes')
        if decision:
            accepted.append(row)
    return accepted
