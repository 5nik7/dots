"""Assign portable resource names without reusing a different mapping's identity."""
from collections import defaultdict
from hashlib import sha256
from pathlib import Path
import re


def slug(value):
    return re.sub('[^a-z0-9_-]+', '-', value.lower()).strip('-')


class RegistrationNames:
    def __init__(self, catalog, records):
        from catalog import Catalog
        from profiles import available
        self.roots = {s['id']: Path(s['root']) for s in catalog.sources}
        self.registry = catalog.registry
        self.reserved = set(self.registry.entries) | set(self.registry.renames) if self.registry else set()
        self.known = defaultdict(set)
        self.active = {r['id']: (Path(r['source']), r['target_spec']) for r in records}
        self.reserved.update(self.active)
        layers = available(catalog.root)
        flat = next((layer for layer in layers if isinstance(layer.get('files'), list)), None)
        reader = (Catalog(catalog.root, catalog.platform, profile=dict(current=flat['id'], layers=[flat]),
                          _names_only=True) if flat else catalog)
        for layer in layers:
            for owner, rows in reader.layer_groups(layer).items():
                for row in rows:
                    identity = owner + ':' + row['id']
                    self.reserved.add(identity)
                    if self.registry and (self.registry.resolve(identity) != identity or
                            identity in self.registry.entries and not catalog.applicable(self.registry.entries[identity])):
                        continue
                    if 'platforms' in row and not catalog.applicable(row['platforms']):
                        continue
                    self.known[owner, row['source'], row.get('target')].add(identity)

    def choose(self, owner, source, target_spec, assigned, *, preferred=None):
        source = Path(source)
        pair = source, target_spec
        relative = source.relative_to(self.roots[owner])
        known = self.known.get((owner, relative.as_posix(), target_spec), set())
        eligible = {name for name in known if self.active.get(name, pair) == pair}
        exact = next(iter(eligible)) if len(eligible) == 1 else None

        def free(identity):
            return (identity not in self.reserved or identity == exact
                    or self.active.get(identity) == pair) and assigned.get(identity, pair) == pair

        if preferred:
            if not free(preferred):
                raise ValueError('resource ID already belongs to another mapping: ' + preferred)
            return preferred
        if exact and free(exact):
            return exact
        parts = relative.parts or (source.name,)
        for depth in range(1, len(parts) + 1):
            name = slug('/'.join(parts[-depth:])) or 'file'
            if not name[0].isalpha():
                name = 'file-' + name
            identity = owner + ':' + name
            if free(identity):
                return identity
        # Multiple targets for one source, or names that normalize identically.
        identity += '-at-' + (slug(target_spec or '') or 'target')
        if free(identity):
            return identity
        key = relative.as_posix() + '\0' + (target_spec or '')
        identity += '-' + sha256(key.encode()).hexdigest()[:12]
        alternative = identity
        index = 2
        while not free(alternative):
            alternative = identity + '-' + str(index)
            index += 1
        return alternative
