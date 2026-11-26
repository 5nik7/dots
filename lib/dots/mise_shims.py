"""Resolve the shim path from global mise settings for shell environment preparation."""
import os
from pathlib import Path
import re


ENV_KEYS = ('MISE_SHIMS_DIR', 'MISE_DATA_DIR', 'MISE_GLOBAL_CONFIG_FILE',
            'MISE_CONFIG_DIR', 'MISE_ENV', 'XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'HOME',
            'USERPROFILE', 'LOCALAPPDATA', 'APPDATA')


def startup_context(root, profile, scalars):
    """Mirror inherited/default values and accept either on same-shell reload."""
    from environment import declarations, TOKEN
    context = dict(os.environ, DOTS=str(root))
    context.update(scalars)
    context.setdefault('HOME', context.get('USERPROFILE') or str(Path.home()))
    for key, (template, _) in declarations(root, profile).items():
        if not context.get(key):
            context[key] = TOKEN.sub(lambda match: context.get(match[1], ''), template)
    guard = {key: tuple(dict.fromkeys((os.environ.get(key, ''), context.get(key, ''))))
             for key in ENV_KEYS}
    return context, guard


def literal(value, home):
    if not isinstance(value, str) or not value or any(c in value for c in ('\0', '\n', '\r', os.pathsep)):
        return None
    if value == '~' or value.startswith(('~/', '~\\')):
        path = home / value[2:]
    else:
        path = Path(value)
    return path if path.is_absolute() else None


def resolve(env, windows, inputs=None):
    home = Path((env.get('USERPROFILE') if windows else env.get('HOME')) or env.get('HOME') or Path.home())
    if env.get('MISE_SHIMS_DIR'):
        return literal(env['MISE_SHIMS_DIR'], home)
    config_home = env.get('XDG_CONFIG_HOME') or (env.get('APPDATA') if windows else None) or home / '.config'
    directory = Path(env.get('MISE_CONFIG_DIR') or Path(config_home) / 'mise')
    config = literal(env.get('MISE_GLOBAL_CONFIG_FILE') or str(directory / 'config.toml'), home)
    if config:
        try:
            configured = global_setting(config, env, inputs)
            if configured is not None:
                return literal(configured, home)
        except (OSError, ValueError):
            pass
    data_home = env.get('XDG_DATA_HOME') or (env.get('LOCALAPPDATA') if windows else None)
    if not data_home:
        data_home = home / ('AppData/Local' if windows else '.local/share')
    data = literal(env.get('MISE_DATA_DIR') or str(Path(data_home) / 'mise'), home)
    return data / 'shims' if data else None


def global_setting(config, env, inputs):
    directory = config.parent
    candidates = [config]
    watches = []
    if not env.get('MISE_GLOBAL_CONFIG_FILE'):
        fragments = directory / 'conf.d'
        watches.extend((directory, fragments))
        entries = sorted(p for p in fragments.iterdir() if not p.name.startswith('.')) if fragments.is_dir() else []
        folders = [p for p in entries if p.is_dir()]
        watches.extend(folders)
        candidates = [p for p in entries if p.is_file() and p.suffix == '.toml']
        environments = [name for name in env.get('MISE_ENV', '').split(',')
                        if re.fullmatch(r'[a-zA-Z0-9_-]+', name)]
        variants = [''] + ['.' + name for name in environments]
        for suffix in ('', '.local'):
            for variant in variants:
                ending = variant + suffix + '.toml'
                candidates.extend(folder / ('mise' + ending) for folder in folders)
                candidates.extend(directory / (stem + ending) for stem in ('config', 'mise'))
        candidates.extend(directory / ('config' + v + '.override.toml') for v in variants)
    files = [path for path in candidates if path.is_file()]
    if inputs is not None:
        # Directory metadata catches new and removed entries. A symlink and
        # its target are separate inputs for the native shell stat guards.
        for path in dict.fromkeys(watches + ([config] if not watches else []) + files):
            inputs.append(path)
            if path.exists() and path.resolve() != path:
                inputs.append(path.resolve())
    if not files:
        return None
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            try:
                from pip._vendor import tomli as tomllib
            except ImportError:
                return None
    for path in reversed(files):
        try:
            with path.open('rb') as stream:
                settings = tomllib.load(stream).get('settings', {})
            if isinstance(settings, dict) and settings.get('shims_dir'):
                return settings['shims_dir']
        except (OSError, ValueError):
            continue
    return None
