"""Application and type views over existing Config owners. Nothing is stored here."""
from collections import defaultdict
from functools import cached_property
import json
import os
from pathlib import Path
import re

from config_keys import canonical
from config_values import name, parts

TYPES = ('colors', 'icons', 'formatting', 'settings', 'env', 'files')
RESERVED = {*TYPES, 'apps', 'environment', 'profile'}
# Native adapters retain their own field names. Only their presentation group changes.
NATIVE_GROUPS = {
    ('nvim', 'highlights'): 'colors', ('nvim', 'icon_styles'): 'colors',
    ('wttr', 'icon_colors'): 'colors', ('wttr', 'night_icon_colors'): 'colors',
    ('wttr', 'widget_color'): 'colors', ('wttr', 'night_icons'): 'icons',
}
ENV_TO_APP = {'GOBIN': 'go', 'GOPATH': 'go', 'GOROOT': 'go', 'LESS': 'less',
              'LESS_TERMCAP_so': 'less', 'LESS_TERMCAP_se': 'less',
              '_PREVIEW_': 'fzf', 'ZSHCOMP': 'zsh'}
ENVIRONMENT_APPS = frozenset(ENV_TO_APP.values()) | {'bat', 'cargo', 'systemd'}
# These shipped mappings formerly used the generic application name "config".
TERMUX_CONFIG_FILE_APPS = {
    'termux:config-json': 'pkgs', 'termux:config': 'codex-termux',
    'termux:config-toml': 'mise', 'termux:method': 'zsh-system-clipboard',
}


def environment_rows(root, selected, *, runtime=False):
    """Use profile templates and only the environment inspector's registered exports."""
    from environment import declarations
    from profiles import public_report
    from profile_environment import APPLICATIONS
    from profile_config import context
    declared = declarations(root, selected)
    safe = public_report({'environment': {k: v for k, (v, _) in declared.items()}})['environment']
    rows = {k: (safe[k], source) for k, (_, source) in declared.items()}
    if selected['current'] == context(root)['current']:
        observed = (set(APPLICATIONS['observed']) & os.environ.keys()) - rows.keys()
        if runtime and observed:
            from environment import inspect
            reported = inspect(root)['values']
            rows.update({k: (reported[k]['value'], 'runtime: ' + reported[k]['source'])
                         for k in observed if k in reported})
        else:
            rows.update({k: (None, 'runtime') for k in observed})
    return rows


def env_app(variable):
    """A named environment declaration can have one discoverable application view."""
    if variable in ENV_TO_APP:
        return ENV_TO_APP[variable]
    prefix, sep, _ = variable.strip('_').partition('_')
    return prefix.lower() if sep else None


def split(key):
    # Profile file IDs use an owner:ID literal which is not a dotted Config key.
    if re.fullmatch(r'files\.[a-z][a-z0-9_-]*:[a-zA-Z0-9_.-]+', key):
        return ('files', key[6:])
    return parts(key)


def app_field(key):
    """Return (app, type, relative path) for a physical or legacy public key."""
    path = split(canonical(key))
    if len(path) >= 3 and path[1] == 'apps' and path[0] in TYPES:
        return path[2], path[0], path[3:]
    if len(path) >= 3 and path[0] == 'apps':
        app, field = path[1:3]
        if field in ('colors', 'icons', 'formatting', 'settings'):
            return app, field, path[3:]
        return app, NATIVE_GROUPS.get((app, field), 'settings'), path[2:]
    if len(path) == 2 and path[0] == 'environment':
        app = env_app(path[1])
        if app:
            return app, 'env', path[1:]
    return None


def paths(app, kind, tail):
    yield name(('apps', app, kind, *tail))
    if app not in RESERVED:
        yield name((app, kind, *tail))
    yield name((kind, app, *tail))
    yield name((kind, 'apps', app, *tail))


def field_path(path):
    """Parse either orientation. Callers decide whether the named app exists."""
    first, *rest = path
    if first in TYPES:
        if rest[:1] == ['apps']:
            rest = rest[1:]
        return (rest[0], first, tuple(rest[1:])) if rest else None
    if first == 'apps':
        if not rest:
            return None
        app, *rest = rest
    elif first not in RESERVED:
        app = first
    else:
        return None
    return (app, rest[0], tuple(rest[1:])) if rest and rest[0] in TYPES else (app, None, tuple(rest))


def direct_owner(key):
    """Resolve a preference leaf from its spelling and its consumer's vocabulary.

    Composite app and type roots, environment declarations and file identities
    need their own layer data. They return None here.
    """
    if key and key.startswith('settings.DOTS_'):
        return key[9:]
    if not key or key.startswith(('DOTS_', 'profile.')) or key == 'settings.files.backup':
        return key
    key = canonical(key)
    try:
        path = split(key)
    except ValueError:
        return None
    field = field_path(path)
    if not field:
        return None
    app, kind, tail = field
    if not tail or kind in ('env', 'files') or path[0] == 'environment':
        return None
    if kind in (None, 'settings'):
        return canonical(name(('apps', app, *tail)))
    if kind == 'formatting':
        return canonical(name((kind, 'apps', app, *tail)))
    if NATIVE_GROUPS.get((app, tail[0])) == kind:
        return name(('apps', app, *tail))
    if ((kind == 'icons' and app in ('nvim', 'wttr')) or
            (kind == 'colors' and app == 'fzf' and tail[0] not in ('ui', 'status'))):
        return name(('apps', app, kind, *tail))
    from style_catalog import APPS, icon_roles, canonical as icon_role
    from config_keys import FEATURES
    if kind == 'icons':
        role = icon_role(name((app, *tail)))
        if role in icon_roles() or any(k.startswith(role + '.') for k in icon_roles()):
            return kind + '.' + role
    if path[0] == kind and path[1] != 'apps' and app not in (*APPS, *FEATURES):
        return key  # shared role such as colors.ui.accent.fg
    return canonical(name((kind, 'apps', app, *tail)))


def needs_namespace(key, action):
    if not key or action not in ('get', 'path', 'explain', 'set', 'unset'):
        return False
    try:
        path = split(key)
    except ValueError:
        return False
    first = path[0]
    if first == 'environment':
        return True
    if first == 'profile' or first.startswith('DOTS_'):
        return False
    if action == 'path' and first not in RESERVED and len(path) > 1 and path[-1] in ('toml','json','conf'):
        return False
    if first == 'apps':
        if len(path) > 3 and path[1:3] == ('fzf', 'colors') and path[3] not in ('ui','status'):
            return False
        return len(path) == 2 or len(path) > 2 and path[2] in TYPES
    if first in ('colors', 'icons', 'formatting') and len(path) >= 2 and path[1] == 'apps':
        if len(path) > 3 and path[2] in ('nvim','wttr') and (
                first == 'icons' or NATIVE_GROUPS.get((path[2],path[3])) == first):
            return True
        return len(path) == 3
    if first in ('colors','icons') and len(path) > 2:
        # Shared roles and preexisting aliases retain their current scope.
        if canonical(key) != key:
            return False
        from style_catalog import supported
        if supported(first, key.split('.',1)[1]):
            return False
    if first == 'settings' and (len(path) == 1 or path[1].startswith('DOTS_') or key == 'settings.files.backup'):
        return False
    return first not in RESERVED or len(path) > 1 or first == 'env'


class Namespace:
    def __init__(self, keys, *, files=(), environment=()):
        self.owners = set(keys)
        self.files = dict(files)
        self.environment = dict(environment)
        self.owners.update('environment.' + key for key in self.environment)
        self.owners.update('files.' + identity for identity in self.files)
        self.apps = set()
        self.fields = defaultdict(dict)
        environment_fields = []
        for key in sorted(self.owners):
            field = app_field(key)
            if key.startswith('files.') and key[6:] in self.files:
                app = self.files[key[6:]].get('app')
                if app:
                    field = (app, 'files', (key[6:],))
            if field:
                app, kind, tail = field
                if kind == 'env':
                    environment_fields.append((app, tail, key))
                else:
                    self.apps.add(app)
                    # A declared native map can have no children yet.
                    if tail or key == name(('apps', app, kind)):
                        self.fields[app, kind][tail] = key
        for identity, app in TERMUX_CONFIG_FILE_APPS.items():
            if self.files.get(identity, {}).get('app') == app:
                self.apps.add('config')
                self.fields['config', 'files'][(identity,)] = 'files.' + identity
        # An arbitrary profile environment variable cannot create an application.
        # Include tools with backend-owned exports but no separate Config controls.
        environment_apps = self.apps | ENVIRONMENT_APPS
        for app, tail, key in environment_fields:
            if app in environment_apps:
                self.apps.add(app)
                self.fields[app, 'env'][tail] = key
        # Shared icon vocabularies (e.g. icons.git) are also reachable from the
        # named application's icon view. Keep their actual shared edit scope.
        for key in sorted(self.owners):
            if key.startswith('icons.') and not key.startswith('icons.apps.'):
                path = parts(key)
                if len(path) > 2 and path[1] in self.apps:
                    self.fields[path[1], 'icons'].setdefault(path[2:], key)

    @classmethod
    def load(cls, root, selected, *, defaults=False, structural=True, runtime=False, app=None):
        from profile_config import keys, file_rows
        rows = ()
        environment = {}
        if structural and not defaults:
            rows = list(file_rows(root, selected))
            environment = environment_rows(root, selected, runtime=runtime)
        owners = keys(root, selected['current'], defaults=defaults, app=app)
        if app is not None:
            # A type-first spelling can also be a real shared key, such as
            # icons.git.branch or settings.files.backup.
            roots = (name(('apps', app)), *(name((kind, app)) for kind in TYPES),
                     *(name((kind, 'apps', app)) for kind in TYPES))
            prefixes = tuple(prefix + sep for prefix in roots for sep in ('.', '['))
            owners = [key for key in owners if key in roots or key.startswith(prefixes)]
        result = cls(owners,
                     files=((identity,row) for identity,_,row in rows), environment=environment)
        result.file_sources = {identity: str(Path(layer['root'])/'profile.json') for identity,layer,_ in rows}
        return result

    def parse(self, key):
        field = field_path(split(key))
        return field if field and field[0] in self.apps else None

    def owner(self, key):
        if key == 'env':
            return 'environment'
        if key.startswith('env.') and (key[4:] in self.environment or re.fullmatch('[A-Z][A-Z0-9_]*', key[4:])):
            return 'environment.' + key[4:]
        if key in self.owners:
            return key
        direct = direct_owner(key)
        if direct in self.owners:
            return direct
        field = self.parse(key)
        if field is None:
            return key
        app, kind, tail = field
        if kind is None:
            return name(('apps', app, *tail))
        if tail in self.fields[app, kind]:
            return self.fields[app, kind][tail]
        # Preserve dynamic native maps and the ability to add a profile export.
        if kind == 'env' and len(tail) == 1 and env_app(tail[0]) == app:
            return 'environment.' + tail[0]
        if kind == 'settings':
            return name(('apps', app, *tail))
        if kind == 'icons' and app in ('nvim', 'wttr'):
            return name(('apps', app, 'icons', *tail))
        if kind in ('colors', 'icons', 'formatting'):
            for native, group in NATIVE_GROUPS.items():
                if native[0] == app and group == kind and tail[:1] == native[1:]:
                    return name(('apps', app, *tail))
            return name((kind, 'apps', app, *tail))
        return key

    @cached_property
    def forms(self):
        forms = {'env.' + key: 'environment.' + key for key in self.environment}
        for (app, kind), entries in self.fields.items():
            for tail, owner in entries.items():
                for spelling in paths(app, kind, tail):
                    forms.setdefault(spelling, owner)
                if owner.startswith('apps.' + app + '.') and app not in RESERVED:
                    forms.setdefault(owner[5:], owner)
        return forms

    def default_app_root(self, app):
        return any(key.startswith('apps.' + app + '.') for key in self.owners)

    def view_key(self, owner, group):
        """A single display path for the selected category."""
        if group not in (*TYPES, 'apps'):
            return owner
        if group == 'apps' and owner.startswith('files.'):
            app = self.files.get(owner[6:], {}).get('app')
            if app:
                return name(('apps', app, 'files', owner[6:]))
        for app, kind, tail in self.locations.get(owner, ()):
            if group == 'apps':
                return name(('apps', app, kind, *tail))
            if group == kind:
                # Preserve established type-first labels in the category.
                return owner if owner.startswith(kind + '.') else name((kind, 'apps', app, *tail))
        return owner

    def query_key(self, owner, query):
        """Keep a user's app- or type-first spelling visible and searchable."""
        head, _, rest = query.partition('.')
        second = rest.split('.',1)[0].split('[',1)[0]
        third = rest.partition('.')[2].split('.', 1)[0].split('[', 1)[0]
        for app, kind, tail in self.locations.get(owner, ()):
            if head == app and app not in RESERVED:
                return name((app, kind, *tail))
            if head == 'apps' and second == app:
                return name(('apps', app, kind, *tail))
            if head == kind and second == app:
                return name((kind, app, *tail))
            if head == kind and second == 'apps' and app.startswith(third):
                return name((kind, 'apps', app, *tail))
        return owner

    @cached_property
    def locations(self):
        result = defaultdict(list)
        for (app, kind), fields in self.fields.items():
            for tail, owner in fields.items():
                result[owner].append((app, kind, tail))
        return result

    def group_edit_owner(self, app, kind, payload=None):
        """Bulk edits must map verbatim to one existing editor and its scope."""
        from config_keys import internal
        from config_values import leaves

        if kind in ('env','files'):
            raise ValueError('choose an individual environment variable or edit a mapping with dots files edit')
        if payload is not None and not isinstance(payload, dict):
            raise ValueError('a group edit requires a JSON object')
        tails = [tail for tail, _ in leaves(payload) if tail] if payload else []
        roots = set()
        for tail in tails:
            physical = parts(internal(self.owner(name(('apps', app, kind, *tail)))))
            if physical[-len(tail):] != tail:
                raise ValueError('group fields have distinct configuration owners; edit each field individually')
            roots.add(physical[:-len(tail)])
        if len(roots) > 1:
            raise ValueError('group fields have distinct configuration owners; edit each field individually')
        if roots:
            root = roots.pop()
        elif (app, kind) in (('fzf','colors'), ('nvim','icons'), ('wttr','icons')):
            # The app's existing native map remains the bulk reset target.
            root = ('apps', app, kind)
        elif kind in ('colors', 'icons', 'formatting'):
            root = (kind, 'apps', app)
        else:
            root = ('apps', app)
        if root == ('apps', app):
            if kind != 'settings' or any(key.startswith('apps.'+app+'.') and field != kind
                    for (candidate, field), entries in self.fields.items() if candidate == app
                    for key in entries.values()):
                raise ValueError('group fields have distinct configuration owners; edit each field individually')
        return name(root)

    def read_group(self, app, kind, root, selected, defaults=False):
        """Resolve each leaf through its real consumer, reusing readers within this view."""
        from config_values import Controls
        from config_keys import internal
        from style_config import Styles
        from importlib import import_module

        if kind == 'files':
            if defaults:
                raise ValueError('file mappings belong to a profile')
            fields = self.fields.get((app, kind), {})
            return [row for identity, row in self.files.items() if (identity,) in fields]
        if kind == 'env':
            if defaults:
                raise ValueError('environment declarations belong to a profile')
            environment = self.environment
            if any(source == 'runtime' for value, source in environment.values()):
                environment = environment_rows(root, selected, runtime=True)
            return {key: value for key, (value, _) in environment.items() if env_app(key) == app}
        entries = self.fields.get((app, kind), {})
        if not entries:
            raise ValueError('unknown configuration group: ' + name(('apps', app, kind)))
        # Discovery includes branches for style records. Resolve only leaves so
        # fieldwise inheritance and literal map entries have one owner each.
        parents = {tail[:length] for tail in entries for length in range(1, len(tail))}
        controls = styles = native = None
        result = {}
        for tail, key in entries.items():
            if not tail or tail in parents:
                continue
            physical = internal(key)
            first, _, rest = physical.partition('.')
            if first in ('icons', 'colors'):
                if styles is None:
                    styles = Styles(root, selected, defaults=defaults)
                value = styles.resolve(first, rest)['value']
            elif app in ('pkgs', 'wttr', 'codex') and first == 'apps':
                if native is None:
                    native = import_module('config_' + app).Native(root, selected)
                value = native.resolve(physical)['value']
            else:
                if controls is None:
                    controls = Controls(root, selected, defaults=defaults)
                value = controls.resolve(physical)['value']
            node = result
            for piece in tail[:-1]:
                node = node.setdefault(piece, {})
            node[tail[-1]] = value
        return result


def resolve_request(root, selected, key, action, *, defaults=False, value=None):
    """Return the owner key, plus an inspection record for composite/structural reads."""
    if action != 'path' or '.' in key and not key.endswith(('.json', '.toml', '.conf')):
        direct = direct_owner(key)
        if direct is not None:
            return direct, None
    if not needs_namespace(key, action):
        return key, None
    path = split(key)
    field = field_path(path)
    kind = field[1] if field else None
    env_query = path[0] in ('env', 'environment') or kind == 'env'
    structural = env_query or kind == 'files' or kind is None and len(path) <= 2
    if path[0] == 'files' and len(path) == 2 and ':' in path[1]:
        return key, None
    if field and field[1] == 'files' and field[2]:
        from profile_config import file_rows
        rows = [] if defaults else list(file_rows(root, selected))
        namespace = Namespace((), files=((ident, row) for ident, _, row in rows))
        namespace.file_sources = {ident: str(Path(layer['root'])/'profile.json') for ident, layer, _ in rows}
    elif key == 'environment' or key.startswith('environment.') or re.fullmatch(r'env\.[A-Z_][A-Za-z0-9_]*', key) or (
            field and field[1] == 'env' and field[2] and field[0] in ENVIRONMENT_APPS):
        namespace = Namespace((), environment={} if defaults else environment_rows(root, selected, runtime=env_query and action in ('get', 'explain')))
    else:
        namespace = Namespace.load(root, selected, defaults=defaults, structural=structural, runtime=env_query,
                                   app=field[0] if field else None)
    field = namespace.parse(key)
    owner = namespace.owner(key)
    report = dict(schema=1, profile='defaults' if defaults else selected['current'])
    inspecting = action in ('get','explain')
    if field:
        app, kind, tail = field
        if kind is None and not tail and inspecting and not namespace.default_app_root(app):
            value = {group: namespace.read_group(app, group, root, selected, defaults)
                     for candidate, group in namespace.fields if candidate == app}
            return 'apps.'+app, dict(report, value=value)
        # Preserve files.OWNER even when an application shares that owner name.
        file_owner = kind == 'files' and key.startswith('files.') and (
            key in namespace.owners or any(key == 'files.' + identity.split(':',1)[0] for identity in namespace.files))
        if kind and not tail and not file_owner:
            if inspecting:
                value = namespace.read_group(app, kind, root, selected, defaults)
                if action == 'explain':
                    report['owners'] = sorted(set(namespace.fields.get((app,kind), {}).values()))
                    report['constraints'] = dict(type='array' if isinstance(value, list) else 'object')
                return name(('apps', app, kind)), dict(report, value=value)
            if action in ('set','unset'):
                return namespace.group_edit_owner(app, kind, json.loads(value) if value is not None else None), None
        if kind == 'files' and tail and not file_owner:
            identity = tail[0]
            mapping = namespace.files.get(identity) if len(tail) == 1 else None
            if mapping is None or tail not in namespace.fields.get((app, 'files'), {}):
                raise ValueError('unknown application file mapping')
            if not inspecting:
                raise ValueError('edit this mapping with dots files edit '+identity)
            report['path'] = namespace.file_sources[identity]
            if action == 'explain':
                report['source'] = report['path']
            return 'files.'+identity, dict(report, value=mapping)
    if owner != 'environment' and not owner.startswith('environment.'):
        return owner, None
    if defaults:
        raise ValueError('environment declarations belong to a profile')
    variable = owner.partition('.')[2]
    if not inspecting:
        if not variable:
            raise ValueError('choose an individual environment variable to edit')
        if namespace.environment.get(variable, ('',''))[1].startswith('runtime') and action in ('set','unset'):
            raise ValueError('runtime environment inspection is read-only')
        return owner, None
    report['path'] = str(Path(selected['layers'][-1]['root'])/'profile.json')
    if not variable:
        return owner, dict(report, value={key: pair[0] for key,pair in namespace.environment.items()})
    if variable not in namespace.environment:
        raise ValueError('unknown environment declaration')
    value, source = namespace.environment[variable]
    if action == 'explain':
        report['source'] = source
    return owner, dict(report, value=value)
