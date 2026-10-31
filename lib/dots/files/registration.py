"""Read-only registration candidates for repository sources and existing links."""
import os
from pathlib import Path
import re

from catalog import relative
from transactions import exists, parents_safe
from file_platform import check_object, native_link_text


def within(path, root):
    """Compare path components without repeatedly constructing ancestor Paths."""
    parts, prefix = Path(path).parts, Path(root).parts
    if os.name == 'nt':
        parts = tuple(map(os.path.normcase, parts))
        prefix = tuple(map(os.path.normcase, prefix))
    return parts[:len(prefix)] == prefix


class Registration:
    def __init__(self, manager):
        self.manager = manager
        self.catalog = manager.catalog
        self.records = self.catalog.records()
        self.locations = manager.locations()

    def owner(self, path, repo=None):
        owners = [s for s in self.catalog.sources
                  if within(path, s['root'])]
        if not owners:
            return None
        owner = max(owners, key=lambda s: len(Path(s['root']).parts))
        if (owner['status'] != 'available' or not self.catalog.applicable(owner['platforms'])
                or repo and owner['id'] != repo):
            raise ValueError('source belongs to an unavailable, excluded or different repository')
        rel = path.relative_to(owner['root'])
        if not any(within(rel, relative(r)) for r in owner['roots']):
            raise ValueError('source is outside declared repository roots')
        if not self.manager.allowed(rel):
            raise ValueError('excluded repository source: ' + str(path))
        return owner

    def source(self, path, repo=None, owner=None):
        path = Path(os.path.abspath(os.path.expanduser(str(path))))
        parents_safe(path)
        check_object(path)
        owner = owner or self.owner(path, repo)
        if owner is None:
            raise ValueError('link source is outside eligible repositories')
        state = self.manager.store.state
        if within(path, state) or within(state, path):
            raise ValueError('repository source overlaps the state store')
        for parent in (path, *path.parents):
            if parent == Path(owner['root']):
                break
            if (parent / '.git').exists():
                raise ValueError('source belongs to an undeclared nested repository')
        if path.is_symlink() or not (path.is_file() or path.is_dir()):
            raise ValueError('source must be an existing regular file or directory; source-link chains are unsupported')
        return path, owner

    def reverse(self, source, owner):
        matches = []
        for loc in self.locations:
            base = Path(loc['root']) / loc['source']
            if loc['repository'] != owner['id']:
                continue
            if source == base or loc['kind'] == 'root' and within(source, base):
                suffix = source.relative_to(base)
                if any(suffix.match(pattern) for pattern in loc['exclusions']):
                    continue
                spec = loc['target'].rstrip('/')
                if suffix != Path('.'):
                    spec += '/' + suffix.as_posix()
                matches.append((len(base.parts), spec, loc['platforms']))
        if not matches:
            return None, owner['platforms']
        depth = max(row[0] for row in matches)
        matches = [r for r in matches if r[0] == depth]
        if len({r[1] for r in matches}) != 1:
            return None, owner['platforms']
        return matches[0][1:]

    def candidate(self, value, repo=None, target=None, observed=()):
        from mappings import target_spec
        path = Path(os.path.abspath(os.path.expanduser(str(value))))
        check_object(path)
        if path.is_symlink():
            parents_safe(path)
            if target:
                raise ValueError('--target requires a repository source, not a destination link')
            source = Path(os.path.abspath(path.parent / native_link_text(os.readlink(path))))
            source, owner = self.source(source, repo)
            spec = target_spec(self.catalog, str(path))
            eligibility = self.reverse(source, owner)[1]
        else:
            owner = self.owner(path, repo)
            if owner is None:
                if target:
                    raise ValueError('--target requires a repository source')
                return None
            source, owner = self.source(path, repo, owner)
            existing = [r for r in self.records if r['source'] == str(source)]
            targets = {r['target_spec'] for r in existing if r['target_spec']}
            targets.update(r['target_spec'] for r in observed
                           if r.get('source') == str(source) and r.get('target_spec'))
            inferred, eligibility = self.reverse(source, owner)
            spec = target_spec(self.catalog, target) if target else (
                next(iter(targets)) if len(targets) == 1 else inferred if not targets else None)
        rel = source.relative_to(owner['root']).as_posix()
        local_id = 'file-' + re.sub('[^a-z0-9_-]+', '-', rel.lower()).strip('-')
        identity = owner['id'] + ':' + local_id
        destination = self.catalog.target(spec) if spec else None
        matching = [r for r in self.records if r['source'] == str(source)
                    and (not destination or r['target'] == destination)]
        if len(matching) == 1:
            identity = matching[0]['id']
            eligibility = matching[0]['platforms']
        elif len(matching) > 1:
            raise ValueError('source has ambiguous existing mappings; select an explicit target')
        if self.catalog.registry:
            self.catalog.registry.require_current(identity)
            eligibility = self.catalog.registry.entries.get(identity, eligibility)
        parts = Path(rel).parts
        app = parts[1] if len(parts)>1 and parts[0]=='config' else parts[0]
        app = re.sub('[^a-z0-9_-]+', '-', app.lower()).strip('-') or 'config'
        if not app[0].isalpha():
            app = 'config-' + app
        row = dict(id=identity, source=str(source), target=destination, target_spec=spec,
                   repository=owner['id'], strategy='directory-link' if source.is_dir() else 'link',
                   platforms=eligibility, app=app,
                   category='config' if parts[0] in ('config', 'termux') else 'script',
                   candidate=str(path), path=destination, kind='registration', profile=self.catalog.profile['current'])
        if not destination:
            row.update(status='needs-target', reason='No unique destination; supply --target or choose one interactively.')
        else:
            dest = Path(destination)
            parents_safe(dest)
            if within(source, dest) or within(dest, source):
                raise ValueError('source and target overlap')
            correct = dest.is_symlink() and dest.resolve() == source
            row['status'] = 'register-existing-link' if correct else 'register-and-link'
        if len(matching) == 1 and not matching[0]['enabled']:
            row.update(status='excluded', reason='Mapping is stashed; restore it explicitly.')
        if not self.catalog.applicable(eligibility):
            row.update(status='excluded', reason='Resource is not eligible for the active platform.')
        return row

    def validate_directory(self, source, owner):
        """Inspect directory identities only; never traverse nested links."""
        for other in self.catalog.sources:
            child = Path(other['root'])
            if other['id'] != owner and within(child, source):
                raise ValueError('directory includes another repository')
        if not source.is_dir():
            return
        def failure(error):
            raise error
        for current, directories, files in os.walk(source, followlinks=False, onerror=failure):
            if '.git' in directories or '.git' in files:
                raise ValueError('directory includes Git metadata; select an owned config directory')
            directories[:] = [d for d in directories if not (Path(current)/d).is_symlink()]

    def repository(self, raw, observed=(), repo=None):
        """Group known directory boundaries; retain individual unknown sources."""
        paths = {Path(row['source']) for row in raw if not repo or row['repository'] == repo}
        groups = set()
        for loc in self.locations:
            base = Path(loc['root']) / loc['source']
            if repo and loc['repository'] != repo:
                continue
            if loc['kind'] == 'root':
                # A specific app location owns its root; a broad config root
                # owns individual immediate app directories, never the root itself.
                if Path(loc['source']).name in ('config', 'shells', 'bin'):
                    for path in paths:
                        if within(path, base) and len(path.relative_to(base).parts)>1:
                            groups.add(base / path.relative_to(base).parts[0])
                elif any(within(p, base) for p in paths):
                    groups.add(base)
        groups.update(Path(r['source']) for r in observed if r.get('strategy') == 'directory-link')
        covered = [Path(r['source']) for r in self.records]
        groups = {p for p in groups if p.is_dir() and not p.is_symlink()
                  and not any(within(c, p) for c in covered)}
        groups = {p for p in groups if not any(q != p and within(p, q) for q in groups)}
        paths = {p for p in paths if not any(within(p, g) for g in groups)} | groups
        rows = []
        for path in sorted(paths):
            try:
                row = self.candidate(path, repo, observed=observed)
                if row:
                    rows.append(row)
            except (OSError, ValueError) as error:
                original = next((r for r in raw if within(r['source'], path)), {})
                rows.append(dict(original, source=str(path), candidate=str(path), path=None,
                                 status='excluded', reason=str(error)))
        return rows


def candidates(manager, repo=None):
    resolver = Registration(manager)
    system = manager.system(repo)
    rows = resolver.repository(manager.catalog.discover(enrich=False, tolerate_unavailable=True), system, repo)
    # Prefer a user-side link operand, and import only sources not represented by
    # a repository registration. Never queue both parent and child operations.
    links = [r for r in system if r['status'] == 'register-existing-link']
    result = links + [r for r in rows if not any(r.get('source') == x.get('source') for x in links)]
    for row in system:
        if row['status'] not in ('candidate', 'existing-source'):
            continue
        if any(r.get('source') and (Path(row['source']) == Path(r['source']) or
               r.get('strategy') == 'directory-link' and within(row['source'], r['source']))
               for r in result if r['status'] != 'excluded'):
            continue
        result.append(dict(row, candidate=row['path'], kind='import'))
    return sorted(result, key=lambda r: r['candidate'])
