"""Portable source paths and inheritance for profile-owned file declarations."""
from functools import cached_property
import os
from pathlib import Path, PureWindowsPath
import re
import stat

from file_platform import state_root
from identities import canonical


def path_parts(path):
    parts = path.parts if isinstance(path, Path) else Path(path).parts
    return tuple(map(os.path.normcase, parts)) if os.name == 'nt' else parts


def within(path, root):
    """Compare native path components without allocating every ancestor Path."""
    parts, prefix = path_parts(path), path_parts(root)
    return parts[:len(prefix)] == prefix


def extra_profile_sources(root, sources):
    """Assign deterministic owners to profile trees, even for an inactive distro."""
    from profiles import PLATFORMS, IDENTITY
    paths = {Path(row['path']) for row in sources}
    for platform in PLATFORMS:
        base = root / 'profiles' / platform
        candidates = [(platform, base)]
        if platform in ('linux', 'wsl') and (base / 'distros').is_dir():
            for path in sorted((base / 'distros').iterdir()):
                if IDENTITY.fullmatch(platform + '/' + path.name):
                    # Escape '_' and '.' so distinct valid distro names keep distinct IDs.
                    suffix = path.name.replace('_', '__').replace('.', '_d')
                    candidates.append((platform + '-' + suffix, path))
        for owner, path in candidates:
            local = path.relative_to(root)
            if local in paths or not (path / 'profile.json').is_file():
                continue
            yield dict(id=owner, path=local.as_posix(), platforms=['linux', 'wsl'] if platform == 'linux' else [platform],
                       bundled=True, roots=['config', 'shells', 'scripts', 'bin', 'fonts'])


def augmented_sources(root, declared):
    return [*declared, *extra_profile_sources(root, declared),
            dict(id='theme', virtual=True, platforms=['termux', 'linux', 'wsl', 'windows'], roots=['.'])]


PROTECTED = {'.git', '.dots', '.ssh', '.gnupg'}
SOURCE = re.compile(r'\$\{(DOTS|PROFILE|THEME)\}(?:/(.+))?\Z')


class ProfileFiles:
    """The Catalog's public path helpers and layer-aware flat-format reader/writer."""

    @cached_property
    def state_directory(self):
        return state_root()

    @cached_property
    def theme_root(self):
        return self.state_directory / 'current/theme'

    def profile_owner(self, layer=None):
        layer = layer or self.profile['layers'][-1]
        return self.source_owner(Path(layer['root']))

    @cached_property
    def owner_roots(self):
        roots = [(Path(s['root']), s) for s in self.sources]
        if len({path for path, _ in roots}) != len(roots):
            raise ValueError('source owners share a repository root')
        return sorted(roots, key=lambda pair: len(pair[0].parts), reverse=True)

    @cached_property
    def owner_prefixes(self):
        return [(path_parts(root), owner) for root, owner in self.owner_roots]

    def source_owner(self, path):
        path = path if isinstance(path, Path) else Path(path)
        parts = path_parts(path)
        if not path.is_absolute() or '..' in parts:
            raise ValueError('expected an absolute source without traversal')
        for prefix, owner in self.owner_prefixes:
            if parts[:len(prefix)] == prefix:
                if owner['status'] == 'excluded':
                    raise ValueError('source belongs to an excluded repository: ' + owner['id'])
                return owner
        raise ValueError('source is outside the checkout, profile and active theme')

    def validate_source_boundary(self, path, owner, checked):
        """Check each directory once per layer read. Symlinks require physical ownership checks."""
        root = Path(owner['root'])
        if within(self.state_directory, path) or within(path, self.state_directory):
            raise ValueError('source overlaps managed state: ' + str(path))
        key = (owner['id'], root)
        if key not in checked:
            if root.resolve() != root:
                raise ValueError('source repository root must not traverse a symlink: ' + str(root))
            checked[key] = root
        pending = []
        current = path
        while current != root and (owner['id'], current) not in checked:
            pending.append(current)
            current = current.parent
        for part in reversed(pending):
            try:
                mode = part.lstat().st_mode
            except FileNotFoundError:
                mode = 0
            physical_parent = checked[owner['id'], part.parent]
            physical = part if physical_parent == part.parent else physical_parent / part.name
            linked = stat.S_ISLNK(mode)
            if linked:
                try:
                    physical = part.resolve()
                except RuntimeError as error:
                    raise ValueError('source contains a symlink loop: ' + str(part)) from error
                if physical == part or physical.is_symlink():
                    raise ValueError('source contains a symlink loop: ' + str(part))
            if physical != part:
                if (not within(physical, root) or self.source_owner(physical)['id'] != owner['id']
                        or within(physical, self.state_directory)
                        or any(p.casefold() in PROTECTED for p in physical.relative_to(root).parts)):
                    raise ValueError('source escapes its owning repository: ' + str(part))
            if linked:
                self.validate_source_boundary(physical, owner, checked)
            elif stat.S_ISDIR(mode) and (part / '.git').exists():
                raise ValueError('source belongs to an undeclared nested repository: ' + str(part))
            checked[owner['id'], part] = physical

    def resolve_source(self, spec, layer=None):
        return self.source_location(spec, layer, {})[0]

    def source_location(self, spec, layer, checked):
        if not isinstance(spec, str):
            raise ValueError('source must be a rooted path string')
        match = SOURCE.fullmatch(spec)
        if not match:
            raise ValueError('source must start with ${DOTS}, ${PROFILE} or ${THEME}')
        token, suffix = match.groups()
        if suffix and (any(p in ('', '.', '..') or p.casefold() in PROTECTED for p in suffix.split('/'))
                       or '\\' in suffix or PureWindowsPath(suffix).drive or '${' in suffix
                       or any(ord(c) < 32 or ord(c) == 127 for c in suffix)):
            raise ValueError('invalid relative source path: ' + spec)
        if token == 'THEME':
            from themes.artifact_names import identifier
            identifier(suffix or '')
            path = self.theme_root / suffix
            return path, self.source_owner(path)
        base = self.root if token == 'DOTS' else Path((layer or self.profile['layers'][-1])['root'])
        path = base / (suffix or '.')
        owner = self.source_owner(path)
        owner_root = Path(owner['root'])
        if path == owner_root and (owner['id'] == 'dots' or '.' not in owner.get('roots', [])):
            raise ValueError('source overlaps the entire checkout/profile')
        if os.name == 'nt':
            from file_platform import validate_windows_path
            validate_windows_path(path)
        if not self._names_only:
            self.validate_source_boundary(path, owner, checked)
        return path, owner

    def source_spec(self, path, layer=None):
        path = Path(path)
        owner = self.source_owner(path)
        layer = layer or self.profile['layers'][-1]
        if owner['id'] == 'theme':
            token, base = 'THEME', self.theme_root
        elif path.is_relative_to(Path(layer['root'])):
            token, base = 'PROFILE', Path(layer['root'])
        else:
            token, base = 'DOTS', self.root
        suffix = path.relative_to(base).as_posix()
        return '${' + token + '}' + ('' if suffix == '.' else '/' + suffix)

    def layer_groups(self, layer, *, templates=None):
        """Adapt a single declaration to owner-relative implementation rows."""
        files = layer.get('files', {})
        if isinstance(files, dict):
            return {canonical(owner): list(rows) for owner, rows in files.items()}
        groups = {}
        checked = {}
        for raw in files:
            if not isinstance(raw, dict):
                raise ValueError('profile mapping must be an object')
            spec = raw.get('source')
            path, owner = self.source_location(spec, layer, checked)
            if templates is not None and isinstance(raw.get('id'), str):
                templates[owner['id'], raw['id']] = spec
            row = dict(raw, source=path.relative_to(owner['root']).as_posix())
            groups.setdefault(owner['id'], []).append(row)
        return groups

    def load_layers(self):
        self.effective = {}
        self.source_templates = {}
        self.mapping_layers = {}
        allowed = {s['id'] for s in self.sources if s['status'] != 'excluded'}
        self.parent_mappings = {}
        for layer in self.profile['layers']:
            if layer is self.profile['layers'][-1]:
                self.parent_mappings = {owner: dict(rows) for owner, rows in self.effective.items()}
            flat = isinstance(layer.get('files'), list)
            for owner, rows in self.layer_groups(layer, templates=self.source_templates).items():
                if owner not in allowed:
                    raise ValueError('profile files refers to an unknown or excluded repository')
                if not flat:
                    for name in self.effective.get(owner, {}):
                        self.mapping_layers.pop((owner, name), None)
                        self.source_templates.pop((owner, name), None)
                    self.effective[owner] = {}
                mappings = self.effective.setdefault(owner, {})
                seen = set()
                for row in rows:
                    if not isinstance(row, dict) or not isinstance(row.get('id'), str):
                        raise ValueError('profile mapping requires an id')
                    name = row['id']
                    if name in seen:
                        raise ValueError('duplicate resource ID in profile: ' + owner + ':' + name)
                    seen.add(name)
                    mappings[name] = row
                    self.mapping_layers[owner, name] = layer

    def flat_updates(self, data, documents):
        """Write changed rows into the leaf. Leave inherited siblings inherited."""
        from registry import implementation
        leaf = self.profile['layers'][-1]
        owners = {s['id']: s for s in self.sources}
        changes = {}
        for owner, document in documents.items():
            before = self.effective.get(owner, {})
            after = {r['id']: implementation(r, self.platform) for r in document['resources']}
            for name in before.keys() | after.keys():
                original, edited = before.get(name), after.get(name)
                if original == edited:
                    continue
                if edited is None:
                    # Mask a removed inherited declaration (including a local override).
                    parent = self.parent_mappings.get(owner, {}).get(name)
                    if parent is not None:
                        edited = dict(parent, enabled=False)
                if edited is not None:
                    path = Path(owners[owner]['root']) / edited['source']
                    edited = dict(edited, source=self.source_spec(path, leaf))
                changes[owner, name] = edited
        output = []
        for raw in data.get('files', []):
            owner = self.source_owner(self.resolve_source(raw['source'], leaf))['id']
            key = owner, raw['id']
            row = changes.pop(key, raw)
            if row is not None:
                output.append(row)
        output.extend(row for _, row in sorted(changes.items()) if row is not None)
        data['files'] = output
